import json
import polars as pl
# Load JSON data
with open('output/data.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# # Sample JSON data (replace this with loading from a file)
# json_data = '''
# {
#     "77BM238": {
#         "Təşkilat": "\\"QALA SIĞORTA\\" AÇIQ SƏHMDAR CƏMİYYƏTİ",
#         "Dövlət qeydiyyat nömrəsi": "77BM238",
#         "Marka": "TOYOTA",
#         "Model": "PRİUS",
#         "Status": "Qüvvədədir"
#     },
#     "77BM244": "Timeout",
#     "77BM253": "Not Found"
# }
# '''
# 
# # Load JSON data
# data = json.loads(json_data)

# Initialize lists to store data
plates = []
organizations = []
registration_numbers = []
markas = []
models = []
statuses = []
errors = []

# Parse JSON and populate lists
for plate, details in data.items():
    plates.append(plate)
    if isinstance(details, dict):  # Successfully retrieved data
        organizations.append(details["Təşkilat"])
        registration_numbers.append(details["Dövlət qeydiyyat nömrəsi"])
        markas.append(details["Marka"])
        models.append(details["Model"])
        statuses.append(details["Status"])
        errors.append(None)  # No error
    else:  # Timeout or Not Found
        organizations.append(None)
        registration_numbers.append(None)
        markas.append(None)
        models.append(None)
        statuses.append(None)
        errors.append(details)  # Store "Timeout" or "Not Found"

# Create Polars DataFrame
df = pl.DataFrame({
    "Plate": plates,
    "Organization": organizations,
    "Registration Number": registration_numbers,
    "Marka": markas,
    "Model": models,
    "Status": statuses,
    "Error": errors
})

# Save DataFrame to CSV
df.write_csv("output/car_plate_data.csv")

print("CSV file created successfully!")
print(df)