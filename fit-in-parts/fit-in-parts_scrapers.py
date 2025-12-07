#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import os.path
import time

# Import file with product_name, brand, and part_number
part_number_file_name = r'D:\Car x Parts\Scripts\input.xlsx'
dataframe = pd.read_excel(part_number_file_name)
product_names = dataframe['product_name'].tolist()
brands = dataframe['brand'].tolist()
part_numbers = [str(part_number).replace("-", "").lower() for part_number in dataframe['part_number'].tolist()]

# Set up the Selenium WebDriver
driver = webdriver.Chrome()  # You need to have Chrome WebDriver installed and in your PATH

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
    'year': [],
    'additional_details': [],
    'new_brand': [],
    'location': [],
    'position': []
}

# Products application not found
not_found_data_list = []

def process_part_number(part_number, brand, product_name, index, total_count):
    retries = 1  # Number of retries for each part number
    for retry in range(retries):
        try:
            product_search_url = 'https://www.fitinpart.sg/index.php?route=product/search/partSearch&part_no=' + part_number + '&show=0'
            
            driver.get(product_search_url)
            start_time = time.time()
            while True:
                if "Please pass the captcha" in driver.page_source:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 120:  # 5 minutes
                        print("Captcha detected for part number", part_number)
                        print("Please solve the captcha manually and press Enter to continue...")
                        input()  # Wait for user input to continue
                        break
                    print("Captcha detected for part number", part_number)
                    print("Please solve the captcha manually...")
                    time.sleep(5)  # Wait for 5 seconds before checking again
                else:
                    break

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'title')))  # Wait for the title element

            title_element = driver.find_element(By.CLASS_NAME, 'title')
            if "found 0 Cross with 0 Equivalent" in title_element.text:
                print("Part number", part_number, "not found.")
                not_found_data_list.append({
                    'product_name': product_name,
                    'brand': brand,
                    'part_number': part_number,
                    'new_brand': '',
                    'error_type': "NOT FOUND"
                })
                return  # Skip the rest of the processing for this part number

            print("--------------------------------------------------")
            print(index + 1, "of", total_count)
            print("Part Number:", part_number)

            product_search_contents = driver.page_source
            doc = BeautifulSoup(product_search_contents, "html.parser")
            a_tags = doc.find_all("a", {'class': 'image_p'})

            if len(a_tags) > 0:
                product_url = a_tags[0].get('href')
                driver.get(product_url)
                try:
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'vehicles')))
                    product_page_contents = driver.page_source
                    doc = BeautifulSoup(product_page_contents, "html.parser")          
                except:
                    product_page_contents = driver.page_source
                    doc = BeautifulSoup(product_page_contents, "html.parser")

                # Extract new_brand
                brand_element = doc.find("div", {"class": "partnum-brand"})
                new_brand = brand_element.find("strong", {"class": "name"}).text.strip() if brand_element else ""

                # Extract specifications
                location = ""
                position = ""
                specifications = doc.find("div", {"class": "specifications"})
                if specifications:
                    rows = specifications.find_all("div", {"class": "item-specification__row"})
                    for row in rows:
                        title = row.find("div", {"class": "item-specification__title"}).text.strip()
                        value = row.find("div", {"class": "item-specification__value"}).text.strip().upper()
                        if "Location" in title:
                            location = value
                        elif "Position" in title:
                            position = value

                title_element = doc.find("div", {"class": "title"})
                if title_element:
                    if "Vehicles" in title_element.text:
                        entries = doc.find_all("div", {"class": "item-vehicle"})
                        print(len(entries), "make-model for " + part_number)
                        print("-----------------------------------------------")
                        print()

                        if len(entries) > 0:
                            for entry in entries:
                                make_div = entry.find("div", "td td-2")
                                model_div = entry.find("div", "td td-3")
                                make = make_div.text.upper()
                                model = model_div.text.upper()

                                row_items_div = entry.find_all("div", "tr tr-item")
                                for row_item in row_items_div:
                                    year = row_item.find("div", {"class": "td td-2"}).text.strip().upper()
                                    engine_capacity = row_item.find("div", {"class": "td td-3"}).text.strip().upper()
                                    chassis = row_item.find("div", {"class": "td td-4"}).text.strip().upper()
                                    engine_model = row_item.find("div", {"class": "td td-5"}).text.strip().upper()
                                    additional_details = row_item.find("div", {"class": "td td-6"}).text.strip().upper()

                                    product_data['product_name'].append(product_name)
                                    product_data['brand'].append(brand)
                                    product_data['part_number'].append(part_number)
                                    product_data['make'].append(make)
                                    product_data['model'].append(model)
                                    product_data['chassis'].append(chassis)
                                    product_data['engine_model'].append(engine_model)
                                    product_data['engine_capacity'].append(engine_capacity)
                                    product_data['year'].append(year)
                                    product_data['additional_details'].append(additional_details)
                                    product_data['new_brand'].append(new_brand)
                                    product_data['location'].append(location)
                                    product_data['position'].append(position)
                else:
                    print("NO entry for " + part_number)
                    print("-----------------------------------------------")
                    print()
                    not_found_data_list.append({
                        'product_name': product_name,
                        'brand': brand,
                        'part_number': part_number,
                        'new_brand': new_brand,
                        'error_type': "NO ENTRY"
                    })    
            else:
                print("No result for " + part_number)
                print("-----------------------------------------------")
                print()
                not_found_data_list.append({
                    'product_name': product_name,
                    'brand': brand,
                    'part_number': part_number,
                    'new_brand': '',
                    'error_type': "NO RESULT"
                })

            break  # If successful, break out of the retry loop
        except Exception as e:
            print("Exception:", str(e))
            if retry == retries - 1:
                print("Maximum retries reached for part number", part_number)
                not_found_data_list.append({
                    'product_name': product_name,
                    'brand': brand,
                    'part_number': part_number,
                    'new_brand': '',
                    'error_type': "EXCEPTION"
                })
            else:
                print("Retrying part number", part_number)

