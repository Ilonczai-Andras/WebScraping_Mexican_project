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

class ParliamentaryScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.session_data = []
        
    def setup_driver(self, headless):
        """Set up Chrome driver with options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def extract_session_header(self):
        """Extract session header information"""
        header_data = {}

        wait = WebDriverWait(self.driver, 10)

        def get_value(label):
            try:
                cell = wait.until(
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
            print("Could not find 'ASUNTOS ATENDIDOS' section")

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
            # affair_data = self.extract_single_affair(affair_tables[0], f"AFF{0+1:03d}")
            # if affair_data:
            #         affairs.append(affair_data)

            for i, block in enumerate(affair_tables):
                affair_data = self.extract_single_affair(block, f"AFF{i+1:03d}")
                if affair_data:
                    affairs.append(affair_data)

        except NoSuchElementException as e:
            print(f"An error occurred: {e}")
            print("Could not find the 'ASUNTOS' section or associated tables.")
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
            print(f"Single affair extraction error: {e}")
            return None

        return affair_data
    
    def scrape_session(self, url):
        """Main method to scrape a parliamentary session"""
        try:
            print(f"Scraping: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Extract all sections
            session_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'header': self.extract_session_header(),
                'matters_attended': self.extract_matters_attended(),
                'affairs': self.extract_affairs()
            }
            
            self.session_data.append(session_data)
            print(f"Successfully scraped session data")
            
            return session_data
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def save_to_excel_per_session(self, folder="exported_excels"):
        if not self.session_data:
            print("No data to save")
            return

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        folder_path = os.path.join(project_root, folder)
        os.makedirs(folder_path, exist_ok=True)

        for session in self.session_data:
            # Safe filename based on session date
            session_date = session['header'].get('date', 'unknown_date')
            safe_date = re.sub(r'[\\/*?:"<>|]', '-', session_date)
            filename = f"parliamentary_session_{safe_date}.xlsx"
            filepath = os.path.join(folder_path, filename)

            session_id = self.generate_session_id(session_date)

            # Prepare data
            header = session['header'].copy()
            header['session_id'] = session_id
            header['url'] = session['url']

            matters_data = [ {**m, 'session_id': session_id} for m in session['matters_attended'] ]
            affairs_data = [ {**a, 'session_id': session_id} for a in session['affairs'] ]

            # Save Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                pd.DataFrame([header]).to_excel(writer, sheet_name='Session_Headers', index=False)
                if matters_data:
                    pd.DataFrame(matters_data).to_excel(writer, sheet_name='Matters_Attended', index=False)
                if affairs_data:
                    pd.DataFrame(affairs_data).to_excel(writer, sheet_name='Affairs', index=False)

            print(f"Session data saved to {filepath}")

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
    
    def close(self):
        """Close the webdriver"""
        self.driver.quit()

def process_sessions(file: str, scrape_all: bool, scrape_name: str = None, visible: bool = True):
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

    scraper = ParliamentaryScraper(headless=visible)

    try:
        for session in sessions_to_scrape:
            # Assuming scrape_session expects a URL inside the data dict
            urls = session.get("data", {}).get("links", [])
            for url in urls:
                scraper.scrape_session(url)
                time.sleep(2)
        scraper.save_to_excel()
    finally:
        scraper.close()