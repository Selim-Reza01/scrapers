#!/usr/bin/env python
# coding: utf-8

# In[4]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os
import time
import re
from tqdm import tqdm  # Progress bar library

# Output file path
output_file = "D:\\Car x Parts\\transmission.xlsx"

# Initialize the web driver with visible browser window
def initialize_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless")  # Ensure this is commented out or removed
    driver = webdriver.Chrome(options=options)
    return driver

# Extract product count from the product name string
def extract_product_count(product_name):
    match = re.search(r"\((\d+)\)", product_name)
    return int(match.group(1)) if match else 0

# Clean product type by removing the count in parentheses
def clean_product_type(product_name):
    return re.sub(r"\(\d+\)", "", product_name).strip()

# Scroll to load more products if necessary
def scroll_to_load_more(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)  # Wait for new products to load
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height != last_height  # Return True if scrolling changed the height

# Collect all product types from the base page
def collect_product_types(driver):
    product_types = []
    try:
        # Collect all product categories
        categories = driver.find_elements(By.CSS_SELECTOR, "ul.products li.product-category a")
        for category in categories:
            product_name = category.find_element(By.CSS_SELECTOR, "h2.woocommerce-loop-category__title").text.strip()
            product_url = category.get_attribute("href")
            product_types.append({"Product_Name": product_name, "Product_URL": product_url})
    except Exception as e:
        print(f"Error collecting product types: {e}")
    return product_types

def collect_product_urls(driver, product_name, product_url):
    expected_count = extract_product_count(product_name)
    print(f"Collecting product URLs from {clean_product_type(product_name)} ({expected_count})")
    print("Product URL Collecting . . .")
    
    driver.get(product_url)
    input("Manually scroll to the bottom of the page and press Enter to continue...")

    # Collect all product URLs on the page
    product_urls = set()
    try:
        products = driver.find_elements(By.CSS_SELECTOR, "ul.products li.product a.woocommerce-LoopProduct-link")
        for product in products:
            url = product.get_attribute("href")
            product_urls.add(url)  # Add to set to ensure uniqueness
    except Exception as e:
        print(f"Error collecting product URLs: {e}")

    print(f"Total Unique URLs Collected: {len(product_urls)}")
    return list(product_urls)


# Get product details from a product page
def get_product_details(driver, product_url):
    driver.get(product_url)
    time.sleep(5)

    try:
        # Scrape product title
        product_title = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product_title.entry-title"))
        ).text.strip()
    except Exception:
        product_title = "Title not found"

    try:
        # Scrape product price
        price = driver.find_element(By.CSS_SELECTOR, "p.price span.woocommerce-Price-amount bdi").text.strip()
    except Exception:
        price = ""  # Leave price empty if not found

    try:
        # Scrape product information
        product_information = driver.find_element(
            By.CSS_SELECTOR,
            "div.woocommerce-Tabs-panel.woocommerce-Tabs-panel--description"
        ).text.strip()
    except Exception:
        product_information = "Product information not found"

    return {
        "Product_Title": product_title,
        "Price": price,
        "Product_URL": product_url,
        "Product_Information": product_information,
    }

# Save to Excel after scraping each product type
def save_to_excel(data, output_file):
    df = pd.DataFrame(data)
    # Reorder columns as required
    df = df[["Product_Type", "Product_Title", "Price", "Product_Information", "Product_URL"]]
    if os.path.exists(output_file):
        existing_data = pd.read_excel(output_file)
        new_data = pd.concat([existing_data, df], ignore_index=True)
        new_data.to_excel(output_file, index=False)
    else:
        df.to_excel(output_file, index=False)

# Main function
def main():
    try:
        driver = initialize_driver()
        base_url = "https://www.loyalparts.com/product-category/car-parts/transmission/"
        driver.get(base_url)

        # Step 1: Collect all product types
        product_types = collect_product_types(driver)

        # Step 2: Loop through each product type and scrape URLs and details
        for product_type in product_types:
            product_name = product_type["Product_Name"]
            product_url = product_type["Product_URL"]
            clean_name = clean_product_type(product_name)  # Clean name without count
            product_urls = collect_product_urls(driver, product_name, product_url)

            # Scrape product details for each unique URL
            all_product_data = []
            print(f"Scraping Progress for {clean_name}:")
            for url in tqdm(product_urls, desc="Scraping Progress"):
                product_data = get_product_details(driver, url)
                product_data["Product_Type"] = clean_name
                all_product_data.append(product_data)

            # Save all scraped data for the current product type
            save_to_excel(all_product_data, output_file)

            print(f"{clean_name} Scraped Successfully!!")
            print("Returning to base page...\n")
            driver.get(base_url)  # Return to the base page

        # Final Thank You Message
        print("\nAll scraping completed successfully!!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

