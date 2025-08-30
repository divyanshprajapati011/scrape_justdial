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

        search_url = f"https://www.justdial.com/{city}/{business_type}"
        page.goto(search_url, timeout=60000)

        # ✅ Try multiple selectors (fallback handling)
        selectors = ["div#bcard", "div.cntanr", "div.jcn", "div.resultbox", "div.store-details"]

        found_selector = None
        for sel in selectors:
            try:
                page.wait_for_selector(sel, timeout=15000)
                found_selector = sel
                break
            except:
                continue

        if not found_selector:
            return pd.DataFrame([])  # No data found

        # ✅ Scroll & collect
        while len(data) < limit:
            page.mouse.wheel(0, 3000)
            time.sleep(2)

            cards = page.query_selector_all(found_selector)
            for card in cards[len(data):limit]:
                name = card.query_selector("a").inner_text().strip() if card.query_selector("a") else ""
                phone = card.query_selector("a.tel") or card.query_selector("p.contact-info")
                phone = phone.inner_text().strip() if phone else ""
                address = card.query_selector("span.cont_fl_addr") or card.query_selector("span.address-info")
                address = address.inner_text().strip() if address else ""
                rating = card.query_selector("span.green-box")
                rating = rating.inner_text().strip() if rating else ""
                reviews = card.query_selector("span.rt_count")
                reviews = reviews.inner_text().strip("() ") if reviews else ""

                data.append({
                    "Name": name,
                    "Phone": phone,
                    "Address": address,
                    "Rating": rating,
                    "Reviews": reviews
                })

            # Break if no new data
            if len(cards) >= limit:
                break

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

