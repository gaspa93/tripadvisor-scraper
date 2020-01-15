# -*- coding: utf-8 -*-

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
import logging
import traceback
import locale
import requests

TA_WEBPAGE = 'https://www.tripadvisor.com'
TA_SEARCH_ENDPOINT = '/Search?geo=1&searchNearby=&redirect=&uiOrigin=MASTHEAD&q={}&supportedSearchTypes=find_near_stand_alone_query&enableNearPage=true'
URL_FILENAME = 'urls.txt'
MAX_WAIT = 10
MAX_RETRY = 10

HEADER = ['id_review', 'title', 'caption', 'rating', 'timestamp', 'username', 'n_review_user', 'location', 'n_votes_review', 'date_experience']
PLACE_HEADER = ['id', 'name', 'reviews', 'rating', 'address', 'ranking_string', 'ranking_pos', 'tags', 'ranking_length', 'url']


class Tripadvisor:

    def __init__(self):
        self.driver = self.__get_driver()
        self.logger = self.__get_logger()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)

        self.driver.close()
        self.driver.quit()

        return True


    def get_urls(self, query, section='ATTRACTIONS'):

        # section = ATTRACTIONS, EATERY, LODGING, ACTIVITY, VACATION_RENTALS, GEOS, USER_PROFILE, TRAVEL_GUIDES
        self.logger.info('Scraping %s in %s urls', section.lower(), query)

        self.driver.get(TA_WEBPAGE + TA_SEARCH_ENDPOINT.format(query))

        wait = WebDriverWait(self.driver, MAX_WAIT)
        xpath_filter = '//a[@class=\'search-filter ui_tab  \'  and @data-filter-id=\'{}\']'.format(section)
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_filter))).click()

        # wait for search results to load
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.search-results-list')))

        response = BeautifulSoup(self.driver.page_source, 'html.parser')

        results_list = response.find_all('div', class_='result-title')
        url_list = []
        for elem in results_list:
            features = elem['onclick'].split(',')

            url = TA_WEBPAGE + features[3].lstrip()[1:-1]
            url_list.append(url)

        return url_list


    def set_language(self, url, lang='ALL'):
        self.driver.get(url)
        self.driver.find_element_by_css_selector('li.ui_radio.location-review-review-list-parts-ReviewFilter__filter_row--p0z3u').click()
        time.sleep(5)

        return 0


    def get_reviews(self, page):

        if page > 1:

            self.driver.find_element_by_xpath('//a[@class=\'pageNum  \' and contains(text(), {})]'.format(page)).click()

            # some pages have automatic translation
            autotranslate_div = self.driver.find_element_by_css_selector('span.location-review-review-list-parts-MachineTranslationHeader__qtext--2lhyR')
            if autotranslate_div and autotranslate:
                self.driver.find_element_by_xpath('//div[@class=\'ui_radio\' and ./input[@id=\'autoTranslateNo\']]').click()

        self.__expand_reviews()

        resp = BeautifulSoup(self.driver.page_source, 'html.parser')
        reviews = self.__parse_reviews(resp)

        return reviews


    def get_place(self, url):
        self.logger.info('Scraping place metadata for url: %s', url)

        htmlpage = requests.get(url).text
        resp = BeautifulSoup(htmlpage, 'html.parser')

        # scrape place data
        place_data = self.__parse_location(resp)

        # get location id and area id parsing the url of the page
        id_location = int(re.search('-d(\d+)-', source_url).group(1))
        geo_id = int(re.search('-g(\d+)-', source_url).group(1))
        place_data['ta_id'] = id_location
        place_data['ta_geoid'] = geo_id
        place_data['url'] = url[:-1]

        return place_data


    def __parse_reviews(self, response):

        r_list = response.find_all('div', class_='location-review-card-Card__ui_card--2Mri0 location-review-card-Card__card--o3LVm location-review-card-Card__section--NiAcw')
        parsed_reviews = []
        for idx, review in enumerate(r_list):
            review_inner = review.find('div', class_='location-review-review-list-parts-SingleReview__mainCol--1hApa')

            id_review = review_inner['data-reviewid']
            user_and_date = review.find('div', class_='social-member-event-MemberEventOnObjectBlock__event_type--3njyv').text
            date_raw = re.search('(.)*(ha\sscritto\suna\srecensione\sa)\s((.)*)', user_and_date).group(3)
            date = self.__parse_date(date_raw)


            username = review.find('a', class_='ui_header_link social-member-event-MemberEventOnObjectBlock__member--35-jC').text
            location = review.find('span', class_='default social-member-common-MemberHometown__hometown--3kM9S small')
            if location is not None:
                location = location.text

            rating_raw = review_inner.find('span', {"class": re.compile("ui_bubble_rating\sbubble_..")})['class'][1][-2:]
            rating_review = float(rating_raw[0] + '.' + rating_raw[1])

            values = review.find_all('span', class_='social-member-MemberHeaderStats__bold--3z3qh')
            n_reviews = int(values[0].text.replace(',', '').replace('.', ''))

            if len(values) > 1:
                votes = int(values[1].text.replace(',', '').replace('.', ''))
            else:
                votes = 0

            #title = self.__filter_string(review.find('span', class_='noQuotes').text)
            title = self.__filter_string(review_inner.find('a', class_='location-review-review-list-parts-ReviewTitle__reviewTitleText--2tFRT').text)
            caption = self.__filter_string(review_inner.find('q', class_='location-review-review-list-parts-ExpandableReview__reviewText--gOmRC').text)

            # date of experience
            date_exp = review_inner.find('span', class_='location-review-review-list-parts-EventDate__event_date--1epHa').text.split(':')[1]
            item = {
                'id_review': id_review,
                'title': title,
                'caption': caption,
                'rating': rating_review,
                'date': date,
                'username': username,
                'n_review_user': n_reviews,
                'location': location,
                'n_votes_review': votes,
                'date_of_experience': date_exp
            }

            parsed_reviews.append(item)

        return parsed_reviews


    def __expand_reviews(self):

        # load the complete review text in the HTML
        try:
            self.driver.find_element_by_xpath('//span[@class=\'location-review-review-list-parts-ExpandableReview__cta--2mR2g\']').click()

            # wait complete reviews to load
            time.sleep(5)

        # It is raised only if there is no link for expansion (e.g.: set of short reviews)
        except Exception as e:
            self.logger.info('Expansion of reviews failed: no reviews to expand.')
            self.logger.info(e)
            pass


    def __parse_date(self, d):
        if d.lower() == 'oggi':
            return datetime.today().date()
        elif d.lower() == 'ieri':
            return (datetime.today() - timedelta(days=1)).date()
        else:
            locale.setlocale(locale.LC_ALL, 'it_it')
            p1, p2 = d.split(' ')
            if len(p1) > 2:
                day = '01'
                month = p1
                year = p2
            else:
                day = p1
                month = p2
                year = str(datetime.now().year)
            month = month[0].upper() + month[1:]
            return datetime.strptime(day + ' ' + month + ', ' + year, '%d %b, %Y').date()


    def __parse_location(self, response):

        # prepare a dictionary to store results
        place = {}

        # get place name
        name = response.find('h1', attrs={'id': 'HEADING'}).text
        place['ta_name'] = name

        # get number of reviews
        try:
            num_reviews = response.find('span', class_='reviewCount').text
            num_reviews = int(num_reviews.split(' ')[0].replace(',', '').replace('.', ''))
        except:
            num_reviews = 0
        place['n_reviews'] = num_reviews

        # get rating using a regular expression to find the correct class
        raw_rating = response.find('span', {"class": re.compile("ui_bubble_rating\sbubble_..")})['class'][1][-2:]
        overall_rating = float(raw_rating[0] + '.' + raw_rating[1])
        place['overall_rating'] = overall_rating

        # get address
        try:
            complete_address = response.find('span', class_='detail').text
        except:
            complete_address = None
        place['address'] = complete_address

        # get ranking
        try:
            ranking_string = response.find('span', class_='header_popularity popIndexValidation ').text
        except:
            ranking_string = None
        place['ranking_string'] = ranking_string

        try:
            rank_pos = int(ranking_string.split(' ')[0][1:])
            ranking_length = int(ranking_string.split(' ')[2].replace(',', ''))
        except:
            rank_pos = None
            ranking_length = None
        place['ranking_pos'] = rank_pos
        place['ranking_length'] = ranking_length

        # get most important tags
        try:
            tag_list = response.find('span', class_='is-hidden-mobile header_detail attractionCategories').text.replace('Other', '').split(',')
            tags = ';'.join([t.strip() for t in tag_list if len(t)>0])  # store a semicolon separated list in file
        except:
            tags = []
        place['tags'] = tags

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


    def __get_driver(self, debug=False):
        options = Options()
        if not debug:
            options.add_argument("--headless")
        options.add_argument("--window-size=1366,768")
        options.add_argument("--disable-notifications")
        options.add_argument("--lang=en")
        input_driver = webdriver.Chrome(chrome_options=options)

        return input_driver


    # util function to clean special characters
    def __filter_string(self, str):
        strOut = str.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
        return strOut
