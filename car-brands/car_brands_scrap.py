#!/usr/bin/env python
# coding: utf-8

# In[3]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup WebDriver
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

car_brands = []

# Loop through all 8 pages
for page in range(1, 9):
    if page == 1:
        url = "https://www.carlogos.org/car-brands/"
    else:
        url = f"https://www.carlogos.org/car-brands/page-{page}.html"

    print(f"Scraping {url} ...")
    driver.get(url)
    time.sleep(2)  # wait for JavaScript to load

    try:
        logo_list = driver.find_elements(By.CSS_SELECTOR, 'ul.logo-list > li > a')
        for a in logo_list:
            text = a.text.split('\n')[0]  # brand name is before the first <label>
            car_brands.append(text)
    except Exception as e:
        print(f"Error on page {page}: {e}")

driver.quit()

# Output
print(f"\nTotal car brands found: {len(car_brands)}")
for brand in car_brands:
    print(brand)


# In[ ]:





# In[7]:


import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Set up Chrome options
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Open the website
driver.get("https://www.car.info/en-se/brands")

# Wait for manual scroll completion
input("Scroll until all brands are loaded, then press ENTER to start scraping...")

# Grab all brand elements
brand_elements = driver.find_elements(By.CSS_SELECTOR, "div.brand_item")

data = []

# Use BeautifulSoup for accurate parsing of full HTML content
for brand in brand_elements:
    try:
        html = brand.get_attribute('outerHTML')
        soup = BeautifulSoup(html, 'html.parser')

        brand_name = soup.select_one("a.brand_name").text.strip()
        year = soup.select_one("div.brand_year").text.strip()

        tooltip = soup.select_one("small.tooltiptext")
        origin_country = tooltip.text.strip() if tooltip and "Country of origin" in tooltip.text else "Unknown"

        data.append({
            "Car Brand": brand_name,
            "Year": year,
            "Origin": origin_country
        })
    except Exception as e:
        print("Error extracting brand:", e)

driver.quit()

# Save to Excel in the specified folder
output_dir = r"D:\Car x Parts"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "car_brands_info.xlsx")

df = pd.DataFrame(data)
df.to_excel(output_file, index=False)

print(f"✅ Data successfully saved to: {output_file}")

