# TripAdvisor Reviews Scraper

Scraper of Tripadvisor reviews, parametric by date and language.
The script allows to scrape:
1. urls of TA points of interests based on string query
2. POIs metadata
3. POIs reviews up to a certain minimum date and with a specified language


## Installation
Follow these steps to use the scraper:
- Download Chromedrive from [here](https://chromedriver.storage.googleapis.com/index.html?path=2.45/).
- Install Python packages from requirements file, either using pip, conda or virtualenv:

        `conda create --name scraping python=3.6 --file requirements.txt`

**Note**: Python >= 3.6 is required.

## Usage
The scraper has 5 parameters:
- `--i`: input file, containing a list of Tripadvisor urls that point to first page of reviews.
- `--lang`: language code to filter reviews.
**Note**: only "select all languages" click is implemented.
- `--N`: number of reviews to scrape.
- `--q`: string query to scrape url places.
- `--place`: boolean value to scrape place metadata instead of reviews.

Some examples:

- `python scraper.py --q amsterdam`: generates the _urls.txt_ file with the top-30 POIs of amsterdam
- `python scraper.py --place 1`: generates a csv file containing metadata of places present in _urls.txt_
- `python scraper.py`: generates a csv file containing reviews of places present in _urls.txt_

The _config.json_ file allows to set the directory to store output csv, as well as their filenames.


## License
GNU GPLv3
