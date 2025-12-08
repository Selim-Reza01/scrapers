#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

# File paths
input_file = r"D:\Study_Lab_Pro\Publisher Scraping\Willey\willey.xlsx"
output_folder = r"D:\Study_Lab_Pro\Publisher Scraping\Willey"
output_file = os.path.join(output_folder, "willey_books_psychology.xlsx")

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# Initialize output data
output_data = []

# Function to get headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

# Read the input Excel file
data = pd.read_excel(input_file)

current_field = None

# Iterate over rows in the input file
for index, row in data.iterrows():
    field = row['Field']
    subject = row['Subject']
    base_url = row['Url']
    total_pages = int(row['Page'])

    # Print the current field being processed only if it's new
    if current_field != field:
        if current_field is not None:
            print("------------------------------------")
        print(f"\nProcessing Field - {field}")
        current_field = field

    books_scraped = 0

    for page in range(1, total_pages + 1):
        # Construct the URL for each page
        url = f"{base_url}?page={page}"
        try:
            # Wait before opening each page URL to avoid rate limiting
            time.sleep(20)

            # Use Requests to get the page
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            
            # Parse the HTML content with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all book cards on the page
            book_cards = soup.find_all('div', class_='product-card')

            # Extract book details from each card
            for card in book_cards:
                book_url_tag = card.find('a', href=True)
                title_tag = card.find('h3')
                edition_tag = card.find('div', class_='product-dt')
                author_tag = card.find('div', class_='product-authors')

                if book_url_tag and title_tag and edition_tag and author_tag:
                    book_url = book_url_tag['href'] if book_url_tag['href'].startswith('https://') else f"https://www.wiley.com{book_url_tag['href']}"
                    title = title_tag.get_text(strip=True)
                    edition = edition_tag.get_text(strip=True)
                    author = author_tag.get_text(strip=True)
                    
                    # Extract year from edition tag if available
                    year = edition.split('|')[-1].strip() if '|' in edition else 'Year not found'

                    # Set default publisher value
                    publisher = 'Wiley'

                    # Append book details to output data
                    book_details = {
                        'Field': field,
                        'Subject': subject,
                        'Title': title,
                        'Author': author,
                        'Edition': edition,
                        'Year': year,
                        'Publisher': publisher,
                        'Book Url': book_url            
                    }
                    output_data.append(book_details)
                    books_scraped += 1

            # Pause to avoid rate limiting
            time.sleep(20)

        except Exception as e:
            print(f"Failed to retrieve page {page} for URL: {url}. Error: {e}")

    print(f"{subject} Scraped: {books_scraped}")

# Save the output to an Excel file
output_df = pd.DataFrame(output_data)
output_df.to_excel(output_file, index=False)
print("\nScraping completed!!")

