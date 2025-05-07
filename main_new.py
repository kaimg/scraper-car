import json
import asyncio
import string
from logger import logger
from itertools import product
from typing import Dict, List, Optional
from pydantic import BaseModel, ValidationError
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from config import TARGET_URL


OUTPUT_FILE = "output/data_new.json"

# Pydantic Model for Scraped Data
class InsuranceData(BaseModel):
    plate_number: str
    organization: Optional[str] = None
    registration_number: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None

class InsuranceScraper:
    def __init__(self, output_file: str = OUTPUT_FILE, concurrency: int = 5, batch_size: int = 100):
        self.url = TARGET_URL
        self.output_file = output_file
        self.results: Dict[str, InsuranceData] = self.load_existing_data()
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.buffer: List[InsuranceData] = []

    def load_existing_data(self) -> Dict[str, InsuranceData]:
        """Loads existing JSON data to avoid duplicates if the script is interrupted."""
        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k: InsuranceData(**v) for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Failed to load existing data: {e}")
            return {}

    def save_data(self):
        """Saves scraped data to a JSON file in batches."""
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump({k: v.dict() for k, v in self.results.items()}, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved {len(self.buffer)} items to {self.output_file}")
            self.buffer.clear()
        except Exception as e:
            logger.error(f"Failed to save data: {e}")

    async def scrape(self, plate_number: str, page):
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
                    logger.info(f"No data for {plate_number}.")
                    self.results[plate_number] = InsuranceData(plate_number=plate_number, error="Not Found")
                    self.buffer.append(self.results[plate_number])  # Add to buffer
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
                        self.results[plate_number] = InsuranceData(
                            plate_number=plate_number,
                            organization=await cells[0].inner_text(),
                            registration_number=await cells[1].inner_text(),
                            brand=await cells[2].inner_text(),
                            model=await cells[3].inner_text(),
                            status=await cells[4].inner_text(),
                        )
                        logger.info(f"Scraped data for {plate_number}: {self.results[plate_number]}")
                        self.buffer.append(self.results[plate_number])  # Add to buffer
                        break
            else:
                logger.info(f"No data found for {plate_number}.")
                self.results[plate_number] = InsuranceData(plate_number=plate_number, error="No Data")
                self.buffer.append(self.results[plate_number])  # Add to buffer

        except PlaywrightTimeoutError:
            logger.warning(f"TIMEOUT: Skipping {plate_number} due to no response.")
            self.results[plate_number] = InsuranceData(plate_number=plate_number, error="Timeout")
            self.buffer.append(self.results[plate_number])  # Add to buffer
        except Exception as e:
            logger.error(f"Error scraping {plate_number}: {e}")
            self.results[plate_number] = InsuranceData(plate_number=plate_number, error=str(e))
            self.buffer.append(self.results[plate_number])  # Add to buffer

        # Save if buffer size is reached
        if len(self.buffer) >= self.batch_size:
            self.save_data()

    def generate_plate_numbers(self) -> List[str]:
        """Generates all possible plate numbers (excluding I and W)."""
        regions = ["90"]
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

            semaphore = asyncio.Semaphore(self.concurrency)
            async def limited_scrape(plate, page):
                async with semaphore:
                    await self.scrape(plate, page)

            # Process plates in batches
            batch_size = self.concurrency * 10  # Adjust batch size as needed
            for i in range(0, len(plates_to_scrape), batch_size):
                batch = plates_to_scrape[i:i + batch_size]
                tasks = []
                for j, plate in enumerate(batch):
                    page = pages[j % self.concurrency]
                    logger.info(f"Checking: {plate}")
                    tasks.append(limited_scrape(plate, page))

                # Execute the current batch of tasks
                await asyncio.gather(*tasks)
                logger.info(f"Completed batch {i // batch_size + 1}")

            # Close pages and browser after all tasks are done
            for page in pages:
                await page.close()
            await browser.close()

        # Save any remaining data in the buffer
        if self.buffer:
            self.save_data()

if __name__ == "__main__":
    scraper = InsuranceScraper(concurrency=10, batch_size=100)
    asyncio.run(scraper.run())