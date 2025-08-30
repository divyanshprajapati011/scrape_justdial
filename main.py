import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib, io, requests, re, time

# ================== APP CONFIG ==================
st.set_page_config(page_title="Maps Scraper 🚀", layout="wide")

# ================== SESSION ROUTER ==================
if "page" not in st.session_state:
    st.session_state.page = "home"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

def go_to(p):
    st.session_state.page = p

# ================== DB ==================
def get_connection():
    return psycopg2.connect(
        user="postgres.jsjlthhnrtwjcyxowpza",
        password="@Deep7067",
        host="aws-1-ap-south-1.pooler.supabase.com",
        port="6543",
        dbname="postgres",
        sslmode="require",
    )

# ================== SECURITY HELPERS ==================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    db = get_connection()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, email) VALUES (%s,%s,%s)",
            (username, hash_password(password), email),
        )
        db.commit()
        return True
    except Exception:
        return False
    finally:
        cur.close(); db.close()

def login_user(username, password):
    db = get_connection()
    cur = db.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, hash_password(password)),
    )
    user = cur.fetchone()
    cur.close(); db.close()
    return user

# ================== SCRAPER (SERPAPI + EMAIL LOOKUP) ==================
SERPAPI_KEY = "ea60d7830fc08072d9ab7f9109e10f1150c042719c20e7d8d9b9c6a25e3afe09"

EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"\+?\d[\d\-\(\) ]{8,}\d"

def extract_email_phone(website_url):
    """website से email और phone extract करने का helper"""
    try:
        resp = requests.get(website_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        text = resp.text
        emails = re.findall(EMAIL_REGEX, text)
        phones = re.findall(PHONE_REGEX, text)

        email = emails[0] if emails else ""
        phone = phones[0] if phones else ""
        return email, phone
    except Exception:
        return "", ""


import requests, re, time
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

from playwright.sync_api import sync_playwright
import pandas as pd
import time
from playwright.sync_api import sync_playwright
import pandas as pd
from bs4 import BeautifulSoup
import time

def scrape_justdial(query, city="Bhopal", limit=50):
    rows = []
    fetched = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        base_url = f"https://www.justdial.com/{city}/{query.replace(' ','-')}"
        page.goto(base_url, timeout=60000)
        time.sleep(5)  # wait for dynamic load

        while fetched < limit:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            listings = soup.select("div.cjrx1")  # ✅ updated selector
            if not listings:
                break

            for item in listings:
                if fetched >= limit:
                    break

                name = item.select_one("span.jcn a")
                name = name.get_text(strip=True) if name else ""

                address = item.select_one("span.cont_fl_addr")
                address = address.get_text(strip=True) if address else ""

                rating = item.select_one("span.green-box")
                rating = rating.get_text(strip=True) if rating else ""

                reviews = item.select_one("span.rt_count")
                reviews = reviews.get_text(strip=True) if reviews else ""

                rows.append({
                    "Business Name": name,
                    "Address": address,
                    "Rating": rating,
                    "Reviews": reviews,
                    "Source Link": base_url
                })
                fetched += 1

            # next page
            next_btn = page.query_selector("a#nextbtn")
            if not next_btn:
                break
            next_btn.click()
            time.sleep(3)

        browser.close()

    return pd.DataFrame(rows)

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buf.seek(0)
    return buf.getvalue()

# ================== TOPBAR ==================
def topbar():
    cols = st.columns([1, 3])
    with cols[0]:
        if st.button("🏠 Home"):
            go_to("home")
    with cols[1]:
        if st.session_state.logged_in and st.session_state.user:
            u = st.session_state.user["username"]
            st.info(f"Logged in as *{u}*")
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                go_to("home")

# ================== PAGES ==================
def page_home():
    st.title("Welcome to Maps Scraper 🚀")
    st.write("Signup → Login → Scrape Google Maps data")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔑 Login", use_container_width=True):
            go_to("login")
    with c2:
        if st.button("📝 Signup", use_container_width=True):
            go_to("signup")
    if st.session_state.logged_in:
        st.success("✅ You are logged in")
        if st.button("➡ Open Scraper", use_container_width=True):
            go_to("scraper")

def page_login():
    st.title("Login 🔑")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.success("✅ Login successful! Redirecting to Scraper...")
            go_to("scraper")
        else:
            st.error("❌ Invalid credentials")
    st.button("⬅ Back", on_click=lambda: go_to("home"))

def page_signup():
    st.title("Signup 📝")
    new_user = st.text_input("Choose Username")
    new_email = st.text_input("Email")
    new_pass = st.text_input("Choose Password", type="password")
    if st.button("Create Account"):
        if new_user and new_email and new_pass:
            if register_user(new_user, new_pass, new_email):
                st.success("Signup successful! Please login now.")
                go_to("login")
            else:
                st.error("❌ User already exists or DB error.")
        else:
            st.warning("⚠ Please fill all fields.")
    st.button("⬅ Back", on_click=lambda: go_to("home"))

def page_scraper():
    if not st.session_state.logged_in or not st.session_state.user:
        st.error("⚠ Please login first")
        if st.button("Go to Login"):
            go_to("login")
        return

    st.title("🚀 Justdial Scraper ")
    query = st.text_input("🔎 Enter your query", "Top Coaching Classes")
    city = st.text_input("🏙 Enter City", "Bhopal")
    max_results = st.number_input("Maximum results to fetch", min_value=5, max_value=200, value=50, step=5)

    start_btn = st.button("Start Scraping")

    if start_btn:
        with st.spinner("⏳ Fetching data from Justdial..."):
            try:
                df = scrape_justdial(query, "Bhopal", int(max_results))
                st.success(f"✅ Found {len(df)} results.")
                st.dataframe(df, use_container_width=True)

                if df.empty:
                    st.warning("⚠ No data found. Try different query/city.")
                else:
                    st.success(f"✅ Found {len(df)} results.")
                    st.dataframe(df, use_container_width=True)

                    # Download CSV
                    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button("⬇ Download CSV", data=csv_bytes, file_name="justdial_scrape.csv", mime="text/csv")

                    # Download Excel
                    xlsx_bytes = df_to_excel_bytes(df)
                    st.download_button("⬇ Download Excel", data=xlsx_bytes,
                                       file_name="justdial_scrape.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"❌ Scraping failed: {e}")


# ================== LAYOUT ==================
topbar()
page = st.session_state.page
if page == "home":
    page_home()
elif page == "login":
    page_login()
elif page == "signup":
    page_signup()
elif page == "scraper":
    page_scraper()
else:
    page_home()


