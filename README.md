# Project Name: OLX Electronics Scraper

### 1. Project Overview
* **Target Website:** https://www.olx.com.pk/items/q-electronics
* **Data Fields Extracted:** Title, Price, Location, Link
* **Tools Used:** Python, Selenium, BeautifulSoup, Pandas

### 2. Setup Instructions
1. Clone this repo: `git clone https://github.com/NafarFatima/Web_scraper.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run script: `python scraper.py`

### 3. Challenges & Solutions
* **Bot Detection:** OLX detects automated browsers, so we disabled the navigator.webdriver flag and added a real user-agent string to appear human.
* **Pagination:** The next page button had no reliable selector, so we built the next page URL directly by appending ?page=2, ?page=3 etc.
* **Lazy Loading:** OLX only loads listings after scrolling, so we added a gradual scroll loop before scraping each page.
