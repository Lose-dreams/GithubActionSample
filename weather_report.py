# 安装依赖: pip3 install requests
import os
import requests
import json
import datetime
import time

# 多人接收微信号，用逗号分隔
# 例如 GitHub Secrets: OPEN_ID=oBgkT3QA4nu7IZBtXMCJhsbOL8R8,oBgkT3btpd8TnK2llvaq30bqcsAA
openIds = os.environ.get("OPEN_ID").split(",")

# 测试号信息
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")

# 天气模板ID
weather_template_id = os.environ.get("TEMPLATE_ID")

# 网络请求重试参数
TIMEOUT = 10       # 秒
RETRY = 3          # 次数
RETRY_DELAY = 5    # 秒


def get_weather_by_code(city_code=None, city_name="太原市小店区"):
    """
    使用中国天气网 cityinfo 接口
    返回：地区、温度区间、天气、风向风力
    """
    # 太原市 code：101100101
    url = "http://www.weather.com.cn/data/cityinfo/101100101.html"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()["weatherinfo"]

    # 温度区间，如 -1℃~4℃
    temp = f'{data["temp1"].replace("℃","")}--{data["temp2"].replace("℃","")}摄氏度'

    weather = data["weather"]           # 冻雨
    wind = data["wind"]                 # 南风<3级

    return city_name, temp, weather, wind



def get_access_token():
    """获取微信 access_token，支持重试"""
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appID.strip()}&secret={appSecret.strip()}'
    for attempt in range(RETRY):
        try:
            response = requests.get(url, timeout=TIMEOUT).json()
            access_token = response.get('access_token')
            if access_token:
                print("获取 access_token:", access_token)
                return access_token
            else:
                print(f"获取 access_token 失败: {response}")
                time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"获取 access_token 网络错误，重试中 ({attempt+1}/{RETRY}): {e}")
            time.sleep(RETRY_DELAY)
    raise Exception("无法获取 access_token，请检查网络或配置")


def get_daily_love():
    """每日一句情话，支持重试"""
    url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
    for attempt in range(RETRY):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            all_dict = r.json()
            sentence = all_dict['returnObj'][0]
            return sentence
        except Exception as e:
            print(f"获取每日一句失败，重试中 ({attempt+1}/{RETRY}): {e}")
            time.sleep(RETRY_DELAY)
    return "今日心情：保持微笑~"


def send_weather(access_token, weather):
    """循环发送给每个微信号，支持重试"""
    today = datetime.date.today()
    today_str = today.strftime("%Y年%m月%d日")

    for openId in openIds:
        body = {
            "touser": openId.strip(),
            "template_id": weather_template_id.strip(),
            "url": "https://weixin.qq.com",
            "data": {
                "date": {"value": today_str},
                "region": {"value": weather[0]},
                "weather": {"value": weather[2]},
                "temp": {"value": weather[1]},
                "wind_dir": {"value": weather[3]},
                "today_note": {"value": get_daily_love()}
            }
        }
        for attempt in range(RETRY):
            try:
                resp = requests.post(
                    f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}',
                    json=body,
                    timeout=TIMEOUT
                )
                resp_json = resp.json()
                if resp_json.get("errcode") == 0:
                    print(f"{openId.strip()} 推送成功")
                    break
                else:
                    print(f"{openId.strip()} 推送失败: {resp_json}")
                    time.sleep(RETRY_DELAY)
            except Exception as e:
                print(f"{openId.strip()} 网络错误，重试中 ({attempt+1}/{RETRY}): {e}")
                time.sleep(RETRY_DELAY)
        else:
            print(f"{openId.strip()} 最终推送失败")


def weather_report():
    """获取天气并推送"""
    access_token = get_access_token()
    weather = get_weather_by_code()
    print(f"天气信息：{weather}")
    send_weather(access_token, weather)


if __name__ == '__main__':
    weather_report()
