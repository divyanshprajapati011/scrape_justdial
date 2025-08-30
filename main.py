import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib, io, requests, re

# ================== APP CONFIG ==================
st.set_page_config(page_title="Maps + Justdial Scraper 🚀", layout="wide")

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
        password="@Deep7067",   # ⚠️ production me env var use karna
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

# ================== APIFY JUSTDIAL SCRAPER ==================
APIFY_TOKEN = "apify_api_54O7FoO2ZtjaJ76fU7yKqzBEQsWqak34LZVv"   # 👈 यहां अपना Apify token डालें

import requests, re
from bs4 import BeautifulSoup

# ================== APIFY + FALLBACK ==================
def scrape_justdial(query, city="Bhopal", limit=50):
    # ---------------- TRY APIFY ----------------
    url = f"https://api.apify.com/v2/acts/apify~justdial-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "queries": [f"{query} in {city}"],
        "maxResults": limit
    }

    try:
        res = requests.post(url, json=payload, timeout=60)
        data = res.json()

        # error case
        if isinstance(data, dict) and "error" in data:
            st.warning(f"⚠ Apify error: {data['error']}")
            data = []

    except Exception as e:
        st.warning(f"⚠ Apify failed: {e}")
        data = []

    # if Apify gave valid data
    if isinstance(data, list) and len(data) > 0:
        rows = []
        for r in data:
            rows.append({
                "Business Name": r.get("name"),
                "Address": r.get("address"),
                "Phone": r.get("phone"),
                "Rating": r.get("rating"),
                "Reviews": r.get("reviewsCount"),
                "Category": r.get("category"),
                "Website": r.get("website"),
                "Source Link": r.get("url"),
            })
        return pd.DataFrame(rows)

    # ---------------- FALLBACK: DIRECT JUSTDIAL ----------------
    st.info("🔄 Falling back to direct Justdial scraping...")

    search_url = f"https://www.justdial.com/{city}/{query.replace(' ', '-')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    resp = requests.get(search_url, headers=headers, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    cards = soup.select("div.resultbox")  # may need adjustment
    rows = []

    for c in cards[:limit]:
        name = c.select_one("h2 a")
        phone = c.select_one("p.contact-info a")
        rating = c.select_one("span.green-box")
        reviews = c.select_one("span.votes")
        address = c.select_one("span.address-info")

        rows.append({
            "Business Name": name.text.strip() if name else None,
            "Address": address.text.strip() if address else None,
            "Phone": phone.text.strip() if phone else None,
            "Rating": rating.text.strip() if rating else None,
            "Reviews": reviews.text.strip() if reviews else None,
            "Category": None,
            "Website": None,
            "Source Link": name["href"] if name and name.has_attr("href") else None,
        })

    return pd.DataFrame(rows)

# ============================================================
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
    st.title("Welcome 🚀")
    st.write("Signup → Login → Scrape Justdial Data via Apify")
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
            st.success("✅ Login successful! Redirecting...")
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

    st.title("🚀 Justdial Scraper (via Apify)")
    query = st.text_input("🔎 Enter your query", "Top Coaching Classes")
    city = st.text_input("🏙 Enter City", "Bhopal")
    max_results = st.number_input("Maximum results to fetch", min_value=5, max_value=200, value=50, step=5)

    start_btn = st.button("Start Scraping")
    if start_btn:
        with st.spinner("⏳ Fetching data from Justdial via Apify..."):
            try:
                df = scrape_justdial_apify(query, city, int(max_results))
                if df.empty:
                    st.warning("⚠ No data found. Try different query/city.")
                else:
                    st.success(f"✅ Found {len(df)} results.")
                    st.dataframe(df, use_container_width=True)

                    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button("⬇ Download CSV", data=csv_bytes, file_name="justdial_scrape.csv", mime="text/csv")

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

