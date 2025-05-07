import json
import asyncio
import string
from itertools import product
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from config import TARGET_URL, OUTPUT_FILE
from logger.logger import logger
from models.models import InsuranceData

class InsuranceScraper:
    def __init__(self, output_file="insurance_data.json", concurrency=5):
        self.url = TARGET_URL
        self.output_file = OUTPUT_FILE
        self.results = self.load_existing_data()
        self.concurrency = concurrency  # Number of concurrent scrapers

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

    async def scrape(self, plate_number, page):
        """Scrapes insurance data for a given plate number using an async page."""
        try:
            await page.goto(self.url, timeout=5000)  # 5-second timeout

            # Fill in the plate number
            input_selector = "input[name='carNumber']"
            await page.fill(input_selector, plate_number)

            # Click the "Yoxla" button
            button_selector = "#pageBody_btnCheck"
            await page.click(button_selector)
            # Check if "Məlumat tapılmadı" (No Data) appears
            error_selector = "#divError"
            try:
                await page.wait_for_selector(error_selector, timeout=3000)  # 3s timeout
                error_text = await page.inner_text(error_selector)
                if "Məlumat tapılmadı" in error_text:
                    #logger.info(f"No data for {plate_number}.")
                    print(f"No data for {plate_number}.")
                    self.results[plate_number] = "Not Found"
                    self.save_data()
                    return  # Skip further processing
            except PlaywrightTimeoutError:
                pass  # If error message doesn't appear, continue to scrape results

            # Wait for results table
            table_selector = ".result-area tbody"
            await page.wait_for_selector(table_selector, timeout=7000)

            # Extract data
            rows = await page.query_selector_all(f"{table_selector} tr")
            if rows:
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 5:
                        self.results[plate_number] = {
                            "Təşkilat": await cells[0].inner_text(),
                            "Dövlət qeydiyyat nömrəsi": await cells[1].inner_text(),
                            "Marka": await cells[2].inner_text(),
                            "Model": await cells[3].inner_text(),
                            "Status": await cells[4].inner_text(),
                        }
                        #logger.info(self.results[plate_number])
                        print(self.results[plate_number])
                        break
            else:
                #logger.info(f"No data found for {plate_number}.")
                print(f"No data found for {plate_number}.")
                self.results[plate_number] = "No Data"

        except PlaywrightTimeoutError:
            #logger.info(f"TIMEOUT: Skipping {plate_number} due to no response.")
            print(f"TIMEOUT: Skipping {plate_number} due to no response.")
            self.results[plate_number] = "Timeout"

        # Save after each request
        self.save_data()

    def generate_plate_numbers(self):
        """Generates all possible plate numbers (excluding I and W)."""
        regions = ["77", "90", "99"]
        letters = [
            ch1 + ch2
            for ch1, ch2 in product(string.ascii_uppercase, repeat=2)
            if "I" not in [ch1, ch2] and "W" not in [ch1, ch2]
        ]
        numbers = [f"{num:03}" for num in range(1, 1000)]  # 001 to 999

        plates = []
        for region in regions:
            for letter in letters:
                for number in numbers:
                    plates.append(f"{region}{letter}{number}")
                    
        return plates

    async def run(self):
        """Runs the scraper asynchronously with multiple pages."""
        plates_to_scrape = [
            plate for plate in self.generate_plate_numbers() if plate not in self.results
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            pages = [await browser.new_page() for _ in range(self.concurrency)]

            tasks = []
            for i, plate in enumerate(plates_to_scrape):
                page = pages[i % self.concurrency]  # Assign tasks across available pages
                #logger.info(f"Checking: {plate}")
                print(f"Checking: {plate}")
                tasks.append(self.scrape(plate, page))

                if len(tasks) >= self.concurrency:  # Process in batches
                    await asyncio.gather(*tasks)
                    tasks = []  # Reset the batch

            await asyncio.gather(*tasks)  # Process remaining tasks
            await browser.close()

if __name__ == "__main__":
    scraper = InsuranceScraper(concurrency=10)  # Adjust concurrency for faster scraping
    asyncio.run(scraper.run())
