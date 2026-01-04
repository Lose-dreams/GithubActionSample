import os
import requests
import json
import datetime

# 从测试号信息获取
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")
openId = os.environ.get("OPEN_ID")
weather_template_id = os.environ.get("TEMPLATE_ID")

def get_weather_by_code(city_code=None, city_name="太原市小店区"):
    """
    使用 wttr.in 中文映射，稳定，GitHub Actions 可用
    """
    url = "https://wttr.in/Taiyuan?format=j1"
    resp = requests.get(url, timeout=10)
    data = resp.json()
    today = data["weather"][0]

    # 气温区间
    low = today["mintempC"]
    high = today["maxtempC"]
    temperature = f"{low}--{high}摄氏度"

    # 英文天气 → 中文
    weather_en = today["hourly"][0]["weatherDesc"][0]["value"]
    weather_map = {
        "Sunny": "晴",
        "Partly cloudy": "多云",
        "Cloudy": "阴",
        "Overcast": "阴",
        "Light rain": "小雨",
        "Moderate rain": "中雨",
        "Heavy rain": "大雨",
        "Light snow": "小雪",
        "Moderate snow": "中雪",
        "Heavy snow": "大雪",
        "Light freezing rain": "冻雨",
        "Freezing rain": "冻雨",
    }
    weather = weather_map.get(weather_en, weather_en)

    # 风向 + 风级
    wind_en = today["hourly"][0]["winddir16Point"]
    wind_speed = int(today["hourly"][0]["windspeedKmph"])
    wind_map = {
        "N": "北风",
        "NE": "东北风",
        "E": "东风",
        "SE": "东南风",
        "S": "南风",
        "SW": "西南风",
        "W": "西风",
        "NW": "西北风"
    }
    wind_dir = wind_map.get(wind_en, wind_en)

    # 风速对应风级
    if wind_speed < 6:
        wind = f"{wind_dir}<3级"
    elif wind_speed < 12:
        wind = f"{wind_dir}3-4级"
    elif wind_speed < 20:
        wind = f"{wind_dir}4-5级"
    else:
        wind = f"{wind_dir}5-6级"

    return city_name, temperature, weather, wind


def get_access_token():
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appID.strip()}&secret={appSecret.strip()}'
    response = requests.get(url).json()
    access_token = response.get('access_token')
    return access_token


def get_daily_love():
    # 每日一句情话
    url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
    r = requests.get(url)
    all_dict = json.loads(r.text)
    return all_dict['returnObj'][0]


def send_weather(access_token, weather):
    today_str = datetime.date.today().strftime("%Y年%m月%d日")
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
    url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'
    print(requests.post(url, json.dumps(body)).text)


def weather_report():
    access_token = get_access_token()
    weather = get_weather_by_code()
    print(f"今天:{datetime.date.today().strftime('%Y年%m月%d日')}")
    print(f"地区:{weather[0]}")
    print(f"天气:{weather[2]}")
    print(f"气温:{weather[1]}")
    print(f"风向:{weather[3]}")
    send_weather(access_token, weather)


if __name__ == '__main__':
    weather_report()
