# -*- coding: utf-8 -*-
import sys
import socket
from socket import error as socket_error
import time
import re
from data_import import read_utterance
from data_import import read_utterance_normal

hosts = read_utterance_normal("../network/commu_data.csv")

def openmes(path):
    with open(path_command, mode='r') as f:
        first_line = f.readline()
        com = first_line[:-1].split(';')  # コミューの番号、命令の内容
    return com

if __name__ == '__main__':
    clients = []

    for clientdata in hosts:
        host = clientdata["host"]
        port = clientdata["port"]
        try:
            for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
                af, socktype, proto, canonname, sa = res
                try:
                    sock = socket.socket(af, socktype, proto)
                    clients.append(sock)
                except OSError as msg:
                    sock = None
                    continue
                try:
                    sock.connect(sa)
                except OSError as msg:
                    sock.close()
                    sock = None
                    continue
                break

        except socket_error as serr:
            print("Connection:" + str(host) + ":" + str(port) + " refused.")
            sys.exit()

    for c in clients:
        print(c)

    with open(path_command, mode='r') as f:
        first_line = f.readline()
    com = first_line[:-1].split(';')  # コミューの番号、命令の内容

    while(True):
        time.sleep(0.01)
        path_command = '../tempdata/commands_to_be_sent.txt'

        # print(com)
        if len(com) >= 2:
            print(re.sub(r'\D', '', com[0]))
            which_commu = int(re.sub(r'\D', '', com[0]))
            client = clients[which_commu]
            host = hosts[which_commu]["host"]
            command = com[1] + "\n"
            print("SEND To: "+host+" command: " + str(com))
            print("sent is " + command)
            client.send(command.encode('utf-8'))

            if len(com) >= 3:
                print("sleep: " + com[2])
                sleeplen = float(com[2])
                t = threading.Timer(sleeplen, openmes, args=[path_command])
                t.start()
                # time.sleep(sleeplen)
            else:
                print("com naive")
                with open(path_command, mode='r') as f:
                    first_line = f.readline()

            com = first_line[:-1].split(';')  # コミューの番号、命令の内容

            with open(path_command, "r+") as f:  # 一行目消去
                new_f = f.readlines()
                f.seek(0)
                ln = 0

                for line in new_f:
                    if ln > 0:
                        f.write(line)
                    ln += 1
                f.truncate()

