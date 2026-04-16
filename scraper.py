from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import pandas as pd
import time

# Setup browser
service = Service("./chromedriver")
driver = webdriver.Chrome(service=service)

# TODO: Add scraping logic
# TODO: Add pagination
# TODO: Add CSV export

driver.quit()
