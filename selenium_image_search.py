from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import configparser
import urllib.parse
import os
import time
import requests
from urllib.parse import parse_qs, urlparse
from tqdm import tqdm
from colorama import init, Fore, Style
import datetime

# Initialize colorama
init()

def print_status(message, status="info"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if status == "success":
        color = Fore.GREEN
    elif status == "error":
        color = Fore.RED
    elif status == "warning":
        color = Fore.YELLOW
    else:
        color = Fore.CYAN
    
    print(f"{Fore.WHITE}[{timestamp}] {color}{message}{Style.RESET_ALL}")

def decode_image_url(imgres_url):
    parsed = urlparse(imgres_url)
    params = parse_qs(parsed.query)
    if 'imgurl' in params:
        return urllib.parse.unquote(params['imgurl'][0])
    return None

def download_image(url, output_dir, filename):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print_status(f"Error downloading image: {e}", "error")
    return False

def main():
    print_status("Starting Google Images Downloader", "info")
    print_status("=" * 50, "info")
    
    # Read configuration
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    
    query_string = config['image_search']['query_string']
    limit = int(config['image_search']['limit'])
    output_dir = config['image_search']['output_dir']
    
    print_status(f"Search Query: {query_string}", "info")
    print_status(f"Download Limit: {limit} images", "info")
    print_status(f"Output Directory: {output_dir}", "info")
    print_status("=" * 50, "info")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print_status(f"Created output directory: {output_dir}", "success")
    
    print_status("Initializing Chrome WebDriver...", "info")
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        # Navigate to Google Images
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query_string)}&tbm=isch"
        print_status(f"Navigating to: {search_url}", "info")
        driver.get(search_url)
        
        # Wait for the search div to load
        print_status("Waiting for images to load...", "info")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "search"))
        )
        
        # Find all image elements within the search div
        image_elements = driver.find_elements(By.CSS_SELECTOR, "#search img")
        total_images = len(image_elements)
        print_status(f"Found {total_images} images on the page", "info")
        
        # Create progress bar
        pbar = tqdm(total=min(limit, total_images), 
                   desc="Downloading images",
                   unit="image",
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
        
        downloaded_count = 0
        failed_count = 0
        
        for img in image_elements:
            if downloaded_count >= limit:
                break
                
            try:
                # Find the parent anchor tag
                parent_link = img.find_element(By.XPATH, "./ancestor::a")
                
                # Hover over the image to trigger the preview
                ActionChains(driver).move_to_element(img).perform()
                time.sleep(1)  # Wait for hover effect
                
                # Get the href attribute
                href = parent_link.get_attribute('href')
                if href and 'imgres' in href:
                    image_url = decode_image_url(href)
                    if image_url:
                        # Generate filename
                        filename = f"image_{downloaded_count + 1}.jpg"
                        if download_image(image_url, output_dir, filename):
                            pbar.update(1)
                            downloaded_count += 1
                        else:
                            failed_count += 1
            except Exception as e:
                print_status(f"Error processing image: {e}", "error")
                failed_count += 1
                continue
        
        pbar.close()
        print_status("=" * 50, "info")
        print_status(f"Download completed!", "success")
        print_status(f"Successfully downloaded: {downloaded_count} images", "success")
        if failed_count > 0:
            print_status(f"Failed to download: {failed_count} images", "warning")
        print_status(f"Total images processed: {downloaded_count + failed_count}", "info")
        print_status("=" * 50, "info")
                
    finally:
        print_status("Closing browser...", "info")
        driver.quit()

if __name__ == '__main__':
    main() 