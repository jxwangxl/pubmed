# -*- coding:utf-8 -*-
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from pathos.multiprocessing import ProcessingPool as Pool #引入多线程
from keywords import KEYWORDS #引入KEYWORDS
import os, re
import requests
from requests.exceptions import ConnectionError, ReadTimeout, ChunkedEncodingError
# from fake_useragent import UserAgent  #代理
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) #解决https warning提示

PATTERN_title = re.compile(r'[\\/:*?"<>|]')


#webdriver选项options设置
options=webdriver.ChromeOptions() #定义浏览器参数
options.add_argument('--ignore-certificate-errors') #忽略证书错误
options.add_argument('--headless') #无界面
options.add_argument('log-level=3') #不打印日志
# ua = UserAgent(use_cache_server=False)  #代理
# options.add_argument('user-agent="%s"'%ua.random)  #随机代理防止被远端服务器封杀


#采用多种方式获取paper_url
def down_paper_from_PMC_and_SciHub(uid,doi,pmcid,title):
    if len(title) > 177:  #文件名太长了会导致系统无法保存，截短
        title_tm = title[:177]+'---'
    else:
        title_tm = title
    #需要下载的文件绝对路径
    file_path_pdf = '{0}/{1}.{2}'.format(KEYWORDS,title_tm, 'pdf')
    file_path_epub = '{0}/{1}.{2}'.format(KEYWORDS,title_tm, 'epub')
    #判断文件绝对路径是否已存在，如果不存在就下载
    if not (os.path.exists(file_path_pdf) or os.path.exists(file_path_epub)):
        paper_url = get_url_from_PMC(uid,pmcid)   #1尝试从PMC下载
        if not paper_url:
            if doi != '0':
                print("从PMC解析uid：%s失败！继续尝试从doi下载！"%uid)
                paper_url = get_url_from_SciHub(doi)   #2尝试从SciHub使用doi下载
            else: 
                print("从doi解析uid：%s失败！继续尝试从title下载！"%uid)
                paper_url = get_url_from_SciHub(title[5:])   #3尝试从SciHub使用title下载
        #获取paper_url成功，下载并保存文献
        if paper_url:
            print("解析uid：%s成功！即将下载！"%uid)
            store_paper_from_url(pmcid,paper_url,title)
        else:   #下载失败，保存下载失败文件信息
            print("下载文章%s失败!"%title)
            file_path_notFound = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_notFound')
            with open(file_path_notFound,"a") as f:
                f.write(uid+'\t'+pmcid+'\t'+doi+'\t'+title+'\n') 
    else:
            print("文件%s已存在，不下载！"%file_path_pdf) 
        
        


#进入Pubmed页面获取paper_url
def get_url_from_PMC(uid,pmcid):
    #由于是多线程，每个函数都定义独立的browser
    browser = webdriver.Chrome(chrome_options=options) #定义浏览器
    wait = WebDriverWait(browser,30) #设置等待时间

    url ="https://www.ncbi.nlm.nih.gov/pmc/articles/pmid/"+str(uid) #文献PMC网站的url
    paper_url = ''
    try:
        print("\n正在从PMC解析uid：%s"%uid)
        #打开网页，打不开网页抛出异常
        browser.get(url)
        #等待网页加载指导出现文献信息页面
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#footer > div.subfooter')))
        #尝试通过css_selector定位元素
        try:
            #通过PDF和ePub两种可能的方式定位并获取paper_url
            locate_PDF = 0
            locate_ePub = 0
            #获取"Article | PubReader | ePub (beta) | PDF (585K) | Citation"，未找到抛出异常
            paper_locate = browser.find_element_by_css_selector("#rightcolumn > div:nth-child(2) > div").text
            locate_list = paper_locate.split('|') #切片成数组
            for i in range(len(locate_list)):
                if "PDF" in locate_list[i]:     #从locate_list中获取PDF位置，记为locate_PDF(优先下载PDF格式)
                    locate_PDF = i + 1
                    break
                if "ePub" in locate_list[i]:     #从locate_list中获取ePub位置，记为locate_ePub
                    locate_ePub = i + 1
            if locate_PDF != 0:     #根据locate_PDF定位paper_url
                paper_url = browser.find_element_by_css_selector("#rightcolumn > div:nth-child(2) > div > ul > li:nth-child(%s) > a"%locate_PDF).get_attribute('href')
                return(paper_url)
            elif locate_ePub != 0:  #根据locate_ePub直接构建paper_url(比较简单)
                paper_url = "https://www.ncbi.nlm.nih.gov/pmc/articles/"+pmcid+"/epub/"
                return(paper_url)
        except NoSuchElementException:
            return(0)
    except TimeoutException:
        return(0)
    finally:
        browser.close()



