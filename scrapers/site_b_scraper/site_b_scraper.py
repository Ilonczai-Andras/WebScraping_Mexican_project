from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import json
import re
import time
import os
from typing import List, Dict, Any

def process_legislatura_data(file: str, url: str, visible=True):
    """Load legislaturas from JSON, run search for each, and save combined results."""
    print("\n--- Starting Data Processing ---")
    print(f"  📥 Input/Output File: '{file}'")
    print(f"  🔗 Target URL: '{url}'")
    print(f"  👁️ Browser Visible: {visible}")
    print("--------------------------------\n")

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
    
    try:
        for leg in legislaturas:
            # Navigate to the URL at the start of each loop
            driver.get(url)

            print(f"➡️ Processing {leg['name']}...")
            
            try:
                # Wait for iframe and switch to it
                iframe = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                driver.switch_to.frame(iframe)

                # Click the initial button
                button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/p/table/tbody/tr/td[2]/table[3]/tbody/tr[1]/td/button"))
                )
                button.click()

                # Wait for the dropdown and get the fresh element
                dropdown_xpath = "/html/body/form/table/tbody/tr[6]/td/table/tbody/tr/td[3]/select"
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, dropdown_xpath))
                )
                dropdown_element = driver.find_element(By.NAME, 'LEGISLATURA')
                select = Select(dropdown_element)
                
                # Check if the legislatura name exists in the dropdown
                options_text = [option.text.strip() for option in select.options]
                if leg['name'].strip() not in options_text:
                    print(f"⚠️ Could not find Legislatura '{leg['name']}' in dropdown — skipping.")
                    leg['data'] = {"status": "skipped", "message": "Legislatura not found in dropdown."}
                    continue
                
                # Select the legislatura by visible text
                select.select_by_visible_text(leg['name'].strip())
                
                # Fill dates
                start_date_element = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[8]/td/table[2]/tbody/tr/td[1]/input")
                end_date_element = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[8]/td/table[2]/tbody/tr/td[5]/input")
                
                start_date_element.clear()
                start_date_element.send_keys(leg["startDate"])
                
                end_date_element.clear()
                end_date_element.send_keys(leg["endDate"])
                
                # Click submit
                submit_button = driver.find_element(By.XPATH, "/html/body/form/table/tbody/tr[10]/td/button[1]")
                submit_button.click()
                
                # Wait for results table
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "/html/body/table[2]"))
                )
                
                # Collect count of sessions
                try:
                    number_text = driver.find_element(By.XPATH, "/html/body/table[2]/tbody/tr[1]/td[2]").text.strip()
                    number = int(re.search(r'\d+', number_text).group())
                except (ValueError, AttributeError):
                    number = 0
                    print(f"⚠️ Could not parse session count for {leg['name']}. Setting to 0.")

                # Collect links from the table
                links = [a.get_attribute('href') for a in driver.find_elements(By.TAG_NAME, 'a') if a.get_attribute('href')]

                # Append data directly to the current dictionary
                leg['data'] = {
                    "legislatura": leg["name"],
                    "link_count": len(links),
                    "all_link_isPresent": len(links) == number,
                    "links": links,
                }
                
                print(f"✅ Processed {leg['name']}: {len(links)} links found (Expected: {number})")
                
            except (NoSuchElementException, TimeoutException) as e:
                print(f"⚠️ Element not found or timed out for Legislatura '{leg['name']}'. Error: {e}")
                leg['data'] = {"status": "error", "message": str(e)}
            except Exception as e:
                print(f"❌ An unexpected error occurred for Legislatura '{leg['name']}': {e}")
                leg['data'] = {"status": "unexpected_error", "message": str(e)}
            finally:
                # Important: Switch back to the default content before the next iteration
                driver.switch_to.default_content()

    except Exception as e:
        print("❌ Error during main scraping loop:", e)
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

    # Save results by overwriting the original file
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(legislaturas, f, indent=2, ensure_ascii=False)

        print(f"✅ Data written back to original file '{file}'.")
    except Exception as e:
        print(f"❌ Error saving results back to file: {e}")
        import traceback
        traceback.print_exc()

# The wrapper function needs to be adjusted to not pass an output_file
def process_all_legislatura_data(urls_to_scrape: List[Dict[str, str]], visible: bool = True):
    for item in urls_to_scrape:
        # Pass only the necessary arguments to the modified function
        process_legislatura_data(
            file=item['filename'],
            url=item['url'],
            visible=visible,
        )