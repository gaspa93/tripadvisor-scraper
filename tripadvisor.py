# -*- coding: utf-8 -*-
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re
import csv
import logging

header = ['id_review', 'title', 'caption', 'timestamp', 'rating', 'username', 'n_review_user', 'location']
        
class Tripadvisor:
    driver = None
    writer = None

    def __init__(self, targetfile, min_date, lang):
        self.min_date = min_date
        self.targetfile = open(targetfile, 'w', encoding='utf-8')
        self.lang = lang
        
        self.driver = self.__get_driver()
        self.writer = self.__get_writer()
        self.logger = self.__get_logger()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
        
        self.logger.info('Closing chromedriver...')
        self.driver.close()
        self.driver.quit()

        return True
        

    def get_reviews(self, url):
        
        self.logger.info('Scraping url: %s', url)
        self.driver.get(url)

        # NOTE: only visible languages can be selected
        self.logger.info('Scraping reviews with language code: %s', self.lang)
        try:
            self.driver.find_element_by_xpath(
                '//div[@class=\'ui_radio item\' and @data-value=\'{}\']'.format(self.lang)).click()
        except:
            self.logger.warn('Language %s not visible. Change to default: ALL', self.lang)
            self.driver.find_element_by_xpath(
                '//div[@class=\'ui_radio item\' and @data-value=\'ALL\']').click()
        
        # wait to load new reviews
        time.sleep(5)  

        n_total_reviews = self.driver.find_element_by_xpath('//span[@class=\'reviewCount\']').text
        n_total_reviews = int(n_total_reviews.split(' ')[0].replace(',', ''))
        
        n_reviews = 0
        if n_total_reviews > 0:

            self.__expand_reviews()

            resp = BeautifulSoup(self.driver.page_source, 'html.parser')
            stop, count = self.__parse_reviews(resp)

            # load other pages with reviews, using a template url
            url = url.replace('Reviews-', 'Reviews-or{}-')
            offset = 0
            n_reviews = count
            while not stop:
                offset = offset + 10
                url_ = url.format(offset)

                self.driver.get(url_)
                self.__expand_reviews()

                resp = BeautifulSoup(self.driver.page_source, 'html.parser')
                stop, count = self.__parse_reviews(resp)
                n_reviews += count
        else:
            self.logger.warn('No reviews available. Stop scraping this link.')
        
        self.logger.info('Scraped %d reviews', n_reviews)
        
        
    def __parse_reviews(self, response):
        
        found_last_new = False

        r_list = response.find_all('div', class_='review-container')
        n_new_reviews = 0
        for idx, review in enumerate(r_list):
            id_review = review['data-reviewid']
            review_date = review.find('span', class_='ratingDate')['title']
            timestamp = datetime.strptime(review_date, '%B %d, %Y')

            # save new reviews
            if timestamp >= self.min_date: 

                if review.find('span', class_='badgetext') is not None:
                    n_reviews = int(review.find('span', class_='badgetext').text)
                else:
                    n_reviews = None

                # container of username and location, if present
                info_text = review.find('div', class_='info_text')

                if info_text.find('div', class_='userLoc') is not None:
                    location = info_text.find('div', class_='userLoc').text
                else:
                    location = None
                
                username = info_text.find('div', class_=None).text

                rating_raw = review.find('span', {"class": re.compile("ui_bubble_rating\sbubble_..")})['class'][1][-2:]
                rating_review = rating_raw[0] + '.' + rating_raw[1]
                
                title = self.__filterString(review.find('span', class_='noQuotes').text)
                caption = self.__filterString(review.find('p', class_='partial_entry').text)

                item = {
                    'id_review': id_review,
                    'title': title,
                    'caption': caption,
                    'timestamp': timestamp,
                    'rating': rating_review,
                    'username': username,
                    'n_review_user': n_reviews,
                    'location': location
                }

                self.writer.writerow(list(item.values()))
                n_new_reviews += 1
            else:
                found_last_new = True

        return [found_last_new, n_new_reviews]

    def __expand_reviews(self):

        # load the complete review text in the HTML
        try:
            # wait until the element is clickable
            self.driver.find_element_by_xpath('//span[@class=\'taLnk ulBlueLinks\']').click()

            # wait complete reviews to load
            time.sleep(5)

        # It is raised only if there is no link for expansion (e.g.: set of short reviews)
        except Exception as e:
            self.logger.info('Expansion of reviews failed: no reviews to expand.')
            self.logger.info(e)
            pass
    
    
    def __get_logger(self):
        # create logger
        logger = logging.getLogger('tripadvisor-scraper')
        logger.setLevel(logging.DEBUG)
        
        # create console handler and set level to debug
        fh = logging.FileHandler('ta-scraper.log')
        fh.setLevel(logging.DEBUG)
        
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # add formatter to ch
        fh.setFormatter(formatter)
        
        # add ch to logger
        logger.addHandler(fh)
        
        return logger
   
    def __get_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1366,768")
        options.add_argument("--disable-notifications")
        input_driver = webdriver.Chrome(chrome_options=options)
    
        return input_driver
    
    def __get_writer(self):
        writer = csv.writer(self.targetfile, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        
        return writer
   
    # util function to clean special characters
    def __filterString(self, str):
        strOut = str.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
        return strOut