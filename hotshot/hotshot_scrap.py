#!/usr/bin/env python
# coding: utf-8

# In[17]:


import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

# Setup Chrome WebDriver with options (without headless mode so you can see it)
chrome_options = Options()
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
# Not using headless mode as you requested
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Set implicit wait for elements to be loaded
driver.implicitly_wait(10)  # Reduced wait time for better performance

def collect_product_urls(driver, product_url):
    print("Product URL Collecting . . .")
    
    driver.get(product_url)
    
    # Wait for the product links to load (no need for manual scrolling)
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.elementor-widget-container a")))

    except Exception as e:
        print(f"Error waiting for page to load: {e}")

    # Display the manual prompt and wait for the user to scroll
    print("Please scroll to the bottom of the page to load all products. Once done, press Enter to continue...")
    input("Press Enter to continue after scrolling...")

    # Collect all product URLs on the page from the adjusted selector
    product_urls = set()
    try:
        products = driver.find_elements(By.CSS_SELECTOR, "div.elementor-widget-container a")
        for product in products:
            url = product.get_attribute("href")
            if url and "/product/" in url:  # Only collect URLs that contain '/product/'
                product_urls.add(url)  # Add to set to ensure uniqueness
    except Exception as e:
        print(f"Error collecting product URLs: {e}")

    print(f"Total Products: {len(product_urls)}")
    return list(product_urls)

def collect_product_data(driver, product_url, category_name):
    driver.get(product_url)

    product_data = {}

    try:
        # Wait for the product page elements to load
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product_title.entry-title")))

        # Category - use the passed category name
        product_data["Category"] = category_name
        
        # Product name (Title)
        title = driver.find_element(By.CSS_SELECTOR, "h1.product_title.entry-title").text
        product_data["Title"] = title
        
        # Product price
        price = driver.find_element(By.CSS_SELECTOR, "p.price span.woocommerce-Price-amount").text
        product_data["Price"] = price
        
        # Stock status
        stock_status = driver.find_element(By.CSS_SELECTOR, "p.stock").text
        product_data["Stock"] = stock_status
        
        # Product details (from woocommerce-product-details__short-description)
        try:
            details = driver.find_element(By.CSS_SELECTOR, "div.woocommerce-product-details__short-description").text
            product_data["Details"] = details
        except Exception as e:
            product_data["Details"] = None  # Use None if details are not found
        
        # Product URL
        product_data["Url"] = product_url

    except Exception as e:
        print(f"Error scraping product data: {e}")
    
    return product_data

def save_to_excel(data, category_name):
    df = pd.DataFrame(data)
    output_file = f"D://Car x Parts//{category_name}_products.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Data saved to: {output_file}")

def main():
    category_url = "https://www.hotshotautomotive.com/product-category/additive/"
    category_name = category_url.split("/")[-2]  # Automatically extract the category name from the URL

    # Collect product URLs
    product_urls = collect_product_urls(driver, category_url)
    
    # Initialize a list to hold product data
    product_data = []
    
    # Collect data for each product, showing progress
    for url in tqdm(product_urls, desc=f"Scraping Progress for {category_name}", ncols=100, unit="product"):
        data = collect_product_data(driver, url, category_name)
        product_data.append(data)
    
    # Save to Excel
    save_to_excel(product_data, category_name)
    
    # Close the driver
    driver.quit()

if __name__ == "__main__":
    main()

