from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import re
from datetime import datetime
import os
import json
import sys
import logging

class ParliamentaryScraper:
    def __init__(self, visible=False, output_folder="exported_excels", log_folder="logs"):
        self.setup_driver(visible)
        self.output_folder = output_folder
        self.log_folder = log_folder
        self.setup_output_folder()
        self.setup_logging()
        
    def setup_driver(self, visible):
        """Set up Chrome driver with optimized options for speed"""
        chrome_options = Options()
        if not visible:
            chrome_options.add_argument("--headless=new")

        # Performance optimizations
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Don't load images
        chrome_options.add_argument("--disable-javascript")  # Only if site works without JS
        chrome_options.add_argument("--disable-css")  # Don't load CSS
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        # Disable logging
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_argument('--log-level=3')
        
        # Set page load strategy to 'eager' (don't wait for all resources)
        chrome_options.page_load_strategy = 'eager'
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        self.wait = WebDriverWait(self.driver, 5)
        
        self.driver.set_page_load_timeout(15)

    def setup_output_folder(self):
        """Create output and log folders if they don't exist"""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.folder_path = os.path.join(project_root, self.output_folder)
        self.log_folder_path = os.path.join(project_root, self.log_folder)
        
        os.makedirs(self.folder_path, exist_ok=True)
        os.makedirs(self.log_folder_path, exist_ok=True)

    def setup_logging(self):
        """Set up logging configuration"""
        # Generate log filename with timestamp including milliseconds
        now = datetime.now()
        log_filename = f"scraping_session_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond//1000:03d}.log"
        log_filepath = os.path.join(self.log_folder_path, log_filename)
        
        # Create logger
        self.logger = logging.getLogger('ParliamentaryScraper')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create file handler
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
        
        # Store log file path for reference
        self.log_file_path = log_filepath
        
        # Log initial setup
        self.logger.info("=" * 80)
        self.logger.info("PARLIAMENTARY SCRAPER SESSION STARTED")
        self.logger.info(f"Log file: {log_filename}")
        self.logger.info(f"Output folder: {self.log_folder_path}")
        self.logger.info(f"Headless mode: {self.driver.execute_script('return navigator.webdriver') is None}")
        self.logger.info("=" * 80)
    
    def extract_session_header(self):
        """Extract session header information with faster waits"""
        header_data = {}

        def get_value(label):
            try:
                cell = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f"//table//tr[td[1][contains(., '{label}')]]/td[2]")
                    )
                )
                return cell.text.strip()
            except:
                return None

        header_data['date'] = get_value("Fecha")
        header_data['start_time'] = get_value("Inicia")
        header_data['end_time'] = get_value("Termina")
        header_data['starting_quorum'] = get_value("Quórum de inicio")
        header_data['next_session'] = get_value("Próxima sesión")
        header_data['presiding_officer'] = get_value("Presidió")

        return header_data
    
    def extract_matters_attended(self):
        """Extract 'Asuntos Atendidos' section with group + matter names"""
        matters = []

        try:
            # Locate the "ASUNTOS ATENDIDOS" header
            header = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//td[contains(., 'ASUNTOS ATENDIDOS')]")
                )
            )

            # Get the table after the header
            matters_table = header.find_element(By.XPATH, "./ancestor::table/following-sibling::table[1]")

            rows = matters_table.find_elements(By.XPATH, ".//tr")
            current_group = None

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    continue

                # If the row is a group header (colspan=2, tdcriterio)
                if "tdcriterio" in cells[0].get_attribute("class") and len(cells) == 1 or len(cells) == 2 and cells[0].get_attribute("colspan") == "2":
                    current_group = cells[0].text.strip()

                # If the row is a matter entry (simpletextli with two columns)
                elif "simpletextli" in cells[0].get_attribute("class") and len(cells) >= 2:
                    matter_name = cells[0].text.strip()
                    count = cells[1].text.strip()

                    matters.append({
                        'group': current_group,
                        'matter_name': matter_name,
                        'count': count
                    })

        except TimeoutException:
            self.logger.warning("Could not find 'ASUNTOS ATENDIDOS' section")

        return matters
    
    def extract_affairs(self):
        """Extract affairs section with detailed information"""
        affairs = []

        try:
            # Find the <td> that contains the text 'ASUNTOS'
            affairs_td = self.driver.find_element(By.XPATH, "//td[contains(text(), 'ASUNTOS')]")
            
            # Navigate up to the parent <tbody>
            tbody = affairs_td.find_element(By.XPATH, "./ancestor::tbody")
            
            # Get the last <tr> within this <tbody>
            content_tr = tbody.find_element(By.XPATH, "./tr[last()]")

            # Find all tables inside the last <tr>, excluding the one with the navigation image.
            # This XPath selects tables that do NOT contain an <img> with a specific src attribute.
            affair_tables = content_tr.find_elements(By.XPATH, "./td/table[not(.//img[contains(@src, 'principio.jpg')])]")

            for i, block in enumerate(affair_tables):
                affair_data = self.extract_single_affair(block, f"AFF{i+1:03d}")
                if affair_data:
                    affairs.append(affair_data)

        except NoSuchElementException as e:
            self.logger.error(f"Could not find the 'ASUNTOS' section or associated tables: {e}")
        return affairs

    def extract_single_affair(self, block, affair_id):
        """Extract data from a single affair block and save using first words as keys"""
        affair_data = {'affair_id': affair_id}

        try:
            # Extract title
            title_element = block.find_element(By.XPATH, ".//td[@class='simpletextmayor' or @class='simpletextmayor2'][1]")
            if title_element:
                affair_data['title'] = title_element.text.strip()

            # Extract main text (under title)
            text_element = block.find_element(By.XPATH, ".//td[@class='simpletextmayor2'][1]")
            if text_element:
                affair_data['text'] = text_element.text.strip()

            # Extract "Aspectos Relevantes"
            try:
                aspects_element = block.find_element(By.XPATH, ".//font[contains(text(), 'Aspectos Relevantes')]/following-sibling::font[@class='simpletextmayor2']")
                affair_data['Aspectos'] = aspects_element.text.strip()
            except NoSuchElementException:
                affair_data['Aspectos'] = None

            # Extract "Último Trámite" and "Resultado"
            try:
                # Find the font element that contains "Último Trámite:"
                ultimo_font = block.find_element(
                    By.XPATH, ".//font[contains(text(), 'Último Trámite:')]"
                )
                
                # Get the following sibling font element with class 'simpletextmayor2'
                font_elem = ultimo_font.find_element(
                    By.XPATH, "./following-sibling::font[@class='simpletextmayor2']"
                )
                
                full_text = font_elem.text.strip()
                
                # Split lines and filter out empty lines
                lines = [line.strip() for line in full_text.splitlines() if line.strip()]
                
                # Extract 'Último' (first line, should be "Votación económica")
                ultimo = lines[0] if len(lines) > 0 else ''
                
                # Extract 'Resultado' from the line that contains "Resultado:"
                resultado = ''
                for line in lines:
                    if "Resultado:" in line:
                        resultado = line.split("Resultado:")[-1].strip()
                        break
                
                affair_data['Último'] = ultimo
                affair_data['Resultado'] = resultado

            except NoSuchElementException:
                affair_data['Último'] = None
                affair_data['Resultado'] = ''

            # Extract PDF link
            try:
                # Look for <a> tag with class "tddatosazul" that contains "Ver archivo"
                pdf_link_element = block.find_element(By.XPATH, ".//a[@class='tddatosazul'][contains(text(), 'Ver archivo')]")
                affair_data['link'] = pdf_link_element.get_attribute('href')
            except NoSuchElementException:
                # Alternative: look for any <a> tag that has an href pointing to a PDF
                try:
                    pdf_link_element = block.find_element(By.XPATH, ".//a[contains(@href, '.pdf')]")
                    affair_data['link'] = pdf_link_element.get_attribute('href')
                except NoSuchElementException:
                    affair_data['link'] = None

            # Extract "Publicación en la Gaceta Parlamentaria"
            try:
                pub_date_element = block.find_element(By.XPATH, ".//font[contains(text(), 'Publicación en la Gaceta Parlamentaria')]/following-sibling::font[@class='simpletextmayor2']")
                affair_data['Publicación'] = pub_date_element.text.strip()
            except NoSuchElementException:
                affair_data['Publicación'] = None

        except Exception as e:
            self.logger.error(f"Single affair extraction error for {affair_id}: {e}")
            return None

        return affair_data

    def generate_session_id(self, date_str):
        """Generate session ID from date string"""
        if not date_str:
            return datetime.now().strftime("%Y%m%d")
        
        try:
            # Try to parse different date formats
            for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d']:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime("%Y%m%d")
                except ValueError:
                    continue
        except:
            pass
            
        return datetime.now().strftime("%Y%m%d")

    def save_session_to_excel(self, session_data):
        """Save a single session's data to Excel immediately"""
        try:
            # Safe filename based on session date
            session_date = session_data['header'].get('date', 'unknown_date')
            safe_date = re.sub(r'[\\/*?:"<>|]', '-', session_date)
            filename = f"parliamentary_session_{safe_date}.xlsx"
            filepath = os.path.join(self.folder_path, filename)

            session_id = self.generate_session_id(session_date)

            # Prepare data with session_id
            header = session_data['header'].copy()
            header['session_id'] = session_id
            header['url'] = session_data['url']
            header['scraped_at'] = session_data['scraped_at']

            matters_data = [{**m, 'session_id': session_id} for m in session_data['matters_attended']]
            affairs_data = [{**a, 'session_id': session_id} for a in session_data['affairs']]

            # Save to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                pd.DataFrame([header]).to_excel(writer, sheet_name='Session_Headers', index=False)
                if matters_data:
                    pd.DataFrame(matters_data).to_excel(writer, sheet_name='Matters_Attended', index=False)
                if affairs_data:
                    pd.DataFrame(affairs_data).to_excel(writer, sheet_name='Affairs', index=False)

            # Log successful save
            self.logger.info(f"SUCCESS - Saved session to: {filename}")
            self.logger.info(f"  - Session date: {session_date}")
            self.logger.info(f"  - Session ID: {session_id}")
            self.logger.info(f"  - Matters: {len(matters_data)}")
            self.logger.info(f"  - Affairs: {len(affairs_data)}")

            return filepath

        except Exception as e:
            self.logger.error(f"ERROR saving session to Excel: {e}")
            self.logger.error(f"  - URL: {session_data.get('url', 'Unknown')}")
            return None
    
    def scrape_session(self, url):
        """Main method to scrape a parliamentary session and save immediately"""
        start_time = time.time()
        try:
            print(f"Scraping: {url}", end=" ... ", flush=True)
            self.logger.info(f"STARTING - {url}")
            
            self.driver.get(url)
            
            # Reduced wait time and check if page is ready
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract all sections
            session_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'header': self.extract_session_header(),
                'matters_attended': self.extract_matters_attended(),
                'affairs': self.extract_affairs()
            }
            
            # Save immediately after successful scrape
            saved_file = self.save_session_to_excel(session_data)
            
            end_time = time.time()
            scraping_time = end_time - start_time
            
            if saved_file:
                print(f"✅ SUCCESS ({scraping_time:.2f}s)", flush=True)
                self.logger.info(f"COMPLETED - {url} in {scraping_time:.2f}s")
                self.logger.info("-" * 80)
            else:
                print(f"⚠️ SCRAPED BUT SAVE FAILED ({scraping_time:.2f}s)", flush=True)
                self.logger.warning(f"SCRAPED BUT SAVE FAILED - {url} in {scraping_time:.2f}s")
                self.logger.info("-" * 80)
            
            return session_data
            
        except Exception as e:
            end_time = time.time()
            scraping_time = end_time - start_time
            error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
            print(f"❌ FAILED ({scraping_time:.2f}s) - {str(e)[:50]}...", flush=True)
            self.logger.error(f"FAILED - {url} in {scraping_time:.2f}s")
            self.logger.error(f"  - Error: {error_msg}")
            self.logger.info("-" * 80)
            return None
    
    def close(self):
        """Close the webdriver and finalize logging"""
        self.logger.info("=" * 80)
        self.logger.info("PARLIAMENTARY SCRAPER SESSION ENDED")
        self.logger.info(f"Log saved to: {self.log_file_path}")
        self.logger.info("=" * 80)
        
        # Close all handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
            
        self.driver.quit()

