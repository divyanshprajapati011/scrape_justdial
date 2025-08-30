import asyncio
import sys
import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

# Windows asyncio fix (Python 3.12 issue)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ================== SCRAPER FUNCTION ==================
async def scrape_justdial(keyword, location, max_results=20):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = f"https://www.justdial.com/{location}/{keyword}"
        await page.goto(url, timeout=60000)

        # Scroll down for loading more results
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(2000)

        # Extract business details
        cards = await page.query_selector_all("//div[contains(@class, 'resultbox')]")

        for card in cards[:max_results]:
            try:
                name = await card.query_selector_eval("h2 a", "el => el.innerText") if await card.query_selector("h2 a") else ""
                addr = await card.query_selector_eval(".resultbox_address", "el => el.innerText") if await card.query_selector(".resultbox_address") else ""
                rating = await card.query_selector_eval(".resultbox_totalrate", "el => el.innerText") if await card.query_selector(".resultbox_totalrate") else ""
                phone = await card.query_selector_eval(".contact-info", "el => el.innerText") if await card.query_selector(".contact-info") else ""

                results.append({
                    "Business Name": name.strip(),
                    "Address": addr.strip(),
                    "Rating": rating.strip(),
                    "Phone": phone.strip()
                })
            except:
                continue

        await browser.close()

    return results


# ================== STREAMLIT UI ==================
st.set_page_config(page_title="Justdial Scraper (Demo)", layout="wide")

st.title("📊 Justdial Business Scraper (Educational Demo)")
st.markdown("Enter **Keyword** and **Location** to scrape Justdial business listings.")

keyword = st.text_input("🔑 Enter Keyword (e.g. Plumber, Restaurant)", "Plumber")
location = st.text_input("📍 Enter Location (e.g. Delhi, Mumbai)", "Delhi")
max_results = st.slider("📌 Max Results", 5, 50, 20)

if st.button("🚀 Start Scraping"):
    with st.spinner("Scraping data from Justdial..."):
        data = asyncio.run(scrape_justdial(keyword, location, max_results))

        if data:
            df = pd.DataFrame(data)
            st.success(f"✅ Scraped {len(df)} businesses!")
            st.dataframe(df)

            # Download buttons
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "justdial_data.csv", "text/csv")

            excel_file = "justdial_data.xlsx"
            df.to_excel(excel_file, index=False)
            with open(excel_file, "rb") as f:
                st.download_button("⬇️ Download Excel", f, file_name=excel_file)
        else:
            st.error("❌ No data found. Maybe Justdial blocked the request.")
