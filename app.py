import streamlit as st
import requests
import math
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Global Football Daily Analytics", page_icon="⚽", layout="wide")

st.title("⚽ Global Football Daily Analytics & Value Bet Predictor")
st.caption("เลือกรอบวันแข่งขันเพื่อดูโปรแกรมฟุตบอลทุกลีกทั่วโลก พร้อมวิเคราะห์ xG และสรุปฟันธงการลงทุน")

# --- 1. FUNCTION ดึงข้อมูลโปรแกรมแข่งขันและค่าน้ำทุกลีกทั่วโลก ---
@st.cache_data(ttl=900)  # Refresh ทุก 15 นาที
def fetch_all_global_odds(api_key):
    """ ดึงตารางแข่งสด/ล่วงหน้าของกีฬาฟุตบอลทั่วโลก """
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu,uk",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        return res.json(), None
    except requests.exceptions.HTTPError as err:
        return None, f"HTTP Error {err.response.status_code}: โปรดตรวจสอบ API Key"
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

# --- 2. MATH & PROBABILITY CALCULATIONS ---
def poisson_pmf(k, lambda_val):
    if lambda_val <= 0: return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

def calculate_analytics(home_xg, away_xg, handicap, target_total=2.5, max_goals=8):
    home_probs = [poisson_pmf(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_pmf(i, away_xg) for i in range(max_goals)]
    
    win_ah = half_win_ah = push_ah = half_loss_ah = loss_ah = 0.0
    over_prob = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            diff = (h - a) + handicap
            
            if diff > 0.25: win_ah += p
            elif diff == 0.25: half_win_ah += p
            elif diff == 0.0: push_ah += p
            elif diff == -0.25: half_loss_ah += p
            else: loss_ah += p

            if (h + a) > target_total:
                over_prob += p

    under_prob = 1.0 - over_prob
    expected_ah_return = win_ah + (half_win_ah * 0.5) + (push_ah * 0.5)
    fair_odds_ah = 1 / expected_ah_return if expected_ah_return > 0 else 0
    
    fair_odds_over = 1 / over_prob if over_prob > 0 else 0
    fair_odds_under = 1 / under_prob if under_prob > 0 else 0

    return {
        "win": win_ah * 100,
        "push": push_ah * 100,
        "loss": loss_ah * 100,
        "fair_odds_ah": fair_odds_ah,
        "over_prob": over_prob * 100,
        "under_prob": under_prob * 100,
        "fair_odds_over": fair_odds_over,
        "fair_odds_under": fair_odds_under,
        "expected_total_goals": home_xg + away_xg
    }

# --- 3. UI DASHBOARD ---
st.sidebar.header("⚙️ ตั้งค่าระบบ & เลือกโปรแกรมแข่ง")

api_key = st.secrets.get("ODDS_API_KEY") if "ODDS_API_KEY" in st.secrets else st.sidebar.text_input("🔑 ใส่ Odds API Key:", type="password")

if not api_key:
    st.info("👈 กรุณากรอก **Odds API Key** ในแถบเมนูด้านซ้ายเพื่อเริ่มใช้งาน")
    st.stop()

with st.spinner("🤖 กำลังดึงโปรแกรมการแข่งขันและราคาน้ำทุกลีกทั่วโลก..."):
    raw_matches, error = fetch_all_global_odds(api_key)

if error:
    st.error(f"เกิดข้อผิดพลาด: {error}")
    st.stop()

if not raw_matches:
    st.warning("ไม่พบรายการแข่งขันฟุตบอลในระบบขณะนี้")
    st.stop()

# --- จัดกลุ่มแมตช์ตามวันที่ (Group By Date) ---
matches_by_date = {}

for m in raw_matches:
    commence_str = m.get("commence_time") # ISO Format e.g., "2026-08-14T15:00:00Z"
    if commence_str:
        dt = datetime.strptime(commence_str[:19], "%Y-%m-%dT%H:%M:%S")
        date_key = dt.strftime("%Y-%m-%d") # ตัวอย่าง "2026-08-14"
        time_str = dt.strftime("%H:%M")   # ตัวอย่าง "15:00"
    else:
        date_key = "ไม่ระบุวัน"
        time_str = "--:--"
        
    m["time_formatted"] = time_str
    
    if date_key not in matches_by_date:
        matches_by_date[date_key] = []
    matches_by_date[date_key].append(m)

# 1. Dropdown เลือกวันที่แข่งขัน
sorted_dates = sorted(list(matches_by_date.keys()))
selected_date = st.sidebar.selectbox("📅 เลือกวันที่แข่งขัน:", sorted_dates)

# 2. Dropdown เลือกคู่บอลในวันที่เลือก (รวมทุกลีกทั่วโลก)
matches_on_selected_date = matches_by_date[selected_date]

match_options = {}
for m in matches_on_selected_date:
    league_name = m.get("sport_title", "Football")
    home = m.get("home_team", "Home")
    away = m.get("away_team", "Away")
    time_str = m.get("time_formatted", "")
    
    label = f"[{time_str}] [{league_name}] {home} vs {away}"
    match_options[label] = m

selected_match_label = st.sidebar.selectbox(f"⚽ เลือกคู่แข่งขัน ({len(matches_on_selected_date)} คู่):", list(match_options.keys()))
selected_match = match_options[selected_match_label]

home_team = selected_match["home_team"]
away_team = selected_match["away_team"]

# สกัดค่าน้ำ/ราคาต่อรองสดจาก Bookmakers
live_handicap = -0.5
live_odds_ah = 0.0
live_total_point = 2.5
live_odds_over = 0.0
live_odds_under = 0.0

bookmakers = selected_match.get("bookmakers", [])
if bookmakers:
    markets = bookmakers[0].get("markets", [])
    for mkt in markets:
        if mkt.get("key") == "spreads":
            for out in mkt.get("outcomes", []):
                if out.get("name") == home_team:
                    live_handicap = float(out.get("point", -0.5))
                    live_odds_ah = float(out.get("price", 0.0))
        elif mkt.get("key") == "totals":
            for out in mkt.get("outcomes", []):
                live_total_point = float(out.get("point", 2.5))
                if out.get("name") == "Over":
                    live_odds_over = float(out.get("price", 0.0))
                elif out.get("name") == "Under":
                    live_odds_under = float(out.get("price", 0.0))

# --- DISPLAY MATCH DETAILS ---
st.markdown("---")
st.subheader(f"🏟️ {home_team} vs {away_team}")
st.caption(f"📅 วันที่เตะ: {selected_date} | เวลา: {selected_match.get('time_formatted')} น. | 🏆 ลีก: {selected_match.get('sport_title')}")

col_xg1, col_xg2 = st.columns(2)
with col_xg1:
    home_xg = st.number_input(f"xG {home_team}:", min_value=0.1, max_value=6.0, value=1.65, step=0.05)
with col_xg2:
    away_xg = st.number_input(f"xG {away_team}:", min_value=0.1, max_value=6.0, value=1.15, step=0.05)

# --- ANALYTICS ---
res = calculate_analytics(home_xg, away_xg, live_handicap, live_total_point)

st.markdown("---")
st.subheader("🎯 วิเคราะห์ราคาต่อรอง (Asian Handicap)")

c1, c2 = st.columns([1, 2])
with c1:
    handicap_input = st.number_input(f"ราคาต่อรองของ {home_team}:", value=live_handicap, step=0.25)
    if live_odds_ah > 0:
        st.caption(f"ค่าน้ำสดบนเว็บ ({home_team} ต่อ {handicap_input}): `{live_odds_ah:.2f}`")

with c2:
    m1, m2, m3 = st.columns(3)
    m1.metric("โอกาสชนะราคา (Win)", f"{res['win']:.2f}%")
    m2.metric("โอกาสเสมอ/ยก (Push)", f"{res['push']:.2f}%")
    m3.metric("โอกาสเสียราคา (Loss)", f"{res['loss']:.2f}%")

# --- กล่องสรุปผลการวิเคราะห์ (ฟันธง ชัดเจน อ่านง่าย) ---
st.markdown("---")
st.subheader("📌 สรุปฟันธงคำแนะนำการลงทุน (Direct Recommendation)")

# 1. คำนวณฝั่ง Asian Handicap (ต่อ/รอง)
if res['win'] >= 52.0:
    ah_status = "🟢 ฟันธง: น่าลงทุน"
    ah_action = f"**วางฝั่ง ต่อ {home_team}** (ราคา {handicap_input}) | โอกาสชนะราคา {res['win']:.1f}%"
elif res['loss'] >= 52.0:
    ah_status = "🟢 ฟันธง: น่าลงทุน"
    ah_action = f"**วางฝั่ง รอง {away_team}** | โอกาสรอดราคา/ชนะรอง {res['loss']:.1f}%"
else:
    ah_status = "🔴 ฟันธง: งดเล่น / ให้ข้ามคู่นี้ (PASS)"
    ah_action = "**ไม่แนะนำให้วางต่อหรือรอง** — บอลสูสีกันเกินไป ไม่มีฝั่งไหนได้เปรียบเชิงสถิติ"

# 2. คำนวณฝั่ง Over/Under (สูง/ต่ำ)
if res['expected_total_goals'] > (live_total_point + 0.3):
    ou_status = "🟢 ฟันธง: น่าเล่นสกอร์สูง"
    ou_action = f"**กด สกอร์สูง (OVER {live_total_point})** | คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก"
elif res['expected_total_goals'] < (live_total_point - 0.3):
    ou_status = "🟢 ฟันธง: น่าเล่นสกอร์ต่ำ"
    ou_action = f"**กด สกอร์ต่ำ (UNDER {live_total_point})** | คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก"
else:
    ou_status = "🔴 ฟันธง: งดเล่นสกอร์สูง/ต่ำ (PASS)"
    ou_action = f"**ไม่แนะนำให้เล่นสูง/ต่ำ** — ประตูคาดการณ์ ({res['expected_total_goals']:.2f} ลูก) ใกล้เคียงราคาเปิดมากเกินไป"

col_rec1, col_rec2 = st.columns(2)

with col_rec1:
    st.markdown("### 🛡️ ฝั่งต่อ/รอง (Asian Handicap)")
    if "🟢" in ah_status:
        st.success(f"{ah_status}\n\n👉 {ah_action}\n\n*ค่าน้ำที่คุ้มเสี่ยง (Fair Odds):* `{res['fair_odds_ah']:.2f}` ขึ้นไป")
    else:
        st.error(f"{ah_status}\n\n👉 {ah_action}")

with col_rec2:
    st.markdown("### ⚽ ฝั่งสกอร์สูง/ต่ำ (Over/Under)")
    if "🟢" in ou_status:
        st.success(f"{ou_status}\n\n👉 {ou_action}\n\n*ค่าน้ำที่คุ้มเสี่ยง:* Over `{res['fair_odds_over']:.2f}` | Under `{res['fair_odds_under']:.2f}`")
    else:
        st.error(f"{ou_status}\n\n👉 {ou_action}")
