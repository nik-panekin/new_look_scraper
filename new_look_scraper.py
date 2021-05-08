"""This script performs data scraping from the New Look store website located
at https://www.newlook.com/. It retrieves essential information for all
products in one particular category (e.g. women's shoes) by means of unofficial
API originally intended for AJAX.
"""
import os
import os.path
import re
import csv
import sys
import time

import requests
from bs4 import BeautifulSoup

# Timeout for web server response (seconds)
TIMEOUT = 5

# Maximum retries count for executing request if an error occurred
MAX_RETRIES = 3

# The delay after executing an HTTP request (seconds)
SLEEP_TIME = 1

# Base URL for the New Look site
BASE_URL = 'https://www.newlook.com/uk'

"""URL for making API requests
You may change it accordingly for scraping items from any category as needed.
E.g. /womens/clothing/dresses/c/uk-womens-clothing-dresses/data-48.json for
retrieving data from "women's dresses" category.
"""
JSON_URL = BASE_URL + '/womens/footwear/c/uk-womens-footwear/data-48.json'

# HTTP headers for making the scraper more "human-like"
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 6.1; rv:88.0)'
                   ' Gecko/20100101 Firefox/88.0'),
    'Accept': '*/*',
}

# Default filename for saving scraped data
DEFAULT_FILENAME = 'new_look.csv'

# Directory name for saving scraped images
IMAGE_DIR = 'img'

# Common text for displaying while script is shutting down
FATAL_ERROR_STR = 'Fatal error. Shutting down.'

# Retrieving HTTP GET response implying TIMEOUT and HEADERS
def get_response(url: str, params: dict=None) -> requests.Response:
    """Input and output parameters are the same as for requests.get() function.
    Also retries, timeouts, headers and error handling are ensured.
    """
    for attempt in range(0, MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                             params=params)
        except requests.exceptions.RequestException:
            time.sleep(SLEEP_TIME)
        else:
            time.sleep(SLEEP_TIME)
            if r.status_code != requests.codes.ok:
                print(f'Error {r.status_code} while accessing {url}.')
                return False
            return r

    print(f'Error: can\'t execute HTTP request while accessing {url}.')
    return False

# Getting data for products via API GET request as JSON dictionary
def get_json(page: int) -> dict:
    """This function prepares all the parameters needed for executing the API
    call via HTTP GET request retrieving JSON dictionary as a response.

    Input:
    page: int - requested page of the multi-page dataset.

    Output:
    JSON response as a dictionary containing all the data and meta-data.
    """
    params = {
        'currency': 'GBP',
        'language': 'en',
        'q': ':relevance',
        'sort': 'relevance',
        'page': page,
    }
    r = get_response(JSON_URL, params=params)

    if not r:
        return False

    try:
        json = r.json()
    except Exception as e:
        print('Error while getting JSON: ' + str(e))
        return False

    if not json.get('success', False):
        print('Error: API request via JSON was not successful.')
        return False

    return json

# Getting total page count from JSON dataset
def get_page_count(json: dict) -> int:
    """Input:
    json: dict - JSON as a dictionary retrieved via API call.

    Output:
    Total page count of the multi-page dataset as int.
    """
    try:
        page_count = json['data']['pagination']['numberOfPages']
    except Exception as e:
        print('Error while getting page count in JSON: ' + str(e))
        return False
    return page_count

# Getting a list of all products from JSON
def get_items(json: dict) -> list:
    """Input:
    json: dict - JSON as a dictionary retrieved via API call.

    Output:
    List of items. Each item is a dictionary as follows:
    {
        'name': str,
        'url': str,
        'description': str,
        'price': str,
        'image': str,
    }
    """
    items = []
    for item in json['data']['results']:
        try:
            new_item = {
                'name': item['name'],
                'url': BASE_URL + item['url'],
                'price': item['price']['formattedValue'],
                'image': 'https:' + item['images'][0]['url'],
            }

            new_item['description'] = re.sub(r'\s+', ' ',
                BeautifulSoup(item['description'], 'lxml').get_text())
        except Exception as e:
            print('Error while parsing JSON for an item: ' + str(e))
        else:
            items.append(new_item)
    return items

# Retrieve an image from URL and save it to a file
def save_image(url: str, filename: str):
    r = get_response(url)

    try:
        with open(filename, 'wb') as f:
            f.write(r.content)
    except OSError:
        print('Error: can\'t save an image to the disk.')
    except Exception as e:
        print('Error while retrieving an image from URL: ' + str(e))

# Saving items data and images to a file
def save_items(items: list, filename: str, first_page=False):
    """Input:
    items: list - a list of dictionaries produced by get_items() function;
    filename - path to CSV file for the data to be saved;
    first_page: bool - a flag indicating whether the CSV file needs to be
    newly rewritten (this case implies header row insertion) or just appended.
    """
    keys = ['name', 'url', 'description', 'price', 'image']
    titles = ['Item name', 'URL', 'Description', 'Price', 'Image']
    try:
        with open(filename, 'w' if first_page else 'a',
                  newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            if first_page:
                writer.writerow(titles)
            for item in items:
                image_url = item['image']
                image_filename = os.path.join(
                    os.getcwd(), IMAGE_DIR, image_url.split('/')[-1])
                save_image(image_url, image_filename)

                item['image'] = 'file:///' + image_filename
                writer.writerow([item.get(key, '') for key in keys])
    except OSError:
        print('Error: can\'t write to CSV file.')
    except Exception as e:
        print('Error while saving scraped data: ' + str(e))

# Executing the whole scraping process
def scrape():
    if not os.path.exists(IMAGE_DIR):
        try:
            os.mkdir(IMAGE_DIR)
        except OSError:
            print('Can\'t create directory for images.\n' + FATAL_ERROR_STR)
            return

    print('Accessing first page.')
    json = get_json(0)
    if not json:
        print(FATAL_ERROR_STR)
        return

    page_count = get_page_count(json)
    if not page_count:
        print(FATAL_ERROR_STR)
        return

    for page in range(0, page_count):
        if page > 0:
            print(f'Scraping page {page + 1} of {page_count}.')
            json = get_json(page)
            if not json:
                print(FATAL_ERROR_STR)
                return

        print(f'Scraping images for page {page + 1}.')
        save_items(get_items(json), DEFAULT_FILENAME, page == 0)
    print('Scraping process done.')


if __name__ == '__main__':
    scrape()
