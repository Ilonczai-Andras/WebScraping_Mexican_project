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
from typing import List, Dict, Any

def process_legislatura_data(file: str, url: str, visible=True, output_file="legislatura_results.json"):
    """Load legislaturas from JSON, run search for each, and save combined results."""
    print("")
    print(f"--- Starting Data Processing ---")
    print(f"  📥 Input File: '{file}'")
    print(f"  🔗 Target URL: '{url}'")
    print(f"  👁️ Browser Visible: {visible}")
    print(f"  📝 Output File: '{output_file}'")
    print(f"--------------------------------")
    print("")

    # Load legislaturas list from JSON
    if not os.path.exists(file):
        print(f"❌ {file} not found. Please create it first.")
        return

    with open(file, "r", encoding="utf-8") as f:
        legislaturas = json.load(f)

    # Chrome setup
    options = Options()
    if not visible:
        options.add_argument("--headless=new")

    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument('--log-level=3')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    all_results = []

    try:
        for leg in legislaturas:
            # Wait for iframe and switch (do this for each iteration)
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

            # Wait for dropdown and create fresh Select object
            dropdown_xpath = "/html/body/form/table/tbody/tr[6]/td/table/tbody/tr/td[3]/select"
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, dropdown_xpath))
            )

            # Find dropdown element fresh for each iteration
            dropdown_element = driver.find_element(By.NAME, 'LEGISLATURA')
            select = Select(dropdown_element)

            matched = False
            for option in select.options:
                if option.text.strip() == leg['name'].strip():
                    try:
                        # Select legislatura using visible text
                        select.select_by_visible_text(option.text)
                        
                        # Fill dates 
                        start_date_xpath = "/html/body/form/table/tbody/tr[8]/td/table[2]/tbody/tr/td[1]/input" 
                        end_date_xpath = "/html/body/form/table/tbody/tr[8]/td/table[2]/tbody/tr/td[5]/input" 
                        
                        start_date_element = driver.find_element(By.XPATH, start_date_xpath)
                        start_date_element.clear()
                        start_date_element.send_keys(leg["startDate"])

                        end_date_element = driver.find_element(By.XPATH, end_date_xpath)
                        end_date_element.clear()
                        end_date_element.send_keys(leg["endDate"])

                        # Click submit 
                        submit_xpath = "/html/body/form/table/tbody/tr[10]/td/button[1]" 
                        submit_button = driver.find_element(By.XPATH, submit_xpath)
                        submit_button.click()
                        
                        # Wait for results table with better condition
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.TAG_NAME, "table"))
                        )
                        
                        # Additional wait to ensure page is fully loaded
                        time.sleep(2)

                        # Collect count of sessions
                        number = int(driver.find_element(By.XPATH, "/html/body/table[2]/tbody/tr[1]/td[2]").text.strip())

                        # Collect links
                        link_elements = driver.find_elements(By.TAG_NAME, 'a')
                        links = [a.get_attribute('href') for a in link_elements if a.get_attribute('href')]

                        all_results.append({
                            "legislatura": leg["name"],
                            "link_count": len(links),
                            "all_link_isPresent" : len(links) == number,
                            "links": links,
                            
                        })

                        print(f"✅ Processed {leg['name']}: {len(links)} links found")
                        matched = True
                    except NoSuchElementException:
                        print(f"⚠️ Could not find Legislatura '{leg['name']}' in dropdown or an element was not found on the results page — skipping.")
                    except Exception as e:
                        print(f"❌ Error processing Legislatura '{leg['name']}': {e}")

                    break
            
            if not matched:
                print(f"⚠️ Could not find Legislatura '{leg['name']}' in dropdown — skipping.")

            # Navigate back to initial page for next iteration
            driver.get(url) # Changed this to 'url' to be more flexible

    except Exception as e:
        print("❌ Error during scraping:", e)
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

    # Save results
    try:
        total_links = sum(len(item["links"]) for item in all_results)

        output_data = {
            "total_link_count": total_links,
            "results": all_results
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ {output_file} created with {len(all_results)} records and {total_links} total links.\n")
    except Exception as e:
        print(f"❌ Error saving results: {e}")

def process_all_legislatura_data(urls_to_scrape: List[Dict[str, str]], visible: bool = True):
    for item in urls_to_scrape:
        process_legislatura_data(
            file=item['input_file'],
            url=item['url'],
            visible=visible,
            output_file=item['output_file']
        )