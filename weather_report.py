# 安装依赖: pip3 install requests
import os
import requests
import json
import datetime
import time
import random

# 多人接收微信号，用逗号分隔
# GitHub Secrets 示例: OPEN_ID=oBgkT3QA4nu7IZBtXMCJhsbOL8R8,oBgkT3btpd8TnK2llvaq30bqcsAA
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

# 情话库（短句备用）
short_love_sentences = [
    "今天也要开心哦~",
    "你是我余生的欢喜",
    "愿你被温柔以待",
    "喜欢你，比昨天多一点",
    "小心感冒，注意保暖",
]

def get_weather_from_cma():
    """尝试从中国天气网获取天气信息"""
    try:
        url = "http://www.weather.com.cn/data/sk/101100101.html"  # 太原小店区
        resp = requests.get(url, timeout=TIMEOUT)
        data = resp.json()
        weather_info = data["weatherinfo"]
        city = weather_info["city"]
        temp = f"{weather_info['temp']}℃"
        wind = weather_info["WD"] + " " + weather_info["WS"]
        return city, temp, "未知", wind, "未知", "未知"  # 天气/湿度/降雨概率先兜底
    except:
        return None

def get_weather_by_wttr():
    """使用 wttr.in 作为兜底"""
    url = "https://wttr.in/Taiyuan?format=j1"
    for attempt in range(RETRY):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            data = resp.json()
            today = data["weather"][0]
            city_name = "太原市小店区"
            temp = f"{today['mintempC']}～{today['maxtempC']}℃"
            weather_desc = today["hourly"][0]["weatherDesc"][0]["value"]
            wind = today["hourly"][0]["windspeedKmph"] + " km/h"
            humidity = today["hourly"][0]["humidity"] + "%"
            rain_prob = today["hourly"][0].get("chanceofrain", "0%")
            return city_name, temp, weather_desc, wind, humidity, rain_prob
        except Exception as e:
            print(f"获取 wttr.in 失败，重试中 ({attempt+1}/{RETRY}): {e}")
            time.sleep(RETRY_DELAY)
    return "太原市小店区", "-4～2℃", "多云", "西北风 3km/h", "48%", "10%"

def get_weather_info():
    """获取天气信息，优先中国天气网，再 wttr.in"""
    cma = get_weather_from_cma()
    if cma:
        city, temp, weather, wind, humidity, rain_prob = cma
    else:
        city, temp, weather, wind, humidity, rain_prob = get_weather_by_wttr()

    # 简单温馨提示
    tips = []
    temp_numbers = [int(s) for s in temp.replace("℃","").replace("～","-").split("-") if s.strip("-").isdigit()]
    if temp_numbers:
        avg_temp = sum(temp_numbers)//len(temp_numbers)
        if avg_temp <= 0:
            tips.append("今天有点冷 ❄️")
        elif avg_temp >= 30:
            tips.append("今天比较热 🥵")
    if "雨" in weather:
        tips.append("记得带伞 ☔️")
    tip_text = "，".join(tips) if tips else ""

    # 拼接中文美化
    weather_text = f"{tip_text} 天气：{weather}" if tip_text else f"天气：{weather}"

    return city, temp, weather_text, wind, humidity, rain_prob

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
    """每日一句情话，长度限制80字"""
    try:
        url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
        r = requests.get(url, timeout=TIMEOUT)
        all_dict = r.json()
        sentence = all_dict['returnObj'][0]
        if len(sentence) > 80:
            sentence = random.choice(short_love_sentences)
        return sentence
    except:
        return random.choice(short_love_sentences)

def send_weather(access_token, weather):
    today_str = datetime.date.today().strftime("%Y年%m月%d日")
    city, temp, weather_desc, wind, humidity, rain_prob = weather
    for openId in openIds:
        body = {
            "touser": openId.strip(),
            "template_id": weather_template_id.strip(),
            "url": "https://weixin.qq.com",
            "data": {
                "date": {"value": today_str},
                "region": {"value": city},
                "weather": {"value": weather_desc},
                "temp": {"value": temp},
                "wind_dir": {"value": wind},
                "humidity": {"value": humidity},
                "rain_prob": {"value": rain_prob},
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
    weather = get_weather_info()
    print(f"天气信息：{weather}")
    access_token = get_access_token()
    send_weather(access_token, weather)

if __name__ == '__main__':
    weather_report()
