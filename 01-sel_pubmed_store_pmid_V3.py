# -*- coding:utf-8 -*-
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import re, os
from selenium.webdriver.common.keys import Keys
from pyquery import PyQuery as pq
from keywords import KEYWORDS, TOTAL

from fake_useragent import UserAgent  #代理



options=webdriver.ChromeOptions() #定义浏览器参数
options.add_argument('--ignore-certificate-errors')
options.add_argument('--headless') #无界面
options.add_argument('log-level=3') #不打印日志
# ua = UserAgent(use_cache_server=False)  #代理
# options.add_argument('user-agent="%s"'%ua.random)  #随机代理



browser = webdriver.Chrome(chrome_options=options)
wait = WebDriverWait(browser,10)


def search():
    browser.get('https://www.ncbi.nlm.nih.gov/pubmed')
    try:
        print("\n正在打开NCBI搜索页面...")
        input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#term')))
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#search')))
        input.clear()
        input.send_keys(KEYWORDS)
        submit.click()
        try:
            submit_match = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#set-best-match-sort > span')))
            submit_match.click()
            print("通过Best match方式排序结果")
        except:
            print("通过Most recent方式排序结果")
        total = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#maincontent > div > div.title_and_pager.bottom > div > h3')))
        print("正在浏览第1页...")
        get_uid()
        print("下载第1页完成！")
        return(total.text)
    except TimeoutException:
        get_uid()
        return(1)

def next_page(page_number):
    try:
        print("\n正在浏览第%d页..."%page_number)
        input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#pageno')))
        input.clear()
        input.send_keys(page_number)
        input.send_keys(Keys.ENTER)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#pageno2')))
        get_uid()
        print("下载第%d页完成！"%page_number)
    except TimeoutException:
        next_page(page_number)

def get_uid():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#maincontent .content .rprt')))
    html = browser.page_source
    doc = pq(html)
    items = doc('#maincontent .content .rprt').items()
    for item in items:
        uid =item.find('.rprtid').text().split('\n')[1]
        store_uid(uid)

def store_uid(uid):
    file_path = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_UID')
    with open(file_path,'a',encoding='utf-8') as fh:
        fh.write(uid+'\n')


def main():
    print("\n\n正在查找%s的UID信息...\n"%KEYWORDS)

    #新建文件夹
    if not os.path.exists(KEYWORDS):  #如果文件夹不存在就创建
        os.mkdir(KEYWORDS)
    file_path = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_UID')
    open(file_path,'w',encoding='utf-8').close()    #清空文件内容

    total = search()
    total = int(re.compile(r'(\d+)').search(total).group(0))
    number = 0

    if total >= 2:
        number = total+1
        if total >= TOTAL:
            number = TOTAL+1
        for i in range(2,number):
            next_page(i)
    
    browser.close()

    print("文献UID下载结束！")
    print("下载的文献UID保存在%s_UID中。\n"%KEYWORDS)



if __name__ == "__main__":
    main()