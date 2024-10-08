import websocket
import datetime
import hashlib
import base64
import hmac
import fsspec
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os
import wave


STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


def pcm2wav(pcm_path, wav_path, channels=1, bits=16, sample_rate=16000):
    pcmf = open(pcm_path, 'rb')
    pcmdata = pcmf.read()
    pcmf.close()

    if bits % 8 != 0:
        raise ValueError("bits % 8 must == 0. now bits:" + str(bits))

    wavfile = wave.open(wav_path, 'wb')
    wavfile.setnchannels(channels)
    wavfile.setsampwidth(bits // 8)
    wavfile.setframerate(sample_rate)
    wavfile.writeframes(pcmdata)


class WsParam(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"aue": "raw", "auf": "audio/L16;rate=16000", "vcn": "aisjiuxu", "tte": "utf8"}
        self.Data = self._formatted_data()
        #使用小语种须使用以下方式，此处的unicode指的是 utf16小端的编码方式，即"UTF-16LE"”
        #self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-16')), "UTF8")}

    def _formatted_data(self):
        return {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}

    def set_data(self, text: str):
        self.Text = text
        self.Data = self._formatted_data()

    # 生成url
    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url



class _TTSWorker(websocket.WebSocketApp):
    def __init__(self):
        self.ws_param = WsParam(
            APPID='b83de31b',
            APISecret='NDA4NGRiZWQ5ZDA3ODMyODBmMDhlYzFj',
            APIKey='ae98f39e2ea6bceae351c200e55e6b28',
            Text="",
        )

        url = self.ws_param.create_url()
        self.speech_path = None
        self.fs = fsspec.filesystem("file")
        super().__init__(
            url=url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )

    def transform(self, text: str, speech_name: str):
        self.speech_name = speech_name
        with open(self.pcm_path, 'wb') as f:
            pass
        self.ws_param.set_data(text=text)
        self.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        pcm2wav(
            pcm_path=self.pcm_path,
            wav_path=self.wav_path,
        )
        return self.wav_path


    @property
    def pcm_path(self):
        return f"{self.speech_name}.pcm"

    @property
    def wav_path(self):
        return f"{self.speech_name}.wav"

    def on_message(self, ws, message):
        try:
            message =json.loads(message)
            code = message["code"]
            sid = message["sid"]
            audio = message["data"]["audio"]
            audio = base64.b64decode(audio)
            status = message["data"]["status"]
            if status == 2:
                print("ws is closed")
                ws.close()
            if code != 0:
                errMsg = message["message"]
                print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
            else:
                with open(self.pcm_path, 'ab') as f:
                    f.write(audio)
        except Exception as e:
            print("receive msg,but parse exception:", e)

    # 收到websocket错误的处理
    def on_error(self, ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(self, ws, close_status_code, close_msg):
        print("### closed ###")

    # 收到websocket连接建立的处理
    def on_open(self, ws):
        def run(*args):
            d = {"common": self.ws_param.CommonArgs,
                 "business": self.ws_param.BusinessArgs,
                 "data": self.ws_param.Data,
                 }
            d = json.dumps(d)
            print("------>开始发送文本数据")
            ws.send(d)
            if self.fs.exists(self.speech_path):
                self.fs.rm(self.speech_path)
        thread.start_new_thread(run, ())



websocket.enableTrace(False)
TTSWorker = _TTSWorker()

# text = (
#     "你好，我的名字是杨再正，我毕业于南京大学，研究方向为基于存算一体器件的机器学习系统。具备的知识技能包括: 熟悉python、C++编程,"
#     "熟悉各类主流深度学习算法，熟悉AI编译器前后端，熟悉各类存算一体架构。我希望能够加入贵公司，为新时代的到来拉开帷幕。下方是我的简历，"
#     "以及我的个人网站链接，您可以访问我的个人网站获取有关于我的更详细的信息。"
# )
# TTSWorker.transform(
#     text=text,
#     speech_name="D:/python_works/Labridge/query_wav",
# )
