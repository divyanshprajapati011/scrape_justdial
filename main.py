# main.py
import streamlit as st
import pandas as pd
import time
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Justdial Scraper", layout="wide")

def scrape_justdial(business_type, city, limit=50):
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        search_url = f"https://www.justdial.com/{city}/{business_type}"
        page.goto(search_url, timeout=60000)

        time.sleep(5)  # wait for JS to load

        cards = page.query_selector_all("div.resultbox")

        for card in cards[:limit]:
            name = card.query_selector("a.resultbox_title").inner_text() if card.query_selector("a.resultbox_title") else ""
            phone = card.query_selector("a.tel").inner_text() if card.query_selector("a.tel") else ""
            address = card.query_selector("span.address-info").inner_text() if card.query_selector("span.address-info") else ""

            # ⭐ Review rating
            rating = ""
            rating_el = card.query_selector("span.green-box") or card.query_selector("span.rating")
            if rating_el:
                rating = rating_el.inner_text()

            data.append({
                "Name": name,
                "Phone": phone,
                "Address": address,
                "Rating": rating
            })

        browser.close()

    return pd.DataFrame(data)

st.title("🚀 Justdial Scraper")

business_type = st.text_input("🔍 Enter business type (e.g. top coaching)", "top coaching")
city = st.text_input("🏙️ Enter City", "Mumbai")
limit = st.number_input("Maximum results to fetch", 10, 200, 50)

if st.button("Start Scraping"):
    try:
        df = scrape_justdial(business_type, city, limit)
        if not df.empty:
            st.success(f"Scraped {len(df)} results ✅")
            st.dataframe(df)
            st.download_button("Download CSV", df.to_csv(index=False), "justdial_data.csv")
        else:
            st.warning("No data found. Try another search.")
    except Exception as e:
        st.error(f"Scraping failed: {e}")
