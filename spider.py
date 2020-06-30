import requests
import re
import time
import random
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


class PaperSpider:

    def __init__(self, paper_title_list, need_other_cited=True, need_cite_format=True):
        self.google_domain = 'https://scholar.google.com.hk/'
        self.paper_title_list = paper_title_list
        # 请替换headers中的cookie为合法cookie; replace below cookie with valid cookie
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6',
            'cache-control': 'max-age=0',
            'cookie': 'NID=204=PvOUsefBSG5QDsh7UadlmVOsRf7JllTq4z8PKvzTZ9yV9yMeZPsUAZgEe6IzPbeLpX9SU_z-QnCKAAiCt8lMKr3XDbHJHyIOyNfFKFlxEI0QaGqhwBUZokwcgrPwhHHkvPobSPfgORBTuMtT4UpvAFpmJoCd2I_CtmmIOEGrtEQ; GSP=A=Hul7MQ:CPTS=1593501177:LM=1593501177:S=7ePiEbiD7wWb4BcR',
            'referer': 'https://scholar.google.com.hk/scholar?hl=zh-CN&as_sdt=1%2C5&as_vis=1&q=A+Min-max+Cut+for+Graph+Partition+and+Data+Clustering&btnG=',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36'
        }
        self.need_other_cited = need_other_cited
        self.need_cite_format = need_cite_format

    def run(self):
        all_info_list = []
        tmp_info_list = []
        count = 0
        columns_info = ['paper', 'title_for_check', 'authors', 'year', 'conference or journal', 'cited_num']
        if self.need_other_cited:
            columns_info.append('other_cited_num')
        if self.need_cite_format:
            columns_info.extend(['GB/T 7714', 'MLA', 'APA'])

        for paper_title in self.paper_title_list:
            paper_info = self.crawl_single_paper(paper_title)
            tmp_info_list.append(paper_info)
            all_info_list.append(paper_info)
            print('paper \"{}\" finish\n'.format(paper_title))
            count += 1

            # save result every 10 paper
            if count % 10 == 0:
                df = pd.DataFrame(tmp_info_list, columns=columns_info)
                df.to_csv('result{}.csv'.format(count), encoding="utf_8_sig")
                tmp_info_list.clear()

        df = pd.DataFrame(all_info_list, columns=columns_info)
        df.to_csv('all_result.csv'.format(count), encoding="utf_8_sig")

    def crawl_single_paper(self, paper_title):
        paper = []
        print('crawling paper \"{}\"'.format(paper_title))
        response_text = self.send_request('https://scholar.google.com.hk/scholar',
                                          {'hl': 'zh-CN',
                                           'as_sdt': '0,5',
                                           'btnG': '',
                                           'q': paper_title}, self.headers)

        # the paper title crawled from google, you can use it to check if this is the paper you want
        title_for_check = ''
        # google scholar author id
        author_ids = []
        # number of citations
        cited_num = 0
        # number of other citations, please note that some author may not have id,
        # so this number is bigger than true number of other citations
        other_cited_num = 0
        # cite format
        GBT = ''
        MLA = ''
        APA = ''
        possible_author_name = ''

        soup = BeautifulSoup(response_text, 'html.parser')
        paper_divs = soup.find_all('div', {'class': 'gs_r gs_or gs_scl'})

        if len(paper_divs) > 0:
            # we assume first result is we want
            paper_div = paper_divs[0]

            if self.need_cite_format:
                paper_id = paper_div['data-cid']
                GBT, MLA, APA = self.crawl_cite_format(paper_id)

            # get it's title
            h3 = paper_div.find('h3', {'class': 'gs_rt'})
            title_for_check = h3.a.get_text()
            title_for_check = str(title_for_check).replace('<b>', '').replace('</b>', '')

            # get it's author ids
            author_div = paper_div.find('div', {'class': 'gs_a'})
            possible_author_name = author_div.get_text()
            for a in author_div.find_all('a'):
                searchObj = re.search(r'user=(.*)&hl=', a['href'], re.M | re.I)
                author_id = searchObj.group(1)
                author_ids.append(author_id)

            # get it's number of citations
            if self.need_other_cited:
                cite_div = paper_div.find('div', {'class': 'gs_ri'}).find('div', {'class': 'gs_fl'})
                cite_a = cite_div.find_all('a')[2]
                if str(cite_a.string).find('被引用次数') != -1:
                    cited_num = int(str(cite_a.string).replace('被引用次数：', ''))
                    cited_url = cite_a['href']
                    if len(cited_url) != 0:
                        real_cited_num, other_cited_num = self.crawl_cited_papers(cited_url, cited_num, author_ids)

        # get it's detail information from https://dblp.uni-trier.de/
        author_name_list, publish_info, year_info, page_info = self.crawl_detail(paper_title)
        author_info = ''
        for authur_name in author_name_list:
            author_info += authur_name + ','
        author_info = author_info[:-1]

        paper.append(paper_title)
        paper.append(title_for_check)
        if len(author_info) == 0:
            paper.append(possible_author_name)
        else:
            paper.append(author_info)
        paper.append(year_info)
        paper.append(publish_info + ',' + page_info)

        paper.append(cited_num)
        if self.need_other_cited:
            paper.append(other_cited_num)
        if self.need_cite_format:
            paper.append(GBT)
            paper.append(MLA)
            paper.append(APA)

        return paper

    def crawl_cited_papers(self, cited_url, cited_num, author_ids):
        author_ids = np.array(author_ids)
        total_cited_num = 0
        other_cited_num = 0
        print('the numbers of cited papers: {}'.format(cited_num))
        for start in range(0, cited_num, 10):

            print(
                'crawling it\'s cited paper range {}~{}'.format(start, start + 10))
            response_text = self.send_request(self.google_domain + cited_url, {'start': start}, self.headers)

            soup = BeautifulSoup(response_text, 'html.parser')
            paper_divs = soup.find_all('div', {'class': 'gs_r gs_or gs_scl'})
            for paper_div in paper_divs:
                total_cited_num += 1
                author_div = paper_div.find('div', {'class': 'gs_a'})
                cited_author_ids = []
                for a in author_div.find_all('a'):
                    searchObj = re.search(r'user=(.*)&hl=', a['href'], re.M | re.I)
                    author_id = searchObj.group(1)
                    cited_author_ids.append(author_id)
                cited_author_ids = np.array(cited_author_ids)
                if len(np.intersect1d(author_ids, cited_author_ids)) == 0:
                    other_cited_num += 1
        return total_cited_num, other_cited_num

    # get it's GB/T 7714, MLA, APA cite format
    def crawl_cite_format(self, paper_id):
        cite_formats = {}
        response_text = self.send_request('https://scholar.google.com.hk/scholar',
                                          {'q': 'info:{}:scholar.google.com/'.format(paper_id), 'output': 'cite',
                                           'scirp': 0,
                                           'hl': 'zh-CN'}, self.headers)
        soup = BeautifulSoup(response_text, 'html.parser')
        reference_trs = soup.find_all('tr')
        for tr in reference_trs:
            format_name = tr.find('th', {'class': 'gs_cith'}).get_text()
            cite_format = tr.find('div', {'class': 'gs_citr'}).get_text().replace('<i>', '').replace('</i>', '')
            cite_formats[format_name] = cite_format
        return cite_formats.get('GB/T 7714', ''), cite_formats.get('MLA', ''), cite_formats.get('APA', '')

    # crawl detail information from dblp
    def crawl_detail(self, paper_title):
        author_name_list = []
        publish_info = ''
        year_info = ''
        page_info = ''
        response = requests.get(
            'https://dblp.uni-trier.de/search/publ/inc', params={'q': paper_title, 'h': 30, 'f': 0, 's': 'ydvspc'})
        soup = BeautifulSoup(response.text, 'html.parser')
        publ_list = soup.find_all('li', {'class': 'entry'})

        if len(publ_list) > 0:
            publ = publ_list[0]
            # author names
            author_tags = publ.find_all('span', {'itemprop': 'author'})
            for tag in author_tags:
                author_name_list.append(tag.find('span', {'itemprop': 'name'}).string)
            # publish info
            conference_tag = publ.find('span', {'itemprop': 'isPartOf'})
            if conference_tag is not None:
                publish_info_tag = conference_tag.find('span', {'itemprop': 'name'})
                if publish_info_tag is not None:
                    publish_info = publish_info_tag.string
            year_info_tag = publ.find('span', {'itemprop': 'datePublished'})
            if year_info_tag is not None:
                year_info = year_info_tag.string
            page_info_tag = publ.find('span', {'itemprop': 'pagination'})
            if page_info_tag is not None:
                page_info = page_info_tag.string

        return author_name_list, publish_info, year_info, page_info

    def send_request(self, url, params, headers=None):
        # if request is too frequent, the cookie will soon become invalid
        time.sleep(random.randint(15, 20))
        response = requests.get(
            url, params=params, headers=headers)
        if response.status_code != 200:
            raise Exception('error response code')

        # check if the cookie is still valid
        if response.text.find('人机身份验证') != -1 or response.text.find('sending automated queries') != -1:
            raise Exception('need verify, consider using new cookie')
        return response.text
