# -*- coding:utf-8 -*-
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import re, os
# import json
from multiprocessing import Pool #引入多线程
# from pathos.multiprocessing import ProcessingPool as Pool #引入多线程
from keywords import KEYWORDS #引入KEYWORDS
# from fake_useragent import UserAgent  #代理

PATTERN_year = re.compile(r'([0-9]{4})')
PATTERN_doi = re.compile(r'DOI: ([\S]*)')
PATTERN_pmcid = re.compile(r'PMCID: (PMC[\d]*)')



options=webdriver.ChromeOptions() #定义浏览器参数
options.add_argument('--ignore-certificate-errors')
options.add_argument('--headless') #无界面
options.add_argument('log-level=3') #不打印日志
# ua = UserAgent(use_cache_server=False)  #代理
# options.add_argument('user-agent="%s"'%ua.random)  #随机代理



def get_title_abstract(uid):
    browser = webdriver.Chrome(chrome_options=options) #定义浏览器
    wait = WebDriverWait(browser,30) #设置等待时间

    url ="https://www.ncbi.nlm.nih.gov/pubmed/"+str(uid)
    browser.get(url)
    literature={
            'pmid':uid,
            'year':'0',
            'jour':'0',
            'title':'0',
            'abstract':'0',
            'doi':'0',
            'pmcid':'0'}
    try:
        print("\n正在解析url：%s"%url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#maincontent > div')))
        #通过browser.find_element_by_css_selector和re获取文件信息
        literature['year'] = re.search(PATTERN_year,browser.find_element_by_css_selector('#maincontent > div > div.rprt_all > div > div.cit').text).group(1)
        literature['jour'] = browser.find_element_by_css_selector('#maincontent > div > div.rprt_all > div > div.cit > span > a').get_attribute('title')[:-1]
        literature['title'] = browser.find_element_by_css_selector('#maincontent > div > div.rprt_all > div > h1').text[:-1]
        try:
            literature['abstract'] = '    '.join(browser.find_element_by_css_selector('#maincontent > div > div.rprt_all > div > div.abstr > div').text.split('\n'))
        except:
            pass
        #查找doi和pmcid
        pmid_doi = browser.find_element_by_css_selector('#maincontent > div > div.rprt_all > div > div.aux > div:nth-child(1) > dl').text
        doi = re.search(PATTERN_doi,pmid_doi) #doi
        if doi:
            literature['doi'] = doi.group(1)
        pmcid = re.search(PATTERN_pmcid,pmid_doi) #pmcid
        if pmcid:
            literature['pmcid'] = pmcid.group(1)
        store_literature(literature)  #存储文章信息
        print("解析url：%s成功！"%url)
    except TimeoutException:
        print("解析url：%s遇到TimeoutException错误！正在重试"%url)
        get_title_abstract(uid)
    except NoSuchElementException:
        print("解析url：%s遇到NoSuchElementException错误！正在重试"%url)
        get_title_abstract(uid)
    finally:
        browser.close()

#存储文章信息函数
def store_literature(literature):
    file_path_info = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_info')
    with open(file_path_info,'a',encoding='utf-8') as fh:
        fh.write(literature['pmid']+'\t'+literature['year']+'\t'+literature['jour']+'\t'+literature['doi']+'\t'+literature['pmcid']+'\n'+\
        'Title: '+literature['title']+'\n'+'Abstract: '+literature['abstract']+'\n\n')
        #fh.writelines(json.dumps(literature)+'\n')



def main():
    print("\n\n正在查找%s的info信息...\n"%KEYWORDS)
    file_path_uid = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_UID')
    fh = open(file_path_uid,'r')
    list_UID = fh.readlines()

    file_path_info = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_info')
    open(file_path_info,'w',encoding='utf-8').close()    #清空文件内容

    groups=[]  #定义多线程使用的数组
    for i in range(0,len(list_UID)):
        list_UID[i] = str(list_UID[i]).strip()
        if list_UID[i]:
            groups.append(list_UID[i])

    pool = Pool(4)
    pool.map(get_title_abstract,groups)
    
    print("文献info下载结束！")
    print("下载的文献info保存在%s_info中。\n"%KEYWORDS)

if __name__ == "__main__":
    main()
