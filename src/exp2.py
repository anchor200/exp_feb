import sys
import time
import socket
import csv
from data_import import read_utterance
import threading
import random
import datetime
from collections import deque
from collections import OrderedDict
import re
import glob
import os
from pykakasi import kakasi

class DialogManager:
    def __init__(self, host, port, TOPIC="Allmighty", PARTICIPANTS = 4):
        self.PARTICIPANTS = PARTICIPANTS
        self.TOPIC = TOPIC
        self.DEFAULT_PACE = 6
        self.ID = "Z"

        self.variables_prepare()
        self.constatns_prepare()
        self.gestures_and_utterance_preset()
        self.timer = time.perf_counter()

        self.kakasi = kakasi()
        self.kakasi.setMode("J", "H")
        self.converter = self.kakasi.getConverter()

        self.socket_and_thread_start(host, port)

    def constatns_prepare(self):
        self.ningenDiscussionDuration = 360#360
        path_bc = '../peripheral/backchanneling.txt'
        with open(path_bc, encoding="utf-8") as f:
            self.Aiduchi = [s.strip() for s in f.readlines()]

        self.Names = []
        self.Opinions = []
        partcipants = [chr(i) for i in range(65, 65+self.PARTICIPANTS)]
        for p in partcipants:
            path = "../tempdata/OpnInputRef" + str(p) + "*.txt"
            l = sorted(glob.glob(path), key=os.path.getmtime)
            with open(l[-1], encoding="utf-8") as f:
                l_strip = [s.strip() for s in f.readlines()]
            print (l_strip)

            od = OrderedDict()
            od["<ID>"] = l_strip[0].split(",")[1]
            od["<YourName" + l_strip[0].split(",")[1] + ">"] = l_strip[0].split(",")[2]
            od["<RoboName" + l_strip[0].split(",")[1] + ">"] = l_strip[0].split(",")[3]
            self.Names.append([l_strip[0].split(",")[1], od])
            od = OrderedDict()
            try:
                for li in l_strip[1:]:
                    n = li.split(",")
                    if n[0] == "<Perspec>":
                        od[n[0]] = n[1].replace("。", "、")
                    else:
                        od[n[0]] = n[1]

                self.Opinions.append([l_strip[0].split(",")[1], od])
            except IndexError:
                continue
        print(self.Names, self.Opinions)

        self.MainClaims = []
        tempMain = []
        path_mc = '../tempdata/main_claims.txt'
        with open(path_mc, encoding="utf-8") as f:
            l_strip = [s.strip() for s in f.readlines()][0]
        keys = l_strip.split(":")[-1].split(";")[0].split(",")
        body = l_strip.split(";")[1:]
        for content in body:
            print(content)
            dev_by_keys = content.split(",")
            od = OrderedDict()
            for i in range(len(keys)):
                od[keys[i]] = dev_by_keys[i]
            tempMain.append(od)
        print(tempMain)

        path_ct = '../tempdata/chosen_topics.txt'
        with open(path_ct, encoding="utf-8") as f:
            l_strip = [s.strip() for s in f.readlines()][0]
        self.ChosenTopics = l_strip.split(",")
        for ct in self.ChosenTopics:
            for dic in tempMain:
                if dic["ID"] == ct:
                    self.MainClaims.append(dic)

        print(self.MainClaims)


        self.dialogue_transcript = []  # 発話の台本
        partcipants = [chr(i) for i in range(65, 65 + self.PARTICIPANTS)]
        srcA = read_utterance("../transcripts/PRESET/Intro.csv")
        self.dialogue_transcript.append(srcA)
        srcA = read_utterance("../transcripts/PRESET/Branch.csv")
        self.dialogue_transcript.append(srcA)
        """for p in partcipants:
            srcA = read_utterance("../transcripts/PRESET/Branch" + p + ".csv")
            self.dialogue_transcript.append(srcA)"""
        self.contol_code = read_utterance("../transcripts/PRESET/ControlCode.csv")

    def variables_prepare(self):
        self.next_speaker_on_ningenSpeech = "A"
        self.isWaitingNingenSpeech = False
        self.next_speech_holder = "0000"
        self.InDiscussion = False
        self.kakasi = kakasi()
        self.kakasi.setMode("J", "H")
        self.converter = self.kakasi.getConverter()

        self.toBegin = 99  # 全員が始めるボタンを押すまで待つ
        self.p_on_focus = -1  # 誰がメインの話者か(1=A)

        self.opn_relation = []  # それぞれの意見に対するそれぞれの反応
        for i in range(self.PARTICIPANTS + 1):
            tempopn = []
            for j in range(self.PARTICIPANTS):
                tempopn.append("<Neutral>")  # <Neutral> <Agree> <DisAgree>の三つある
            self.opn_relation.append(tempopn)

        self.path_command = '../tempdata/commands_to_be_sent.txt'
        s = ""
        with open(self.path_command, mode='w', encoding="utf-8") as f:
            f.write(s)
        # 送るのが待たれているコマンドを記録するファイル
        command = str(self.PARTICIPANTS - 1) + ";" + "/aitalk-pitch 0.7" + "\n"
        with open(self.path_command, mode='a') as f:
            f.write(command)
        for j in range(self.PARTICIPANTS):
            command = str(j) + ";" + "/gesture init" + "\n"
            with open(self.path_command, mode='a') as f:
                f.write(command)
            command = str(j) + ";" + "/look M 0 300 300" + "\n"
            with open(self.path_command, mode='a') as f:
                f.write(command)
            command = str(j) + ";" + "/aitalk-speed 1.1" + "\n"
            with open(self.path_command, mode='a') as f:
                f.write(command)

        todaydetail = datetime.datetime.today()
        self.time_count_path = "../tempdata/time_count_exp2"  + "_" + str(todaydetail.strftime("%Y%m%d_%H%M%S")) + ".txt"
        s = ""
        with open(self.time_count_path, mode='w', encoding="utf-8") as f:
            f.write(s)

    def gestures_and_utterance_preset(self):
        self.gesture_furikaeri = "furikaeri"
        self.gesture_furikaeri_kaijo = "furikaeri_kaijo"
        self.gestures_close_eye = "close_eye"
        self.gestures_open_eye = "open_eye"
        self.gesture_front = "/look M 0 300 300"
        self.gestures_on_short_utterance = ["short_utterance_R", "short_utterance_L"]
        self.gestures_on_long_utterance = ["long_utterance", "long_utterance_3", "long_utterance_4"]
        self.gestures_on_agreement = ["nod1", "nod2", "nod3"]
        self.gestures_on_opposition = ["kubihuri", "kubikasigeL", "kubikasigeR"]
        # self.gestures_on_raise_hand = ["raisehand_L_first", "raisehand_R_fisrt"]
        self.gestures_on_raise_hand = ["short_utterance_R", "short_utterance_L"]
        self.utterance_on_raise_hand = ["僕からいいかな", "えっと", "はい", "話していい？", "話したいです", "うーんと", "なんというか、その", "いろいろあるけど、えっと"]
        self.gaze_on_listening = [["/look M 0 300 300", "/look M -200 300 300", "/look M 0 300 300", "/look M 200 300 300"],
                                  ["/look M 200 300 300", "/look M 0 300 300", "/look M -200 300 300", "/look M 0 300 300"],
                                  ["/look M 0 300 300", "/look M 200 300 300", "/look M 0 300 300", "/look M -200 300 300"],
                                  ["/look M -200 300 300", "/look M 0 300 300", "/look M 200 300 300", "/look M 0 300 300"]]
        self.up_gaze_on_listening = [["/look M 0 400 300", "/look M -400 400 300 /gesture yokomuki", "/look M -100 400 300", "/look M 200 400 300"],
                                  ["/look M 200 400 300", "/look M 0 400 300", "/look M -400 400 300 /gesture yokomuki", "/look M -100 400 300"],
                                  ["/look M -100 400 300", "/look M 200 400 300", "/look M 0 400 300", "/look M -400 400 300 /gesture yokomuki"],
                                  ["/look M -400 400 300 /gesture yokomuki", "/look M -100 400 300", "/look M 200 400 300", "/look M 0 400 300"]]
        self.up_gaze_on_listening_modoshi = [["/look M 0 400 300", "/look M -400 400 300 /gesture yokomuki_kaijo", "/look M -0 400 300", "/look M 200 400 300"],
                                  ["/look M 200 300 300", "/look M 0 300 300", "/look M -400 300 300 /gesture yokomuki_kaijo", "/look M 0 300 300"],
                                  ["/look M 0 300 300", "/look M 200 300 300", "/look M 0 400 300", "/look M -400 300 300 /gesture yokomuki_kaijo"],
                                  ["/look M -400 300 300 /gesture yokomuki_kaijo", "/look M 0 300 300", "/look M 200 300 300", "/look M 0 300 300"]]

    def socket_and_thread_start(self, host, port):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.clients = []
        self.serversocket.bind((host, port))
        self.serversocket.listen(128)

        # サーバソケットを渡してワーカースレッドを起動する
        NUMBER_OF_THREADS = 10
        for _ in range(NUMBER_OF_THREADS):
            self.thread = threading.Thread(target=self.worker_thread, args=(self.serversocket,))
            self.thread.daemon = True
            self.thread.start()

        # command_to_sendの命令がすべて実行されたかどうかを記録する
        # 一定行以上あるなら選択できないようにする
        self.thread_for_discussion_end_check = threading.Thread(target=self.operation_waiting_check)
        self.thread_for_discussion_end_check.start()

        while True:
            # メインスレッドは遊ばせておく (ハンドラを処理させても構わない)
            time.sleep(1)

    def operation_waiting_check(self):
        # ここのループを回してる関係でつなぎなおしができなくなってる
        while True:
            time.sleep(0.1)

            if time.perf_counter() - self.timer > self.ningenDiscussionDuration and self.InDiscussion:
                print("discussion end")
                command = ""
                for i in range(self.PARTICIPANTS):
                    command += str(i) + ";/gesture " + self.gestures_open_eye + ";0\n"
                with open(self.path_command, mode='a', encoding="utf-8") as f:
                    f.write(command)
                print("eye opened")
                time.sleep(0.1)

                while True:
                    try:
                        for c in self.clients:
                            c[0].sendto("<Clear>:".encode('utf-8'), c[1])
                            print("clear send")
                        break
                    except ConnectionResetError:
                        sleep(3)
                        print("connection reset trial")
                        continue


                new_list = self.next_speech_holder
                self.InDiscussion = False

                line_to_send, next_speaker = self.generate_choice_sender(new_list)
                print("send to end discussion" + line_to_send)

                t = threading.Timer(0, self.send_choice, args=[line_to_send, next_speaker])
                t.start()

            if -0.3 + self.ningenDiscussionDuration / 3 < int(time.perf_counter() - self.timer) <= 0.3 + self.ningenDiscussionDuration / 3 and self.InDiscussion:
                print("discussion mid 1")
                try:
                    for c in self.clients:
                        c[0].sendto("<Middle>:".encode('utf-8'), c[1])
                except BrokenPipeError:
                    print("broken pipe")
                    pass

            if -0.3 + self.ningenDiscussionDuration / 2 < int(time.perf_counter() - self.timer) <= 0.3 + self.ningenDiscussionDuration / 2 and self.InDiscussion:
                print("discussion mid 2")
                try:
                    for c in self.clients:
                        c[0].sendto("<Middle>:".encode('utf-8'), c[1])
                    for c in self.clients:
                        holding = ("<Choice>:0002," + self.ID + ",&「<ArgumentA>」か、「<ArgumentC>」か、#なるべく全員で結論を出してください。##残り時間は半分です,<YourNameX>さん,").replace("X", c[2])
                        c[0].sendto(self.fix_transcript(holding).encode('utf-8'), c[1])
                except BrokenPipeError:
                    print("broken pipe")
                    pass

            if -0.3 + self.ningenDiscussionDuration * 0.7 < int(time.perf_counter() - self.timer) <= 0.3 + self.ningenDiscussionDuration * 0.7 and self.InDiscussion:
                print("discussion mid 3")
                try:
                    for c in self.clients:
                        c[0].sendto("<Middle>:".encode('utf-8'), c[1])
                except BrokenPipeError:
                    print("broken pipe")
                    pass



    def sender_detection(self, client_address, client_port):
        j = 0
        sender_of_the_message = j
        for i in self.clients:
            if (client_address, client_port) == i[1]:
                sender_of_the_message = j
                break
            j += 1
        """for i in self.clients:
            if client_address == i[1][0]:
                sender_of_the_message = j
                break
            j += 1"""

        return sender_of_the_message

    def wait_duration_calculation(self, utterance):
        temp = len(self.converter.do(utterance))
        return max(temp / 5, 2.5)
        return temp / 5 + 1  # unity側の、押してから選択肢が消えるまでの時間との兼ね合いがある。

    def command_generation(self, mes, operation):
        # print(mes)
        waittime = 0
        who = -1
        if "<Command>" in mes:
            temp1 = mes.split("<Command>:")
            for temp2 in temp1:
                temp = temp2.split(",")
                if len(temp) >= 3:
                    command = ""
                    if temp[0] == "A":
                        who = 0
                    elif temp[0] == "B":
                        who = 1
                    elif temp[0] == "C":
                        who = 2
                    elif temp[0] == "D":
                        who = 3

                    if who >= 0:
                        print("look!")
                        for i in range(self.PARTICIPANTS):
                            if not i == who:
                                print("look control")
                                gaze = self.gaze_on_listening[who][i]
                                command = str(i) + ";" + gaze + ";" + "0\n"
                                with open(self.path_command, mode='a', encoding="utf-8") as f:
                                    f.write(command)
                                time.sleep(0.1)
                        if operation == "<LookNingen>":  # 人間を見上げる
                            for i in range(self.PARTICIPANTS):
                                if not i == who:
                                    print("look control")
                                    gaze = self.up_gaze_on_listening[who][i]
                                    command = str(i) + ";" + gaze + ";" + "0\n"
                                    with open(self.path_command, mode='a', encoding="utf-8") as f:
                                        f.write(command)
                                    time.sleep(0.1)
                        if operation == "<LookKaijo>":  # 人間を見上げる
                            for i in range(self.PARTICIPANTS):
                                if not i == who:
                                    print("look control modoshi")
                                    gaze = self.up_gaze_on_listening_modoshi[who][i]
                                    command = str(i) + ";" + gaze + ";" + "0\n"
                                    with open(self.path_command, mode='a', encoding="utf-8") as f:
                                        f.write(command)
                                    time.sleep(0.1)

                    sentences = re.split('[。？]', temp[2])

                    # sentences = temp[2].split("。")  # 長すぎるといけないので文章を分ける
                    hajime = 0
                    sentences = [re.sub(r' |/|\n', "、", s) for s in sentences if not s == ""]
                    print("split")
                    print(sentences)
                    for sentence in sentences:
                        sentence = sentence.replace("負の側面", "ふの側面")
                        sentence = sentence.replace("「老い」", "おい")
                        sentence = sentence.replace("「悪」", "あく")
                        command = ""
                        command += str(who) + ";" + "/say " + sentence + "[EOF]"
                        waittimeTemp = self.wait_duration_calculation(sentence)

                        if bool(re.search(r'<LookNingenALL>|<LookALLKaijo>', operation)) and hajime == 0:
                            print("look all")
                            self.look_ningen(operation, who)
                            command += ";" + str(waittimeTemp)
                            command += "\n"
                            with open(self.path_command, mode='a', encoding="utf-8") as f:
                                f.write(command)
                            print("wrote a command as a leader of lookningenall: " + command)
                            time.sleep(0.1)

                        else:  # 振り向き等がない場合
                            if hajime == 0:
                                gesture = ""
                                if operation == "<LookNingen>":
                                    gesture = self.gesture_furikaeri
                                elif operation == "<LookKaijo>":
                                    gesture = self.gesture_furikaeri_kaijo
                                elif temp[3] == "":
                                    if waittime < 8.0:
                                        gesture = random.choice(self.gestures_on_short_utterance)
                                    else:
                                        gesture = random.choice(self.gestures_on_long_utterance)
                                elif temp[3] == "<Positive>":
                                    gesture = random.choice(self.gestures_on_agreement)
                                elif temp[3] == "<Negative>":
                                    gesture = random.choice(self.gestures_on_opposition)
                                command += " /gesture " + gesture

                            if not hajime == len(sentences) - 1:
                                command += ";" + str(0) + "\n"
                            else:
                                command += ";" + str(waittimeTemp) + "\n"

                            with open(self.path_command, mode='a', encoding="utf-8") as f:
                                f.write(command)
                            print("wrote a command: " + command)
                            time.sleep(0.1)
                        hajime += 1
                        waittime += waittimeTemp

        return waittime

    def id_search(self, id):  # 現在の台本、あいづち、個tントローラー全部見る
        for line in self.dialogue_transcript[self.p_on_focus]:
            if id == line["発話ID"]:
                return line
        for line in self.contol_code:
            if id == line["発話ID"]:
                print(line)
                return line

    def designate_next_line(self, next_list, designator, who_num):  # next listはIDの一覧  # whoは直前の発話者の番号
        line_list = []
        for id in next_list:
            line_list.append(self.id_search(id))

        who_next = -1
        if len(line_list) > 0:
            try:
                print ("おいおいおい")
                print(line_list)
                who_next = line_list[0]["発話者"]
                if who_next == "A":
                    who_next = 0
                elif who_next == "B":
                    who_next = 1
                elif who_next == "C":
                    who_next = 2
                elif who_next == "D":
                    who_next = 3
            except TypeError:
                print("次がわからない状態")

        if designator == "":
            return line_list
        elif designator == "<Holding>":
            return line_list
        elif designator == "<NingenDiscuss>":
            return line_list
        elif designator == "<PrefDiv>":  # 賛否が関係ある時は、0賛成1中立2反対  遠い意見は削除する
            try:
                if self.opn_relation[self.p_on_focus][who_next] == "<Agree>":
                    print("agree mood")
                    return [line_list[0]]
                elif self.opn_relation[self.p_on_focus][who_next] == "<DisAgree>":
                    print("disagree mood")
                    return [line_list[1]]
            except IndexError:
                print(who_num)
                pass

            return line_list

        return []

    def preference_register(self, operation, who_num):
        print(operation, re.search(r'<Agree>|<Neutral>|<DisAgree>' ,operation), self.p_on_focus, who_num)
        if bool(re.search(r'<Agree>|<Neutral>|<DisAgree>', operation)):
            print("register pref", operation)
            self.opn_relation[self.p_on_focus][who_num] = operation

    def look_ningen(self, operation, who_num):
        command = ""
        diddid = False
        if operation == "<LookNingenALL>":
            print(operation)
            for i in range(self.PARTICIPANTS):
                command += str(i) + ";/gesture " + self.gesture_furikaeri + ";0\n"
            diddid = True
        elif operation == "<LookALLKaijo>":
            print(operation)
            for i in range(self.PARTICIPANTS):
                command += str(i) + ";/gesture " + self.gesture_furikaeri_kaijo + ";0\n"
                command += str(i) + ";" + self.gesture_front + ";0\n"
            diddid = True

        with open(self.path_command, mode='a', encoding="utf-8") as f:
            f.write(command)
        return  diddid

    def generate_choice_sender(self, speech):
        sender = "<Choice>:"
        next = "Z"
        aiduchiIn = OrderedDict()
        i = 0
        mark = -1
        print("speech!")
        print(speech)
        for detail in speech:
            if "<Aiduchi>" in detail["表示"]:
                mark = i
            i += 1
        if mark >= 0:
            aiduchiIn = speech.pop(mark)

            aiduchis = random.sample(self.Aiduchi, 3)
            print(aiduchis)
            for aiduchi in aiduchis:
                text = aiduchi.split(",")[0]
                attitude = aiduchi.split(",")[1]
                sender += aiduchiIn["発話ID"] + "," + aiduchiIn["発話者"] + "," + text + "," + text + "," + attitude + ";"

                next = aiduchiIn["発話者"]

        for detail in speech:
            try:
                sender += detail["発話ID"] + "," + detail["発話者"] + "," +  detail["表示"] + "," +  detail["発話"] + "," + detail["態度"] + ";"
                next = detail["発話者"]
            except TypeError:
                sender += detail["発話ID"] + "," + detail["発話者"] + "," + detail["表示"] + "," + detail["発話"] + ";"
        return sender[:-1], next

    def choice_generation(self, mes):
      if "<Command>" in mes:
            who = mes.split(":")[-1].split(",")[0]
            who_num = 0
            waiting_time = 0
            if who == "A":
                who_num = 0
            elif who == "B":
                who_num = 1
            elif who == "C":
                who_num = 2
            elif who == "D":
                who_num = 3
            speech_id = mes.split(":")[-1].split(",")[1]
            temp_line = self.id_search(speech_id)
            new_list = temp_line["次の発話の候補"].split(";")
            designator = temp_line["次の発話の決め方"]
            operation = temp_line["特殊な操作"]
            print("----------------------------", new_list, designator, operation)
            self.preference_register(operation, who_num)  # この後には何らかの発話をさせるかもここで戻らせる
            new_list = self.designate_next_line(new_list, designator, who_num)
            print("ここで消えるもんが消えてなきゃおかしい！")
            print(new_list)

            if designator == "<Begin>":  # スタートが来た場合は先頭に送る   ここ大事！！！！
                self.toBegin += 1
                if self.toBegin < self.PARTICIPANTS:
                    return
                if self.p_on_focus == -1:
                    self.p_on_focus = 0
                    new_list = [self.id_search(self.dialogue_transcript[self.p_on_focus][0]["発話ID"])]

                s = "start: " + str(time.perf_counter())
                with open(self.time_count_path, mode='a', encoding="utf-8") as f:
                    f.write(s)

            if designator == "<Transition>":
                self.p_on_focus += 1
                new_list = [self.id_search(self.dialogue_transcript[self.p_on_focus][0]["発話ID"])]

                s = "start: " + str(time.perf_counter()) + ":(" + str(self.p_on_focus) + ")"
                with open(self.time_count_path, mode='a', encoding="utf-8") as f:
                    f.write(s)

            elif designator == "<Terminate>":
                time.sleep(10)
                end_mes = "<Choice>:0001," + self.ID + ",@おわり,みんな、ありがとう,"
                for c in self.clients:
                    c[0].sendto(end_mes.encode('utf-8'), c[1])

                s = "end: " + str(time.perf_counter())
                with open(self.time_count_path, mode='a', encoding="utf-8") as f:
                    f.write(s)

                return
            elif designator == "<NingenDiscuss>":
                self.next_speech_holder = new_list
                print("saved:")
                print(new_list)
                waiting_time = self.command_generation(mes, operation)
                # 本当はテキストからとってくるべき。
                self.timer = time.perf_counter()    # 時間を設定した！
                self.InDiscussion = True

                # ここで目を閉じさせる
                command = ""
                for i in range(self.PARTICIPANTS):
                    command += str(i) + ";/gesture " + self.gestures_close_eye + ";0\n"
                with open(self.path_command, mode='a', encoding="utf-8") as f:
                    f.write(command)

                time.sleep(waiting_time)
                for c in self.clients:
                    holding = ("<Choice>:0002," + self.ID + ",&「<ArgumentA>」か、「<ArgumentC>」か、#なるべく全員で結論を出してください。,<YourNameX>さん,").replace("X", c[2])
                    c[0].sendto(self.fix_transcript(holding).encode('utf-8'), c[1])

                return

            elif designator == "<Holding>":  # discussion中にボタンを押させないなら、このへんは意味ない
                print(time.perf_counter() - self.timer)
                if time.perf_counter() - self.timer > self.ningenDiscussionDuration:  # 人が話す時間
                    new_list = self.next_speech_holder
                    self.InDiscussion = False
                else:
                    waiting_time = 5
                    self.command_generation(mes, operation)
                    pass

            else:
                print("いたって平凡な発話をします")
                waiting_time = self.command_generation(mes, operation)
                print("この発話は" + str(waiting_time) + "秒かかります")

            """if who_speak >= 0:
                for i in range(self.PARTICIPANTS):
                    gaze = self.gaze_on_listening[who_speak][i]
                    command = str(i) + ";" + gaze + ";" + "0\n"
                    with open(self.path_command, mode='a', encoding="utf-8") as f:
                        f.write(command)"""




            line_to_send, next_speaker = self.generate_choice_sender(new_list)
            print("send" + line_to_send)
            print("waitin: " + str(waiting_time))

            t = threading.Timer(waiting_time, self.send_choice, args=[line_to_send, next_speaker])
            t.start()

            # あいづちのときはまた別

    def fix_transcript(self, line):
        print(line)
        for names in self.Names:
            dic = names[1]
            keys = dic.keys()
            for key in keys:
                line = line.replace(key, dic[key])

        users = ["A", "B", "C", "D"]
        for i in range(len(users)):
            opinions = self.Opinions[i]
            dic = opinions[1]
            keys = dic.keys()
            for key in keys:
                line = line.replace(key[:-1] + users[i] + ">", dic[key])

        for i in range(len(users)):
            claims = self.MainClaims[i]
            keys = claims.keys()
            for key in keys:
                line = line.replace(key[:-1] + users[i] + ">", claims[key])
            print(line)
        return  line

    def send_choice(self, line_to_send, next_speaker):
        line_to_send = self.fix_transcript(line_to_send)
        command = "<Command>:" + str(next_speaker) + "," + line_to_send.split(":")[-1].split(",")[0] + "," + line_to_send.split(":")[-1].split(",")[3] + "," + line_to_send.split(":")[-1].split(",")[4]
        print("call again" + command)
        # self.choice_generation(command)

        if line_to_send.split(":")[-1].split(",")[2][0] != '@':
            for c in self.clients:
                print("actually sent")
                c[0].sendto(line_to_send.encode('utf-8'), c[1])

            self.choice_generation(command)
        else:
            self.isWaitingNingenSpeech = True
            self.next_speaker_on_ningenSpeech = next_speaker
            wildcard = True
            # wildcard = False
            if next_speaker == "X":
                wildcard = True
            for c in self.clients:
                if wildcard:
                    print("get wild " + line_to_send + "|||" + line_to_send.replace("X", c[2]))
                    c[0].sendto(self.fix_transcript(line_to_send.replace("X", c[2])).encode('utf-8'), c[1])
                elif c[2] == next_speaker:
                    print("actually sent")
                    c[0].sendto(line_to_send.encode('utf-8'), c[1])



        """wildcard = True
        # wildcard = False
        if next_speaker == "X":
            wildcard = True
        for c in self.clients:
            if wildcard:
                print("get wild " + line_to_send + "|||" + line_to_send.replace("X", c[2]))
                c[0].sendto(self.fix_transcript(line_to_send.replace("X", c[2])).encode('utf-8'), c[1])
            elif c[2] == next_speaker:
                print("actually sent")
                c[0].sendto(line_to_send.encode('utf-8'), c[1])"""


    def worker_thread(self, none):
        """クライアントとの接続を処理するハンドラ"""
        self.next_speaker = 0
        while True:
            # クライアントからの接続を待ち受ける (接続されるまでブロックする)
            # ワーカスレッド同士でクライアントからの接続を奪い合う
            clientsocket, (client_address, client_port) = self.serversocket.accept()

            message = clientsocket.recv(1024)
            raw_mes = message.decode('utf-8')
            self.ID = "Z"
            NAME = "Hiroshi"
            if "<ID>" in raw_mes:
                self.ID = raw_mes.split(":")[-1].split(",")[0]
                NAME = raw_mes.split(":")[-1].split(",")[-1]
                print(self.ID, NAME)

                delcand = -1
                i = 0
                for c in self.clients:
                    if c[2] == self.ID:
                        delcand = i
                    i += 1
                if delcand != -1:
                    del self.clients[delcand]


            self.clients.append((clientsocket, (client_address, client_port), self.ID))

            # clientsocket.sendto(("you are <ID> :" + ID + "," + NAME).encode('utf-8'), (client_address, client_port))
            time.sleep(1)
            clientsocket.sendto(("<Choice>:0000," + self.ID + ",@はじめる,よろしく,").encode('utf-8'), (client_address, client_port))

            print('New client: {0}:{1}'.format(client_address, client_port))
            # クライアントは0からカウント　ユーザ0、ユーザ1、ユーザ2
            while True:
                try:
                    message = clientsocket.recv(1024)
                    raw_mes = message.decode('utf-8')

                    if raw_mes != "":
                        print("recv:" + raw_mes)
                        # sender = self.sender_detection(client_address, client_port)
                        if "0000" in raw_mes:
                            self.choice_generation(raw_mes)
                        if self.isWaitingNingenSpeech:
                            self.isWaitingNingenSpeech = False
                            raw_mes = raw_mes.replace(":A,", ":" + self.next_speaker_on_ningenSpeech + ",")

                            self.choice_generation(raw_mes)

                except OSError:
                    break

            clientsocket.close()
            print('Bye-Bye: {0}:{1}'.format(client_address, client_port))
            sender = self.sender_detection(client_address, client_port)
            del self.clients[sender]  # 接続が切れたらクライアントリストから削除


if __name__ == '__main__':
    def_port = 5000
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('192.168.100.1', 80))
    ip = s.getsockname()[0]
    print("waiting at :" + ip + ":" + str(def_port))
    s = DialogManager(ip, def_port)
    # s = DialogManager('127.0.0.1', 5000, TOPIC=0)