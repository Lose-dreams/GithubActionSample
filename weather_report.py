# 安装依赖 pip3 install requests html5lib bs4 schedule
import os
import requests
import json


# 从测试号信息获取
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")
# 收信人ID即 用户列表中的微信号
openId = os.environ.get("OPEN_ID")
# 天气预报模板ID
weather_template_id = os.environ.get("TEMPLATE_ID")

def get_weather_by_code(city_code, city_name="太原市小店区"):
    """
    使用 itboy 天气接口（GitHub Actions 可用）
    """
    url = "https://t.weather.itboy.net/api/weather/city/101100107"
    resp = requests.get(url, timeout=10)
    data = resp.json()["data"]

    temp = f'{data["wendu"]}℃'
    weather = data["forecast"][0]["type"]
    wind = data["forecast"][0]["fx"] + data["forecast"][0]["fl"]

    return city_name, temp, weather, wind




def get_access_token():
    # 获取access token的url
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}' \
        .format(appID.strip(), appSecret.strip())
    response = requests.get(url).json()
    print(response)
    access_token = response.get('access_token')
    return access_token


def get_daily_love():
    # 每日一句情话
    url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
    r = requests.get(url)
    all_dict = json.loads(r.text)
    sentence = all_dict['returnObj'][0]
    daily_love = sentence
    return daily_love


def send_weather(access_token, weather):
    # touser 就是 openID
    # template_id 就是模板ID
    # url 就是点击模板跳转的url
    # data就按这种格式写，time和text就是之前{{time.DATA}}中的那个time，value就是你要替换DATA的值

    import datetime
    today = datetime.date.today()
    today_str = today.strftime("%Y年%m月%d日")

    body = {
        "touser": openId.strip(),
        "template_id": weather_template_id.strip(),
        "url": "https://weixin.qq.com",
        "data": {
            "date": {
                "value": today_str
            },
            "region": {
                "value": weather[0]
            },
            "weather": {
                "value": weather[2]
            },
            "temp": {
                "value": weather[1]
            },
            "wind_dir": {
                "value": weather[3]
            },
            "today_note": {
                "value": get_daily_love()
            }
        }
    }
    url = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}'.format(access_token)
    print(requests.post(url, json.dumps(body)).text)



def weather_report():
    # 1. 获取 access_token
    access_token = get_access_token()

    # 2. 获取 太原市小店区 天气（区县级）
    weather = get_weather_by_code(
        city_code="101100107",
        city_name="太原市小店区"
    )

    print(f"天气信息：{weather}")

    # 3. 推送微信模板消息
    send_weather(access_token, weather)




if __name__ == '__main__':
    weather_report()

