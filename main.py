import logging
from scrapers.site_a_scraper.site_a_scraper import scrape_all_legislaturas
from scrapers.site_b_scraper.site_b_scraper import process_all_legislatura_data
from scrapers.site_c_scraper.site_c_scraper import process_sessions
from config.settings import scrape_targets


class ScraperManager:
    def __init__(self, targets):
        self.targets = targets
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def create_legislatura_json(self):
        """Scrape all legislaturas and create JSON files."""
        logging.info("Creating legislatura JSONs...")
        scrape_all_legislaturas(urls_to_scrape=self.targets)

    def extend_legislatura_json(self):
        """Extend existing legislatura JSON files with additional data."""
        logging.info("Extending legislatura JSONs...")
        process_all_legislatura_data(urls_to_scrape=self.targets)

    def process_only_one_session_with_name(self, file_name: str, name: str):
        """Process a single session by name within a given file."""
        logging.info(f"Processing session '{name}' from file {file_name}...")
        process_sessions(file=file_name, scrape_all=False, scrape_name=name, visible=True)

    def process_all_sessions(self):
        """Process all sessions for both senators and deputies."""
        logging.info("Processing all sessions for senators and deputies...")
        for file_name in ["senadores.json", "diputados.json"]:
            process_sessions(file=file_name, scrape_all=True, visible=True)

    def run_all(self):
        """Run the full scraping and processing workflow."""
        logging.info("Starting full web scraping process...")
        self.create_legislatura_json()
        self.extend_legislatura_json()
        self.process_all_sessions()


if __name__ == "__main__":
    manager = ScraperManager(targets=scrape_targets)

    # You can run only specific parts if needed:

    # manager.create_legislatura_json()
    # manager.extend_legislatura_json()
    # manager.process_all_sessions()

    # Run only one session
    manager.process_only_one_session_with_name(file_name="senadores.json", name="LXVI")

    # Or run everything at once:
    # manager.run_all()