# Process part numbers
current_index = 0  # Index to keep track of the current part number
while current_index < len(part_numbers):
    part_number = part_numbers[current_index]
    brand = brands[current_index]
    product_name = product_names[current_index]

    try:
        process_part_number(part_number, brand, product_name, current_index, len(part_numbers))
        current_index += 1  # Move to the next part number if successful
    except Exception as e:
        print("Exception:", str(e))
        current_index += 1

# Create dataframes from the collected data
products_application_df = pd.DataFrame(product_data)
products_application_not_found_df = pd.DataFrame(not_found_data_list)

# Save dataframes to Excel files
output_folder = r'D:\Car x Parts\Scripts\Output'
os.makedirs(output_folder, exist_ok=True)  # Create the output folder if it doesn't exist
parts_found_file = os.path.join(output_folder, 'new_data.xlsx')
parts_not_found_file = os.path.join(output_folder, 'not_found_new.xlsx')

products_application_df.to_excel(parts_found_file, index=False)
products_application_not_found_df.to_excel(parts_not_found_file, index=False)

# Close the WebDriver
driver.quit()

print("Part numbers found ->", len(product_data['part_number']))
print("Part numbers not found ->", len(not_found_data_list))

print("Process Complete ... Ciao Ciao")


# In[ ]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import os.path
import time

# Import file with product_name, brand, and part_number
part_number_file_name = r'D:\Car x Parts\Scripts\input.xlsx'
dataframe = pd.read_excel(part_number_file_name)
product_names = dataframe['product_name'].tolist()
brands = dataframe['brand'].tolist()
part_numbers = [str(part_number).replace("-", "").lower() for part_number in dataframe['part_number'].tolist()]

# Set up the Selenium WebDriver
driver = webdriver.Chrome()  # You need to have Chrome WebDriver installed and in your PATH

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
    'year': [],
    'additional_details': [],
    'new_brand': [],
    'location': [],
    'position': []
}

# Products application not found
not_found_data_list = []

