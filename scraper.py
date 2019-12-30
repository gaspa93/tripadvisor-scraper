# -*- coding: utf-8 -*-
from tripadvisor import Tripadvisor, ScrapeType
from datetime import datetime, timedelta
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
    parser.add_argument('--N', type=int, default=10, help='Max number of reviews to scrape')
    parser.add_argument('--i', type=str, default='urls.txt', help='target URLs file')
    parser.add_argument('--q', type=str, required=False, help='Scraping urls of places based on a string query')
    parser.add_argument('--place', type=bool, default=False, help='Scraping place metadata instead of reviews')

    args = parser.parse_args()

    # scrape urls of places
    if args.q is not None:
        with Tripadvisor(args.N, args.lang, scrape_target=ScrapeType.URL) as scraper:
            scraper.get_urls(args.q)

    # scrape place metadata
    elif args.place:
        with Tripadvisor(args.N, args.lang, scrape_target=ScrapeType.PLACE) as scraper:
            with open(args.i, 'r') as urls_file:
                for url in urls_file:
                    scraper.get_places(url)

    # scrape place reviews
    else:
        with Tripadvisor(args.N, args.lang) as scraper:
            with open(args.i, 'r') as urls_file:
                for url in urls_file:
                    scraper.get_reviews(url)
