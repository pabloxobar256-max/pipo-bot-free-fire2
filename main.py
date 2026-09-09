import os, requests, threading, time, sys, jwt, socket, urllib3, json, ssl, http.client, gzip, random
from datetime import datetime, timedelta
from google.protobuf.timestamp_pb2 import Timestamp
from io import BytesIO
import telebot
from xCore import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = "8917097516:AAGGAMM5_19HCmgWRvQK55m7eWZFfyJPIss"
bot = telebot.TeleBot(BOT_TOKEN)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, 'accounts.json')

connected_clients = {}
connected_clients_lock = threading.Lock()
all_accounts = {}
all_accounts_lock = threading.Lock()

spam_speed = 0.5
spam_running = False
current_target = None
spam_timer = None
SPAM_DURATION = 30 * 60

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def set_acc_status(acc_id, status):
    with all_accounts_lock:
        if acc_id in all_accounts:
            all_accounts[acc_id]['status'] = status

class MyMessage:
    def __init__(self):
        self.field21 = 0
        self.field22 = b''
        self.field23 = b''

    def ParseFromString(self, data):
        try:
            from xCore import MyMessage as RealMyMessage
            msg = RealMyMessage()
            msg.ParseFromString(data)
            self.field21 = msg.field21
            self.field22 = msg.field22
            self.field23 = msg.field23
        except Exception:
            if len(data) > 0:
                self.field21 = int.from_bytes(data[:8], 'little') if len(data) >= 8 else 0
                self.field22 = data[8:24] if len(data) >= 24 else b''
                self.field23 = data[24:40] if len(data) >= 40 else b''

def load_accounts_from_file(filepath):
    accounts = []
    try:
        if not os.path.exists(filepath):
            return accounts
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        uid = parts[0].strip()
                        password = parts[1].strip()
                        if uid and password:
                            accounts.append({'id': uid, 'password': password})
        return accounts
    except Exception:
        return accounts

