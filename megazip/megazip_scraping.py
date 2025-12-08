#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os.path
import time

# Import file with product_name, brand, and part_number
part_number_file_name = 'D:\\Car x Parts\\Scripts\\megazip_input.xlsx'
dataframe = pd.read_excel(part_number_file_name)
product_names = dataframe['product_name'].tolist()
brands = dataframe['brand'].tolist()
part_numbers = [str(part_number).replace("-", "").lower() for part_number in dataframe['part_number'].tolist()]

# Create a session object for making requests
session = requests.Session()

# Set timeout value for requests
timeout = 60  # Adjust the timeout value (in seconds) as needed

# Set User-Agent header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Product information
product_data = {
    'product_name': [],
    'brand': [],
    'part_number': [],
    'make': [],
    'model': [],
    'chassis': [],
    'engine_model': [],
    'engine_capacity': [],
    'year_start': [],
    'year_end': [],
    'additional_details': []
}

# Products application not found
not_found_data = {
    'product_name': [],
    'brand': [],
    'part_number': [],
    'error_type': [],
    'status_code': []
}

def extract_model_opening_url(model_element):
    href = model_element['data-ajax-href']
    if href:
        return href
    else:
        return None

def extract_year_range(year_text):
    year_parts = year_text.split(' - ')
    valid_years = [year for year in year_parts if year.isnumeric() and len(year) == 4]
    if len(valid_years) == 2:
        year_start = valid_years[0]
        year_end = valid_years[1]
        return int(year_start), int(year_end)
    elif len(valid_years) == 1:
        year_part = valid_years[0]
        year_start = year_part
        year_end = year_part
        return int(year_start), int(year_end)
    return None, None

