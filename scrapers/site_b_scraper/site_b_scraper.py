from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json
import re
import config.settings as settings
import time
import os

def extend_legislaturasJson_with_links(visible=True, output_file="legislatura_results.json"):
    """Load legislaturas from JSON, run search for each, and save combined results."""

    # Load legislaturas list from JSON
    legislatura_file = "legislatura.json"
    if not os.path.exists(legislatura_file):
        print(f"❌ {legislatura_file} not found. Please create it first.")
        return

    with open(legislatura_file, "r", encoding="utf-8") as f:
        legislaturas = json.load(f)

    # Chrome setup
    options = Options()
    if not visible:
        options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(settings.senate_url)

    try:
        # Wait for iframe and switch
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        driver.switch_to.frame(iframe)

        # Click initial button
        full_xpath = "/html/body/p/table/tbody/tr/td[2]/table[3]/tbody/tr[1]/td/button"
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, full_xpath))
        )
        button.click()

        # Wait for dropdown
        dropdown_xpath = "/html/body/form/table/tbody/tr[6]/td/table/tbody/tr/td[3]/select"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, dropdown_xpath))
        )

        all_results = []

        dropdown_element = driver.find_element(By.NAME, 'LEGISLATURA')
        select = Select(dropdown_element)

        for leg in legislaturas:
            matched = False
            for option in select.options:
                if option.text.strip() == leg['name'].strip():

                    # Select legislatura using value instead of visible text
                    select.select_by_visible_text(option.text)

                    # Fill dates 
                    start_date_xpath = "/html/body/form/table/tbody/tr[8]/td/table[2]/tbody/tr/td[1]/input" 
                    end_date_xpath = "/html/body/form/table/tbody/tr[8]/td/table[2]/tbody/tr/td[5]/input" 
                    driver.find_element(By.XPATH, start_date_xpath).clear() 
                    driver.find_element(By.XPATH, start_date_xpath).send_keys(leg["startDate"]) 

                    driver.find_element(By.XPATH, end_date_xpath).clear() 
                    driver.find_element(By.XPATH, end_date_xpath).send_keys(leg["endDate"])

                    # Click submit 
                    submit_xpath = "/html/body/form/table/tbody/tr[10]/td/button[1]" 
                    driver.find_element(By.XPATH, submit_xpath).click() 
                    # Wait for results (better to wait for table update) 
                    time.sleep(2)

                    matched = True
                    break
            if not matched:
                print(f"⚠️ Could not find Legislatura '{leg['name']}' in dropdown — skipping.")
                continue

        # Save results
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"✅ {output_file} created with {len(all_results)} records.")

    except Exception as e:
        print("❌ Error during scraping:", e)
    finally:
        driver.quit()
