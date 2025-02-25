# -*- coding: utf-8 -*-
"""FINAL_yesterday.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1QXS6vBt8VStVsq4ze9TDb7QcPWTXvXDd

**0. 라이브러리 설치 및 호출**
"""

!pip install konlpy
!pip install transformers
!pip install sentencepiece

import requests
import bs4
import time
import random
from datetime import datetime
import pandas as pd
import pytz
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from konlpy.tag import Okt
from transformers import BartForConditionalGeneration, PreTrainedTokenizerFast
from sentence_transformers import SentenceTransformer, util
import torch

input_string = "datetime("+ input("'YYYY,MM,DD,HH,mm' 형태로 입력하세요.(01월같은 경우 1만 입력)")+")"
yesterday = eval(input_string)

"""**1. 크롤링 파트 시작 : 공통 코드**"""

pd.set_option('display.max_colwidth', None)

def is_new_article(category_last_date_time, date,category):
    return date > category_last_date_time.get(category)

def make_dataframes(category_text):
    dataframes_ = {}
    for key in category_text.keys():
        if not category_text[key]:
            continue
        dataframes_[key] = pd.DataFrame(category_text[key], columns = ["시간","제목","본문"])

    return dataframes_

def save_to_csv(dataframes_, journal):
    date_grouped_articles = {}

    for key, df in dataframes_.items():
        if df.empty:
            continue

        for _, row in df.iterrows():

            date_str = row['시간'].strftime("%Y%m%d")

            if date_str not in date_grouped_articles:
                date_grouped_articles[date_str] = {}

            if key not in date_grouped_articles[date_str]:
                date_grouped_articles[date_str][key] = []

            date_grouped_articles[date_str][key].append(row)

    for date_str, categories in date_grouped_articles.items():
        for category, articles in categories.items():
            new_df = pd.DataFrame(articles)

            filename = f"{category}_{journal}.csv"

            path = filename
            try:
                existing_df = pd.read_csv(path, encoding='utf-8-sig')

                existing_df['시간'] = pd.to_datetime(existing_df['시간'])

                merged_df = pd.concat([existing_df, new_df], ignore_index=True)

                merged_df = merged_df.drop_duplicates(subset=['시간', '제목'], keep='first')

                final_df = merged_df.sort_values(by='시간', ascending=True)

            except FileNotFoundError:
                final_df = new_df.sort_values(by='시간', ascending=True)

            final_df.to_csv(path, index=False, encoding="utf-8-sig")

"""**1-1. 한겨레**"""

