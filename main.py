# main.py
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib, io, time, urllib.parse, re, requests, os, subprocess, sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ================== APP CONFIG ==================
st.set_page_config(page_title="Justdial Scraper + Auth Flow", layout="wide")

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

# ================== PLAYWRIGHT SAFETY NET ==================
def ensure_chromium_once():
    cache_flag = "/tmp/.chromium_ready"
    if os.path.exists(cache_flag):
        return
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            browser.close()
        open(cache_flag, "w").close()
    except Exception:
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            open(cache_flag, "w").close()
        except Exception as e:
            st.warning(f"Playwright browser install attempt failed: {e}")

ensure_chromium_once()

# ================== SCRAPER UTILS ==================
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s]{7,}\d)")
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_email_phone_from_site(url, timeout=12):
    if not url or not url.startswith("http"):
        return "", ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        html = resp.text
        emails = list({e for e in EMAIL_RE.findall(html)})
        phones = list({p.strip() for p in PHONE_RE.findall(html)})
        return "; ".join(emails[:5]), "; ".join(phones[:5])
    except Exception:
        return "", ""

# ================== JUSTDIAL SCRAPER ==================
def get_jd_url(query: str, city="Bhopal"):
    query = urllib.parse.quote_plus(query.strip().replace(" ", "-"))
    city = urllib.parse.quote_plus(city.strip())
    return f"https://www.justdial.com/{city}/{query}"

def scrape_justdial(query: str, city: str, limit=20, email_lookup=False) -> pd.DataFrame:
    results = []
    search_url = get_jd_url(query, city)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()

        page.goto(search_url, timeout=60000)
        time.sleep(3)

        last_height = 0
        while len(results) < limit:
            page.mouse.wheel(0, 2000)
            time.sleep(2)

            cards = page.query_selector_all("article")
            for card in cards:
                try:
                    name = card.query_selector("h2, h3, h4")
                    phone = card.query_selector("a[href*='tel:']")
                    addr = card.query_selector("p")
                    website = card.query_selector("a[href*='http']")

                    site_url = website.get_attribute("href") if website else ""
                    email, extra_phone = ("", "")
                    if email_lookup and site_url:
                        email, extra_phone = fetch_email_phone_from_site(site_url)

                    results.append({
                        "name": name.inner_text().strip() if name else "",
                        "phone": phone.inner_text().strip() if phone else "",
                        "address": addr.inner_text().strip() if addr else "",
                        "website": site_url,
                        "email": email,
                        "extra_phone": extra_phone
                    })
                except:
                    continue

            if len(results) >= limit:
                break

            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        browser.close()

    return pd.DataFrame(results[:limit])

# ================== DOWNLOAD HELPERS ==================
def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buf.seek(0)
    return buf.getvalue()

# ================== TOPBAR ==================
def topbar():
    cols = st.columns([1,1,1,3])
    with cols[0]:
        if st.button("🏠 Home"):
            go_to("home")
    with cols[3]:
        if st.session_state.logged_in and st.session_state.user:
            u = st.session_state.user["username"]
            st.info(f"Logged in as **{u}**")
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                go_to("home")

# ================== PAGES ==================
def page_home():
    st.title("Welcome to Justdial Scraper 🚀")
    st.write("Choose an option below to continue.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔑 Go to Login", use_container_width=True):
            go_to("login")
    with c2:
        if st.button("📝 Create Account", use_container_width=True):
            go_to("signup")
    if st.session_state.logged_in:
        st.success("You are already logged in.")
        if st.button("➡️ Open Scraper", use_container_width=True):
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
            st.success("Login successful! Redirecting to Scraper...")
            go_to("scraper")
        else:
            st.error("Invalid credentials")
    st.button("⬅️ Back", on_click=lambda: go_to("home"))

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
                st.error("User already exists or DB error.")
        else:
            st.warning("Please fill all fields.")
    st.button("⬅️ Back", on_click=lambda: go_to("home"))

def page_scraper():
    if not st.session_state.logged_in or not st.session_state.user:
        st.error("Please login first")
        if st.button("Go to Login"):
            go_to("login")
        return
    st.title("🚀 Justdial Scraper")
    user_input = st.text_input("🔎 Enter business type (e.g. top coaching)", "top coaching")
    city = st.text_input("🏙️ Enter City", "Bhopal")
    max_results = st.number_input("Maximum results to fetch", min_value=5, max_value=500, value=60, step=5)
    do_email_lookup = st.checkbox("Website से Email/extra Phones भी निकालें (slower)", value=True)
    start_btn = st.button("Start Scraping")
    if start_btn:
        if not user_input.strip() or not city.strip():
            st.error("Please enter a valid input")
        else:
            with st.spinner("Scraping in progress..."):
                try:
                    df = scrape_justdial(user_input, city, int(max_results), bool(do_email_lookup))
                    if df.empty:
                        st.warning("No data found. Try another search.")
                    else:
                        st.success(f"Scraping completed! Found {len(df)} results.")
                        st.dataframe(df, use_container_width=True)
                        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                        st.download_button("⬇️ Download CSV", data=csv_bytes, file_name="justdial_scrape.csv", mime="text/csv")
                        xlsx_bytes = df_to_excel_bytes(df)
                        st.download_button(
                            "⬇️ Download Excel",
                            data=xlsx_bytes,
                            file_name="justdial_scrape.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"Scraping failed: {e}")

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
