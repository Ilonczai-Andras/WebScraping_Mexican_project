import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Any

def scrape_legislatura_by_url(url: str, visible: bool = True, output_file: str = "legislatura.json") -> None:
    """Scrape legislatura data from a single URL and save it to a JSON file.

    Args:
        url (str): The URL to scrape.
        visible (bool): If True, the browser will be visible. Defaults to True.
        output_file (str): The name of the output JSON file. Defaults to "legislatura.json".
    """
    
    # New print statement using f-string for clarity
    print("")
    print(f"--- Starting Scrape ---")
    print(f"  URL: {url}")
    print(f"  Browser Visible: {visible}")
    print(f"  Output File: {output_file}")
    print(f"-----------------------")
    print("")
    
    # Chrome options
    options = Options()
    if not visible:
        options.add_argument("--headless=new")

    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument('--log-level=3')
    
    # Use a context manager for the driver to ensure it's closed properly
    with webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options) as driver:
        try:
            driver.get(url)

            # Wait for iframe to be present and switch to it
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)

            # Wait for the button to be clickable and click it
            full_xpath = "/html/body/p/table/tbody/tr/td[2]/table[3]/tbody/tr[1]/td/button"
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, full_xpath))
            )
            button.click()

        except Exception as e:
            print(f"❌ Could not scrape data from {url}: {e}")
            return
        
        # Get page source after the button click
        html = driver.page_source
        
        # Extract Legislaturas from the JavaScript code
        pattern = re.compile(
            r"Legislaturas\[\d+\]=new Legislatura\('([^']+)','([^']+)','(\d+)','([^']+)'\);"
        )
        matches = pattern.findall(html)
        
        data = [
            {"startDate": start, "endDate": end, "value": int(num), "name": roman}
            for start, end, num, roman in matches
        ]
        
    # Save the data to the specified JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ {output_file} created with {len(data)} records.\n")

def scrape_all_legislaturas(urls_to_scrape: List[Dict[str, str]], visible: bool = True) -> None:
    """
    Scrapes data from a list of URLs, saving each to its own JSON file.

    Args:
        urls_to_scrape (List[Dict[str, str]]): A list of dictionaries, where each dictionary
                                               contains a 'url' and a 'filename'.
        visible (bool): If True, the browser will be visible. Defaults to True.
    """
    for item in urls_to_scrape:
        scrape_legislatura_by_url(
            url=item['url'],
            visible=visible,
            output_file=item['filename']
        )