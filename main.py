import asyncio
import sys
import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

import asyncio
import sys
import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def scrape_justdial(keyword, location, max_results=20):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Debug mode: False so you can see page
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                       "Chrome/112.0.0.0 Safari/537.36")

        page = await context.new_page()
        url = f"https://www.justdial.com/{location}/{keyword}"
        await page.goto(url, timeout=60000)

        # ✅ Wait for result boxes to load
        try:
            await page.wait_for_selector("div.resultbox", timeout=15000)
        except:
            return []  # If no results load

        # Scroll to load more
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(2000)

        # Extract business cards
        cards = await page.query_selector_all("div.resultbox")

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
