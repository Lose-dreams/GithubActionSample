import os
import requests
import datetime
import time
import random

# ========= 基础配置 =========
OPEN_IDS = os.environ.get("OPEN_ID").split(",")
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")

TIMEOUT = 10
RETRY = 3
RETRY_DELAY = 5

# ========= 情话兜底池（≤18字） =========
LOVE_FALLBACK = [
    "今天也有人偷偷想你",
    "风很冷，但我很暖",
    "你一笑，世界就亮了",
    "慢慢走，我陪你",
    "愿你被温柔以待",
]

# ========= 通用请求重试 =========
def request_with_retry(method, url, **kwargs):
    for i in range(RETRY):
        try:
            return requests.request(method, url, timeout=TIMEOUT, **kwargs)
        except Exception as e:
            print(f"请求失败，重试({i+1}/{RETRY})：{e}")
            time.sleep(RETRY_DELAY)
    raise Exception("网络请求最终失败")

# ========= 天气获取（wttr.in） =========
def get_weather():
    url = "https://wttr.in/Taiyuan?format=j1"
    r = request_with_retry("GET", url)
    data = r.json()

    today = data["weather"][0]
    hour = today["hourly"][0]

    min_t = today["mintempC"]
    max_t = today["maxtempC"]
    temp = f"{min_t}～{max_t}℃"

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
        "Snow": "下雪",
    }
    weather = weather_map.get(weather_en, "多云")

    wind = f"{hour['windspeedKmph']}km/h"
    humidity = f"{hour['humidity']}%"
    rain_prob = f"{hour.get('chanceofrain', '0')}%"

    return (
        "太原市小店区",
        temp,
        weather,
        wind,
        humidity,
        rain_prob,
    )

# ========= 获取微信 access_token =========
def get_access_token():
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    )
    for _ in range(RETRY):
        r = request_with_retry("GET", url).json()
        if "access_token" in r:
            return r["access_token"]
        print("access_token 获取失败：", r)
        time.sleep(RETRY_DELAY)
    raise Exception("access_token 获取失败")

# ========= 每日一句情话（网站 + 自动筛选 ≤18字） =========
def get_daily_love():
    url = "https://v1.hitokoto.cn/?c=h&encode=json"

    for _ in range(5):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            data = r.json()
            sentence = data.get("hitokoto", "").strip()

            # 只接受 4～18 字
            if 4 <= len(sentence) <= 18:
                return sentence
        except Exception as e:
            print("情话获取失败，重试中：", e)
            time.sleep(1)

    return random.choice(LOVE_FALLBACK)

# ========= 推送天气 =========
def send_weather(token, weather):
    today = datetime.date.today().strftime("%Y年%m月%d日")
    city, temp, weather_desc, wind, humidity, rain_prob = weather

    for open_id in OPEN_IDS:
        body = {
            "touser": open_id.strip(),
            "template_id": TEMPLATE_ID,
            "data": {
                "date": {"value": today},
                "region": {"value": city},
                "weather": {"value": weather_desc},
                "temp": {"value": temp},
                "wind_dir": {"value": wind},
                "humidity": {"value": humidity},
                "rain_prob": {"value": rain_prob},
                "today_note": {"value": get_daily_love()},
            },
        }

        r = request_with_retry(
            "POST",
            f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
            json=body,
        ).json()

        print(open_id, r)

# ========= 主入口 =========
def main():
    weather = get_weather()
    token = get_access_token()
    send_weather(token, weather)

if __name__ == "__main__":
    main()
