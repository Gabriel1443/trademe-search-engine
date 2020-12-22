import logging
import random
import os 
import re
import csv
from multiprocessing import get_context, cpu_count, pool
import queue
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import pandas as pd
from ruamel.yaml import YAML
import lxml.html

def clean_text(text:str) -> str:
    to_replace = ["\r", "\n"]
    for item in to_replace:
        text = text.replace(item, "")
        
    text_list = text.split(" ")
    text_list = [item for item in text_list if item != ""]
    text_str = " ".join(text_list)
    return text_str

def clean_img_str(text:str) -> str:
    return_str = re.search("http.+jpg", text)
    if not return_str is None:
        return return_str.group(0)
    
    else:
        return ""
    # return re.search("http.+jpg", text).group(0)

def map_func_list(text_list:list, func) -> list:
    output = []
    for item in text_list:
        output.append(func(item))
    
    return output

yaml = YAML()

logging.basicConfig(
    format='%(levelname)s:%(message)s',
    level=logging.INFO,
    filemode='w',
)
logger = logging.getLogger(__name__)

class TrademeSearch:

    def __init__(self, search_strings, proxies = None):
        search_string = "+".join(search_strings)
        self.output_filename = "_".join(search_strings) + ".csv"
        self.search_string = search_string
#         self.user_agent = user_agent
        self.proxies = proxies

    def _requests_retry_session(
        self,
        retries=5,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        session=None,
    ):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _make_url(self, page_n):
        url = "https://www.trademe.co.nz/Browse/SearchResults.aspx?&cid=0&searchType=&searchString={search_string}&x=0&y=0&type=Search&sort_order=&redirectFromAll=False&rptpath=all&rsqid=df688ec6c2424b35a4c85217e34dd87c-009&page={page_n}&user_region=100&user_district=0&generalSearch_keypresses=16&generalSearch_suggested=0&generalSearch_suggestedCategory=&v=List".format(search_string = self.search_string, page_n = page_n)
        # url = "https://www.trademe.co.nz/Browse/SearchResults.aspx?searchString=slow+cooker&type=Search&searchType=all&user_region=100&user_district=0&generalSearch_keypresses=11&generalSearch_suggested=0&generalSearch_suggestedCategory=&rsqid=c86902522bc14876979fde8500bf44ea-001&v=List"
        return url
        
    def fetch_page_data(
            self,
            page_n = 1,
            max_retries = 20,
        ):
        
        url = self._make_url(page_n)
        s = requests.Session()

        if not self.proxies is None:
            use_proxy = random.choice(self.proxies)
            logger.debug(f"using proxy: {use_proxy}")
            s.proxies.update(use_proxy)
        
        response = self._requests_retry_session(session=s).get(url)
        tree = lxml.html.fromstring(response.text)
        infos = tree.xpath('//div[@class="supergrid-overlord "]/div[@class = "supergrid-bucket largelist "]/a/div/div[@class="location-wrapper"]/div[@class="info" or @class="info reserve-not-met"]')
        buynow = []
        bid = []
        for item in infos:
            raw_buynow = item.xpath('div[@class="buynow bnonly"]/div/div[@id="SuperListView_BucketList_BuyNow_listingBuyNowPrice"]/text()')
            raw_bid = item.xpath('div/div[@id="SuperListView_BucketList_BidInfo_listingBidPrice"]/text()')
            if len(raw_buynow) > 0:
                buynow.append(raw_buynow[0])
            else:
                buynow.append("")
            
            if len(raw_bid) > 0:
                bid.append(raw_bid[0])
            else:
                bid.append("")
            
        raw_image_element = tree.xpath('//div[@class="supergrid-overlord "]/div[@class = "supergrid-bucket largelist "]/a/div/div[@class="image " or @class="image job-service"]')
        raw_image = []
        for item in raw_image_element:
            raw_image_item = item.xpath("@style")
            if len(raw_image_item) == 0:
                raw_image_item = ""
            else:
                raw_image_item = raw_image_item[0]

            raw_image.append(raw_image_item)

        clean_image = map_func_list(raw_image, clean_img_str)
        raw_location = tree.xpath('//div[@class="supergrid-overlord "]/div[@class = "supergrid-bucket largelist "]/a/div/div[@class="location-wrapper"]/div[@class="location-info"]/div[@class="location"]/text()')
        clean_location = map_func_list(raw_location, clean_text)
        raw_title = tree.xpath('//div[@class="supergrid-overlord "]/div[@class = "supergrid-bucket largelist "]/a/div/div[@class="location-wrapper"]/div[@class="info" or @class="info reserve-not-met"]/div[@class="title"]/text()')
        clean_title = map_func_list(raw_title, clean_text)
        try:
            df = pd.DataFrame(
                {
                    "clean_image": clean_image,
                    "clean_location": clean_location,
                    "clean_title": clean_title,
                    "buynow": buynow,
                    "bid": bid,
                }
            )
        except:
            logger.info(f"lenght of clean_image: {len(clean_image)}")
            logger.info(f"lenght of clean_location: {len(clean_location)}")
            logger.info(f"lenght of clean_title: {len(clean_title)}")
            logger.info(f"lenght of buynow: {len(buynow)}")
            logger.info(f"lenght of bid: {len(bid)}")
            print(self._make_url(page_n))
            breakpoint()
        
        return df
    
    def fetch_data(self):
        df_list = []
        page = 1
        while True:
            logger.info(f"fetching page: {page}")
            temp_df = self.fetch_page_data(page)
            df_list.append(temp_df)
            if temp_df.shape[0] < 60:
                break
            
            page += 1
        
        df = pd.concat(df_list)
        df = df.reset_index(drop = True)
        df.to_csv(self.output_filename, quoting=csv.QUOTE_ALL, index = True, index_label = "task_n", encoding = 'utf-8-sig',)
        logger.info(f"{self.output_filename} result saved!")
        return True
    
if __name__ == "__main__":
    proxy_pool = [{'http': 'http://54.206.98.132:3128', 'https': 'http://54.206.98.132:3128'}]

    logger.info("Scraping starts!")
    job = TrademeSearch(["whisk"], proxies = proxy_pool)
    job.fetch_data()