class FF_Client:
    def __init__(self, id, password):
        self.id = id
        self.password = password
        self.key = None
        self.iv = None
        self.CliEnts = None
        self.CliEnts2 = None
        self.running = True
        self.target_id = None
        self.room_opened = False
        self.spam_thread_started = False
        self.send_lock = threading.Lock()
        self.account_uid = None
        threading.Thread(target=self.start_client, daemon=True).start()

    def start_client(self):
        set_acc_status(self.id, 'connecting')
        try:
            self.Get_FiNal_ToKen_0115()
        except Exception:
            time.sleep(1)
            self.start_client()

    def Get_FiNal_ToKen_0115(self):
        while self.running:
            try:
                result = self.Guest_GeneRaTe(self.id, self.password)
                if not result:
                    set_acc_status(self.id, 'connecting')
                    time.sleep(2)
                    continue

                token, key, iv, ts, ip, port, ip2, port2 = result
                if not all([ip, port, ip2, port2]):
                    time.sleep(2)
                    continue

                self.JwT_ToKen = token

                try:
                    self.AfTer_DeC_JwT = jwt.decode(token, options={"verify_signature": False})
                    self.AccounT_Uid = self.AfTer_DeC_JwT.get('account_id')
                    if not self.AccounT_Uid:
                        raise ValueError("No account_id in JWT")
                    self.account_uid = self.AccounT_Uid
                    self.EncoDed_AccounT = hex(self.AccounT_Uid)[2:]
                    self.HeX_VaLue = DecodE_HeX(ts)
                    self.TimE_HEx = self.HeX_VaLue
                    self.JwT_ToKen_ = token.encode().hex()
                except Exception:
                    time.sleep(1)
                    continue

                try:
                    encrypted_token = EnC_PacKeT(self.JwT_ToKen_, key, iv)
                    header_length = hex(len(encrypted_token) // 2)[2:]
                    uid_length = len(self.EncoDed_AccounT)
                    prefix_map = {7: '000000000', 8: '00000000', 9: '0000000', 10: '000000'}
                    prefix = prefix_map.get(uid_length, '00000000')
                    self.Header = f'0115{prefix}{self.EncoDed_AccounT}{self.TimE_HEx}00000{header_length}'
                    self.FiNal_ToKen_0115 = self.Header + encrypted_token
                except Exception:
                    time.sleep(1)
                    continue

                self.AutH_ToKen = self.FiNal_ToKen_0115
                connection_thread = threading.Thread(
                    target=self.Connect_SerVer,
                    args=(self.JwT_ToKen, self.AutH_ToKen, ip, port, key, iv, ip2, port2),
                    daemon=True
                )
                connection_thread.start()
                connection_thread.join(timeout=30)
                return
            except Exception:
                set_acc_status(self.id, 'connecting')
                time.sleep(2)

    def start_spam_loop(self):
        if self.spam_thread_started:
            return
        self.spam_thread_started = True

        def spam_loop():
            while self.running:
                if not (spam_running and self.target_id):
                    time.sleep(0.2)
                    continue
                try:
                    current = self.target_id
                    with self.send_lock:
                        if self.CliEnts2 and self.key and self.iv:
                            self.CliEnts2.send(spmroom(self.key, self.iv, current))
                            self.CliEnts2.send(SEnd_InV(1, current, self.key, self.iv))
                    print(f"{YELLOW}[ROOM] {self.id} => {current}{RESET}")
                except Exception:
                    time.sleep(0.5)
                    continue
                time.sleep(spam_speed)

        threading.Thread(target=spam_loop, daemon=True).start()

    def set_target(self, target_id):
        self.target_id = target_id

    def Connect_SerVer_OnLine(self, Token, tok, host, port, key, iv, host2, port2):
        try:
            self.AutH_ToKen_0115 = tok
            self.CliEnts2 = socket.create_connection((host2, int(port2)))
            self.CliEnts2.settimeout(10)
            self.CliEnts2.send(bytes.fromhex(self.AutH_ToKen_0115))

            if not self.room_opened:
                self.CliEnts2.send(openroom(self.key, self.iv))
                self.room_opened = True
                print(f"{GREEN}Bot {self.id} Online{RESET}")

            self.start_spam_loop()
        except Exception as e:
            print(f"{RED}Error in Connect_SerVer_OnLine for {self.id}: {e}{RESET}")
            return

        while self.running:
            try:
                self.DaTa2 = self.CliEnts2.recv(99999)
                if self.DaTa2:
                    if '0500' in self.DaTa2.hex()[0:4] and len(self.DaTa2.hex()) > 30:
                        try:
                            self.packet = json.loads(DeCode_PackEt(f'08{self.DaTa2.hex().split("08", 1)[1]}'))
                            self.AutH = self.packet['5']['data']['7']['data']
                        except Exception:
                            pass
            except socket.timeout:
                continue
            except Exception:
                time.sleep(0.5)

    def Connect_SerVer(self, Token, tok, host, port, key, iv, host2, port2):
        try:
            self.AutH_ToKen_0115 = tok
            self.CliEnts = socket.create_connection((host, int(port)))
            self.CliEnts.send(bytes.fromhex(self.AutH_ToKen_0115))
            self.DaTa = self.CliEnts.recv(1024)

            online_thread = threading.Thread(
                target=self.Connect_SerVer_OnLine,
                args=(Token, tok, host, port, key, iv, host2, port2),
                daemon=True
            )
            online_thread.start()

            self.key = key
            self.iv = iv

            with connected_clients_lock:
                connected_clients[self.id] = self
            set_acc_status(self.id, 'online')

            while self.running:
                try:
                    self.DaTa = self.CliEnts.recv(1024)
                    if len(self.DaTa) == 0:
                        break
                except Exception:
                    break

            with connected_clients_lock:
                connected_clients.pop(self.id, None)
            set_acc_status(self.id, 'connecting')

            if self.running:
                time.sleep(2)
                self.Connect_SerVer(Token, tok, host, port, key, iv, host2, port2)
        except Exception:
            with connected_clients_lock:
                connected_clients.pop(self.id, None)
            set_acc_status(self.id, 'connecting')
            if self.running:
                time.sleep(2)
                self.Connect_SerVer(Token, tok, host, port, key, iv, host2, port2)

    def GeT_Key_Iv(self, serialized_data):
        my_message = MyMessage()
        my_message.ParseFromString(serialized_data)
        timestamp = my_message.field21
        key = my_message.field22
        iv = my_message.field23
        timestamp_obj = Timestamp()
        timestamp_obj.FromNanoseconds(timestamp)
        combined_timestamp = timestamp_obj.seconds * 1_000_000_000 + timestamp_obj.nanos
        return combined_timestamp, key, iv

    def Guest_GeneRaTe(self, uid, password):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close"
        }
        dataa = {
            "uid": f"{uid}", "password": f"{password}", "response_type": "token",
            "client_type": "2",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_id": "100067"
        }
        try:
            response = requests.post(url, headers=headers, data=dataa, timeout=10)
            response.raise_for_status()
            resp = response.json()
            if 'access_token' not in resp:
                return None
            return self.ToKen_GeneRaTe(resp['access_token'], resp['open_id'])
        except Exception:
            time.sleep(1)
            return None

    def GeT_LoGin_PorTs(self, JwT_ToKen, PayLoad):
        url = 'https://clientbp.ggpolarbear.com/GetLoginData'
        headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {JwT_ToKen}',
            'X-Unity-Version': '2022.3.47f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': 'clientbp.ggpolarbear.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip'
        }
        for attempt in range(3):
            try:
                res = requests.post(url, headers=headers, data=PayLoad, verify=False, timeout=10)
                if res.status_code == 503:
                    time.sleep(1)
                    continue
                res.raise_for_status()
                besto = json.loads(DeCode_PackEt(res.content.hex()))
                if '32' not in besto or '14' not in besto:
                    continue
                address = besto['32']['data']
                address2 = besto['14']['data']
                ip, ip2 = address[:len(address) - 6], address2[:len(address2) - 6]
                port, port2 = address[len(address) - 5:], address2[len(address2) - 5:]
                return ip, port, ip2, port2
            except Exception:
                time.sleep(1)
                continue
        return None, None, None, None

    def ToKen_GeneRaTe(self, Access_ToKen, Access_Uid):
        try:
            self.PLaFTrom = "4"
            self.Version, self.V = '2024010012', '1.126.2'
            pyl = {
                3: str(datetime.now())[:-7], 4: "free fire", 5: 2, 7: self.V,
                8: "Android OS 11 / API-30 (RQ3A.210805.001)", 9: "Handheld", 10: "Verizon",
                11: "WIFI", 12: 1080, 13: 2400, 14: "440", 15: "ARMv8", 16: 6144,
                17: "Adreno (TM) 650", 18: "OpenGL ES 3.2 V@1.50",
                19: "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57", 20: "", 21: "en",
                22: Access_Uid, 23: self.PLaFTrom, 24: "Handheld", 25: "google G011A",
                29: Access_ToKen, 30: 3, 41: "Verizon", 42: "WIFI",
                57: "1ac4b80ecf0478a44203bf8fac6120f5", 60: 32966, 61: 29779, 62: 2479,
                63: 914, 64: 31176, 65: 32966, 66: 31176, 67: 32966, 70: 4, 73: 2,
                74: "/data/app/com.dts.freefireth-g8eDE0T268FtFmnFZ2UpmA==/lib/arm",
                76: 1, 77: "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-g8eDE0T268FtFmnFZ2UpmA==/base.apk",
                78: 6, 79: 1, 81: "64", 83: self.Version, 86: "OpenGLES3", 87: 255,
                88: self.PLaFTrom,
                89: "J\u0003FD\u0004\r_UH\u0003\u000b\u0016_\u0003D^J>\u000fWT\u0000\\=\nQ_;\u0000\r;Z\u0005a",
                90: "Phoenix", 91: "AZ", 92: 10214, 93: "3rd_party",
                94: "KqsHT7gtKWkK0gY/HwmdwXIhSiz4fQldX3YjZeK86XBTthKAf1bW4Vsz6Di0S8vqr0Jc4HX3TMQ8KaUU3GeVvYzWF9I=",
                95: 111207, 97: 1, 98: 1, 99: f"{self.PLaFTrom}", 100: f"{self.PLaFTrom}"
            }
            pyl_hex = CrEaTe_ProTo(pyl).hex()
            payload = bytes.fromhex(EnC_AEs(pyl_hex))

            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection("loginbp.ggpolarbear.com", context=context, timeout=10)
            headers = {
                'X-Unity-Version': '2018.4.11f1', 'ReleaseVersion': 'OB54',
                'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                'Host': 'loginbp.ggpolarbear.com', 'Connection': 'Keep-Alive', 'Accept-Encoding': 'gzip'
            }
            conn.request("POST", "/MajorLogin", body=payload, headers=headers)
            response = conn.getresponse()
            raw_data = response.read()
            if response.getheader('Content-Encoding') == 'gzip':
                with gzip.GzipFile(fileobj=BytesIO(raw_data)) as f:
                    raw_data = f.read()
            if response.status not in [200, 201]:
                return None

            besto = json.loads(DeCode_PackEt(raw_data.hex()))
            jwt_token = besto['8']['data']
            combined_timestamp, key, iv = self.GeT_Key_Iv(raw_data)
            ip, port, ip2, port2 = self.GeT_LoGin_PorTs(jwt_token, payload)
            return jwt_token, key, iv, combined_timestamp, ip, port, ip2, port2
        except Exception:
            return None

