from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from PIL import Image
import pandas as pd
import google.generativeai as genai
import os
import time

def setup_driver():
    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd('Network.setBlockedURLs', {'urls': ['*clientlib-devtool.js']})
    return driver

def handle_captcha(driver):
    try:
        driver.implicitly_wait(7)
        time.sleep(5)
        screenshot = driver.get_screenshot_as_png()
        with open("full_page_screenshot.png", "wb") as file:
            file.write(screenshot)

        image = Image.open("full_page_screenshot.png")
        width, height = image.size
        left, top = width * 0.50, height * 0.20
        right, bottom = left + width * 0.20, top + height * 0.28
        padding = 10
        region_image = image.crop((left - padding, top - padding, right + padding, bottom + padding))
        region_image.save('captcha_regionS.png')

        genai.configure(api_key="AIzaSyDCITTatIubdbdbHSlNWgXrNI-RghcogJc")
        def solve_captcha(image_path):
            model = genai.GenerativeModel("gemini-1.5-flash")
            image = Image.open(image_path)
            response = model.generate_content(["Perform the math operation in the picture and give output of the math operation only", image])
            return response.text.strip()

        captcha_solution = solve_captcha("captcha_regionS.png")
        captcha_input = driver.find_element(By.ID, "customCaptchaInput")
        captcha_input.send_keys(captcha_solution)
        
        submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "check")))
        submit_button.click()
        print(f"CAPTCHA solved: {captcha_solution}")
    except Exception as e:
        print(f"Error handling CAPTCHA: {e}")

def check_for_captcha(driver):
    try:
        captcha_element = driver.find_element(By.ID, "customCaptchaInput")
        if captcha_element.is_displayed():
            print("CAPTCHA detected. Solving CAPTCHA...")
            handle_captcha(driver)
            return True
        return False
    except:
        return False

def retry_click(driver, by_locator, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(by_locator))
            element.click()
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error clicking element: {e}")
    return False

def scrape_director_details(driver, uid):
    try:
        if check_for_captcha(driver):
            handle_captcha(driver)
        time.sleep(3)
        table = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "content")))
        rows = driver.find_elements(By.XPATH, "//tbody[@id='content']/tr")

        director_data = []
        for row in rows:
            columns = row.find_elements(By.TAG_NAME, "td")
            director_data.append([col.text for col in columns])

        df = pd.DataFrame(director_data, columns=["Sr. No", "DIN/PAN", "Name", "Designation", "Date of Appointment", "Cessation Date", "Signatory"])
        df['CIN'] = uid
        return df

    except Exception as e:
        print(f"Error scraping director details for {uid}: {e}")
        return pd.DataFrame()

def search_master_data(uid):
    driver = setup_driver()
    try:
        driver.get("https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html")
        search_box = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "masterdata-search-box")))
        search_box.clear()
        search_box.send_keys(uid)
        search_box.send_keys(Keys.RETURN)
        
        if check_for_captcha(driver):
            handle_captcha(driver)

        company_name_locator = (By.CSS_SELECTOR, "td.companyname")
        if retry_click(driver, company_name_locator):
            if check_for_captcha(driver):
                handle_captcha(driver)
            retry_click(driver, company_name_locator)

        director_button = (By.CSS_SELECTOR, "button.tablinks.directorData")
        retry_click(driver, director_button)

        df = scrape_director_details(driver, uid)
        return df

    except Exception as e:
        print(f"Error processing UID {uid}: {e}")
        return pd.DataFrame()
    finally:
        driver.quit()

# script.py

# ... (your existing imports and functions)

def retry_search_master_data(uid, retries=3):
    for attempt in range(retries):
        try:
            return search_master_data(uid)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for UID {uid}: {e}")
            time.sleep(2)  # Add a delay between retries
            if attempt == retries - 1:
                print(f"Max retries reached for UID {uid}. Skipping...")
                return pd.DataFrame()  # Return an empty dataframe if all retries fail

def process_cin_batch(cin_batch):
    results = []
    for cin in cin_batch:
        df = retry_search_master_data(cin)  # Use retry_search_master_data instead of search_master_data
        if not df.empty:
            results.append(df)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

# main_script.py