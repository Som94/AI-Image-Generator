import logging
import os

import requests
from dotenv import load_dotenv
from flask import Flask, Response, make_response, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

if not USERNAME or not PASSWORD:
    logging.error("Missing environment variables: USERNAME and/or PASSWORD.")
    raise ValueError("USERNAME and PASSWORD must be set as environment variables.")

app = Flask(__name__)


def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    ########## for prod ##########
    # chrome_binary_path = "/usr/bin/google-chrome-stable"
    chrome_binary_path = "/usr/bin/google-chrome"
    if os.path.exists(chrome_binary_path):
        print("Chrome exists....123")
        options.binary_location = chrome_binary_path
    # =====================================
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def login_to_bing(driver):
    try:
        driver.get("https://login.live.com/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "i0116"))
        ).send_keys(USERNAME + Keys.RETURN)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "i0118"))
        ).send_keys(PASSWORD + Keys.RETURN)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "idBtn_Back"))
            ).click()
        except Exception:
            logging.info("No 'Stay signed in' prompt detected.")
    except Exception as e:
        logging.error(f"Login to Bing failed: {e}")
        raise


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", pict_url=None)


@app.route("/generate", methods=["POST"])
def generate_image():
    response = {"status": False, "message": "", "data": []}
    prompt = request.form.get("desc", "").strip()
    print("prompt ====> ")
    print(prompt)
    if not prompt:
        logging.warning("Empty prompt received.")
        response["message"] = "Prompt cannot be empty"
        return make_response(response)

    driver = init_browser()
    try:
        login_to_bing(driver)

        driver.get("https://www.bing.com/create")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "sb_form_q"))
        )

        search_box = driver.find_element(By.ID, "sb_form_q")
        search_box.send_keys(prompt + Keys.RETURN)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.mimg"))
        )

        images = driver.find_elements(By.CSS_SELECTOR, "img.mimg")[:4]

        pict_url = [
            img.get_attribute("src")
            for img in images
            if img.get_attribute("src").startswith("http")
        ]

        logging.info(f"Generated image URL: {pict_url}")
        if pict_url:
            response["status"] = True
            response["message"] = "Image generated successfully!"
            response["data"] = pict_url
        return make_response(response)

    except Exception as e:
        logging.error(f"Image generation failed: {e}")
        response["message"] = "Image generation failed"
        return make_response(response)

    finally:
        driver.quit()


def proxy_image(image_url):
    response = requests.get(image_url)
    return Response(response.content, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
