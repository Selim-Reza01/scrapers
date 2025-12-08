#!/usr/bin/env python
# coding: utf-8

# In[7]:


import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

# Define the input and output file paths
input_file = 'D:\\Study_Lab_Pro\\book_scraping\\macmillian.xlsx'
output_file = 'D:\\Study_Lab_Pro\\book_scrapings.xlsx'

# Function to extract book details from a given book page URL
def extract_book_details(book_url):
    try:
        response = requests.get(book_url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title = soup.find('h1', {'class': 'h-size3'}).text.strip() if soup.find('h1', {'class': 'h-size3'}) else 'N/A'
        
        # Extract author(s), now correctly handling the specific HTML structure
        author = 'N/A'
        author_element = soup.find('p', {'class': 'small text-muted author'})
        if author_element:
            author_span = author_element.find('span')
            if author_span:
                author_text = author_span.text.strip()
                if 'Author(s):' in author_text:
                    author = author_text.split('Author(s):')[-1].strip()

        # Extract edition and year
        edition_element = soup.find_all('p', {'class': 'edition'})
        edition, edition_year = 'N/A', 'N/A'
        if edition_element:
            # Try to find edition and year
            for elem in edition_element:
                if 'Edition' in elem.text:
                    edition = elem.text.split('Edition')[0].strip()
                if '©' in elem.text:
                    edition_year = elem.text.split('©')[-1].strip()
        
        return title, author, edition_year, edition, book_url
    except Exception as e:
        print(f"Error while extracting data from {book_url}: {e}")
        return 'N/A', 'N/A', 'N/A', 'N/A', book_url

# Function to process each discipline's URL and collect book links
def collect_books_for_discipline(discipline, url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all book links on the page
        book_links = soup.find_all('a', {'class': 'btn-search-icbutton'})
        book_urls = ['https://www.macmillanlearning.com' + link['href'] for link in book_links if '#authors' not in link['href']]

        # Remove duplicates by converting to a set
        book_urls = list(set(book_urls))

        books = []
        for book_url in book_urls:
            title, author, year, edition, book_url = extract_book_details(book_url)
            books.append([discipline, title, author, year, edition, book_url])

        return books
    except Exception as e:
        print(f"Error while processing discipline {discipline}: {e}")
        return []

# Load the input Excel file
input_data = pd.read_excel(input_file)

# Create a list to hold all the books data
all_books = []

# Process each discipline and URL
for index, row in input_data.iterrows():
    discipline = row['disciplines']
    url = row['url']
    print(f"Processing discipline: {discipline}")

    # Collect books for the discipline
    books = collect_books_for_discipline(discipline, url)
    print(f"Found {len(books)} books for discipline: {discipline}")
    
    # Add the collected books to the master list
    all_books.extend(books)

# Convert the collected books data into a DataFrame
books_df = pd.DataFrame(all_books, columns=['Discipline', 'Title', 'Author', 'Year', 'Edition', 'Url'])

# Save the data to an output Excel file
books_df.to_excel(output_file, index=False)

# Show the total number of books found
print(f"Total books found: {len(all_books)}")

