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
import traceback

TA_WEBPAGE = 'https://www.tripadvisor.com'
MAX_WAIT = 10

HEADER = ['id_review', 'title', 'caption', 'timestamp', 'rating', 'username', 'n_review_user', 'location']
PLACE_HEADER = ['id', 'name', 'reviews', 'rating', 'address', 'ranking_string', 'ranking_pos', 'tags', 'ranking_length', 'url']


class Tripadvisor:

    def __init__(self, targetfile, min_date, lang):
        self.min_date = min_date
        self.targetfile = open(targetfile, 'w', encoding='utf-8', newline='\n')
        self.lang = lang
        
        self.driver = self.__get_driver()
        self.writer = self.__get_writer()
        self.logger = self.__get_logger()

        self.placefile = open('ta_places.csv', 'w', encoding='utf-8', newline='\n')
        self.placewriter = self.__get_placewriter()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
        
        self.logger.info('Closing chromedriver...')
        self.driver.close()
        self.driver.quit()

        self.targetfile.close()
        self.placefile.close()

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

    def get_reviews_from_query(self, query):
        
        section = 'ATTRACTIONS'  # EATERY, LODGING, ACTIVITY, VACATION_RENTALS, GEOS, USER_PROFILE, TRAVEL_GUIDES
        self.logger.info('Scraping %s in %s', section.lower(), query)

        self.driver.get(TA_WEBPAGE)

        new_website_popup = 'div.overlays-pieces-CloseX__close--3jowQ.overlays-pieces-CloseX__inverted--3ADoB'
        
        try:
            self.driver.find_element_by_css_selector(new_website_popup).click()
        except NoSuchElementException:
            self.logger.warn('No pop-up to remove')

        self.driver.find_element_by_css_selector('div.brand-global-nav-action-search-Search__searchButton--2dmUT').click()
        search_bar = self.driver.find_element_by_id('mainSearch')
        search_bar.send_keys(query)
        search_bar.send_keys(Keys.RETURN)

        wait = WebDriverWait(self.driver, MAX_WAIT)
        xpath_filter = '//a[@class=\'search-filter ui_tab  \'  and @data-filter-id=\'{}\']'.format(section)
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_filter))).click()

        # wait for search results to load
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.search-results-list')))

        response = BeautifulSoup(self.driver.page_source, 'html.parser')

        results_list = response.find_all('div', class_='result-title')
        for elem in results_list:
            features = elem['onclick'].split(',')

            url = TA_WEBPAGE + features[3].lstrip()[1:-1]

            # get page
            self.driver.get(url)
            resp = BeautifulSoup(self.driver.page_source, 'html.parser')

            # scrape place data
            place_data = self.__parse_location(resp, url)
            place_data['url'] = url

            self.placewriter.writerow(list(place_data.values()))

            # scrape reviews of place using lang and min date configured
            self.get_reviews(url)

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
                
                title = self.__filter_string(review.find('span', class_='noQuotes').text)
                caption = self.__filter_string(review.find('p', class_='partial_entry').text)

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

    def __parse_location(self, response, source_url):
    
        # prepare a dictionary to store results
        place = {}
        
        # get location id and area id parsing the url of the page
        id_location = int(re.search('-d(\d+)-', source_url).group(1))
        geo_id = int(re.search('-g(\d+)-', source_url).group(1))
        place['id'] = id_location
        place['geoid'] = geo_id
        
        # get place name
        name = response.find('h1', attrs={'id': 'HEADING'}).text
        place['name'] = name

        # get number of reviews
        num_reviews = response.find('span', class_='reviewCount').text
        num_reviews = int(num_reviews.split(' ')[0].replace(',', ''))
        place['reviews'] = num_reviews

        # get rating using a regular expression to find the correct class
        overall_rating = response.find('span', {"class": re.compile("ui_bubble_rating\sbubble_..")})['alt']
        overall_rating = float(overall_rating.split(' ')[0])
        place['rating'] = overall_rating

        # get address
        complete_address = response.find('span', class_='detail').text
        place['address'] = complete_address

        # get ranking
        ranking_string = response.find('span', class_='header_popularity popIndexValidation ').text
        rank_pos = int(ranking_string.split(' ')[0][1])
        ranking_length = int(ranking_string.split(' ')[2].replace(',', ''))
        place['ranking_string'] = ranking_string
        place['ranking_pos'] = rank_pos
        place['ranking_length'] = ranking_length

        # get most important tags
        tags = response.find('div', class_='detail').text.replace('More', '').split(',')
        place['tags'] = ';'.join([t.strip() for t in tags if len(t)>0])  # store a semicolon separated list in file

        return place

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
        writer.writerow(HEADER)
        
        return writer

    def __get_placewriter(self):
        writer = csv.writer(self.placefile, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(PLACE_HEADER)

        return writer
   
    # util function to clean special characters
    def __filter_string(self, str):
        strOut = str.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
        return strOut