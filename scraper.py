from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

# BROWSER SETUP
# We use Chrome with a few tweaks to make it behave like a real human browser
# Without these, OLX can detect that we're a bot and block us

service = Service("./chromedriver")
options = webdriver.ChromeOptions()

# Open browser in full screen so all page elements load properly
options.add_argument("--start-maximized")

# Hide the fact that Chrome is being controlled by automation software
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

# Pretend to be a real user visiting from Chrome to OLX 
options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=service, options=options)

# Extra layer of bot protection it removes the 'navigator.webdriver' flag
# that websites use to detect Selenium automation
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

# Wait up to 15 seconds for elements to appear before giving up
wait = WebDriverWait(driver, 15)

# These lists will hold all our scraped data across all pages
titles, prices, locations, links = [], [], [], []

# Open the OLX electronics search page and give it time to fully load
driver.get("https://www.olx.com.pk/items/q-electronics")
time.sleep(6)  # OLX loads content dynamically, so we wait a bit longer on first load


# SCRAPING FUNCTION
# Extracts all product listings visible on the current page.

def scrape_current_page():
    count = 0  # track how many valid items we find on this page

    # Scroll down gradually, OLX uses lazy loading, meaning products only
    # appear in the HTML after you scroll past them, just like a real user would
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(1)  # small pause between scrolls so content has time to load

    # Parse the fully loaded page HTML using BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Try to find product cards using OLX's data attribute 
    # If that fails, fall back to grab all list items with a class
    items = soup.find_all("li", attrs={"data-aut-id": True})
    if not items:
        items = soup.select("ul > li[class]")  # fallback

    for item in items:
        #  Title
        # OLX marks the title with data-aut-id="itemTitle", but we also
        # check h2/h3 tags in case the structure changes
        title_tag = (item.find(attrs={"data-aut-id": "itemTitle"}) or
                     item.find("h2") or item.find("h3"))
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        #  Price
        # Prices are tagged with data-aut-id="itemPrice" on OLX
        price_tag = item.find(attrs={"data-aut-id": "itemPrice"})
        price = price_tag.get_text(strip=True) if price_tag else "N/A"

        # Location
        # OLX doesn't always use a consistent tag for location, so we scan
        # all <span> tags and pick the first one that looks like a city name,
        # short text, no digits, and not the same as the price
        location = "N/A"
        for span in item.find_all("span"):
            text = span.get_text(strip=True)
            if text and len(text) < 40 and not any(c.isdigit() for c in text) and text != price:
                location = text
                break

        # Link 
        # Grab the href from the first anchor tag inside the listing card.
        # Some links are relative (/item/...) so we prepend the base URL if needed
        a_tag = item.find("a", href=True)
        link = a_tag["href"] if a_tag else "N/A"
        if link != "N/A" and not link.startswith("http"):
            link = "https://www.olx.com.pk" + link

        # Only save the item if we actually got a title,skip ads/empty cards
        if title not in ("N/A", ""):
            titles.append(title)
            prices.append(price)
            locations.append(location)
            links.append(link)
            count += 1

    return count


# PAGINATION FUNCTION
# OLX pagination can be tricky,buttons change, URLs vary
# Trying 5 different strategies, moving on if one doesn't work

def go_to_next_page(current_page):

    # Strategy 1: Directly build the next page URL
    # This is the most reliable approach,no clicking needed, just navigate
    try:
        current_url = driver.current_url
        print(f"  Current URL: {current_url}")

        # If the URL already has a page number, just increment it
        if "?page=" in current_url:
            next_url = current_url.replace(f"?page={current_page}", f"?page={current_page + 1}")
        elif "&page=" in current_url:
            next_url = current_url.replace(f"&page={current_page}", f"&page={current_page + 1}")
        else:
            # First time adding a page param — append it to the URL
            separator = "&" if "?" in current_url else "?"
            next_url = f"{current_url}{separator}page={current_page + 1}"

        print(f"  Navigating to: {next_url}")
        driver.get(next_url)
        time.sleep(5)
        return True
    except Exception as e:
        print(f"  URL strategy failed: {e}")

    # Strategy 2: Click the official "next page" button using OLX's test ID
    try:
        btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[@data-testid='pagination-forward']")
        ))
        driver.execute_script("arguments[0].scrollIntoView();", btn)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(5)
        return True
    except:
        pass

    # Strategy 3: Try finding the button by its accessibility label
    try:
        btn = driver.find_element(By.XPATH, "//a[@aria-label='Next page']")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(5)
        return True
    except:
        pass

    # Strategy 4: Look for any link that literally says "Next"
    try:
        btn = driver.find_element(By.XPATH, "//a[contains(text(),'Next') or contains(text(),'next')]")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(5)
        return True
    except:
        pass

    # Strategy 5: Find the currently active page button, then click the one after it
    # Useful when OLX shows numbered pagination (1, 2, 3, 4...)
    try:
        current_page_btn = driver.find_element(
            By.XPATH, f"//button[@aria-current='page'] | //a[@aria-current='page']"
        )
        parent = current_page_btn.find_element(By.XPATH, "..")
        all_links = parent.find_elements(By.TAG_NAME, "a")
        for i, a in enumerate(all_links):
            if a.get_attribute("aria-current") == "page" and i + 1 < len(all_links):
                driver.execute_script("arguments[0].click();", all_links[i + 1])
                time.sleep(5)
                return True
    except:
        pass

    return False


# MAIN LOOP , Go through pages one by one


for page in range(1, 30):  # scrape up to 30 pages 
    print(f"\n Scraping page {page}...")

    count = scrape_current_page()
    print(f"  Got {count} items | Total so far: {len(titles)}")

    if page < 31:
        success = go_to_next_page(page)
        if not success:
            print("Could not navigate to next page. Stopping.")
            break

        time.sleep(2) 


# SAVE RESULTS

df = pd.DataFrame({"Title": titles, "Price": prices, "Location": locations, "Link": links})

df.drop_duplicates(subset=["Title", "Link"], inplace=True)

print(f"\n Total unique items scraped: {len(df)}")
df.to_csv("data.csv", index=False)
print(" Saved to data.csv")

driver.quit()