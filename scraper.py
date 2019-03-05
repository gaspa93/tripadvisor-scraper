# -*- coding: utf-8 -*-
from tripadvisor import Tripadvisor
from datetime import datetime
import argparse


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tripadvisor reviews scraper.')
    parser.add_argument('--lang', type=str, default='ALL', help='language code of the reviews to scrape')
    parser.add_argument('--o', type=str, default='ta_reviews.csv', help='CSV target file')
    parser.add_argument('--i', type=str, default='urls.txt', help='target URLs file')
    parser.add_argument('--date', type=valid_date, default=datetime.today(), help='Min date of reviews to scrape, format YYYY-MM-DD')
    parser.add_argument('--q', type=str, required=False, help='Scraping reviews of places based on a string query')
    
    args = parser.parse_args()

    with Tripadvisor(args.o, args.date, args.lang) as scraper:

        # scraping based on urls file
        if args.q is None:
            with open(args.i, 'r') as urls_file:
                for url in urls_file:
                    scraper.get_reviews(url)

        # scraping based on query on Tripadvisor search bar
        else:
            scraper.get_reviews_from_query(args.q)

