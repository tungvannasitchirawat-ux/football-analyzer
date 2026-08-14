import streamlit as st
import requests

# ดึง API Key จาก Secrets หรือ Sidebar
ODDS_API_KEY = st.sidebar.text_input("🔑 ใส่ Odds API Key:", type="password")

@st.cache_data(ttl=600) # Cache ไว้ 10 นาที
def fetch_live_odds_and_fixtures(api_key):
    if not api_key:
        return []
    
    # ดึงตารางแข่งและราคาต่อรองบอลทั่วโลก (soccer)
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu,uk",
        "markets": "h2h,spreads", # spreads คือราคาต่อรอง Asian Handicap
        "oddsFormat": "decimal"
    }
    
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Error fetching odds: {e}")
    return []

if ODDS_API_KEY:
    live_data = fetch_live_odds_and_fixtures(ODDS_API_KEY)
    if live_data:
        st.success(f"โหลดข้อมูลแมตช์สดและราคาเรียลไทม์สำเร็จ {len(live_data)} คู่!")
