import json
import time
import string
import asyncio
from itertools import product
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from config import TARGET_URL, OUTPUT_FILE
from models import InsuranceData, InsuranceDatabase

class InsuranceScraper:
    def __init__(self, output_file="insurance_data.json"):
        self.url = TARGET_URL
        self.output_file = OUTPUT_FILE
        self.results = self.load_existing_data()

    def load_existing_data(self):
        """Loads existing JSON data to avoid duplicates if the script is interrupted."""
        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_data(self):
        """Saves scraped data to a JSON file."""
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4, ensure_ascii=False)

    def scrape(self, plate_number):
        """Scrapes insurance data for a given plate number."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # Set headless=False for debugging
            page = browser.new_page()

            try:
                page.goto(self.url, timeout=5000)  # 5-second timeout

                # Fill in the plate number
                input_selector = "input[name='carNumber']"
                page.fill(input_selector, plate_number)

                # Click the "Yoxla" button
                button_selector = "#pageBody_btnCheck"
                page.click(button_selector)

                # Check if "Məlumat tapılmadı" (No Data) appears
                error_selector = "#divError"
                try:
                    page.wait_for_selector(error_selector, timeout=3000)  # 3s timeout
                    error_text = page.inner_text(error_selector)
                    if "Məlumat tapılmadı" in error_text:
                        print(f"No data for {plate_number}.")
                        self.results[plate_number] = "Not Found"
                        self.save_data()
                        return  # Skip further processing
                except PlaywrightTimeoutError:
                    pass  # If error message doesn't appear, continue to scrape results
                
                # Wait for results table
                table_selector = ".result-area tbody"
                page.wait_for_selector(table_selector, timeout=7000)

                # Extract data
                rows = page.query_selector_all(f"{table_selector} tr")
                if rows:
                    for row in rows:
                        cells = row.query_selector_all("td")
                        if len(cells) >= 5:
                            self.results[plate_number] = {
                                "Təşkilat": cells[0].inner_text(),
                                "Dövlət qeydiyyat nömrəsi": cells[1].inner_text(),
                                "Marka": cells[2].inner_text(),
                                "Model": cells[3].inner_text(),
                                "Status": cells[4].inner_text(),
                            }
                            print(self.results[plate_number])
                            break
                else:
                    print(f"No data found for {plate_number}.")
                    self.results[plate_number] = "No Data"

            except PlaywrightTimeoutError:
                print(f"TIMEOUT: Skipping {plate_number} due to no response.")
                self.results[plate_number] = "Timeout"
            finally:
                browser.close()

        # Save after each request
        self.save_data()

    def generate_plate_numbers(self):
        plates = list()
        """Generates all possible plate numbers (excluding I and W)."""
        regions = ["10", "77", "90", "99"]  # Fixed regions
        letters = [ch1 + ch2 for ch1, ch2 in product(string.ascii_uppercase, repeat=2) if "I" not in [ch1, ch2] and "W" not in [ch1, ch2]]
        numbers = [f"{num:03}" for num in range(1, 1000)]  # 001 to 999

        for region in regions:
            for letter in letters:
                for number in numbers:
                    # yield f"{region}{letter}{number}"
                    plates.append(f"{region}{letter}{number}")
        
        return plates

    def run(self):
        """Iterates over all plates and scrapes them."""
        # print(self.generate_plate_numbers())
        a = ['10AA002', '10AA016', '10AA026', '10AA062', '10AA057', '10AA069', '10AA080', '10AA076', '10AA093', '10AA122', '10AA129', '10AA126', '10AA128', '10AA136', '10AA143', '10AA148', '10AA154', '10AA161', '10AA162', '10AA166', '10AA163', '10AA167', '10AA168', '10AA173', '10AA190', '10AA188', '10AA189', '10AA191', '10AA185', '10AA196', '10AA220', '10AA216', '10AA222', '10AA225', '10AA241', '10AA248', '10AA261', '10AA275', '10AA274', '10AA280', '10AA276', '10AA292', '10AA283', '10AA302', '10AA307', '10AA308', '10AA303', '10AA315', '10AA319', '10AA332', '10AA325', '10AA330', '10AA334', '10AA333', '10AA339', '10AA352', '10AA348', '10AA354', '10AA361', '10AA373', '10AA382', '10AA390', '10AA397', '10AA461', '10AA463', '10AA466', '10AA473', '10AA480', '10AA489', '10AA490', '10AA500', '10AA497', '10AA507', '10AA514', '10AA524', '10AA535', '10AA552', '10AA560', '10AA561', '10AA555', '10AA567', '10AA570', '10AA578', '10AA582', '10AA575', '10AA579', '10AA589', '10AA583', '10AA602', '10AA596', '10AA604', '10AA610', '10AA609', '10AA606', '10AA631', '10AA641', '10AA635', '10AA638', '10AA655', '10AA678', '10AA676', '10AA673', '10AA696', '10AA706', '10AA720', '10AA723', '10AA751', '10AA757', '10AA759', '10AA756', '10AA755', '10AA767', '10AA764', '10AA771', '10AA778', '10AA781', '10AA783', '10AA797', '10AA798', '10AA793', '10AA804', '10AA838', '10AA847', '10AA880', '10AA878', '10AA888', '10AA923', '10AA926', '10AA933', '10AA942', '10AA940', '10AA939', '10AA950', '10AA948', '10AA971', '10AA965', '10AA970', '10AA967', '10AA974', '10AA983']
        for plate in a:
            if plate not in self.results:  # Skip if already scraped
        # plate = "77UA782"
                #if plate.startswith("10AA17"):
                #    print(f"Skipped: {plate}")
                #   continue
                print(f"Checking: {plate}")
            self.scrape(plate)
        time.sleep(1)  # Delay to avoid rate limits


if __name__ == "__main__":
    scraper = InsuranceScraper()
    scraper.run()