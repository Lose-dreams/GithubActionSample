import os
import requests
import datetime
import random
import time

# ========= 配置 ==========
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
OPEN_ID_LIST = os.environ.get("OPEN_ID").split(",")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID")
AMAP_KEY = os.environ.get("AMAP_KEY")

TIMEOUT = 10
RETRY = 3
RETRY_DELAY = 5

CITY = "太原市小店区"

LOVE_FALLBACK = [
    "今天也有人偷偷想你",
    "风有点冷，但我想你",
    "慢慢走，我陪你",
    "愿你被温柔以待",
    "今天也要开心",
]

# ========= 通用请求重试 ==========
def request_with_retry(method, url, **kwargs):
    for i in range(RETRY):
        try:
            return requests.request(method, url, timeout=TIMEOUT, **kwargs)
        except Exception as e:
            print(f"请求失败，重试({i+1}/{RETRY})：{e}")
            time.sleep(RETRY_DELAY)
    raise Exception("网络请求失败")

# ========= 高德天气 ==========
def get_weather():
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "key": AMAP_KEY,
        "city": "小店区",
        "extensions": "all",
    }
    data = request_with_retry("GET", url, params=params).json()
    forecast = data["forecasts"][0]["casts"][0]

    weather_desc = forecast["dayweather"]
    temp = f"{forecast['nighttemp']}~{forecast['daytemp']}℃"
    wind = f"{forecast['daywind']}风{forecast['daypower']}级"

    # ===== 温馨提示 =====
    tips = []
    if "雨" in weather_desc or "雪" in weather_desc:
        tips.append("记得带伞 ☔")
    try:
        min_temp = int(forecast['nighttemp'])
        if min_temp <= 1:
            tips.append("注意保暖 🧣")
    except:
        pass
    tip_text = "；".join(tips) if tips else ""

    return CITY, temp, weather_desc, wind, tip_text

# ========= access_token ==========
def get_access_token():
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    )
    for _ in range(RETRY):
        r = request_with_retry("GET", url).json()
        if "access_token" in r:
            return r["access_token"]
        time.sleep(RETRY_DELAY)
    raise Exception("access_token 获取失败")

# ========= 每日情话 ==========
def get_daily_love():
    try:
        r = request_with_retry(
            "GET",
            "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
        )
        text = r.json().get("returnObj", [""])[0].strip()
        if 4 <= len(text) <= 16:
            return text
    except:
        pass
    return random.choice(LOVE_FALLBACK)

# ========= 发送模板消息 ==========
def send_weather(token, weather):
    today = datetime.date.today().strftime("%Y年%m月%d日")
    city, temp, weather_desc, wind, tip_text = weather

    for open_id in OPEN_ID_LIST:
        body = {
            "touser": open_id.strip(),
            "template_id": TEMPLATE_ID,
            "data": {
                "date": {"value": today},
                "region": {"value": city},
                "weather": {"value": f"{weather_desc}，气温{temp}，{wind}🌬"},
                "today_note": {"value": get_daily_love()},
                "tip": {"value": tip_text}
            }
        }
        resp = request_with_retry(
            "POST",
            f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
            json=body
        ).json()
        print(open_id, resp)

# ========= 主入口 ==========
def weather_report():
    token = get_access_token()
    weather = get_weather()
    print("天气信息:", weather)
    send_weather(token, weather)

if __name__ == "__main__":
    weather_report()
