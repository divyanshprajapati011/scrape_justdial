import requests, re, time
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_justdial(query, city="Bhopal", limit=50):
    """Scrape Justdial search results"""
    base_url = f"https://www.justdial.com/{city}/{query.replace(' ','-')}"
    rows = []
    fetched = 0
    page = 1

    while fetched < limit:
        url = f"{base_url}/page-{page}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("div.jbbg")  # each business card

        if not listings:
            break

        for item in listings:
            if fetched >= limit:
                break

            name = item.select_one("a.ln24").get_text(strip=True) if item.select_one("a.ln24") else ""
            phone = ""
            phone_tag = item.select_one("p.contact-info span")
            if phone_tag:
                phone = phone_tag.get_text(strip=True)

            address = item.select_one("p.address-info").get_text(" ", strip=True) if item.select_one("p.address-info") else ""
            rating = item.select_one("span.green-box").get_text(strip=True) if item.select_one("span.green-box") else ""
            reviews = item.select_one("span.rt_count").get_text(strip=True) if item.select_one("span.rt_count") else ""
            category = item.select_one("span.category-info").get_text(strip=True) if item.select_one("span.category-info") else ""

            rows.append({
                "Business Name": name,
                "Address": address,
                "Phone": phone,
                "Rating": rating,
                "Reviews": reviews,
                "Category": category,
                "Source Link": url
            })

            fetched += 1

        page += 1
        time.sleep(2)  # polite scraping delay

    return pd.DataFrame(rows)
