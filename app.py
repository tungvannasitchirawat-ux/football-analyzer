import streamlit as st
import requests
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Live Football Odds & AH Engine", page_icon="⚽", layout="wide")

st.title("⚽ Live Football Odds & Asian Handicap Analytics")
st.caption("ระบบดึงแมตช์สดและราคาต่อรองเรียลไทม์ผ่าน The Odds API")

# --- 1. FUNCTION ดึงข้อมูล ODDS & FIXTURES เรียลไทม์ ---
@st.cache_data(ttl=600)  # Cache ไว้ 10 นาที
def fetch_live_odds(api_key):
    if not api_key:
        return None, "กรุณากรอก API Key"
    
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu,uk",
        "markets": "h2h,spreads",  # spreads = ราคาต่อรอง Asian Handicap
        "oddsFormat": "decimal"
    }
    
    try:
        res = requests.get(url, params=params, timeout=12)
        res.raise_for_status()
        return res.json(), None
    except requests.exceptions.HTTPError as err:
        return None, f"HTTP Error {err.response.status_code}: โปรดตรวจสอบ API Key"
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

# --- 2. MATH CALCULATIONS ---
def poisson_pmf(k, lambda_val):
    if lambda_val <= 0: return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

def calculate_ah(home_xg, away_xg, handicap, max_goals=8):
    home_probs = [poisson_pmf(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_pmf(i, away_xg) for i in range(max_goals)]
    
    win_ah = half_win_ah = push_ah = half_loss_ah = loss_ah = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            diff = (h - a) + handicap
            
            if diff > 0.25: win_ah += p
            elif diff == 0.25: half_win_ah += p
            elif diff == 0.0: push_ah += p
            elif diff == -0.25: half_loss_ah += p
            else: loss_ah += p

    exp_prob = win_ah + (half_win_ah * 0.5) + (push_ah * 0.5)
    fair_odds = 1 / exp_prob if exp_prob > 0 else 0

    return {
        "win": win_ah * 100, "half_win": half_win_ah * 100,
        "push": push_ah * 100, "half_loss": half_loss_ah * 100,
        "loss": loss_ah * 100, "fair_odds": fair_odds
    }

# --- 3. UI DASHBOARD ---
st.sidebar.header("⚙️ ตั้งค่าระบบ")

# ดึง Key จาก Secrets หรือ Sidebar
api_key = st.secrets.get("ODDS_API_KEY") if "ODDS_API_KEY" in st.secrets else st.sidebar.text_input("🔑 ใส่ Odds API Key:", type="password")

if not api_key:
    st.info("👈 กรุณากรอก **Odds API Key** ในแถบเมนูด้านซ้ายเพื่อเริ่มใช้งาน")
    st.stop()

with st.spinner("กำลังโหลดข้อมูลแมตช์สดและค่าน้ำเรียลไทม์..."):
    live_data, error = fetch_live_odds(api_key)

if error:
    st.error(f"เกิดข้อผิดพลาด: {error}")
    st.stop()

if not live_data:
    st.warning("ไม่พบรายการแมตช์สดในขณะนี้")
    st.stop()

st.success(f"✅ ดึงข้อมูลแมตช์สดและราคาเรียลไทม์สำเร็จ {len(live_data)} คู่!")

# --- UI SELECTOR ---
match_options = {}
for m in live_data:
    home_team = m.get("home_team", "Home")
    away_team = m.get("away_team", "Away")
    sport_title = m.get("sport_title", "Soccer")
    label = f"[{sport_title}] {home_team} vs {away_team}"
    match_options[label] = m

selected_label = st.sidebar.selectbox("เลือกคู่แข่งขันสด:", list(match_options.keys()))
selected_match = match_options[selected_label]

home_team = selected_match["home_team"]
away_team = selected_match["away_team"]

# สกัดราคาต่อรอง (Spread / Handicap) สดจาก Bookmakers (ถ้ามี)
live_handicap = -0.5
live_odds_val = 0.0

bookmakers = selected_match.get("bookmakers", [])
if bookmakers:
    markets = bookmakers[0].get("markets", [])
    for mkt in markets:
        if mkt.get("key") == "spreads":
            outcomes = mkt.get("outcomes", [])
            for out in outcomes:
                if out.get("name") == home_team:
                    live_handicap = float(out.get("point", -0.5))
                    live_odds_val = float(out.get("price", 0.0))

# --- DISPLAY MATCH DETAILS ---
st.markdown("---")
st.subheader(f"🏟️ {home_team} vs {away_team}")
st.caption(f"🏆 ลีก: {selected_match.get('sport_title')} | เวลาแข่ง: {selected_match.get('commence_time')[:16].replace('T', ' ')}")

col_xg1, col_xg2 = st.columns(2)
with col_xg1:
    home_xg = st.number_input(f"xG {home_team}:", min_value=0.1, max_value=6.0, value=1.65, step=0.05)
with col_xg2:
    away_xg = st.number_input(f"xG {away_team}:", min_value=0.1, max_value=6.0, value=1.15, step=0.05)

st.markdown("---")

# --- HANDICAP ANALYSIS ---
st.subheader("🎯 วิเคราะห์ราคาต่อรอง (Asian Handicap)")

col_ah1, col_ah2 = st.columns([1, 2])

with col_ah1:
    handicap = st.number_input(
        f"ราคาต่อรองสดของ {home_team}:", 
        value=live_handicap, 
        step=0.25
    )
    if live_odds_val > 0:
        st.info(f"📊 **ค่าน้ำสดบนเว็บ (Market Odds):** `{live_odds_val:.2f}`")

res = calculate_ah(home_xg, away_xg, handicap)

with col_ah2:
    st.subheader("📈 ผลการวิเคราะห์ความน่าจะเป็น")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("โอกาสชนะราคา (Win)", f"{res['win']:.2f}%")
        if res['half_win'] > 0: st.metric("โอกาสได้ครึ่ง", f"{res['half_win']:.2f}%")
    with m2:
        st.metric("โอกาสเสมอ/ยก (Push)", f"{res['push']:.2f}%")
    with m3:
        st.metric("โอกาสเสียราคา (Loss)", f"{res['loss']:.2f}%")
        if res['half_loss'] > 0: st.metric("โอกาสเสียครึ่ง", f"{res['half_loss']:.2f}%")

st.markdown("---")

# --- VALUE BET DECISION ---
fair_odds = res['fair_odds']
is_value = live_odds_val > fair_odds if live_odds_val > 0 else False

if is_value:
    st.success(f"""
    🔥 **พบจุดได้เปรียบ (VALUE BET DETECTED)!**
    * ค่าน้ำยุติธรรม (Fair Odds): **`{fair_odds:.2f}`**
    * ค่าน้ำบนเว็บเปิดมาสูงกว่าที่: **`{live_odds_val:.2f}`** 
    👉 **คำแนะนำ:** ราคานี้มีความคุ้มค่าเชิงสถิติที่จะเลือกลงทุน!
    """)
else:
    st.warning(f"""
    💡 **วิเคราะห์ราคาน้ำยุติธรรม (Fair Odds):**
    * ค่าน้ำยุติธรรมที่ควรจะเป็น (Fair Odds): **`{fair_odds:.2f}`**
    * หากค่าน้ำบนเว็บเปิดต่ำกว่า `{fair_odds:.2f}` แสดงว่าเจ้ามือคิด Margin สูง ไม่ค่อยคุ้มเสี่ยงครับ
    """)