#进入SciHub页面获取paper_url
def get_url_from_SciHub(doiORtitle):
    #由于是多线程，每个函数都定义独立的browser
    browser = webdriver.Chrome(chrome_options=options) #定义浏览器
    wait = WebDriverWait(browser,30) #设置等待时间
    url ="http://sci-hub.tw/"
    try:
        print("\n正在从SciHub解析doiORtitle：%s"%doiORtitle)
        #打开网页，打不开网页抛出异常
        browser.get(url)
        paper_url = None
        #获取SciHub页面的搜索输入框
        input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#input > form > input[type="textbox"]:nth-child(2)')))
        #获取SciHub页面的搜索按钮
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#open > p')))
        input.clear()   #清空输入框
        input.send_keys(doiORtitle) #发送doi或者title到输入框
        submit.click()  #点击搜索按钮开始搜索
        #等待网页加载出现save按钮，加载失败则抛出异常
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#buttons > ul > li:nth-child(2) > a')))
        #通过css_selector定位，通过get_attribute获取paper_url
        paper_url = browser.find_element_by_css_selector("#buttons > ul > li:nth-child(2) > a").get_attribute('onclick')
        if paper_url:   #获取成功，则对paper_url进行提取(切掉前后多余的字符)
            paper_url = str(paper_url)[15:-1]
            if "http" not in paper_url:    #判断提取的paper_url是否有"http"或者"https"前缀
                paper_url = "http:" + paper_url #没有则加上"http:" (一般"//"开头)
            return(paper_url)   #返回paper_url
        else:
            return(0)  #获取失败则返回"0"
    except TimeoutException:
        return(0)
    finally:
        browser.close()



#从paper_url下载并保存文章
def store_paper_from_url(pmcid,paper_url,title):
    #设置requests的headers，伪装成浏览器防止被远端服务器封杀
    headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0'}
    if len(title) > 177:  #文件名太长了会导致系统无法保存，截短
        title_tm = title[:177]+'---'
    else:
        title_tm = title
    try:
        #get命令获取paper_url内容
        paper = requests.get(paper_url,headers=headers,verify=False)
        #创建保存文件夹（main函数中已经创建，此处可以省略）
        if not os.path.exists(KEYWORDS):  #如果文件夹不存在就创建
            os.mkdir(KEYWORDS)
        #判断paper_url中的文献类型pdf还是epub？
        if "pdf" in paper_url:
            file_path = '{0}/{1}.{2}'.format(KEYWORDS,title_tm, 'pdf')
        elif "epub" in paper_url:
            file_path = '{0}/{1}.{2}'.format(KEYWORDS,title_tm, 'epub')
        if not os.path.exists(file_path):   #判断文件是否存在，如果文件不存在就下载
            with open(file_path, 'wb') as f:    #二进制写入数据到文件中
                f.write(paper.content)
                print("下载并保存%s成功!"%paper_url)
        else:
            print("文件%s已存在，不保存！"%file_path)
    except (ConnectionError, ReadTimeout) as e:
        print("下载%s出现%s错误，正在重试！"%(paper_url,e))
        store_paper_from_url(pmcid,paper_url,title)
    except ChunkedEncodingError as e:
        print("下载%s出现%s错误，放弃下载，下载失败！"%(paper_url,e))
        #保存下载失败文件信息
        file_path_notFound = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_notFound')
        with open(file_path_notFound,"a") as f:
            f.write(paper_url+'\t'+title+'\n')


#主函数，多线程运行，统计下载文献数量
def main():
    print("\n\n正在下载%s的全文...\n"%KEYWORDS)

    #新建文件夹
    if not os.path.exists(KEYWORDS):  #如果文件夹不存在就创建
        os.mkdir(KEYWORDS)

    #清空notFound文件
    file_path_notFound = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_notFound')
    open(file_path_notFound,'w',encoding='utf-8').close()    #清空文件内容
        
    #打开info文件，从中提取uid, doi, pmcid, title信息，分别保存成list用于多线程参数
    file_path_info = '{0}/{1}'.format(KEYWORDS,KEYWORDS+'_info')

    with open(file_path_info,'r',encoding='utf-8') as fh:
        line_number = 0
        uid = []
        doi = []
        pmcid = []
        title = []
        for line in fh:
            line_number += 1
            list_line = line.strip().split('\t')
            if line_number%4 == 1:
                title0 = ''
                uid.append(list_line[0])
                doi.append(list_line[3])
                pmcid.append(list_line[4])
                title1 = str(list_line[1])+'-'
            if line_number%4 == 2:
                title2 = re.sub(PATTERN_title, ' ', str(list_line[0])[7:])
                title0 = title1 + title2
                title.append(title0)
                title0 = ''




    #统计下载前文件夹中文件数量
    file_count_before = len([name for name in os.listdir(KEYWORDS) if os.path.isfile(os.path.join(KEYWORDS,name))])
    
    #多线程运行down_paper_from_PMC_and_SciHub任务
    pool = Pool(4)
    pool.map(down_paper_from_PMC_and_SciHub,uid,doi,pmcid,title)

    #统计下载前文件夹中文件数量
    file_count_after = len([name for name in os.listdir(KEYWORDS) if os.path.isfile(os.path.join(KEYWORDS,name))])

    #输出运行结束信息
    print("文献全文下载结束！本次运行下载了%d篇文献！"%(file_count_after-file_count_before))
    print("下载的文献全文保存在%s文件夹中。"%KEYWORDS)
    print("下载失败的文献信息保存在%s_notFound.txt中。\n"%KEYWORDS)


if __name__ == "__main__":
    main()
