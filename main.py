# main.py
import streamlit as st
import pandas as pd
import time
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Justdial Scraper", layout="wide")

def scrape_justdial(business_type, city, limit=50):
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context()
        page = context.new_page()

        # 🔗 Build search URL
        search_url = f"https://www.justdial.com/{city}/{business_type}"
        page.goto(search_url, timeout=60000)
        time.sleep(5)  # wait for JS

        # ✅ Correct selector for business cards
        cards = page.query_selector_all("div#bcard")

        for card in cards[:limit]:
            name = card.query_selector("h2 a") .inner_text().strip() if card.query_selector("h2 a") else ""
            phone = card.query_selector("a.tel") .inner_text().strip() if card.query_selector("a.tel") else ""
            address = card.query_selector("span.cont_fl_addr") .inner_text().strip() if card.query_selector("span.cont_fl_addr") else ""

            # ⭐ Rating
            rating = card.query_selector("span.green-box").inner_text().strip() if card.query_selector("span.green-box") else ""

            # 📝 No. of Reviews
            reviews = card.query_selector("span.rt_count").inner_text().strip("() ") if card.query_selector("span.rt_count") else ""

            data.append({
                "Name": name,
                "Phone": phone,
                "Address": address,
                "Rating": rating,
                "Reviews": reviews
            })

        browser.close()

    return pd.DataFrame(data)

# ================== Streamlit UI ==================
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
            st.download_button("📥 Download CSV", df.to_csv(index=False), "justdial_data.csv")
        else:
            st.warning("⚠️ No data found. Try another keyword or city.")
    except Exception as e:
        st.error(f"❌ Scraping failed: {e}")
