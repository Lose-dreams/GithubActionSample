# 安装依赖: pip3 install requests
import os
import requests
import json
import datetime
import time

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

def gentle_tip(min_t, max_t, rain):
    """根据温度和降雨生成温柔提醒"""
    min_t = int(min_t)
    max_t = int(max_t)
    rain = int(rain) if str(rain).isdigit() else 0

    if rain >= 50:
        return "今天可能会下雨，出门记得带伞 ☔"
    if min_t <= -5:
        return "今天真的很冷，多穿一点别着凉 🧣"
    if max_t >= 30:
        return "天气有点热，记得多喝水 ☀️"
    return "记得照顾好自己，慢慢来就好 🌤️"

def get_weather_by_code(city_code=None, city_name="太原市小店区"):
    """获取天气信息，优先中国天气网，兜底 wttr.in"""
    for attempt in range(RETRY):
        try:
            # 1️⃣ 尝试中国天气网接口
            url = f"http://www.weather.com.cn/data/sk/101100501.html"  # 太原小店区示例代码
            resp = requests.get(url, timeout=TIMEOUT)
            data = resp.json().get("weatherinfo", {})
            if data:
                weather_cn = data.get("weather", "晴")
                temp1 = data.get("temp1", "-4℃")
                temp2 = data.get("temp2", "2℃")
                wind = data.get("wind", "西北风 3km/h")
                humidity = data.get("SD", "--").replace("%", "")
                rain = data.get("rain", "0")
                tip = gentle_tip(temp1.replace("℃","").replace("～",""), temp2.replace("℃","").replace("～",""), rain)
                weather_text = (
                    f"天气：{weather_cn}\n"
                    f"气温：{temp1}～{temp2}\n"
                    f"风向：{wind}\n"
                    f"湿度：{humidity}%\n"
                    f"降雨概率：{rain}%\n"
                    f"{tip}"
                )
                return city_name, "", weather_text, ""
            else:
                raise Exception("中国天气网返回空数据")
        except Exception as e:
            print(f"获取中国天气网失败，尝试 wttr.in ({attempt+1}/{RETRY}): {e}")
            time.sleep(RETRY_DELAY)

    # 2️⃣ 兜底 wttr.in
    for attempt in range(RETRY):
        try:
            url = "https://wttr.in/Taiyuan?format=j1"
            resp = requests.get(url, timeout=TIMEOUT)
            data = resp.json()
            today = data["weather"][0]
            min_t = today["mintempC"]
            max_t = today["maxtempC"]
            weather_cn = today["hourly"][0]["weatherDesc"][0]["value"]
            wind = today["hourly"][0]["windspeedKmph"] + " km/h"
            humidity = today["hourly"][0].get("humidity", "--")
            rain = today["hourly"][0].get("chanceofrain", "0")
            tip = gentle_tip(min_t, max_t, rain)
            weather_text = (
                f"今天太原有点冷 ❄️\n"
                f"天气：{weather_cn}\n"
                f"气温：{min_t}～{max_t}℃\n"
                f"风：{wind}\n"
                f"湿度：{humidity}%\n"
                f"降雨概率：{rain}%\n"
                f"{tip}"
            )
            return city_name, "", weather_text, ""
        except Exception as e:
            print(f"获取 wttr.in 数据失败，重试中 ({attempt+1}/{RETRY}): {e}")
            time.sleep(RETRY_DELAY)

    raise Exception("获取天气失败，请检查网络")

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
