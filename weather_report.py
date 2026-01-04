# 安装依赖: pip3 install requests
import os
import requests
import json
import datetime

# 多人接收微信号，用逗号分隔
# 例如 GitHub Secrets: OPEN_ID=wxid1,wxid2
openIds = os.environ.get("OPEN_ID").split(",")

# 测试号信息
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")

# 天气模板ID
weather_template_id = os.environ.get("TEMPLATE_ID")


def get_weather_by_code(city_code=None, city_name="太原市小店区"):
    """使用 wttr.in 获取太原小店区天气（稳定、支持GitHub Actions）"""
    url = "https://wttr.in/Taiyuan?format=j1"
    resp = requests.get(url, timeout=10)
    data = resp.json()

    today = data["weather"][0]

    temp = f'{today["avgtempC"]}℃'
    weather = today["hourly"][0]["weatherDesc"][0]["value"]
    wind = today["hourly"][0]["windspeedKmph"] + " km/h"

    return city_name, temp, weather, wind


def get_access_token():
    """获取微信 access_token"""
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appID.strip()}&secret={appSecret.strip()}'
    response = requests.get(url).json()
    access_token = response.get('access_token')
    print("获取 access_token:", access_token)
    return access_token


def get_daily_love():
    """每日一句情话"""
    url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
    r = requests.get(url)
    all_dict = json.loads(r.text)
    sentence = all_dict['returnObj'][0]
    return sentence


def send_weather(access_token, weather):
    """循环发送给每个微信号"""
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
        resp = requests.post(
            f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}',
            json=body
        )
        print(f"{openId.strip()} 推送结果: {resp.text}")


def weather_report():
    """获取天气并推送"""
    access_token = get_access_token()
    weather = get_weather_by_code()
    print(f"天气信息：{weather}")
    send_weather(access_token, weather)


if __name__ == '__main__':
    weather_report()
