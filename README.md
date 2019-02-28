# TripAdvisor Reviews Scraper

Scraper of Tripadvisor reviews, parametric by date and language.
The script allows to extract information about reviews up to a certain minimum date and with a specified language.


## Installation
Follow these steps to use the scraper:
- Download Chromedrive from [here](https://chromedriver.storage.googleapis.com/index.html?path=2.45/).
- Install Python packages from requirements file, either using pip, conda or virtualenv:

`conda create --name scraping-env python=3.6 --file requirements.txt`

**Note**: Python >= 3.6 is required. 

## Usage
The scraper has 4 parameters:
- `--i`: input file, containing a list of Tripadvisor urls that point to first page of reviews.
- `--o`: output file, results are stored in CSV format.
- `--lang`: language code to filter reviews. 
**Note**: at the moment, only languages that are visible on Tripadvisor website can be selected (e.g.: the ones with highest number of reviews).
- `--date`: minimum date of reviews that we want to store, in the format YYYY-MM-DD.

## License
GNU GPLv3