def process_part_number(part_number, brand, product_name, index, total_count):
    # For every brand, need to update '/mitsubishi/shoe-set-rr-brake-' this part with new brand in product_search_url
    product_search_url = 'https://www.megazip.net/zapchasti-dlya/toyota/absorber-assy-shock-front-rh-'+ part_number +'?q='+ part_number
    response = session.get(product_search_url, headers=headers, timeout=timeout)

    # Retry with a delay if the status code is 403
    if response.status_code == 403:
        print("Received 403 status code. Retrying after a delay...")
        time.sleep(5)  # Adjust the delay time as needed
        response = session.get(product_search_url, headers=headers, timeout=timeout)

    print("--------------------------------------------------")
    print(index + 1, "of", total_count)
    print("Part Number:", part_number)
    print("Response:", response.status_code)

    product_search_contents = response.text
    doc = BeautifulSoup(product_search_contents, "html.parser")

    # Find compatibility models
    models = doc.select('.s-catalog__model-group a.js-search-models.s-catalog__model-link')
    model_count = len(models)
    print("Models Found:", model_count)

    if model_count == 0:
        # No model found, save part number separately
        not_found_data['product_name'].append(product_name)
        not_found_data['brand'].append(brand)
        not_found_data['part_number'].append(part_number)
        not_found_data['error_type'].append('No Model Found')
        not_found_data['status_code'].append(response.status_code)

    for model in models:
        model_name = model.text.strip()
        model_url = 'https://www.megazip.net' + model['href']

        # Extract the model opening URL from the model element
        model_opening_url = extract_model_opening_url(model)
        if model_opening_url:
            print("Processing Model:", model_name)

            # Send a GET request for the model opening URL
            response_model = session.get("https://www.megazip.net" + model_opening_url, headers=headers, timeout=timeout)
            model_contents = response_model.text
            model_doc = BeautifulSoup(model_contents, "html.parser")

            # Find chassis
            chassis_items = model_doc.select('.s-catalog__columns-list.s-catalog__columns-list_in_search li')

            if not chassis_items:
                # No chassis found in the default selector, try alternative selector
                chassis_items = model_doc.select('#search_applicability_bodies li.current a.js-search-bodies')

            for chassis_item in chassis_items:
                chassis_name_element = chassis_item.select_one('.js-search-bodies.s-catalog__model-link')
                if chassis_name_element:
                    chassis_name = chassis_name_element.text.strip()
                    print('Chassis Found:', chassis_name)
                    chassis_url = chassis_name_element['href']

                    # Check if chassis URL needs to be opened to extract the engine model
                    open_chassis_url = True  # Set to True if chassis URL needs to be opened, False otherwise

                    if not open_chassis_url:
                        # Engine model can be extracted directly from the chassis item
                        engine_model_element = chassis_item.select_one('.s-catalog__columns-list.s-catalog__columns-list_in_search dt')
                        if engine_model_element:
                            engine_model_sibling = engine_model_element.find_next_sibling('dd', class_='s-catalog__columns-list.s-catalog__columns-list_in_search dd')
                            if engine_model_sibling:
                                engine_model = engine_model_sibling.text.strip()
                        else:
                            engine_model = ''

                    if open_chassis_url:
                        response_chassis = session.get("https://www.megazip.net" + chassis_url, headers=headers, timeout=timeout)
                        chassis_contents = response_chassis.text
                        chassis_doc = BeautifulSoup(chassis_contents, "html.parser")

                        # Find engine model
                        engine_model_element = None
                        engine_model_alt_element = None
                        engine_model_text = ''

                        # Find engine model using regular expressions for different variations of 'Engine'
                        engine_model_element = chassis_doc.find('dt', text=re.compile(r'engine', re.IGNORECASE))
                        if not engine_model_element:
                            engine_model_alt_element = chassis_doc.select_one('.s-catalog__columns-list.s-catalog__columns-list_in_search dt')

                        if engine_model_element:
                            engine_model_sibling = engine_model_element.find_next_sibling('dd', class_='s-catalog__attrs-data')
                            if engine_model_sibling:
                                engine_model_text = engine_model_sibling.text.strip()

                        elif engine_model_alt_element:
                            engine_model_sibling = engine_model_alt_element.find_next_sibling('dd', class_='s-catalog__columns-list.s-catalog__columns-list_in_search dd')
                            if engine_model_sibling:
                                engine_model_text = engine_model_sibling.text.strip()

                        engine_model = engine_model_text

                        # Find years
                        years_elements = chassis_doc.select('.s-catalog__attrs-term', text=re.compile(r'year', re.IGNORECASE))
                        start_years = []
                        end_years = []
                        for years_element in years_elements:
                            year_data = years_element.find_next_sibling('dd', class_='s-catalog__attrs-data').text.strip()
                            year_start, year_end = extract_year_range(year_data)
                            if year_start is not None and year_end is not None:
                                start_years.append(year_start)
                                end_years.append(year_end)

                        # Determine the smallest start year and the largest end year
                        year_start = str(min(start_years)) if start_years else ''
                        year_end = str(max(end_years)) if end_years else ''

                        # Append data to product_data dictionary
                        product_data['product_name'].append(product_name)
                        product_data['brand'].append(brand)
                        product_data['part_number'].append(part_number)
                        product_data['make'].append('Mitsubishi')  # Set make as per brand name
                        product_data['model'].append(model_name)
                        product_data['chassis'].append(chassis_name)
                        product_data['engine_model'].append(engine_model)
                        product_data['engine_capacity'].append('')
                        product_data['year_start'].append(year_start)
                        product_data['year_end'].append(year_end)
                        product_data['additional_details'].append('')

                else:
                    print("Chassis name element not found in the chassis item.")
                    # If chassis name element not found, try alternative method
                    chassis_name = chassis_item.text.strip()
                    print('Chassis Found:', chassis_name)
                    chassis_url = chassis_item['href']

                    response_chassis = session.get("https://www.megazip.net" + chassis_url, headers=headers, timeout=timeout)
                    chassis_contents = response_chassis.text
                    chassis_doc = BeautifulSoup(chassis_contents, "html.parser")

                    # Rest of the code for processing the chassis information
                    engine_model_element = None
                    engine_model_alt_element = None
                    engine_model_text = ''

                    # Find engine model using regular expressions for different variations of 'Engine'
                    engine_model_element = chassis_doc.find('dt', text=re.compile(r'engine', re.IGNORECASE))
                    if not engine_model_element:
                        engine_model_alt_element = chassis_doc.select_one('.s-catalog__columns-list.s-catalog__columns-list_in_search dt')

                    if engine_model_element:
                        engine_model_sibling = engine_model_element.find_next_sibling('dd', class_='s-catalog__attrs-data')
                        if engine_model_sibling:
                            engine_model_text = engine_model_sibling.text.strip()

                    elif engine_model_alt_element:
                        engine_model_sibling = engine_model_alt_element.find_next_sibling('dd', class_='s-catalog__columns-list.s-catalog__columns-list_in_search dd')
                        if engine_model_sibling:
                            engine_model_text = engine_model_sibling.text.strip()

                    engine_model = engine_model_text

                    # Find years
                    years_elements = chassis_doc.select('.s-catalog__attrs-term', text=re.compile(r'year', re.IGNORECASE))
                    start_years = []
                    end_years = []
                    for years_element in years_elements:
                        year_data = years_element.find_next_sibling('dd', class_='s-catalog__attrs-data').text.strip()
                        year_start, year_end = extract_year_range(year_data)
                        if year_start is not None and year_end is not None:
                            start_years.append(year_start)
                            end_years.append(year_end)

                    # Determine the smallest start year and the largest end year
                    year_start = str(min(start_years)) if start_years else ''
                    year_end = str(max(end_years)) if end_years else ''

                    # Append data to product_data dictionary
                    product_data['product_name'].append(product_name)
                    product_data['brand'].append(brand)
                    product_data['part_number'].append(part_number)
                    product_data['make'].append('Mitsubishi')  # Set make as per brand name
                    product_data['model'].append(model_name)
                    product_data['chassis'].append(chassis_name)
                    product_data['engine_model'].append(engine_model)
                    product_data['engine_capacity'].append('')
                    product_data['year_start'].append(year_start)
                    product_data['year_end'].append(year_end)
                    product_data['additional_details'].append('')

        else:
            print("Model Opening URL not found in the model element.")

# Process each part number
total_count = len(part_numbers)
for index, (part_number, brand, product_name) in enumerate(zip(part_numbers, brands, product_names)):
    process_part_number(part_number, brand, product_name, index, total_count)
    time.sleep(1)  # Add a delay of 1 second between requests

    print()  # Print an empty line for better readability

# Convert product_data to DataFrame
product_data_df = pd.DataFrame(product_data)

# Save DataFrame to Excel
output_file_name = 'D:\\Car x Parts\\Scripts\\megazip_output.xlsx'

if not os.path.exists(output_file_name):
    product_data_df.to_excel(output_file_name, index=False)
else:
    with pd.ExcelWriter(output_file_name, mode='a', engine='openpyxl') as writer:
        product_data_df.to_excel(writer, index=False, sheet_name='Sheet1')

# Convert not_found_data to DataFrame
not_found_data_df = pd.DataFrame(not_found_data)

if not os.path.exists(output_file_name):
    not_found_data_df.to_excel(output_file_name, index=False, sheet_name='No Model Found')
else:
    with pd.ExcelWriter(output_file_name, mode='a', engine='openpyxl') as writer:
        not_found_data_df.to_excel(writer, index=False, sheet_name='No Model Found')

print("Scraping completed. Enjoy!!")


# In[ ]:




