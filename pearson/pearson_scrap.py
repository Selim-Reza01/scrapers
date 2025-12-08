#!/usr/bin/env python
# coding: utf-8

# In[5]:


import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Input and output file paths
input_file = 'D:\\Study_Lab_Pro\\book_scraping\\pearson.xlsx'
output_file = 'D:\\Study_Lab_Pro\\book_scraping\\output_books.xlsx'

# Function to initialize the WebDriver
def init_driver():
    chrome_options = Options()
    # Initialize Chrome driver (Ensure chromedriver is installed and in your PATH)
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Function to fetch the book information from the search results page
def fetch_books_from_page(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver, 10)  # Use explicit wait for elements to be visible

    books = []
    
    try:
        # Wait until book items are visible
        items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'ais-Hits-item')))
    except Exception as e:
        return books
    
    for item in items:
        try:
            # Extract the title
            title = item.find_element(By.CLASS_NAME, 'programItem__title').text.strip()

            # Extract the edition
            edition = item.find_element(By.CLASS_NAME, 'programItem__edition').text.strip()

            # Extract the author
            author = item.find_element(By.CLASS_NAME, 'programItem__author').text.strip()

            # Extract the URL
            link_element = item.find_element(By.CSS_SELECTOR, '.programItem__title a')
            book_url = link_element.get_attribute('href')

            book = {
                'title': title,
                'edition': edition,
                'author': author,
                'url': book_url
            }
            books.append(book)
        except Exception as e:
            continue
    
    return books

# Function to visit each book page and fetch the title and publication year
def fetch_book_details(driver, book_url):
    try:
        driver.get(book_url)
        wait = WebDriverWait(driver, 10)

        # Fetch the publication year
        year_tag = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'minor')))
        year_text = year_tag.text.strip()
        year = year_text[-4:]  # Extract the last 4 digits as the year

        # Fetch the title
        title_tag = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-blueconic="product-title"]')))
        title = title_tag.text.strip()

        return title, year
    except Exception as e:
        return None, None

# Function to check if there's a next page and get its URL
def get_next_page_url(driver):
    try:
        next_page = driver.find_element(By.CLASS_NAME, 'ais-Pagination-link--nextPage')
        return next_page.get_attribute('href') if next_page else None
    except:
        return None

# Function to process all pages for a given category
def process_category_pages(driver, url, category):
    all_books = []
    while url:
        print(f"Fetching books from {category} {url}")
        books = fetch_books_from_page(driver, url)
        if books:
            all_books.extend(books)
        
        # Check for the next page
        url = get_next_page_url(driver)
    return all_books

# Function to process the input Excel file
def process_input_file(input_file, output_file):
    driver = init_driver()

    # Load the input Excel file
    df = pd.read_excel(input_file)

    # Create or load the output Excel file
    if os.path.exists(output_file):
        output_df = pd.read_excel(output_file)
    else:
        output_df = pd.DataFrame(columns=['Category', 'Title', 'Author', 'Edition', 'Year', 'URL'])

    # Track the number of books per category
    category_book_count = {}

    for index, row in df.iterrows():
        category = row['Category']
        url = row['URL']
        
        # Process the category and get all books from paginated results
        books = process_category_pages(driver, url, category)
        if books:
            for book in books:
                # Visit each book's page to get the title and publication year
                title, year = fetch_book_details(driver, book['url'])

                # If title and year are found and it's not a duplicate, add it to the output
                if title and year:
                    if not output_df[(output_df['Title'] == title) & (output_df['URL'] == book['url'])].empty:
                        continue
                    output_df = pd.concat([output_df, pd.DataFrame([{
                        'Category': category,
                        'Title': title,
                        'Author': book['author'],
                        'Edition': book['edition'],
                        'Year': year,
                        'URL': book['url']
                    }])], ignore_index=True)

            # Update category book count
            category_book_count[category] = len(books)
    
    # Save the output DataFrame to the Excel file
    output_df.to_excel(output_file, index=False)

    # Print the result
    for category, count in category_book_count.items():
        print(f"Category: {category}, Books found: {count}")

    print(f"Total books found: {len(output_df)}")
    driver.quit()

# Call the process function
process_input_file(input_file, output_file)

