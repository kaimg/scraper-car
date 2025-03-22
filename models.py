import json
from config import OUTPUT_FILE

class CarInsurance:
    """Model representing a car's insurance information."""
    
    def __init__(self, plate_number, organization, registration_number, brand, model, status):
        self.plate_number = plate_number  # e.g., "10AA001"
        self.organization = organization  # e.g., "Some Insurance Company"
        self.registration_number = registration_number  # e.g., "10AA001"
        self.brand = brand  # e.g., "BMW"
        self.model = model  # e.g., "X5"
        self.status = status  # e.g., "Valid"

    def __repr__(self):
        """String representation of the object."""
        return f"<CarInsurance {self.plate_number} - {self.brand} {self.model} ({self.status})>"

    @classmethod
    def from_json(cls, plate_number, data):
        """Creates an instance from JSON data."""
        if isinstance(data, str):  # Handles 'No Data' or 'Timeout' cases
            return None
        return cls(
            plate_number=plate_number,
            organization=data.get("Təşkilat", "Unknown"),
            registration_number=data.get("Dövlət qeydiyyat nömrəsi", "Unknown"),
            brand=data.get("Marka", "Unknown"),
            model=data.get("Model", "Unknown"),
            status=data.get("Status", "Unknown"),
        )


class InsuranceData:
    """Class for loading and managing the insurance dataset."""
    
    def __init__(self, json_file="output/tmp.json"):
        self.json_file = json_file
        self.insurance_entries = self.load_data()

    def load_data(self):
        """Loads JSON data and returns a list of CarInsurance objects."""
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error: JSON file not found or invalid.")
            return []

        # Convert JSON data into list of CarInsurance objects
        return [CarInsurance.from_json(plate, details) for plate, details in data.items() if CarInsurance.from_json(plate, details)]

    def get_unique_organizations(self):
        """Returns a set of unique insurance organizations."""
        return {entry.organization for entry in self.insurance_entries}

    def get_unique_brands(self):
        """Returns a set of unique car brands."""
        return {entry.brand for entry in self.insurance_entries}

    def print_summary(self):
        """Prints unique organizations and brands."""
        print("\n✅ Unique Insurance Organizations:")
        for org in sorted(self.get_unique_organizations()):
            print(f"  - {org}")

        print("\n✅ Unique Car Brands:")
        for brand in sorted(self.get_unique_brands()):
            print(f"  - {brand}")

    def __repr__(self):
        """String representation of the dataset."""
        return f"<InsuranceDatabase with {len(self.insurance_entries)} entries>"

    
# Example Usage
if __name__ == "__main__":
    db = InsuranceData()
    db.print_summary()
