import requests, json
from requests_toolbelt import MultipartEncoder
import requests
import json
from urllib import request
from bs4 import BeautifulSoup
from http import cookiejar
import urllib
from lxml import html, etree

session = requests.Session()
user_agent = r'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36'


def login(username, password):
    url = 'https://leetcode.com'
    cookies = session.get(url).cookies
    print(cookies)
    for cookie in cookies:
        if cookie.name == 'csrftoken':
            csrftoken = cookie.value

    url = "https://leetcode.com/accounts/login"

    params_data = {
        'csrfmiddlewaretoken': csrftoken,
        'login': username,
        'password': password,
        'next': 'problems',
        'recaptcha_token' : '03AGdBq27lmVN1u_Ox6DldpIM4E-Eo4mTKFYmusj3EWxQlHjg5nK7GqumpRHf8uUFMMBBqgUS5relGqz45ea37sHi7nf6V0zkGZn4Nkl4z5ODHaSC_-z6rce8w-unr7TY3tVPs5uylVPEC47RXa-GMkEgV3TgBAIMs2DhY7U9S1_1dhC9cMCcSWn-OJaY3aaB-9j7EdrMPojzZC3KZrLjQv6qes4xEU02izLb_I-yyHuuH61gPJi_Viyt6VXRgUozG8tzWjBJQ5Hea6Fy7Jv0GHVa76h4yZL9lXijsWBJoiKjqm-EeqrRPW31LfArfhTKFUGh9_2Q3K_5ya_smzB4aDiEFOmbOYC-8hnQPj2UJNT1iE1chGzyuyV-L5zQy-yaoDASmCqgHhlR8LIXxce_kG-6RmJky0ZPcbGKc16_g0Xn-vqVo7DsKDXR7ad7hdcuIxUrUUaxnwhTZu8UvOxQcW5zYkMZIm9Zz_q2hBRcqRKYbbc2msJl3UNTHX4dBv8asngb-2ilcGuQ8'
    }
    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive', 'Referer': 'https://leetcode.com/accounts/login/',
               "origin": "https://leetcode.com"}
    request = MultipartEncoder(params_data)

    headers['Content-Type'] = request.content_type
    html = session.post(url, headers=headers, data=request, timeout=10, allow_redirects=False).text
    print('got the html')
    soup = BeautifulSoup(html, 'html.parser')
    print(soup)
    is_login = session.cookies.get('LEETCODE_SESSION') != None
    return is_login

if __name__ == '__main__':
    login('chrisxny', 'Xny19911006@')