def start_account(account):
    try:
        FF_Client(account['id'], account['password'])
    except Exception:
        set_acc_status(account['id'], 'offline')

def start_accounts():
    print(f"{YELLOW}Loading accounts from: {ACCOUNTS_FILE}{RESET}")
    accounts = load_accounts_from_file(ACCOUNTS_FILE)
    if not accounts:
        print(f"{RED}No accounts found in accounts.json{RESET}")
        return
    with all_accounts_lock:
        for a in accounts:
            all_accounts[a['id']] = {'id': a['id'], 'password': a['password'], 'status': 'offline'}
    for account in accounts:
        threading.Thread(target=start_account, args=(account,), daemon=True).start()
        time.sleep(0.05)
    print(f"{GREEN}Loaded {len(accounts)} accounts{RESET}")

def stop_spam_auto():
    global spam_running, current_target
    print(f"{YELLOW}[TIMER] 30 minutes completed - Stopping ROOM spam{RESET}")
    spam_running = False
    current_target = None
    with connected_clients_lock:
        for _, client in connected_clients.items():
            client.target_id = None

def start_spam_timer():
    global spam_timer
    if spam_timer:
        spam_timer.cancel()
    spam_timer = threading.Timer(SPAM_DURATION, stop_spam_auto)
    spam_timer.daemon = True
    spam_timer.start()

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message, 
        "SYX-BARO BOT\n\n"
        "/spam [UID] - تشغيل سبام روم\n"
        "/stop - إيقاف السبام\n"
        "/status - عرض حالة الحسابات",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['spam'])
