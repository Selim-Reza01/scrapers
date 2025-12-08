#!/usr/bin/env python
# coding: utf-8

# In[41]:


import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from tqdm import tqdm  # To show progress bar

BASE_URL = "https://www.oilco.com.bd"
CATEGORY_URL = f"{BASE_URL}/category"
OUTPUT_FILE_PATH = r"D:\Car x Parts\scraped_data.xlsx"  # Updated file path

# Set up Selenium WebDriver with Chrome (non-headless mode)
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument("--no-sandbox")  # Disable sandboxing
    chrome_options.add_argument("start-maximized")  # Maximize the window

    # Initialize WebDriver using webdriver.Chrome directly
    driver = webdriver.Chrome(options=chrome_options)
    
    return driver

# Function to fetch the HTML content of a URL with explicit wait
def get_html_with_selenium(url, driver):
    driver.get(url)
    return driver.page_source

# Function to extract category links
def extract_categories(driver):
    html = get_html_with_selenium(CATEGORY_URL, driver)
    if not html:
        print("Failed to retrieve category page.")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    categories = []
    
    # Scrape all href links containing "/category/"
    for a_tag in soup.find_all('a', href=True):
        if '/category/' in a_tag['href']:
            category_name = a_tag.find('h5', class_="Vehicle_heading__kSdKB")
            if category_name:
                category_name = category_name.text.strip()
                category_url = BASE_URL + a_tag['href']  # Build the full URL
                categories.append((category_name, category_url))
    
    return categories

# Function to extract product URLs from a category page (links containing /all?)
def extract_product_urls_from_category(driver, category_url):
    html = get_html_with_selenium(category_url, driver)
    if not html:
        print(f"Failed to retrieve category page: {category_url}")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    product_urls = []
    
    # Scrape all href links containing "/all?" (Product URLs)
    for a_tag in soup.find_all('a', href=True):
        if '/all?' in a_tag['href']:
            product_name = a_tag.find('h5', class_="Vehicle_heading__kSdKB")
            product_url = BASE_URL + a_tag['href']  # Build the full URL
            product_urls.append((product_url, product_name.text.strip() if product_name else "null"))
    
    return product_urls

# Function to scroll and extract all item URLs from a product URL
def scroll_to_load_more(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Wait for new items to load

def extract_item_urls(driver, url):
    time.sleep(5)
    driver.get(url)

    item_urls = []
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        scroll_to_load_more(driver)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Extract product URLs
        product_cards = soup.find_all('div', class_='product_card_wrapper')
        for product_card in product_cards:
            a_tag = product_card.find('a', href=True)
            if a_tag:
                item_url = "https://www.oilco.com.bd" + a_tag['href']
                item_urls.append(item_url)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    return item_urls

# Function to extract product details from a product item page
def extract_product_details(driver, item_url):
    html = get_html_with_selenium(item_url, driver)
    if not html:
        print(f"Failed to retrieve product page: {item_url}")
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title
    title = soup.find('h1', class_="Product_product_title__zRwvR")
    title = title.text.strip() if title else "null"
    
    # Extract price
    price_container = soup.find('div', class_="Product_product_price_container__CkiRA")
    price = "null"
    if price_container:
        # Check for discounted price
        discounted_price = price_container.find('span', class_='Product_discounted_price__jUmxj')
        if discounted_price:
            price = discounted_price.text.strip()
        else:
            regular_price = price_container.find('span', class_='Product_product_price__JKSaf')
            if regular_price:
                price = regular_price.text.strip()
    
    # Extract stock status
    stock_status = "In Stock" if soup.find('div', class_='Product_out_of_stock_message__nEDCc') is None else "Out of Stock"
    
    # Use the same driver instance to extract Details Info from the same page
    combined_details = extract_description_and_at_a_glance(driver, item_url)

    # Return the combined result
    return {
        "Title": title,
        "Price": price,
        "Details Info": combined_details,
        "Stock": stock_status,
        "Url": item_url
    }

# Scrape Details Info from the existing page
def extract_description_and_at_a_glance(driver, url):
    html = get_html_with_selenium(url, driver)
    soup = BeautifulSoup(html, 'html.parser')

    # Initialize both variables
    description = ""
    at_a_glance = ""
    
    # Scrape Description (if available)
    description_section = soup.find('div', class_="Product_product_description_item__content__zau6u")
    if description_section:
        description_tag = description_section.find('p')
        description = description_tag.text.strip() if description_tag else ""

    # Scrape AT A GLANCE (if available)
    at_a_glance_section = soup.find_all('div', class_="Product_product_description_item__content__zau6u")
    for section in at_a_glance_section:
        # Look for the AT A GLANCE title within the section
        title_tag = section.find_previous('span', class_="Product_product_description_item__title__value__U7wRh")
        if title_tag and "AT A GLANCE" in title_tag.text.strip():
            at_a_glance_data = []
            # Extract all <p> tags under the AT A GLANCE section
            for p_tag in section.find_all('p'):
                at_a_glance_data.append(p_tag.text.strip())
            at_a_glance = "\n".join(at_a_glance_data)

    # Combine both sections into one result
    combined_details = f"DESCRIPTION:\n{description}\n\nAT A GLANCE:\n{at_a_glance}"
    
    return combined_details

# Save data to Excel
def save_to_excel(data):
    df = pd.DataFrame(data)
    df.to_excel(OUTPUT_FILE_PATH, index=False)

# Main function to orchestrate the scraping
def scrape_data():
    # Set up Selenium driver
    driver = get_driver()

    categories = extract_categories(driver)
    data = []

    print(f"Category Found: {len(categories)}")
    for category_index, (category_name, category_url) in enumerate(categories, start=1):
        print(f"Working on Category {category_index} out of {len(categories)}: {category_name}")
        product_urls_with_names = extract_product_urls_from_category(driver, category_url)
        
        print(f"Products Found: {len(product_urls_with_names)}")
        for product_index, (product_url, product_name) in enumerate(product_urls_with_names, start=1):
            print(f"Working on Product {product_index} of {len(product_urls_with_names)} ({product_name})")
            
            # Use the scroll-based function to extract item URLs
            item_urls = extract_item_urls(driver, product_url)
            
            # Remove duplicates by converting to a set and back to a list
            item_urls = list(set(item_urls))
            
            print(f"Item URLs Found: {len(item_urls)}")
            for item_index, item_url in tqdm(enumerate(item_urls, start=1), desc="Item scraping", total=len(item_urls)):
                product_details = extract_product_details(driver, item_url)
                if product_details:
                    data.append({
                        "Category": category_name,
                        "Product": product_name,  # Use the correct product name
                        "Title": product_details['Title'],
                        "Price": product_details['Price'],
                        "Details Info": product_details['Details Info'],
                        "Stock": product_details['Stock'],
                        "Url": product_details['Url']
                    })
            
            # Save data periodically after processing each item
            save_to_excel(data)
        
        print(f"Successfully Scraped {category_name}")
    
    # Final save after all categories and products are scraped
    save_to_excel(data)
    print("Data saved to Excel.")
    print("Scraping completed successfully.")

    # Close the driver after scraping
    driver.quit()

# Run the scraper
try:
    scrape_data()
except Exception as e:
    print(f"Unexpected error: {e}")
    save_to_excel([])  # Save empty data in case of unexpected termination
    print("Data saved to Excel due to unexpected termination.")

