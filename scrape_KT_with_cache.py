import requests
from bs4 import BeautifulSoup
import re
import time
from pymongo import MongoClient
import redis
import hashlib
import json

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client['politics_news_database']
news_collection = db['po_news_articles']

# Redis setup for caching and tracking state
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def hash_url(url):
    """Hash the URL to use as a Redis key"""
    return hashlib.md5(url.encode()).hexdigest()

def save_last_processed_page(page_number):
    """Save the last processed page number to Redis for resuming later"""
    redis_client.set('last_processed_page', page_number)

def get_last_processed_page():
    """Get the last processed page number from Redis"""
    return int(redis_client.get('last_processed_page').decode()) if redis_client.get('last_processed_page') else 1

def mark_url_processed(url):
    """Mark a URL as processed"""
    redis_client.sadd('processed_urls', hash_url(url))

def is_url_processed(url):
    """Check if a URL has already been processed"""
    return redis_client.sismember('processed_urls', hash_url(url))

def pause_signal():
    """Check if a pause signal has been sent"""
    return redis_client.get('pause_crawl') == b'True'

def extract_and_save_news_items(url):
    """Scrape the news items from the page and save them to MongoDB"""
    page = requests.get(url, timeout=10)
    soup = BeautifulSoup(page.content, 'html.parser')
    results = soup.find(class_='td_block_inner tdb-block-inner td-fix-index')

    if not results:
        return

    new_elements = results.find_all("div", class_="td-module-meta-info")
    for new_element in new_elements:
        title_element = new_element.find("p", class_="entry-title td-module-title")
        author_element = new_element.find("span", class_="td-post-author-name")
        date_element = new_element.find("span", class_="td-post-date")

        if title_element and date_element and author_element:
            title = title_element.text.strip()
            title = re.sub(r'ဗီဒီယို, ', '', title)
            title = re.sub(r'ကြာမြင့်ချိန်.*', '', title).strip(', ')

            news_item = {
                'title': title,
                'date': date_element.text.strip(),
                'author': author_element.text.strip(),
                'url': url
            }

            # Insert or update the article in MongoDB, using title as a unique key
            news_collection.update_one({'title': title}, {'$set': news_item}, upsert=True)

    # Mark this URL as processed
    mark_url_processed(url)

def crawl_website(start_url, max_pages=1000, pause_signal=None):
    """Crawl the website from a start URL and save data to MongoDB"""
    last_processed_page = get_last_processed_page()

    for page_number in range(last_processed_page, max_pages + 1):
        if pause_signal and pause_signal():
            print("Pausing the crawl...")
            break

        url = f'{start_url}/page/{page_number}'
        print(f"Processing page {page_number}: {url}")

        if is_url_processed(url):
            print(f"Page {page_number} has already been processed.")
            continue

        try:
            extract_and_save_news_items(url)
            save_last_processed_page(page_number)  # Save the current page number

            # Small delay to avoid overloading the server
            time.sleep(1)

        except Exception as e:
            print(f"Failed to process page {page_number}: {e}")
            continue

    print("Crawling complete.")

# Start crawling from the politics category, page 1 to 1000
start_url = 'https://yktnews.com/category/politics'
crawl_website(start_url, max_pages=1000, pause_signal=pause_signal)
