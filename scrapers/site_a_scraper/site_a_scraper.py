import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import config.settings as settings


def scrape_legislaturas(visible=True, output_file="legislatura.json"):
    """Scrape legislaturas from the given website and save as JSON."""
    
    # Chrome options
    options = Options()
    if not visible:
        options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(settings.senate_url)

    try:
        # Wait for iframe
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        driver.switch_to.frame(iframe)

        # Wait for button click
        full_xpath = "/html/body/p/table/tbody/tr/td[2]/table[3]/tbody/tr[1]/td/button"
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, full_xpath))
        )
        button.click()

    except Exception as e:
        print("❌ Could not click the button:", e)

    # Get page source
    html = driver.page_source
    driver.quit()

    # Extract Legislaturas from JS including the numeric value
    pattern = re.compile(
        r"Legislaturas\[\d+\]=new Legislatura\('([^']+)','([^']+)','(\d+)','([^']+)'\);"
    )
    matches = pattern.findall(html)
    # matches now gives: start, end, numeric_value, roman_name

    data = [
        {"startDate": start, "endDate": end, "value": int(num), "name": roman}
        for start, end, num, roman in matches
    ]

    # Save JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ {output_file} created with {len(data)} records.")

