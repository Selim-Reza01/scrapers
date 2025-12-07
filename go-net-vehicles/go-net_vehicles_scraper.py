import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import os
import time

# --- Configuration ---
catalog_url = "https://www.goo-net-exchange.com/catalog/TOYOTA__86/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Save in the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
output_csv = os.path.join(script_dir, "japan_toyota_86.csv")

# --- Helper Functions ---
def extract_text(tag, default="-"):
    return tag.get_text(strip=True) if tag else default

def get_spec_value(table_soup, target):
    row = table_soup.find("th", string=target)
    if row is None: return "-"
    td = row.find_next("td")
    return extract_text(td)

def scrape_gears(table):
    gear_ratio_row = table.find("th", string="Gear_ratio")
    if not gear_ratio_row: return "-"
    tds = gear_ratio_row.find_next("td")
    gears_output = []
    for gear_p in tds.find_all("p"):
        name = extract_text(gear_p.find("strong"))
        val = extract_text(gear_p.find("span"))
        gears_output.append(f"{name}:{val}")
    return ", ".join(gears_output) if gears_output else "-"

# --- Step 1: Get catalog list page ---
print("Fetching catalog list page...")
response = requests.get(catalog_url, headers=headers)
response.encoding = 'utf-8'
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

# --- Step 2: Extract all model entries from list ---
models_data = []
list_cars = soup.find_all("div", class_="list-car")

for list_car in list_cars:
    # Extract Sale Year
    title_tag = list_car.find("h6", class_="title")
    sale_year = "-"
    if title_tag:
        title_text = extract_text(title_tag)
        if "Sale in" in title_text:
            sale_year = title_text.split("Sale in")[-1].strip()
    
    # Extract table rows
    table = list_car.find("table")
    if not table:
        continue
    
    rows = table.find("tbody").find_all("tr")
    
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 9:
            continue
        
        # Extract Model Type and URL
        model_type_td = tds[1]
        model_link = model_type_td.find("a")
        if not model_link:
            continue
        
        model_type = extract_text(model_link)
        # Check for Limited Model span
        limited_span = model_type_td.find("span")
        if limited_span:
            model_type += " " + extract_text(limited_span)
        
        detail_url = "https://www.goo-net-exchange.com" + model_link.get("href")
        
        # Extract T/M DRIVE (Transmission)
        tm_drive_td = tds[5]
        tm_drive_text = extract_text(tm_drive_td).replace("\n", " ")
        
        # Extract Weight
        weight = extract_text(tds[7])
        
        # Extract MSRP
        msrp = extract_text(tds[8])
        
        models_data.append({
            "sale_year": sale_year,
            "model_type": model_type,
            "detail_url": detail_url,
            "tm_drive": tm_drive_text,
            "weight_list": weight,
            "msrp": msrp
        })

print(f"Found {len(models_data)} models to scrape")

# --- Step 3: Scrape each detail page ---
all_rows = []
header = [
    "Url", "Datetime", "Sale_Year", "Model_Type_List", "T/M_Drive_List", "Weight_List", "MSRP",
    "Brand", "Title",
    "Model", "Dimension", "Wheelbase", "Tread front/rear", "Dimension(Interior)", "Weight", "Body Type", "Doors", "Riding Capacity",
    "Engine Model", "Maximum Power", "Displacement", "Compression Ratio", "Fuel Supply Equipment", "Fuel Type", "Cylinders",
    "Maximum Torque", "Bore×Stroke", "Charger", "Fuel Tank Equipment",
    "Steering System", "Suspension System(front)", "Breaking System(front)", "Tires Size(front)", "Minimum Turning Radius",
    "Suspension System(rear)", "Breaking System(rear)", "Tires Size(rear)",
    "Driving Wheel", "Transmission", "LSD", "Gear_ratio", "Final Drive Gear Ratio"
]

