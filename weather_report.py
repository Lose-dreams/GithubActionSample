import os
import requests
import datetime
import random
import time

# ========= 配置 ==========
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
OPEN_ID = os.environ.get("OPEN_ID")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")

TIMEOUT = 10
RETRY = 3
RETRY_DELAY = 5

LOVE_FALLBACK = [
    "今天也有人偷偷想你",
    "风很冷，但我很暖",
    "你一笑，世界就亮了",
    "慢慢走，我陪你",
    "愿你被温柔以待",
]

# ========= 通用请求重试 ==========
def request_with_retry(method, url, **kwargs):
    for i in range(RETRY):
        try:
            return requests.request(method, url, timeout=TIMEOUT, **kwargs)
        except Exception as e:
            print(f"请求失败，重试({i+1}/{RETRY})：{e}")
            time.sleep(RETRY_DELAY)
    raise Exception("网络请求最终失败")

# ========= 获取天气（wttr.in） ==========
def get_weather():
    url = "https://wttr.in/Taiyuan?format=j1"
    r = request_with_retry("GET", url)
    data = r.json()

    today = data["weather"][0]
    hour = today["hourly"][0]

    min_t = today["mintempC"]
    max_t = today["maxtempC"]
    temp = f"{min_t}~{max_t}℃"

    weather_en = hour["weatherDesc"][0]["value"]
    weather_map = {
        "Clear": "晴",
        "Sunny": "晴",
        "Partly Cloudy": "多云",
        "Cloudy": "阴",
        "Overcast": "阴",
        "Light rain": "小雨",
        "Moderate rain": "中雨",
        "Heavy rain": "大雨",
        "Showers": "阵雨",
        "Snow": "下雪",
    }
    weather_desc = weather_map.get(weather_en, "多云")

    # 风速美化
    wind_kph = int(hour["windspeedKmph"])
    if wind_kph <= 5:
        wind = "微风（1级）"
    elif wind_kph <= 11:
        wind = "轻风（2级）"
    else:
        wind = f"{hour['winddir']}（{wind_kph//3}级）"

    humidity = f"{hour['humidity']}%"
    rain_prob = f"{hour.get('chanceofrain','0')}%"

    return "太原市小店区", temp, weather_desc, wind, humidity, rain_prob

# ========= 获取微信 access_token ==========
def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID.strip()}&secret={APP_SECRET.strip()}"
    for _ in range(RETRY):
        r = request_with_retry("GET", url).json()
        if "access_token" in r:
            return r["access_token"]
        print("access_token 获取失败:", r)
        time.sleep(RETRY_DELAY)
    raise Exception("access_token 获取失败")

# ========= 获取每日情话 ==========
def get_daily_love():
    url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
    for _ in range(5):
        try:
            r = request_with_retry("GET", url)
            sentence = r.json().get("returnObj", [""])[0].strip()
            if 4 <= len(sentence) <= 18:
                return sentence
        except Exception as e:
            print("情话获取失败，重试中:", e)
            time.sleep(1)
    return random.choice(LOVE_FALLBACK)

# ========= 发送微信模板消息 ==========
def send_weather(token, weather):
    today = datetime.date.today().strftime("%Y年%m月%d日")
    city, temp, weather_desc, wind, humidity, rain_prob = weather

    # 温馨提示
    tips = []
    if "雨" in weather_desc:
        tips.append("记得带伞 ☔")
    try:
        min_temp = int(temp.split("~")[0].replace("℃",""))
        if min_temp <= 1:
            tips.append("注意保暖 🧣")
    except:
        pass
    tip_text = "；".join(tips)

    body = {
        "touser": OPEN_ID.strip(),
        "template_id": TEMPLATE_ID.strip(),
        "url": "https://weixin.qq.com",
        "data": {
            "title": {"value": "小雷老师的专属天气预报"},
            "date": {"value": today},
            "region": {"value": city},
            "weather": {"value": weather_desc},
            "temp": {"value": temp},
            "wind_dir": {"value": wind},
            "today_note": {"value": get_daily_love()},
            "tip": {"value": tip_text or ""}  # 保证 tip 不为空
        }
    }

    resp = request_with_retry(
        "POST",
        f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
        json=body
    ).json()
    print(resp)

# ========= 主入口 ==========
def weather_report():
    token = get_access_token()
    weather = get_weather()
    print("天气信息:", weather)
    send_weather(token, weather)

if __name__ == "__main__":
    weather_report()
