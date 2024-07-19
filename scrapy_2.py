import requests
from bs4 import BeautifulSoup
import csv
import re

def get_news_from_page(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    results = soup.find(class_='bbc-k6wdzo')
    if results:
        new_elements = results.find_all("div", class_="promo-text")
        news_items = []
        for new_element in new_elements:
            title_element = new_element.find("h2", class_="bbc-145rmxj e47bds20")
            date_element = new_element.find("time", class_="promo-timestamp bbc-11pkra2 e1mklfmt0")
            if title_element and date_element:
                # Remove "ဗီဒီယို" and words after "ကြာမြင့်ချိန်"
                title = title_element.text.strip()
                title = re.sub(r'ဗီဒီယို, ', '', title)
                title = re.sub(r'ကြာမြင့်ချိန်.*', '', title).strip(', ')
                news_item = {
                    'title': title,
                    'date': date_element.text.strip()
                }
                news_items.append(news_item)
        return news_items
    return []

# Prepare the data
all_news_items = []

# Iterate over pages 1 to 40
for page_number in range(1, 41):
    url = f'https://www.bbc.com/burmese/topics/cnlv9j1z93wt?page={page_number}'
    print(f"Scraping page {page_number}")
    news_items = get_news_from_page(url)
    all_news_items.extend(news_items)

# Write data to CSV file
csv_file = 'scraped_news.csv'
csv_columns = ['title', 'date']

try:
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for news_item in all_news_items:
            writer.writerow(news_item)
except IOError:
    print("I/O error")

print(f"Data has been written to {csv_file}")
