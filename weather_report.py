# weather_report.py
import os
import requests
import json
from bs4 import BeautifulSoup
import datetime
import random
import time

# ========= 配置 =========
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")
openId = os.environ.get("OPEN_ID")
weather_template_id = os.environ.get("TEMPLATE_ID")

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

# ========= 获取天气 =========
def get_weather(my_city):
    urls = [
        "http://www.weather.com.cn/textFC/hb.shtml",
        "http://www.weather.com.cn/textFC/db.shtml",
        "http://www.weather.com.cn/textFC/hd.shtml",
        "http://www.weather.com.cn/textFC/hz.shtml",
        "http://www.weather.com.cn/textFC/hn.shtml",
        "http://www.weather.com.cn/textFC/xb.shtml",
        "http://www.weather.com.cn/textFC/xn.shtml"
    ]
    for url in urls:
        resp = request_with_retry("GET", url)
        text = resp.content.decode("utf-8")
        soup = BeautifulSoup(text, 'html5lib')
        div_conMidtab = soup.find("div", class_="conMidtab")
        tables = div_conMidtab.find_all("table")
        for table in tables:
            trs = table.find_all("tr")[2:]
            for tr in trs:
                tds = tr.find_all("td")
                city_td = tds[-8]
                this_city = list(city_td.stripped_strings)[0]
                if this_city == my_city:
                    high_temp_td = tds[-5]
                    low_temp_td = tds[-2]
                    weather_type_day_td = tds[-7]
                    weather_type_night_td = tds[-4]
                    wind_td_day = tds[-6]
                    wind_td_day_night = tds[-3]

                    high_temp = list(high_temp_td.stripped_strings)[0]
                    low_temp = list(low_temp_td.stripped_strings)[0]
                    weather_typ_day = list(weather_type_day_td.stripped_strings)[0]
                    weather_type_night = list(weather_type_night_td.stripped_strings)[0]

                    wind_day_strs = list(wind_td_day.stripped_strings)
                    wind_day = "".join(wind_day_strs) if wind_day_strs else "--"
                    wind_night_strs = list(wind_td_day_night.stripped_strings)
                    wind_night = "".join(wind_night_strs) if wind_night_strs else "--"

                    temp = f"{low_temp}~{high_temp}摄氏度" if high_temp != "-" else f"{low_temp}摄氏度"
                    weather_typ = weather_typ_day if weather_typ_day != "-" else weather_type_night
                    wind = wind_day if wind_day != "--" else wind_night

                    # 美化风向显示
                    if "无持续风向" in wind:
                        wind += "<3级"
                    else:
                        wind += "（" + "".join([c for c in wind if c.isdigit()]) + "级）" if any(c.isdigit() for c in wind) else ""

                    return this_city, temp, weather_typ, wind
    # 兜底
    return my_city, "0~0摄氏度", "多云", "微风（1级）"

# ========= 获取微信 access_token =========
def get_access_token():
    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appID.strip()}&secret={appSecret.strip()}'
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
            r = request_with_retry("GET", url)
            sentence = r.json().get("returnObj", [""])[0].strip()
            if 4 <= len(sentence) <= 18:
                return sentence
        except Exception as e:
            print("情话获取失败，重试中:", e)
            time.sleep(1)
    return random.choice(LOVE_FALLBACK)

# ========= 推送天气 =========
def send_weather(access_token, weather):
    today = datetime.date.today().strftime("%Y年%m月%d日")
    city, temp, weather_typ, wind = weather

    # 温馨提示
    tips = []
    if "雨" in weather_typ:
        tips.append("记得带伞 ☔")
    if temp:
        min_temp = int(temp.split("~")[0])
        if min_temp <= 1:
            tips.append("注意保暖 🧣")
    tip_text = "；".join(tips)

    body = {
        "touser": openId.strip(),
        "template_id": weather_template_id.strip(),
        "url": "https://weixin.qq.com",
        "data": {
            "date": {"value": today},
            "region": {"value": city},
            "weather": {"value": weather_typ},
            "temp": {"value": temp},
            "wind_dir": {"value": wind},
            "today_note": {"value": get_daily_love()},
            "tip": {"value": tip_text},  # 即使为空也显示
        }
    }

    resp = request_with_retry("POST", f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}', json=body).json()
    print(resp)

# ========= 主入口 =========
def weather_report(city_name):
    access_token = get_access_token()
    weather = get_weather(city_name)
    print(f"天气信息: {weather}")
    send_weather(access_token, weather)

if __name__ == "__main__":
    # 修改这里城市即可
    weather_report("太原市小店区")
