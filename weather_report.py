# weather_report.py
import os
import requests
import datetime
import time
import random

# ========= 配置 =========
OPEN_IDS = os.environ.get("OPEN_ID", "").split(",")
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")

TIMEOUT = 10
RETRY = 3
RETRY_DELAY = 5

# 情话兜底（≤18字）
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

# ========= 格式化 =========
def format_temp(min_t, max_t):
    return f"{min_t}～{max_t}℃"

def wind_dir_from_degree(deg):
    dirs = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    return dirs[int((deg + 22.5) // 45) % 8]

def format_wind(speed, degree):
    speed = int(speed)
    if speed <= 1:
        return "微风"
    return f"{wind_dir_from_degree(degree)} {speed} km/h"

# ========= 获取天气 =========
def get_weather():
    url = "https://wttr.in/Taiyuan?format=j1"
    data = request_with_retry("GET", url).json()

    today = data["weather"][0]
    hour = today["hourly"][0]

    min_t = int(today["mintempC"])
    max_t = int(today["maxtempC"])
    temp = format_temp(min_t, max_t)

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

    wind_speed = hour.get("windspeedKmph", 0)
    wind_degree = hour.get("winddirDegree", 0)
    if wind_degree == "":
        wind_degree = 0
    wind = format_wind(wind_speed, int(wind_degree))

    return "太原市小店区", weather, temp, wind, min_t, max_t

# ========= 获取微信 access_token =========
def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    for _ in range(RETRY):
        r = request_with_retry("GET", url).json()
        if "access_token" in r:
            return r["access_token"]
        print("access_token 获取失败:", r)
        time.sleep(RETRY_DELAY)
    raise Exception("access_token 获取失败")

# ========= 获取每日情话 =========
def get_daily_love():
    url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
    for _ in range(5):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            sentence = r.json().get("returnObj", [""])[0].strip()
            if 4 <= len(sentence) <= 18:
                return sentence
        except Exception as e:
            print("情话获取失败，重试中:", e)
            time.sleep(1)
    return random.choice(LOVE_FALLBACK)

# ========= 温馨提示 =========
def get_tips(weather, min_t, max_t):
    tips = []
    if "雨" in weather:
        tips.append("记得带伞 ☔")
    if min_t <= 1:
        tips.append("注意保暖 🧣")
    return "；".join(tips)

# ========= 推送 =========
def send_weather(token, weather_info):
    today = datetime.date.today().strftime("%Y年%m月%d日")
    city, weather, temp, wind, min_t, max_t = weather_info
    tips = get_tips(weather, min_t, max_t)

    for open_id in OPEN_IDS:
        data = {
            "date": {"value": today},
            "region": {"value": city},
            "weather": {"value": weather},
            "temp": {"value": temp},
            "wind_dir": {"value": wind},
            "today_note": {"value": get_daily_love()},
            "tip": {"value": tips},  # 即使为空也不会报错
        }

        body = {
            "touser": open_id.strip(),
            "template_id": TEMPLATE_ID,
            "data": data,
        }

        resp = request_with_retry(
            "POST",
            f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
            json=body,
        ).json()
        print(open_id, resp)

# ========= 主入口 =========
def main():
    weather = get_weather()
    token = get_access_token()
    send_weather(token, weather)

if __name__ == "__main__":
    main()