for idx, model in enumerate(models_data, 1):
    print(f"Scraping {idx}/{len(models_data)}: {model['detail_url']}")
    
    try:
        # Fetch detail page
        response = requests.get(model['detail_url'], headers=headers)
        response.encoding = 'utf-8'
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # --- Scrape General Specifications ---
        detail_right = soup.find("div", class_="detail-right")
        if not detail_right:
            print(f"  Warning: No detail-right found for {model['detail_url']}")
            continue
        
        brand = extract_text(detail_right.find("p", class_="type-car"))
        title = extract_text(detail_right.find("h1", class_="name-car"))
        
        general_box = detail_right.find("div", class_="general-box")
        general_pairs = {}
        if general_box:
            for p in general_box.find_all("p"):
                strong = p.find("strong")
                span = p.find("span")
                key = extract_text(strong)
                val = extract_text(span)
                general_pairs[key] = val
        
        # --- Scrape Specifications Tables ---
        content_left = soup.find("div", class_="content-left")
        if not content_left:
            print(f"  Warning: No content-left found for {model['detail_url']}")
            continue
        
        def extract_table(title_box):
            box = content_left.find("p", class_="title-box", string=title_box)
            if not box:
                return None
            parent = box.find_parent("div", class_="specifications-box")
            return parent.find("table") if parent else None
        
        engine_table = extract_table("Engine/Fuel")
        suspension_table = extract_table("Suspension")
        drivetrain_table = extract_table("Drivetrain")
        
        # Engine/Fuel Specs
        engine_specs = {}
        if engine_table:
            engine_specs = {
                "Engine Model": get_spec_value(engine_table, "Engine Model"),
                "Maximum Power": get_spec_value(engine_table, "Maximum Power"),
                "Displacement": get_spec_value(engine_table, "Displacement"),
                "Compression Ratio": get_spec_value(engine_table, "Compression Ratio"),
                "Fuel Supply Equipment": get_spec_value(engine_table, "Fuel Supply Equipment"),
                "Fuel Type": get_spec_value(engine_table, "Fuel Type"),
                "Cylinders": get_spec_value(engine_table, "Cylinders"),
                "Maximum Torque": get_spec_value(engine_table, "Maximum Torque"),
                "Bore×Stroke": get_spec_value(engine_table, "Bore×Stroke"),
                "Charger": get_spec_value(engine_table, "Charger"),
                "Fuel Tank Equipment": get_spec_value(engine_table, "Fuel Tank Equipment"),
            }
        
        # Suspension Specs
        suspension_specs = {}
        if suspension_table:
            suspension_specs = {
                "Steering System": get_spec_value(suspension_table, "Steering System"),
                "Suspension System(front)": get_spec_value(suspension_table, "Suspension System(front)"),
                "Breaking System(front)": get_spec_value(suspension_table, "Breaking System(front)"),
                "Tires Size(front)": get_spec_value(suspension_table, "Tires Size(front)"),
                "Minimum Turning Radius": get_spec_value(suspension_table, "Minimum Turning Radius"),
                "Suspension System(rear)": get_spec_value(suspension_table, "Suspension System(rear)"),
                "Breaking System(rear)": get_spec_value(suspension_table, "Breaking System(rear)"),
                "Tires Size(rear)": get_spec_value(suspension_table, "Tires Size(rear)"),
            }
        
        # Drivetrain Specs
        drivetrain_specs = {}
        if drivetrain_table:
            drivetrain_specs = {
                "Driving Wheel": get_spec_value(drivetrain_table, "Driving Wheel"),
                "Transmission": get_spec_value(drivetrain_table, "Transmission"),
                "LSD": get_spec_value(drivetrain_table, "LSD"),
                "Gear_ratio": scrape_gears(drivetrain_table),
                "Final Drive Gear Ratio": get_spec_value(drivetrain_table, "Final Drive Gear Ratio"),
            }
        
        # --- Prepare Row ---
        now_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row = [
            model['detail_url'],
            now_dt,
            model['sale_year'],
            model['model_type'],
            model['tm_drive'],
            model['weight_list'],
            model['msrp'],
            brand,
            title,
            general_pairs.get("Model", "-"),
            general_pairs.get("Dimension", "-"),
            general_pairs.get("Wheelbase", "-"),
            general_pairs.get("Tread front/rear", "-"),
            general_pairs.get("Dimension(Interior)", "-"),
            general_pairs.get("Weight", "-"),
            general_pairs.get("Body Type", "-"),
            general_pairs.get("Doors", "-"),
            general_pairs.get("Riding Capacity", "-"),
            # Engine
            engine_specs.get("Engine Model", "-"),
            engine_specs.get("Maximum Power", "-"),
            engine_specs.get("Displacement", "-"),
            engine_specs.get("Compression Ratio", "-"),
            engine_specs.get("Fuel Supply Equipment", "-"),
            engine_specs.get("Fuel Type", "-"),
            engine_specs.get("Cylinders", "-"),
            engine_specs.get("Maximum Torque", "-"),
            engine_specs.get("Bore×Stroke", "-"),
            engine_specs.get("Charger", "-"),
            engine_specs.get("Fuel Tank Equipment", "-"),
            # Suspension
            suspension_specs.get("Steering System", "-"),
            suspension_specs.get("Suspension System(front)", "-"),
            suspension_specs.get("Breaking System(front)", "-"),
            suspension_specs.get("Tires Size(front)", "-"),
            suspension_specs.get("Minimum Turning Radius", "-"),
            suspension_specs.get("Suspension System(rear)", "-"),
            suspension_specs.get("Breaking System(rear)", "-"),
            suspension_specs.get("Tires Size(rear)", "-"),
            # Drivetrain
            drivetrain_specs.get("Driving Wheel", "-"),
            drivetrain_specs.get("Transmission", "-"),
            drivetrain_specs.get("LSD", "-"),
            drivetrain_specs.get("Gear_ratio", "-"),
            drivetrain_specs.get("Final Drive Gear Ratio", "-"),
        ]
        
        all_rows.append(row)
        
        # Be polite to the server
        time.sleep(1)
        
    except Exception as e:
        print(f"  Error scraping {model['detail_url']}: {e}")
        continue

# --- Step 4: Save to CSV ---
with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(all_rows)

print(f"\nScraped {len(all_rows)} models successfully!")
print(f"Data saved to {output_csv}")