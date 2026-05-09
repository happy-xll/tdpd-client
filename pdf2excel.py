import os
import requests
import urllib
import pdfplumber
import pandas as pd
from lxml import html

def download_pdf(url, type, year, month):
    try:
        r = requests.get(url)
        tree = html.fromstring(r.text)
        pdf_link = tree.xpath('//a[@download="{}年{}月{}.pdf"]//@href' . format(year, month, type))

        url_a = urllib.parse.urlsplit(url)
        print(os.path.dirname(url_a.path))
        r_url = '{}://{}{}/{}'.format(url_a.scheme, url_a.netloc, os.path.dirname(url_a.path), pdf_link[0].replace('./', ''))
        print(r_url)
        fd = requests.get(r_url)
        if fd.status_code == 200:
            up =  urllib.parse.urlsplit(r_url)
            pdf_n = os.path.basename(up.path)
            cont = fd.content
            if not os.path.exists('./temp/'):
                os.makedirs('./temp/')
            fp = './temp/{}'.format(pdf_n)
            with open(fp, "wb+") as f:
                f.write(cont)
                return fp

        return fp
    except Exception as e:
        return None

def fetch_pdf_link(type, year, month):
    url = "https://www.mot.gov.cn/tongjishuju/gonglu/index.html"
    r = requests.get(url)
    try:
        tree = html.fromstring(r.text)
        links_label = tree.xpath('//a[@title="{}年{}月{}"]//@href'.format(year, month, type))
        print(links_label)
        r_url = download_pdf(links_label[0], type, year, month)
        print(r_url)
        return r_url

    except Exception as e:
        print("request_data %s error" % str(e))
        return None

def pdf2df(pdf, year, month):
    pdf = pdfplumber.open(pdf)

    first_page = pdf.pages[0]
    table = first_page.extract_table()

    def remove_space(s):
        return s.replace(' ', '')

    prov_n = table[3][0].split('\n')
    prov_trv = table[3][5].split('\n')
    prov_trv = list(map(remove_space, prov_trv))
    prov_trv = list(map(int, prov_trv))

    df = pd.DataFrame({'prov_name': list(map(remove_space, prov_n)), 'trv': prov_trv })
    df = df.rename(columns={'prov_name': 'sname'})

    df_r = pd.read_csv('provinces.csv')
    #df_r = df_r.append(pd.DataFrame({'regName': '总计', 'sname':'总计', 'ad_prov': None, 'province':'Total'}), ignore_index=True)
    df =df.join(df_r.set_index(['sname']), on =['sname'])
    df.dropna(axis=0, inplace=True)

    df['year'] = year
    df['month'] = month
    dfp = df.pivot(index=['year', 'month'], columns='province', values='trv')
    print(dfp)
    return dfp.reset_index()

def pdfdf2excel( year, month, to_file):
    # 货物周转量， 旅客周转量
    sheets =  {'freightturnover': '公路货物运输量', 'passengerturnover': '公路旅客运输量'}
    writer=pd.ExcelWriter(to_file)
    for item in sheets:
        print(item)
        #pdf = '{}年{}月{}.pdf'.format(year, month, sheets.get(item))
        pdf = fetch_pdf_link(sheets.get(item), year, month)
        print(pdf)
        sheet_d = pdf2df(pdf, year, month)
        sheet_d.to_excel(writer, sheet_name=item, index=False)

    writer.save()
    writer.close()

if __name__ == '__main__':
    #pdf2df('2022年12月公路旅客运输量.pdf', 2022, 2)
    #pdf2df('2022年12月公路货物运输量.pdf', 2022, 2)
    #fetch_pdf_link('公路旅客运输量', 2022, 12)
    pdfdf2excel(2022, 12, '2022-12-trans.xlsx')
