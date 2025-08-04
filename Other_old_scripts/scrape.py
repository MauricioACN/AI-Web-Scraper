import time
import requests
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


load_dotenv()

SBR_WEBDRIVER = os.getenv("SBR_WEBDRIVER")


def scrape_website(website):
    print("Connecting to Scraping Browser...")
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, "goog", "chrome")
    with Remote(sbr_connection, options=ChromeOptions()) as driver:
        driver.get(website)
        # print("Waiting captcha to solve...")
        # solve_res = driver.execute(
        #     "executeCdpCommand",
        #     {
        #         "cmd": "Captcha.waitForSolve",
        #         "params": {"detectTimeout": 10000},
        #     },
        # )
        # print("Captcha solve status:", solve_res["value"]["status"])
        # print("Navigated! Scraping page content...")
        html = driver.page_source
        return html


def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""


def clean_body_content(body_content):
    soup = BeautifulSoup(body_content, "html.parser")

    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()

    # Get text or further process the content
    cleaned_content = soup.get_text(separator="\n")
    cleaned_content = "\n".join(
        line.strip() for line in cleaned_content.splitlines() if line.strip()
    )

    return cleaned_content


def split_dom_content(dom_content, max_length=6000):
    return [
        dom_content[i: i + max_length] for i in range(0, len(dom_content), max_length)
    ]


BASE_HEADERS = {
    "origin": "https://www.canadiantire.ca",
    "referer": "https://www.canadiantire.ca/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "bv-bfd-token": "15041_3_0,odp_site,en_CA",
    "accept": "*/*"
}


def fetch_reviews(product_id, limit=30):
    """Obtiene todas las reseñas paginadas de un producto."""
    url = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/cv2/resources/data/reviews.json"
    all_reviews = []
    offset = 0

    while True:
        params = {
            "resource": "reviews",
            "action": "REVIEWS_N_STATS",
            "filter": f"productid:eq:{product_id}",
            "filter_reviews": "contentlocale:eq:en*,fr*,en_CA,en_CA",
            "filter": "isratingsonly:eq:false",
            "include": "authors,products,comments",
            "filteredstats": "reviews",
            "Stats": "Reviews",
            "limit": limit,
            "offset": offset,
            "limit_comments": 3,
            "sort": "submissiontime:desc",
            "apiversion": "5.5",
            "displaycode": "15041_3_0-en_ca"
        }

        resp = requests.get(url, headers=BASE_HEADERS, params=params)
        data = resp.json()
        reviews = data.get("Results", [])

        if not reviews:
            break

        all_reviews.extend(reviews)
        offset += limit
        print(f"Fetched {len(all_reviews)} reviews...")
        time.sleep(0.5)  # Evitar bloqueo por demasiadas requests

    return all_reviews


def fetch_highlights(product_id):
    """Obtiene los temas destacados con ejemplos de reseñas."""
    url = f"https://rh.nexus.bazaarvoice.com/highlights/v3/1/canadiantire-ca/{product_id}"
    resp = requests.get(url, headers=BASE_HEADERS)
    return resp.json().get("subjects", {})


def fetch_features(product_id):
    """Obtiene las características detectadas del producto."""
    url = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/sentiments/resources/sentiment/v1/features"
    params = {
        "productId": product_id,
        "language": "en"
    }
    resp = requests.get(url, headers=BASE_HEADERS, params=params)
    return resp.json().get("response", {}).get("features", [])
