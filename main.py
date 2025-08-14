import logging
from scrapers.site_a_scraper.site_a_scraper import scrape_legislaturas
from scrapers.site_b_scraper.site_b_scraper import extend_legislaturasJson_with_links

def run_scrapers():
    logging.info("Starting web scraping process...")

    # logging.info("Creating legislatura.json")
    # scrape_legislaturas()

    logging.info("Extending the legislatura.json")
    extend_legislaturasJson_with_links()

if __name__ == "__main__":
    run_scrapers()