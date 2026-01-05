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
    优先：中国天气网
    兜底：wttr.in（温柔模板）
    """
    # ========== ① 中国天气网 ==========
    try:
        url = "http://www.weather.com.cn/data/cityinfo/101100101.html"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)

        # 有时会返回空内容或 HTML，必须先判断
        if resp.status_code == 200 and resp.text.strip().startswith("{"):
            data = resp.json()["weatherinfo"]

            weather = data["weather"]   # 冻雨
            temp = (
                f'{data["temp1"].replace("℃","")}'
                f'～{data["temp2"].replace("℃","")}℃'
            )
            wind = data["wind"]         # 南风<3级

            return city_name, temp, weather, wind

        else:
            raise Exception("中国天气网返回非 JSON")

    except Exception as e:
        print("中国天气网失败，启用 wttr.in 兜底：", e)

    # ========== ② wttr.in 兜底 ==========
    try:
        url = "https://wttr.in/Taiyuan?format=j1"
        resp = requests.get(url, timeout=TIMEOUT)
        data = resp.json()

        today = data["weather"][0]
        hour = today["hourly"][0]

        min_t = today["mintempC"]
        max_t = today["maxtempC"]
        weather_en = hour["weatherDesc"][0]["value"]
        wind_dir = hour["winddir16Point"]
        wind_speed = hour["windspeedKmph"]

        # 英文简单转中文（够用、不复杂）
        weather_map = {
            "Partly cloudy": "多云",
            "Cloudy": "阴",
            "Sunny": "晴",
            "Clear": "晴",
            "Light rain": "小雨",
            "Rain": "雨",
            "Snow": "雪"
        }
        weather_cn = weather_map.get(weather_en, weather_en)

        temp = f"{min_t}～{max_t}℃"
        wind = f"{wind_dir}风 {wind_speed}km/h"

        # ⚠️ 这里是你指定的兜底模板
        weather_text = (
            f"今天太原有点冷 ❄️\n"
            f"天气：{weather_cn}\n"
            f"气温：{temp}\n"
            f"风：{wind}\n"
            f"记得多穿一点"
        )

        return city_name, temp, weather_text, wind

    except Exception as e:
        print("wttr.in 兜底也失败：", e)
        return city_name, "--", "天气数据获取失败", "--"



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
