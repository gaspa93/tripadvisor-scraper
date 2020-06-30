# -*- coding: utf-8 -*-

from tripadvisor import Tripadvisor
import argparse
import csv

HEADER = ['id_review', 'title', 'caption', 'rating', 'timestamp', 'username', 'userlink', 'n_review_user', 'location', 'n_votes_review', 'date_of_experience']
PLACE_HEADER = ['id', 'name', 'reviews', 'rating', 'address', 'ranking_string', 'ranking_pos', 'tags', 'ranking_length', 'url']

def csv_writer(path='data/', outfile='ta_reviews'):
    targetfile = open(path + outfile + '.csv', mode='w', encoding='utf-8', newline='\n')
    writer = csv.writer(targetfile, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(HEADER)

    return writer

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tripadvisor scraper.')
    parser.add_argument('--N', type=int, default=10, help='Max number of reviews to scrape')
    parser.add_argument('--i', type=str, default='urls.txt', help='target URLs file')
    parser.add_argument('--q', type=str, required=False, help='Scraping urls of places based on a string query')
    parser.add_argument('--place', dest='place', action='store_true', help='Scraping place metadata instead of reviews')
    parser.add_argument('--debug', dest='debug', action='store_true', help='Debug mode: chromedriver with graphical part')
    parser.set_defaults(place=False, debug=False)

    args = parser.parse_args()

    # store reviews in CSV file
    writer = csv_writer()

    with Tripadvisor(debug=args.debug) as scraper:
        # scrape urls of places
        if args.q:
            urls = scraper.get_urls(args.q)
            print(urls)

        # scrape place metadata
        elif args.place:
            with open(args.i, 'r') as urls_file:
                for url in urls_file:
                    poi = scraper.get_place(url)
                    print(poi)

        # scrape place reviews
        else:
            with open(args.i, 'r') as urls_file:
                for url in urls_file:

                    scraper.set_language(url)

                    n = 0
                    pag = 1
                    while n < args.N:
                        reviews = scraper.get_reviews(pag)

                        for r in reviews:
                            writer.writerow(list(r.values()))

                        n += len(reviews)
                        pag += 1