def process_sessions(file: str, scrape_all: bool, scrape_name: str = None, visible: bool = False, delay: float = 0.5):
    """Process sessions from JSON file with auto-save after each successful scrape"""
    with open(file, "r", encoding="utf-8") as f:
        json_file = json.load(f)

    # Filter URLs based on scrape_all or scrape_name
    if scrape_all:
        sessions_to_scrape = json_file
    else:
        sessions_to_scrape = [item for item in json_file if item.get("name") == scrape_name]
        if not sessions_to_scrape:
            print(f"No session found with name '{scrape_name}'")
            return

    scraper = ParliamentaryScraper(visible=visible)

    try:
        successful_scrapes = 0
        failed_scrapes = 0
        total_urls = sum(len(session.get("data", {}).get("links", [])) for session in sessions_to_scrape)
        total_time = 0
        
        print(f"🚀 Starting to process {total_urls} URLs...")
        print("=" * 80)
        
        # Log session start details
        scraper.logger.info(f"BATCH PROCESSING STARTED")
        scraper.logger.info(f"Total URLs to process: {total_urls}")
        scraper.logger.info(f"Sessions to scrape: {len(sessions_to_scrape)}")
        scraper.logger.info(f"Delay between requests: {delay}s")
        scraper.logger.info(f"Visible mode: {visible}")
        
        overall_start_time = time.time()
        
        for session in sessions_to_scrape:
            session_name = session.get("name", "Unknown")
            urls = session.get("data", {}).get("links", [])
            scraper.logger.info(f"Processing session '{session_name}' with {len(urls)} URLs")
            
            for i, url in enumerate(urls, 1):
                current_session = successful_scrapes + failed_scrapes + 1
                
                # Print progress header
                print(f"[{current_session:3d}/{total_urls}] ", end="", flush=True)
                
                result = scraper.scrape_session(url)
                
                if result:
                    successful_scrapes += 1
                else:
                    failed_scrapes += 1
                
                # Calculate and display statistics
                success_rate = (successful_scrapes / current_session) * 100
                elapsed_time = time.time() - overall_start_time
                avg_time_per_session = elapsed_time / current_session
                estimated_remaining = (total_urls - current_session) * avg_time_per_session
                
                print(f"📊 Success: {successful_scrapes}/{current_session} ({success_rate:.1f}%) | "
                      f"Avg: {avg_time_per_session:.1f}s | "
                      f"ETA: {estimated_remaining/60:.1f}m", flush=True)
                print("-" * 80, flush=True)
                
                # Log progress every 10 sessions
                if current_session % 10 == 0:
                    scraper.logger.info(f"PROGRESS - {current_session}/{total_urls} sessions processed")
                    scraper.logger.info(f"  - Success rate: {success_rate:.1f}%")
                    scraper.logger.info(f"  - Average time: {avg_time_per_session:.1f}s")
                    scraper.logger.info(f"  - Estimated remaining: {estimated_remaining/60:.1f}m")
                
                if current_session < total_urls:  # Don't delay after last session
                    time.sleep(delay)
        
        # Final summary
        total_elapsed = time.time() - overall_start_time
        print("=" * 80)
        print(f"🏁 SCRAPING COMPLETED!")
        print(f"✅ Successful: {successful_scrapes}")
        print(f"❌ Failed: {failed_scrapes}")
        print(f"📈 Success Rate: {(successful_scrapes/total_urls)*100:.1f}%")
        print(f"⏱️  Total Time: {total_elapsed/60:.1f} minutes")
        print(f"⚡ Average per session: {total_elapsed/total_urls:.1f} seconds")
        print("=" * 80)
        
        # Log final summary
        scraper.logger.info("BATCH PROCESSING COMPLETED")
        scraper.logger.info(f"Total URLs processed: {total_urls}")
        scraper.logger.info(f"Successful scrapes: {successful_scrapes}")
        scraper.logger.info(f"Failed scrapes: {failed_scrapes}")
        scraper.logger.info(f"Success rate: {(successful_scrapes/total_urls)*100:.1f}%")
        scraper.logger.info(f"Total time: {total_elapsed/60:.1f} minutes")
        scraper.logger.info(f"Average per session: {total_elapsed/total_urls:.1f} seconds")
        
    except KeyboardInterrupt:
        current_session = successful_scrapes + failed_scrapes
        success_rate = (successful_scrapes / current_session * 100) if current_session > 0 else 0
        print(f"\n🛑 SCRAPING INTERRUPTED!")
        print(f"✅ Successfully saved: {successful_scrapes} sessions")
        print(f"❌ Failed: {failed_scrapes} sessions") 
        print(f"📊 Success rate: {success_rate:.1f}%")
        print(f"📈 Progress: {current_session}/{total_urls} sessions processed")
        
        # Log interruption
        scraper.logger.warning("BATCH PROCESSING INTERRUPTED BY USER")
        scraper.logger.info(f"Sessions processed before interruption: {current_session}/{total_urls}")
        scraper.logger.info(f"Success rate at interruption: {success_rate:.1f}%")
        
    except Exception as e:
        print(f"💥 Unexpected error during processing: {e}")
        scraper.logger.error(f"UNEXPECTED ERROR during batch processing: {e}")
    finally:
        scraper.close()
        print("🔌 WebDriver closed.")