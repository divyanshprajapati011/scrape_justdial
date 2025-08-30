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
