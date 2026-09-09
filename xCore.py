import requests, json, binascii, time, urllib3, base64, re, socket, threading, random, os, jwt, sys
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 2, '', 'my_message.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x10my_message.proto">\n\tMyMessage\x12\x0f\n\x07\x66ield21\x18\x15 \x01(\x03'
    b'\x12\x0f\n\x07\x66ield22\x18\x16 \x01(\x0c\x12\x0f\n\x07\x66ield23\x18\x17 \x01(\x0c\x62\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'my_message_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_MYMESSAGE']._serialized_start = 20
    _globals['_MYMESSAGE']._serialized_end = 82

Key, Iv = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56]), \
          bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def EnC_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def DEc_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return unpad(cipher.decrypt(bytes.fromhex(HeX)), AES.block_size).hex()

def EnC_PacKeT(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

def DEc_PacKeT(HeX, K, V):
    return unpad(AES.new(K, AES.MODE_CBC, V).decrypt(bytes.fromhex(HeX)), 16).hex()

def EnC_Uid(H, Tp):
    e, H = [], int(H)
    while H:
        e.append((H & 0x7F) | (0x80 if H > 0x7F else 0))
        H >>= 7
    return bytes(e).hex() if Tp == 'Uid' else None

def EnC_Vr(N):
    if N < 0: return ''
    H = []
    while True:
        BesTo = N & 0x7F
        N >>= 7
        if N:
            BesTo |= 0x80
        H.append(BesTo)
        if not N:
            break
    return bytes(H)

def DEc_Uid(H):
    n = s = 0
    for b in bytes.fromhex(H):
        n |= (b & 0x7F) << s
        if not b & 0x80:
            break
        s += 7
    return n

def DecodE_HeX(H):
    R = hex(H)
    F = str(R)[2:]
    if len(F) == 1:
        F = "0" + F
        return F
    else:
        return F

def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            packet.extend(CrEaTe_LenGTh(field, CrEaTe_ProTo(value)))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    packet.extend(CrEaTe_LenGTh(field, CrEaTe_ProTo(item)))
                elif isinstance(item, int):
                    packet.extend(CrEaTe_VarianT(field, item))
                elif isinstance(item, str) or isinstance(item, bytes):
                    packet.extend(CrEaTe_LenGTh(field, item))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))
    return packet

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint":
            field_data['data'] = result.data
        if result.wire_type == "string":
            field_data['data'] = result.data
        if result.wire_type == "bytes":
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_dict = Fix_PackEt(parsed_results)
        return json.dumps(parsed_results_dict)
    except Exception as e:
        return None

def xMsGFixinG(n):
    return '🗿'.join(str(n)[i:i + 3] for i in range(0, len(str(n)), 3))

def ArA_CoLor():
    Tp = [
        "FF9999", "99FF99", "99CCFF", "FFD700", "FFB6C1", "FFA07A",
        "98FB98", "E6E6FA", "AFEEEE", "F0E68C", "FFE4B5", "D8BFD8",
        "FFFACD", "87CEFA", "FFDEAD", "B0E0E6", "FFDAB9", "E0FFFF",
        "F5DEB3", "FFC0CB", "FFF0F5", "ADD8E6"
    ]
    return random.choice(Tp)

def xBunnEr():
    bN = [902000306, 902000305, 902000003, 902000016, 902000017, 902000019, 902000020, 902000021,
          902000023, 902000070, 902000087, 902000108, 902000011, 902049020, 902049018, 902049017,
          902049016, 902049015, 902049003, 902033016, 902033017, 902033018, 902048018, 902000306, 902000305]
    return random.choice(bN)

def GeneRaTePk(Pk, N, K, V):
    PkEnc = EnC_PacKeT(Pk, K, V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    if len(_) == 2:
        HeadEr = N + "000000"
    elif len(_) == 3:
        HeadEr = N + "00000"
    elif len(_) == 4:
        HeadEr = N + "0000"
    elif len(_) == 5:
        HeadEr = N + "000"
    elif len(_) == 6:
        HeadEr = N + "00"
    elif len(_) == 7:
        HeadEr = N + "0"
    else:
        HeadEr = N
    return bytes.fromhex(HeadEr + _ + PkEnc)

# ==================== باكتات سبام روم ====================

def openroom(K, V):
    fields = {
        1: 2,
        2: {
            1: 32,
            2: 53,
            3: 3,
            4: "syx-baro",
            5: "123123",
            6: 8,
            7: 10,
            8: 1,
            9: 8,
            11: 1,
            14: 134217728,
            15: [
                {1: "IDC1", 2: 74, 3: "ME"},
                {1: "IDC2", 2: 51, 3: "ME"},
                {1: "IDC3", 2: 123, 3: "ME"},
                {1: "IDC4", 2: 221, 3: "ME"}
            ],
            16: "\x01\x03\x04\x07\t\n\x0b\x12\x16\x19\x1a \x1d'",
            27: 1,
            31: "PEAKRA",
            32: 1744858358,
            33: 6,
            34: "\x00\x01",
            35: 16,
            40: "en",
            42: {1: "Craftland_Room", 2: "-1/-1//"},
            46: 80,
            49: [
                {1: 3, 2: 391}, {1: 4, 2: 385}, {1: 5, 2: 192},
                {1: 29, 2: 204}, {1: 22, 2: 115}, {1: 14, 2: 175}, {1: 21}
            ],
            51: {7: 51}
        }
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)

def spmroom(K, V, uid):
    fields = {1: 22, 2: {1: int(uid)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)

def SEnd_InV(Nu, Uid, K, V):
    fields = {1: 2, 2: {1: int(Uid), 2: "ME", 4: int(Nu)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0515', K, V)

def ExitBot(id, K, V):
    fields = {1: 7, 2: {1: int(11037044965)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0515', K, V)

def GeT_Status(PLayer_Uid, K, V):
    PLayer_Uid = EnC_Uid(PLayer_Uid, Tp='Uid')
    if len(PLayer_Uid) == 8:
        Pk = f'080112080a04{PLayer_Uid}1005'
    elif len(PLayer_Uid) == 10:
        Pk = f"080112090a05{PLayer_Uid}1005"
    return GeneRaTePk(Pk, '0f15', K, V)

def GeT_PLayer_InFo(uid, Token):
    try:
        data = bytes.fromhex(EnC_AEs(f"08{EnC_Uid(uid, Tp='Uid')}1007"))
        url = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
        headers = {
            'X-Unity-Version': '2022.3.47f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'Authorization': f'Bearer {Token}',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Host': 'clientbp.ggpolarbear.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip'
        }
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if response.status_code not in (200, 201):
            return None
        packet = binascii.hexlify(response.content).decode('utf-8')
        BesTo_data = json.loads(DeCode_PackEt(packet))
        d = BesTo_data["1"]["data"]
        info = {
            "nickname": str(d["3"]["data"]),
            "uid": str(d["1"]["data"]),
            "level": d.get("6", {}).get("data"),
            "likes": d.get("21", {}).get("data"),
            "server": d.get("5", {}).get("data"),
        }
        try:
            info["last_login"] = datetime.fromtimestamp(d["24"]["data"]).strftime("%d/%m/%y %I:%M %p")
        except Exception:
            info["last_login"] = None
        try:
            info["created"] = datetime.fromtimestamp(d["44"]["data"]).strftime("%d/%m/%y")
        except Exception:
            info["created"] = None
        try:
            info["bio"] = BesTo_data["9"]["data"]["9"]["data"]
        except Exception:
            info["bio"] = None
        return info
    except Exception:
        return None