#!/usr/bin/env python
# coding: utf-8

# In[1]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

# Initialize WebDriver with headless mode
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# URL and pagination setup
base_url = "https://japanparts.com.bd/collections/wiper-blade?page={}"
num_pages = 2

# Output data structure
data = []
scraped_urls = set()  # To store unique URLs

# Function to extract product details
def extract_product_details(product_url):
    driver.get(product_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".brator-product-hero-content-title h2")))

    # Initialize the dictionary to store product data
    product_data = {
        "Product URL": product_url,
        "Title": "",
        "Price": "",
        "Product Details": "",
        "Car Application": "",
        "Specification": "",
    }

    try:
        # Extract product title
        product_data["Title"] = driver.find_element(By.CSS_SELECTOR, ".brator-product-hero-content-title h2").text
    except Exception as e:
        print(f"Error extracting 'Title': {e}")

    try:
        # Extract price
        product_data["Price"] = driver.find_element(By.CSS_SELECTOR, ".brator-product-single-item-price span").text
    except Exception as e:
        print(f"Error extracting 'Price': {e}")

    try:
        # Extract product details
        product_data["Product Details"] = driver.find_element(
            By.CSS_SELECTOR, "#tabs-product-content .js-tabs__content.product-single__description"
        ).text
    except Exception as e:
        print(f"Error extracting 'Product Details': {e}")

    try:
        # Extract car application using JavaScript
        product_data["Car Application"] = driver.execute_script(
            "return document.querySelector('.specification-product-applicable.product-single__description').textContent.trim();"
        )
    except Exception as e:
        print(f"Error extracting 'Car Application': {e}")

    try:
        # Extract specification data using JavaScript
        product_data["Specification"] = driver.execute_script(
            """
            let spec_items = document.querySelectorAll('.specification-product-item');
            let specs = [];
            spec_items.forEach(item => {
                let key = item.querySelector('.specification-product-item-left p')?.textContent.trim();
                let value = item.querySelector('.specification-product-item-right p')?.textContent.trim();
                if (key) specs.push(key + ": " + (value || ""));
            });
            return specs.join("\\n");
            """
        )
    except Exception as e:
        print(f"Error extracting 'Specification': {e}")

    return product_data

# Loop through each page
for page in range(1, num_pages + 1):
    print(f"Working for Page {page}...")
    driver.get(base_url.format(page))
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".brator-product-single-item-title a")))

    # Find all product links on the page
    product_elements = driver.find_elements(By.CSS_SELECTOR, ".brator-product-single-item-title a")
    product_urls = [elem.get_attribute("href") for elem in product_elements]

    # Remove duplicates
    unique_product_urls = list(set(product_urls) - scraped_urls)
    scraped_urls.update(unique_product_urls)

    # Scrape product details
    for product_url in unique_product_urls:
        product_details = extract_product_details(product_url)
        data.append(product_details)

    print(f"Scraped {len(unique_product_urls)} Products")
    print("-----------------------")

# Save data to Excel
df = pd.DataFrame(data)
output_file = "D:\japanparts_wipeer-blade.xlsx"
df.to_excel(output_file, index=False)

# Close the driver
driver.quit()

print("Scraping completed successfully.")