def cmd_spam(message):
    global spam_running, current_target
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "استخدم: /spam [UID]")
        return
    
    uid = args[1]
    if not uid.isdigit():
        bot.reply_to(message, "الايدي غير صالح")
        return
    
    with connected_clients_lock:
        online_count = len(connected_clients)
        if online_count == 0:
            bot.reply_to(message, "لا توجد حسابات متصلة")
            return
    
    spam_running = False
    time.sleep(0.5)
    
    current_target = uid
    spam_running = True
    
    with connected_clients_lock:
        for _, client in connected_clients.items():
            client.set_target(uid)
    
    start_spam_timer()
    
    bot.reply_to(message, 
        f"تم تشغيل سبام روم\n\n"
        f"الهدف: {uid}\n"
        f"الحسابات: {online_count}\n"
        f"المدة: 30 دقيقة"
    )
    print(f"{GREEN}[SPAM]{RESET} Started on {uid} with {online_count} accounts")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    global spam_running, current_target, spam_timer
    
    spam_running = False
    current_target = None
    with connected_clients_lock:
        for _, client in connected_clients.items():
            client.target_id = None
    if spam_timer:
        spam_timer.cancel()
        spam_timer = None
    
    bot.reply_to(message, "تم إيقاف السبام")
    print(f"{YELLOW}[STOP]{RESET} Spam stopped")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    with connected_clients_lock:
        online = len(connected_clients)
        online_ids = list(connected_clients.keys())[:10]
    
    with all_accounts_lock:
        total = len(all_accounts)
        offline = total - online
    
    status_text = (
        f"حالة البوت\n\n"
        f"متصل: {online}\n"
        f"غير متصل: {offline}\n"
        f"الاجمالي: {total}\n\n"
    )
    
    if spam_running:
        status_text += f"السبام: يعمل -> {current_target}\n"
        status_text += "المدة المتبقية: 30 دقيقة"
    else:
        status_text += "السبام: متوقف"
    
    if online_ids:
        status_text += f"\n\nاول 10 حسابات:\n{', '.join(online_ids)}"
    
    bot.reply_to(message, status_text)

def run_bot():
    print(f"{GREEN}[START]{RESET} ROOM SPAM Bot")
    print(f"{GREEN}[INFO]{RESET} File: accounts.json")
    
    threading.Thread(target=start_accounts, daemon=True).start()
    
    print(f"{GREEN}[BOT]{RESET} Bot is running...")
    bot.infinity_polling()

if __name__ == "__main__":
    run_bot()