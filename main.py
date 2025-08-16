import logging
from scrapers.site_a_scraper.site_a_scraper import scrape_all_legislaturas
from scrapers.site_b_scraper.site_b_scraper import process_all_legislatura_data
from scrapers.site_c_scraper.site_c_scraper import process_sessions
from config.settings import scrape_targets

def createJsonFiles():

    logging.info("Creating legislatura json's")
    scrape_all_legislaturas(urls_to_scrape=scrape_targets)

def run_scrapers():

    logging.info("Extending the legislatura.json")
    process_all_legislatura_data(urls_to_scrape=scrape_targets)

def process_all_sessions():

    process_sessions(file="senadores.json", scrape_all=False, scrape_name="LVII", visible=False)
    
if __name__ == "__main__":
    logging.info("Starting web scraping process...")

    #createJsonFiles()
    #run_scrapers()
    process_all_sessions()