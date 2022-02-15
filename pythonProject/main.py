# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import requests
import json
from urllib import request
from bs4 import BeautifulSoup
from http import cookiejar
import urllib
from lxml import html, etree


def get_vaccine_city():
    # Use a breakpoint in the code line below to debug your script.
    home_url = 'https://scheduling.coronavirus.in.gov'
    location_url = 'https://scheduling.coronavirus.in.gov/Home/LocationSelection'
    session = requests.session()
    tokenRequest = session.get(location_url)
    parser = etree.HTMLParser()
    tree = etree.fromstring(tokenRequest.text, parser)
    verificationToken = tree.xpath('//form//input[@name="__RequestVerificationToken"]/@value')[0]
    print(verificationToken)
    sessionCookies = tokenRequest.cookies
    payload = {'ZipCode': '46123', 'IsSecondDosage' : 'False', '__RequestVerificationToken': verificationToken}
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36', 'content-type'
    : 'application/x-www-form-urlencoded', 'referer':location_url, 'origin':'https://scheduling.coronavirus.in.gov'}
    html = session.post(location_url, data=payload, headers=headers, cookies=sessionCookies).text
    print('got the html')
    soup = BeautifulSoup(html, 'html.parser')
    list = []
    for link in soup.find_all("a", class_="basic-btn"):
        list.append(link.get('href'))
        print(link.get('href'))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    get_vaccine_city()



