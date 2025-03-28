import logging
import os
import subprocess

import requests
from dotenv import load_dotenv
from flask import Flask, Response, make_response, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def install_chrome():
    chrome_dir = "/tmp/chrome-linux64"
    chrome_zip = "/tmp/chrome-linux64.zip"
    chrome_binary_path = os.path.join(
        chrome_dir, "chrome-linux64", "chrome"
    )  # Corrected path

    # Ensure unzip is installed
    if (
        subprocess.run("command -v unzip", shell=True, capture_output=True).returncode
        != 0
    ):
        raise RuntimeError(
            "Unzip command not found. Install 'unzip' before proceeding."
        )

    os.makedirs(chrome_dir, exist_ok=True)

    subprocess.run(
        f"wget -q -O {chrome_zip} https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.111/linux64/chrome-linux64.zip && "
        f"unzip -o {chrome_zip} -d {chrome_dir} && "
        f"chmod +x {chrome_binary_path} && "
        f"rm -rf {chrome_zip}",
        shell=True,
        check=True,
    )

    if not os.path.exists(chrome_binary_path):
        raise FileNotFoundError(
            "Chrome binary not found. Ensure it's downloaded correctly."
        )

    return chrome_binary_path


def install_chromedriver():
    chromedriver_dir = "/tmp/chromedriver"
    chromedriver_path = os.path.join(chromedriver_dir, "chromedriver")

    os.makedirs(chromedriver_dir, exist_ok=True)

    subprocess.run(
        f"wget -q -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.111/linux64/chromedriver-linux64.zip && "
        f"unzip -o /tmp/chromedriver.zip -d {chromedriver_dir} && "
        f"chmod +x {chromedriver_path} && "
        f"rm -rf /tmp/chromedriver.zip",
        shell=True,
        check=True,
    )

    if not os.path.exists(chromedriver_path):
        raise FileNotFoundError(
            "ChromeDriver binary not found. Ensure it's downloaded correctly."
        )

    return chromedriver_path


# Install Chrome & ChromeDriver
chrome_binary = install_chrome()
chromedriver_binary = install_chromedriver()

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
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    if os.path.exists(chrome_binary):
        options.binary_location = chrome_binary
    else:
        logging.error("Chrome binary not found!")

    try:
        service = Service(chromedriver_binary)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize Chrome WebDriver: {e}")
        return None


def login_to_bing(driver):
    logging.info("Logging into Bing...")
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

    if not prompt:
        logging.warning("Empty prompt received.")
        response["message"] = "Prompt cannot be empty"
        return make_response(response)

    driver = None
    try:
        driver = init_browser()
        if not driver:
            raise RuntimeError("WebDriver initialization failed.")

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
            if img.get_attribute("src") and img.get_attribute("src").startswith("http")
        ]

        logging.info(f"Generated image URLs: {pict_url}")
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
        if driver:
            driver.quit()


@app.route("/proxy/<path:image_url>")
def proxy_image(image_url):
    response = requests.get(image_url)
    return Response(response.content, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