def process2(category_last_date_time, category_dict):
    category_title_link = {}
    headers = {
        "user-agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    for category, category_link in category_dict.items() :
        base_link = category_link + "?page={}"
        title_and_link = []
        page_number = 1
        done = False
        while True:
            formatted_link = base_link.format(page_number)

            res = requests.get(formatted_link,headers= headers)
            soup = bs4.BeautifulSoup(res.text, "lxml")

            article_list = soup.select(
                "div.section_left__5BOCT > div > ul > li.ArticleList_item___OGQO > article > div > div > a")
            for i, a in enumerate(article_list) :
                title = a.find("div",class_ = "title").get_text().strip()
                url = a.get("href")
                url = "https://www.hani.co.kr" + url

                if i == 14:
                    nres = requests.get(url,headers= headers)
                    nsoup = bs4.BeautifulSoup(nres.text,"lxml")

                    date = nsoup.select(
                        "ul.ArticleDetailView_dateList__tniXJ > li.ArticleDetailView_dateListItem__mRc3d > span")
                    if len(date) == 0 :
                      pass
                    else :
                      date = date[1].get_text(strip = True)
                      date = datetime.strptime(date, "%Y-%m-%d %H:%M")

                    if not is_new_article(category_last_date_time, date,category):
                        done = True
                        break

                title_and_link.append([title,url])

            if done:
                break
            page_number += 1

            time.sleep(random.uniform(0,1))

        category_title_link[category] = title_and_link
    return category_title_link

def process3(category_last_date_time, category_title_link):
    headers = {
        "user-agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    category_text = {}
    for category, title_and_link in category_title_link.items() :
        article = []
        for title,url in title_and_link:
            res = requests.get(url,headers= headers)
            soup = bs4.BeautifulSoup(res.text,"lxml")

            date = soup.select(
                "ul.ArticleDetailView_dateList__tniXJ > li.ArticleDetailView_dateListItem__mRc3d > span")
            if len(date) == 0 :
              pass
            else :
              date = date[1].get_text(strip = True)
              date = datetime.strptime(date, "%Y-%m-%d %H:%M")

            if not is_new_article(category_last_date_time, date,category):
                break

            try:
                text_elements = soup.select("div.article-text > p.text")
                full_text = ""
                for i in range(len(text_elements)-1):
                    full_text += text_elements[i].get_text().strip()
                article.append([date,title,full_text])

            except IndexError as e:
                continue

            time.sleep(random.uniform(0,1))
        category_text[category] = article
    return category_text

def main(yesterday) :
  category_last_date_time = {category : yesterday for category in ["정치","사회","경제","국제"]}
  category_dict = {
        "정치":"https://www.hani.co.kr/arti/politics",
        "사회":"https://www.hani.co.kr/arti/society",
        "경제":"https://www.hani.co.kr/arti/economy",
        "국제":"https://www.hani.co.kr/arti/international"
  }
  category_title_link= process2(category_last_date_time, category_dict)
  category_text = process3(category_last_date_time, category_title_link)

  dataframes_ = make_dataframes(category_text)
  journal = "한겨레"
  save_to_csv(dataframes_, journal)
  print("Task executed!")

main(yesterday)

"""**1-2. 중앙일보**"""

def process1():
    headers = {"user-agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
    res = requests.get("https://www.joongang.co.kr/",headers = headers)
    soup = bs4.BeautifulSoup(res.text, "lxml")
    category_wide = soup.select("li.nav_item > a")

    category_dict = {}

    for i,a in enumerate(category_wide) :
        if i in range(1,5):
            title = a.get_text().strip()
            url = a.get("href")
            category_dict[title] = url
    return category_dict

def process2(category_last_date_time, category_dict):
    headers = {"user-agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
    category_title_link = {}

    for category, category_link in category_dict.items() :
        base_link = category_link + "?page={}"
        title_and_link = []
        page_number = 1
        done = False
        while True:
            formatted_link = base_link.format(page_number)

            res = requests.get(formatted_link, headers = headers)
            soup = bs4.BeautifulSoup(res.text, "lxml")

            article_list = soup.select("div.contents_bottom li.card h2.headline a")
            for i, a in enumerate(article_list) :
                title = a.get_text().strip()
                url = a.get("href")

                if i == 23:
                    nres = requests.get(url, headers = headers)
                    nsoup = bs4.BeautifulSoup(nres.text,"lxml")

                    try:
                        date = nsoup.select("p.date time[itemprop=\"datePublished\"]")
                        date_str = date[0].get("datetime")
                        date = datetime.strptime(date_str,"%Y-%m-%dT%H:%M:%S%z")
                        date = date.replace(tzinfo = None)
                        if not is_new_article(category_last_date_time, date,category):
                            done = True
                            break
                    except ValueError as e:
                            continue

                title_and_link.append([title,url])

            if done:
                break
            page_number += 1

        category_title_link[category] = title_and_link
    return category_title_link

def process3(category_last_date_time, category_title_link):
    headers = {"user-agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
    category_text = {}
    for category, title_and_link in category_title_link.items() :
        article = []
        for title,url in title_and_link:
            res = requests.get(url,headers = headers)
            soup = bs4.BeautifulSoup(res.text,"lxml")

            date = soup.select("p.date time[itemprop=\"datePublished\"]")

            date_str = date[0].get("datetime")
            date = datetime.strptime(date_str,"%Y-%m-%dT%H:%M:%S%z")
            date = date.replace(tzinfo = None)

            if not is_new_article(category_last_date_time, date,category):
                break

            try:
                text_elements = soup.select("p[data-divno]")
                full_text = ""
                for i in range(len(text_elements)):
                    full_text += text_elements[i].get_text().strip()

                article.append([date,title,full_text])

            except IndexError as e:
                continue

            time.sleep(random.uniform(0,2))
        category_text[category] = article
    return category_text

def main(yesterday) :
  category_last_date_time = {category : yesterday for category in ["정치","경제","사회","국제"]}
  category_dict = process1()
  category_title_link= process2(category_last_date_time, category_dict)
  category_text = process3(category_last_date_time, category_title_link)

  dataframes_ = make_dataframes(category_text)
  journal = '중앙일보'
  save_to_csv(dataframes_, journal)

  print("Task executed!")

main(yesterday)

"""**1-3. 뉴시스**"""

def process2(category_last_date_time,category_dict):
    category_title_link = {}

    for category, category_link in category_dict.items() :
        base_link = category_link
        title_and_link = []
        page_number = 1
        done = False
        while True:
            formatted_link = base_link.format(page_number)

            res = requests.get(formatted_link)
            soup = bs4.BeautifulSoup(res.text, "lxml")

            article_list = soup.select(
                "div.article > ul.articleList2 > li > div.boxStyle05 > div.txtCont > p.tit >a")
            for i, a in enumerate(article_list) :
                title = a.get_text().strip()
                if title.startswith("["):
                    continue
                url = a.get("href")
                url = "https://www.newsis.com" + url

                if i == 19:
                    nres = requests.get(url)
                    nsoup = bs4.BeautifulSoup(nres.text,"lxml")

                    date = nsoup.select(
                        "div.infoLine > div.left >p.txt > span")

                    date = date[0].get_text(strip = True)

                    final_date = ""

                    for c in date:
                        if c in ["등","록"," "]:
                            continue
                        final_date += c

                    date = datetime.strptime(final_date, "%Y.%m.%d%H:%M:%S")

                    if not is_new_article(category_last_date_time,date,category):
                        done = True
                        break

                title_and_link.append([title,url])

            if done:
                break
            page_number += 1

            time.sleep(random.uniform(0,1))

        category_title_link[category] = title_and_link
    return category_title_link

def process3(category_last_date_time, category_title_link):
    category_text = {}
    for category, title_and_link in category_title_link.items() :
        article = []
        for title,url in title_and_link:
            res = requests.get(url)
            soup = bs4.BeautifulSoup(res.text,"lxml")

            date = soup.select(
                "div.infoLine > div.left >p.txt > span")

            date = date[0].get_text(strip = True)

            final_date = ""

            for c in date:
                if c in ["등","록"," "]:
                    continue
                final_date += c

            date = datetime.strptime(final_date, "%Y.%m.%d%H:%M:%S")

            if not is_new_article(category_last_date_time, date,category):
                break

            try:
                for t in soup.find_all('div',class_="thumCont"):
                    t.extract()
                for s in soup.find_all('div',class_="summury"):
                    s.extract()
                text_elements = soup.select("div.view > div.viewer > article")


                full_text = ""

                full_text = text_elements[0].get_text().strip()
                full_text = full_text.replace("\n","")
                full_text = full_text.replace("\r","")

                lst = full_text.split("◎공감언론 뉴시스")
                full_text = lst[0]
                lst = full_text.split("기자 = ")
                full_text = lst[1]

                article.append([date,title,full_text])

            except IndexError as e:
                continue

            time.sleep(random.uniform(0,1))
        category_text[category] = article
    return category_text

def main(yesterday) :
  category_last_date_time = {category : yesterday for category in ["정치","사회","경제","국제"]}

  category_dict = {
  "정치": "https://www.newsis.com/politic/list/?cid=10300&scid=10301&page={}",
  "경제": "https://www.newsis.com/economy/list/?cid=10400&scid=10401&page={}",
  "사회": "https://www.newsis.com/society/list/?cid=10200&scid=10201&page={}",
  "국제": "https://www.newsis.com/world/list/?cid=10100&scid=10101&page={}"
  }

  category_title_link = process2(category_last_date_time, category_dict)
  category_text = process3(category_last_date_time, category_title_link)
  dataframes_ = make_dataframes(category_text)
  journal = '뉴시스'
  save_to_csv(dataframes_, journal)

  print("Task executed!")

main(yesterday)

"""**1-4. 동아일보**"""

def process1():
    res = requests.get("https://www.donga.com/")
    soup = bs4.BeautifulSoup(res.text, "lxml")
    category_wide = soup.select("li.nav_node > a")

    category_dict = {}

    for i,a in enumerate(category_wide) :
        if i in range(1,5):
            title = a.get_text().strip()
            url = a.get("href")
            category_dict[title] = url
    return category_dict

def process2(category_last_date_time, category_dict):
    category_title_link = {}

    for category, category_link in category_dict.items() :
        base_link = category_link + "?p={}&prod=news&ymd=&m="
        title_and_link = []
        article_number = 1
        done = False
        while True:
            formatted_link = base_link.format(article_number)

            res = requests.get(formatted_link)
            soup = bs4.BeautifulSoup(res.text, "lxml")

            article_list = soup.select("section.sub_news_sec > ul.row_list article div.news_body h4 a")
            for i, a in enumerate(article_list) :
                title = a.get_text().strip()
                url = a.get("href")

                if i == 9:
                    nres = requests.get(url)
                    nsoup = bs4.BeautifulSoup(nres.text,"lxml")

                    date = nsoup.select("ul.news_info span[aria-hidden=\"true\"]")
                    date = date[0].get_text(strip = True)
                    date = datetime.strptime(date, "%Y-%m-%d %H:%M")

                    if not is_new_article(category_last_date_time, date,category):
                        done = True
                        break

                title_and_link.append([title,url])

            if done:
                break
            article_number += 10

            time.sleep(random.uniform(0,1))

        category_title_link[category] = title_and_link
    return category_title_link

def process3(category_last_date_time, category_title_link):
    category_text = {}
    for category, title_and_link in category_title_link.items() :
        article = []
        for title,url in title_and_link:
            res = requests.get(url)
            soup = bs4.BeautifulSoup(res.text,"lxml")

            date = soup.select("ul.news_info span[aria-hidden=\"true\"]")
            date = date[0].get_text(strip = True)
            date = datetime.strptime(date, "%Y-%m-%d %H:%M")

            if not is_new_article(category_last_date_time,date,category):
                break

            try:
                text_element = soup.select("section.news_view")[0]
                for f in text_element.find_all('figure'):
                    f.extract()
                text = text_element.get_text().strip()
                article.append([date,title,text])

            except IndexError as e:
                continue

            time.sleep(random.uniform(0,1))
        category_text[category] = article
    return category_text

def main(yesterday) :
  category_last_date_time = {category : yesterday for category in ["정치","경제","국제","사회"]}
  category_dict = process1()
  category_title_link= process2(category_last_date_time, category_dict)
  category_text = process3(category_last_date_time, category_title_link)

  dataframes_ = make_dataframes(category_text)
  journal = '동아일보'
  save_to_csv(dataframes_, journal)

  print("Task executed!")

main(yesterday)

"""**1-5. 오마이**"""

def process2(category_last_date_time, category_dict):
    category_title_link = {}

    for category, category_link in category_dict.items() :
        base_link = category_link + "&pageno={}"
        title_and_link = []
        page_number = 1
        done = False
        while True:
            formatted_link = base_link.format(page_number)

            res = requests.get(formatted_link)
            soup = bs4.BeautifulSoup(res.text, "lxml")

            article_list = soup.select(
                "div.content > ul.list_type1 >li >div.news_list > div.cont dt >a")
            for i, a in enumerate(article_list) :
                title = a.get_text().strip()
                if title.startswith("["):
                    continue
                url = a.get("href")
                url = "https://www.ohmynews.com" + url

                if i == 19:
                    nres = requests.get(url)
                    nsoup = bs4.BeautifulSoup(nres.text,"lxml")

                    date = nsoup.select(
                        "div.info_data > div")

                    date = date[0].get_text(strip = True)
                    date = date.split("최종 업데이트")[0]
                    final_date = ""

                    for c in date:
                        if c == "l":
                            continue
                        final_date+=c
                    final_date = "20"+final_date
                    date = datetime.strptime(final_date, "%Y.%m.%d %H:%M")

                    if not is_new_article(category_last_date_time,date,category):
                        done = True
                        break

                title_and_link.append([title,url])

            if done:
                break
            page_number += 1

            time.sleep(random.uniform(0,2))

        category_title_link[category] = title_and_link
    return category_title_link

def process3(category_last_date_time, category_title_link):
    category_text = {}
    for category, title_and_link in category_title_link.items() :
        article = []
        for title,url in title_and_link:
            res = requests.get(url)
            soup = bs4.BeautifulSoup(res.text,"lxml")

            date = soup.select(
                "div.newstitle >div.info_data > div")
            if len(date) == 0 :
              pass
            else :
              date = date[0].get_text(strip = True)
              date = date.split("최종 업데이트")[0]
              final_date = ""

            for c in date:
                if c == "l":
                    continue
                final_date+=c
            if final_date[1] != '0' :
              final_date = "20"+final_date
            date = datetime.strptime(final_date, "%Y.%m.%d %H:%M")

            if not is_new_article(category_last_date_time, date,category):
                break

            try:
                text_elements = soup.select("div.content > div.newswrap > div.news_body > div.news_view > div.article_view > div.at_contents")
                for f in soup.find_all('figure'):
                    f.extract()
                full_text = ""
                for i in range(len(text_elements)):
                    content = text_elements[i].get_text().strip()
                    if content:
                        full_text += content
                    else:
                        pass
                full_text = full_text.replace("\n","")
                article.append([date,title,full_text])

            except IndexError as e:
                continue

            time.sleep(random.uniform(0,1))
        category_text[category] = article
    return category_text

def main(yesterday) :
  category_last_date_time = {category : yesterday for category in ["정치","사회","경제","국제"]}

  category_dict = {
      "정치":"https://www.ohmynews.com/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0400",
      "사회":"https://www.ohmynews.com/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0200",
      "경제":"https://www.ohmynews.com/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0300",
      "국제":"https://www.ohmynews.com/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0600"
  }
  category_title_link= process2(category_last_date_time, category_dict)
  category_text = process3(category_last_date_time,category_title_link)

  dataframes_ = make_dataframes(category_text)
  journal = '오마이'
  save_to_csv(dataframes_, journal)

  print("Task executed!")

main(yesterday)

"""**1-6, 서울일보**"""

def process2(category_last_date_time,category_dict):
    category_title_link = {}

    for category, category_link in category_dict.items() :
        base_link = category_link
        title_and_link = []
        page_number = 1
        done = False
        while True:
            formatted_link = base_link.format(page_number)

            res = requests.get(formatted_link)
            soup = bs4.BeautifulSoup(res.text, "lxml")

            article_list = soup.select(
                "ul.type2 > li > div.view-cont > h4.titles > a")
            for i, a in enumerate(article_list) :
                title = a.get_text().strip()
                url = a.get("href")
                url = "https://www.seoulilbo.com" + url

                if i == 19:
                    nres = requests.get(url)
                    nsoup = bs4.BeautifulSoup(nres.text,"lxml")

                    date = nsoup.select(
                        "div.info-box > ul.infomation > li")
                    date = date[1].get_text().strip()
                    only_date = ""
                    for c in date:
                        if c in ["입","력"," "]:
                            continue
                        only_date += c

                    date = datetime.strptime(only_date, "%Y.%m.%d%H:%M")

                    if not is_new_article(category_last_date_time,date,category):
                        done = True
                        break

                title_and_link.append([title,url])

            if done:
                break
            page_number += 1

            time.sleep(random.uniform(0,1))

        category_title_link[category] = title_and_link
    return category_title_link

def process3(category_last_date_time, category_title_link):
    category_text = {}
    for category, title_and_link in category_title_link.items() :
        article = []
        for title,url in title_and_link:
            res = requests.get(url)
            soup = bs4.BeautifulSoup(res.text,"lxml")

            date = soup.select(
                "div.info-box > ul.infomation > li")
            date = date[1].get_text().strip()
            only_date = ""
            for c in date:
                if c in ["입","력"," "]:
                    continue
                only_date += c

            date = datetime.strptime(only_date, "%Y.%m.%d%H:%M")

            if not is_new_article(category_last_date_time, date,category):
                break

            try:
                text_elements = soup.select("div.article-body > article#article-view-content-div >p")
                full_text = ""
                for i in range(len(text_elements)-1):
                    full_text += text_elements[i].get_text().strip()
                article.append([date,title,full_text])


            except IndexError as e:
                continue

            time.sleep(random.uniform(0,1))
        category_text[category] = article
    return category_text

def main(yesterday) :
  category_last_date_time = {category : yesterday for category in ["정치","경제","사회"]}

  category_dict = {
      "정치":"https://www.seoulilbo.com/news/articleList.html?page={}&total=12445&box_idxno=&sc_sub_section_code=S2N56&view_type=sm",
      "사회":"https://www.seoulilbo.com/news/articleList.html?page={}&total=59163&box_idxno=&sc_sub_section_code=S2N65&view_type=sm",
      "경제":"https://www.seoulilbo.com/news/articleList.html?page={}&total=20072&box_idxno=&sc_sub_section_code=S2N61&view_type=sm",
      }

  category_title_link= process2(category_last_date_time, category_dict)
  category_text = process3(category_last_date_time,category_title_link)

  dataframes_ = make_dataframes(category_text)
  journal = '서울일보'
  save_to_csv(dataframes_, journal)

  print("Task executed!")

main(yesterday)

"""**2. 크롤링 파트 종료 : concat**"""

eco_new = pd.read_csv("경제_뉴시스.csv")
eco_dong = pd.read_csv("경제_동아일보.csv")
eco_omy = pd.read_csv("경제_오마이.csv")
eco_jung = pd.read_csv("경제_중앙일보.csv")
eco_han = pd.read_csv("경제_한겨레.csv")
try :
  eco_seo = pd.read_csv("경제_서울일보.csv")
except :
  eco_seo = pd.DataFrame(columns=['시간', '제목', '본문'])
economy_df = pd.concat([eco_new, eco_dong, eco_omy, eco_jung, eco_han, eco_seo])

glo_new = pd.read_csv("국제_뉴시스.csv")
glo_dong = pd.read_csv("국제_동아일보.csv")
glo_omy = pd.read_csv("국제_오마이.csv")
glo_jung = pd.read_csv("국제_중앙일보.csv")
glo_han = pd.read_csv("국제_한겨레.csv")
global_df = pd.concat([glo_new, glo_dong, glo_omy, glo_jung, glo_han])

soc_new = pd.read_csv("사회_뉴시스.csv")
soc_dong = pd.read_csv("사회_동아일보.csv")
soc_omy = pd.read_csv("사회_오마이.csv")
soc_jung = pd.read_csv("사회_중앙일보.csv")
soc_han = pd.read_csv("사회_한겨레.csv")
try :
  soc_seo = pd.read_csv("사회_서울일보.csv")
except :
  soc_seo = pd.DataFrame(columns=['시간', '제목', '본문'])
society_df = pd.concat([soc_new, soc_dong, soc_omy, soc_jung, soc_han, soc_seo])

pol_new = pd.read_csv("정치_뉴시스.csv")
pol_dong = pd.read_csv("정치_동아일보.csv")
pol_omy = pd.read_csv("정치_오마이.csv")
pol_jung = pd.read_csv("정치_중앙일보.csv")
pol_han = pd.read_csv("정치_한겨레.csv")
try :
  pol_seo = pd.read_csv("정치_서울일보.csv")
except :
  pol_seo = pd.DataFrame(columns=['시간', '제목', '본문'])
politic_df = pd.concat([pol_new, pol_dong, pol_omy, pol_jung, pol_han, pol_seo])

"""**3. 인공지능 파트 시작 : 토큰화 및 문장 생성**"""

model_name = "gogamza/kobart-base-v2"
tokenizer = PreTrainedTokenizerFast.from_pretrained(model_name)
model = BartForConditionalGeneration.from_pretrained(model_name)
sbert_model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

def preprocess_korean_text(documents):
    okt = Okt()
    processed_documents = []
    for doc in documents:
        tokens = okt.nouns(doc)
        processed_documents.append(" ".join(tokens))
    return processed_documents

def calculate_similarity_korean(documents):
    preprocessed_documents = preprocess_korean_text(documents)

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(preprocessed_documents)

    similarity_matrix = cosine_similarity(tfidf_matrix)

    return similarity_matrix

def calculate_similarity(sentence, similar_document):
    original_embedding = sbert_model.encode(similar_document, convert_to_tensor=True)
    summary_embedding = sbert_model.encode(sentence, convert_to_tensor=True)

    similarity = util.cos_sim(original_embedding, summary_embedding)
    return similarity.item()

def summarize_korean_sentences(sentences, tokenizer, model, max_length, min_length):
    input_text = " ".join(sentences)

    inputs = tokenizer.encode(input_text, return_tensors="pt", truncation=True, max_length=1024)

    summary_ids = model.generate(
        inputs,
        max_length=max_length,
        min_length=min_length,
        length_penalty=2.0,
        num_beams=4,
        early_stopping=True,
    )

    summarized_text = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summarized_text

def summary_article(korean_documents) :

  n = len(korean_documents)
  similarity_matrix = calculate_similarity_korean(korean_documents)

  for i in range(n) :
    similarity_matrix[i][i] = 0

  max_similarity=similarity_matrix.max(axis=1)

  graph = [set() for i in range(n)]
  for i in range(n) :
    for j in range(n) :
      if similarity_matrix[i][j] >= 0.5 :
        graph[i].add(j)
        graph[j].add(i)

  length = 0
  for i in range(n) :
    if len(graph[i]) > length :
      length = len(graph[i])
      index = i

  similar_documents = [korean_documents[index]]
  for i in graph[index] :
    similar_documents.append(korean_documents[i])

  model = BartForConditionalGeneration.from_pretrained("gogamza/kobart-summarization")
  tokenizer = PreTrainedTokenizerFast.from_pretrained("gogamza/kobart-summarization")

  summary = summarize_korean_sentences(similar_documents, tokenizer, model, max_length=256, min_length=128)

  return summary, similar_documents

"""**5. 요약 문장과의 유사도 계산**"""

economy_df = economy_df.dropna()
global_df = global_df.dropna()
society_df = society_df.dropna()
politic_df = politic_df.dropna()

summary_eco, documents_eco = summary_article(economy_df['본문'].to_list())
similarity_eco = []
for similar_document in documents_eco :
  similarity_eco.append(calculate_similarity(summary_eco, similar_document))

summary_glo, documents_glo = summary_article(global_df['본문'].to_list())
similarity_glo = []
for similar_document in documents_glo :
  similarity_glo.append(calculate_similarity(summary_glo, similar_document))

summary_soc, documents_soc = summary_article(society_df['본문'].to_list())
similarity_soc = []
for similar_document in documents_soc :
  similarity_soc.append(calculate_similarity(summary_soc, similar_document))

summary_pol, documents_pol = summary_article(politic_df['본문'].to_list())
similarity_pol = []
for similar_document in documents_pol :
  similarity_pol.append(calculate_similarity(summary_pol, similar_document))

"""**6. 인공지능 파트 종료 : 최종 결과 출력**     
끝이다아아아아
"""

print(f"경제 (유사도: {int(float(f'{max(similarity_eco):.2f}')*100)}% / 참고 기사의 수: {len(similarity_eco)})")
print(summary_eco)
print(f"\n국제 (유사도: {int(float(f'{max(similarity_glo):.2f}')*100)}% / 참고 기사의 수: {len(similarity_glo)})")
print(summary_glo)
print(f"\n사회 (유사도: {int(float(f'{max(similarity_soc):.2f}')*100)}% / 참고 기사의 수: {len(similarity_soc)})")
print(summary_soc)
print(f"\n정치 (유사도: {int(float(f'{max(similarity_pol):.2f}')*100)}% / 참고 기사의 수: {len(similarity_pol)})")
print(summary_pol)

num_total_article = len(economy_df) + len(society_df) + len(global_df) + len(politic_df)
print("\n총 참고 기사의 수 : ", num_total_article)