def process_part_number(part_number, brand, product_name, index, total_count):
    retries = 1  # Number of retries for each part number
    for retry in range(retries):
        try:
            product_search_url = 'https://www.fitinpart.sg/index.php?route=product/search/partSearch&part_no=' + part_number + '&show=0'
            
            driver.get(product_search_url)
            start_time = time.time()
            while True:
                if "Please pass the captcha" in driver.page_source:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 120:  # 5 minutes
                        print("Captcha detected for part number", part_number)
                        print("Please solve the captcha manually and press Enter to continue...")
                        input()  # Wait for user input to continue
                        break
                    print("Captcha detected for part number", part_number)
                    print("Please solve the captcha manually...")
                    time.sleep(5)  # Wait for 5 seconds before checking again
                else:
                    break

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'title')))  # Wait for the title element

            title_element = driver.find_element(By.CLASS_NAME, 'title')
            if "found 0 Cross with 0 Equivalent" in title_element.text:
                print("Part number", part_number, "not found.")
                not_found_data_list.append({
                    'product_name': product_name,
                    'brand': brand,
                    'part_number': part_number,
                    'new_brand': '',
                    'error_type': "NOT FOUND"
                })
                return  # Skip the rest of the processing for this part number

            print("--------------------------------------------------")
            print(index + 1, "of", total_count)
            print("Part Number:", part_number)

            product_search_contents = driver.page_source
            doc = BeautifulSoup(product_search_contents, "html.parser")
            a_tags = doc.find_all("a", {'class': 'image_p'})

            if len(a_tags) > 0:
                product_url = a_tags[0].get('href')
                driver.get(product_url)
                try:
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'vehicles')))
                    product_page_contents = driver.page_source
                    doc = BeautifulSoup(product_page_contents, "html.parser")          
                except:
                    product_page_contents = driver.page_source
                    doc = BeautifulSoup(product_page_contents, "html.parser")

                # Extract new_brand
                brand_element = doc.find("div", {"class": "partnum-brand"})
                new_brand = brand_element.find("strong", {"class": "name"}).text.strip() if brand_element else ""

                # Extract specifications
                location = ""
                position = ""
                specifications = doc.find("div", {"class": "specifications"})
                if specifications:
                    rows = specifications.find_all("div", {"class": "item-specification__row"})
                    for row in rows:
                        title = row.find("div", {"class": "item-specification__title"}).text.strip()
                        value = row.find("div", {"class": "item-specification__value"}).text.strip().upper()
                        if "Location" in title:
                            location = value
                        elif "Position" in title:
                            position = value

                title_element = doc.find("div", {"class": "title"})
                if title_element:
                    if "Vehicles" in title_element.text:
                        entries = doc.find_all("div", {"class": "item-vehicle"})
                        print(len(entries), "make-model for " + part_number)
                        print("-----------------------------------------------")
                        print()

                        if len(entries) > 0:
                            for entry in entries:
                                make_div = entry.find("div", "td td-2")
                                model_div = entry.find("div", "td td-3")
                                make = make_div.text.upper()
                                model = model_div.text.upper()

                                row_items_div = entry.find_all("div", "tr tr-item")
                                for row_item in row_items_div:
                                    year = row_item.find("div", {"class": "td td-2"}).text.strip().upper()
                                    engine_capacity = row_item.find("div", {"class": "td td-3"}).text.strip().upper()
                                    chassis = row_item.find("div", {"class": "td td-4"}).text.strip().upper()
                                    engine_model = row_item.find("div", {"class": "td td-5"}).text.strip().upper()
                                    additional_details = row_item.find("div", {"class": "td td-6"}).text.strip().upper()

                                    product_data['product_name'].append(product_name)
                                    product_data['brand'].append(brand)
                                    product_data['part_number'].append(part_number)
                                    product_data['make'].append(make)
                                    product_data['model'].append(model)
                                    product_data['chassis'].append(chassis)
                                    product_data['engine_model'].append(engine_model)
                                    product_data['engine_capacity'].append(engine_capacity)
                                    product_data['year'].append(year)
                                    product_data['additional_details'].append(additional_details)
                                    product_data['new_brand'].append(new_brand)
                                    product_data['location'].append(location)
                                    product_data['position'].append(position)
                else:
                    print("NO entry for " + part_number)
                    print("-----------------------------------------------")
                    print()
                    not_found_data_list.append({
                        'product_name': product_name,
                        'brand': brand,
                        'part_number': part_number,
                        'new_brand': new_brand,
                        'error_type': "NO ENTRY"
                    })    
            else:
                print("No result for " + part_number)
                print("-----------------------------------------------")
                print()
                not_found_data_list.append({
                    'product_name': product_name,
                    'brand': brand,
                    'part_number': part_number,
                    'new_brand': '',
                    'error_type': "NO RESULT"
                })

            break  # If successful, break out of the retry loop
        except Exception as e:
            print("Exception:", str(e))
            if retry == retries - 1:
                print("Maximum retries reached for part number", part_number)
                not_found_data_list.append({
                    'product_name': product_name,
                    'brand': brand,
                    'part_number': part_number,
                    'new_brand': '',
                    'error_type': "EXCEPTION"
                })
            else:
                print("Retrying part number", part_number)

# Process part numbers
current_index = 0  # Index to keep track of the current part number
while current_index < len(part_numbers):
    part_number = part_numbers[current_index]
    brand = brands[current_index]
    product_name = product_names[current_index]

    try:
        process_part_number(part_number, brand, product_name, current_index, len(part_numbers))
        current_index += 1  # Move to the next part number if successful
    except Exception as e:
        print("Exception:", str(e))
        current_index += 1

# Create dataframes from the collected data
products_application_df = pd.DataFrame(product_data)
products_application_not_found_df = pd.DataFrame(not_found_data_list)

# Save dataframes to Excel files
output_folder = r'D:\Car x Parts\Scripts\Output'
os.makedirs(output_folder, exist_ok=True)  # Create the output folder if it doesn't exist
parts_found_file = os.path.join(output_folder, 'new_data.xlsx')
parts_not_found_file = os.path.join(output_folder, 'not_found_new.xlsx')

products_application_df.to_excel(parts_found_file, index=False)
products_application_not_found_df.to_excel(parts_not_found_file, index=False)

# Close the WebDriver
driver.quit()

print("Part numbers found ->", len(product_data['part_number']))
print("Part numbers not found ->", len(not_found_data_list))

print("Process Complete ... Ciao Ciao")

