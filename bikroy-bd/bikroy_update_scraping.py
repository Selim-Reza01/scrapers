#!/usr/bin/env python
# coding: utf-8

# In[6]:


from bs4 import BeautifulSoup
import requests
import pandas as pd
import os

# Base URL of the page to scrape
base_url = "https://bikroy.com/en/ads/bangladesh/cars?sort=date&order=desc&buy_now=0&urgent=0&page="

# Output location path where the data will be saved
output_location = "D:\\Car x Parts\\Scripts\\bikrpy_car_data(401-468).csv"  # Update the path as needed

# Function to extract car details from each car's individual page
def extract_car_details(car_url):
    # Fetch the car details page
    car_response = requests.get(car_url)
    car_soup = BeautifulSoup(car_response.content, 'html.parser')

    # Extracting each attribute using class selectors
    car_details = {
        'Brand': car_soup.select_one('.label--3oVZK:contains("Brand:") ~ .value--1lKHt span').text if car_soup.select_one('.label--3oVZK:contains("Brand:") ~ .value--1lKHt span') else '',
        'Model': car_soup.select_one('.label--3oVZK:contains("Model:") ~ .value--1lKHt span').text if car_soup.select_one('.label--3oVZK:contains("Model:") ~ .value--1lKHt span') else '',
        'Trim / Edition': car_soup.select_one('.label--3oVZK:contains("Trim / Edition:") ~ .value--1lKHt').text if car_soup.select_one('.label--3oVZK:contains("Trim / Edition:") ~ .value--1lKHt') else '',
        'Year of Manufacture': car_soup.select_one('.label--3oVZK:contains("Year of Manufacture:") ~ .value--1lKHt span').text if car_soup.select_one('.label--3oVZK:contains("Year of Manufacture:") ~ .value--1lKHt span') else '',
        'Registration year': car_soup.select_one('.label--3oVZK:contains("Registration year:") ~ .value--1lKHt').text if car_soup.select_one('.label--3oVZK:contains("Registration year:") ~ .value--1lKHt') else '',
        'Condition': car_soup.select_one('.label--3oVZK:contains("Condition:") ~ .value--1lKHt span').text if car_soup.select_one('.label--3oVZK:contains("Condition:") ~ .value--1lKHt span') else '',
        'Transmission': car_soup.select_one('.label--3oVZK:contains("Transmission:") ~ .value--1lKHt').text if car_soup.select_one('.label--3oVZK:contains("Transmission:") ~ .value--1lKHt') else '',
        'Body type': car_soup.select_one('.label--3oVZK:contains("Body type:") ~ .value--1lKHt span').text if car_soup.select_one('.label--3oVZK:contains("Body type:") ~ .value--1lKHt span') else '',
        'Fuel type': car_soup.select_one('.label--3oVZK:contains("Fuel type:") ~ .value--1lKHt').text if car_soup.select_one('.label--3oVZK:contains("Fuel type:") ~ .value--1lKHt') else '',
        'Engine capacity': car_soup.select_one('.label--3oVZK:contains("Engine capacity:") ~ .value--1lKHt').text if car_soup.select_one('.label--3oVZK:contains("Engine capacity:") ~ .value--1lKHt') else '',
        'Kilometers run': car_soup.select_one('.label--3oVZK:contains("Kilometers run:") ~ .value--1lKHt').text if car_soup.select_one('.label--3oVZK:contains("Kilometers run:") ~ .value--1lKHt') else '',
        'Description': ' '.join([p.text for p in car_soup.select('.description--1nRbz p')]) if car_soup.select('.description--1nRbz p') else '',
        'URL': car_url
    }
    return car_details

# Function to extract car URLs from the main listing page
def extract_car_urls(soup):
    car_urls = []

    # Extracting URLs from <ul> list that contains all cars
    car_list = soup.find('ul', class_='list--3NxGO')
    if car_list:
        cars = car_list.find_all('a', class_='card-link--3ssYv gtm-ad-item')
        for car in cars:
            car_url = car['href']
            full_car_url = "https://bikroy.com" + car_url
            car_urls.append(full_car_url)

    return car_urls

# Function to scrape cars within a specified range of pages
def scrape_bikroy_cars(start_page, end_page):
    all_car_data = []

    for page in range(start_page, end_page + 1):
        # Update the URL to navigate pages
        page_url = f"{base_url}{page}"
        response = requests.get(page_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract car URLs from the listing page
        car_urls = extract_car_urls(soup)

        # Extract details for each car
        for car_url in car_urls:
            car_details = extract_car_details(car_url)
            all_car_data.append(car_details)

        print(f"Scraped page {page} with {len(car_urls)} cars.")

    # Saving data to a CSV file
    df = pd.DataFrame(all_car_data)
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_location), exist_ok=True)
    df.to_csv(output_location, index=False, encoding='utf-8-sig')
    print(f"Data saved to {output_location}")
    print(f"Total cars data extracted: {len(all_car_data)}")

# Specify the range of pages you want to scrape
start_page = 401  # Starting page number
end_page = 468    # Ending page number
scrape_bikroy_cars(start_page, end_page)

