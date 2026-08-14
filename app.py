import streamlit as st
import requests
import math
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Real Match Football Analytics", page_icon="⚽", layout="wide")

st.title("⚽ Real-Time Football Analytics & Value Bet Predictor")
st.caption("ดึงรายการแข่งขันจริงประจำวันจาก Football-Data API พร้อมวิเคราะห์ xG และสรุปฟันธง")

# --- 1. FETCH REAL MATCHES FROM FOOTBALL-DATA.ORG ---
@st.cache_data(ttl=900)
def fetch_real_matches(api_key, date_str):
    """ ดึงตารางแข่งขันจริงของวันที่เลือก """
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": api_key}
    params = {
        "dateFrom": date_str,
        "dateTo": date_str
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            matches_raw = data.get("matches", [])
            parsed_matches = []
            
            for m in matches_raw:
                league_name = m.get("competition", {}).get("name", "Unknown League")
                home_team = m.get("homeTeam", {}).get("name", "Home")
                away_team = m.get("awayTeam", {}).get("name", "Away")
                
                # แปลงเวลาเตะเป็นเวลาท้องถิ่น
                utc_time = m.get("utcDate", "")
                time_str = utc_time[11:16] if len(utc_time) >= 16 else "--:--"
                
                parsed_matches.append({
                    "id": m.get("id"),
                    "league": league_name,
                    "home": home_team,
                    "away": away_team,
                    "time": time_str,
                    "status": m.get("status")
                })
            return parsed_matches, None
        elif res.status_code == 403:
            return None, "API Key ไม่ถูกต้อง หรือสิทธิ์การใช้งานจำกัด"
        else:
            return None, f"Error {res.status_code}: ไม่สามารถดึงข้อมูลได้"
    except Exception as e:
        return None, str(e)

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
st.sidebar.header("⚙️ ตัวเลือกลีก & แมตช์ประจำวัน")

api_key = st.secrets.get("FOOTBALL_DATA_API_KEY") if "FOOTBALL_DATA_API_KEY" in st.secrets else st.sidebar.text_input("🔑 ใส่ Football-Data API Key:", type="password")

if not api_key:
    st.info("👈 กรุณากรอก **Football-Data API Key** ในแถบเมนูด้านซ้ายเพื่อโหลดตารางแข่งจริง")
    st.stop()

selected_date_obj = st.sidebar.date_input("📅 เลือกวันที่เตะ:", datetime.now())
selected_date_str = selected_date_obj.strftime("%Y-%m-%d")

with st.spinner(f"🤖 กำลังดึงโปรแกรมการแข่งขันจริงของวันที่ {selected_date_str}..."):
    matches, error = fetch_real_matches(api_key, selected_date_str)

if error:
    st.sidebar.error(f"เกิดข้อผิดพลาด: {error}")
    st.stop()

if not matches:
    st.warning(f"ไม่พบโปรแกรมการแข่งขันจริงในวันที่ {selected_date_str} (อาจไม่มีการแข่งขันในลีกหลักวันนี้)")
    st.stop()

st.sidebar.success(f"✅ ดึงโปรแกรมแข่งจริงสำเร็จ {len(matches)} คู่!")

# 1. กรองตามลีกจริง
all_leagues = sorted(list(set([m["league"] for m in matches])))
selected_league = st.sidebar.selectbox("🏆 เลือกลีกที่ต้องการ:", ["-- แสดงทุกลีก --"] + all_leagues)

if selected_league != "-- แสดงทุกลีก --":
    filtered_matches = [m for m in matches if m["league"] == selected_league]
else:
    filtered_matches = matches

# 2. เลือกคู่แข่งจริง
match_options = {f"[{m['time']} UTC] [{m['league']}] {m['home']} vs {m['away']}": m for m in filtered_matches}
selected_match_label = st.sidebar.selectbox(f"⚽ เลือกคู่แข่งขัน ({len(filtered_matches)} คู่):", list(match_options.keys()))
selected_match = match_options[selected_match_label]

home_team = selected_match["home"]
away_team = selected_match["away"]

# --- DISPLAY MATCH DETAILS ---
st.markdown("---")
st.subheader(f"🏟️ {home_team} vs {away_team}")
st.caption(f"📅 วันที่เตะ: {selected_date_str} | เวลา: {selected_match['time']} UTC | 🏆 ลีก: {selected_match['league']}")

col_xg1, col_xg2 = st.columns(2)
with col_xg1:
    home_xg = st.number_input(f"xG {home_team}:", min_value=0.1, max_value=6.0, value=1.65, step=0.05)
with col_xg2:
    away_xg = st.number_input(f"xG {away_team}:", min_value=0.1, max_value=6.0, value=1.15, step=0.05)

st.markdown("---")
st.subheader("🎯 วิเคราะห์ราคาต่อรอง (Asian Handicap) & สูง/ต่ำ")

col_input1, col_input2 = st.columns(2)
with col_input1:
    handicap_input = st.number_input(f"ราคาต่อรองของ {home_team}:", value=-0.5, step=0.25)
with col_input2:
    total_input = st.number_input("ราคาเรตสูง/ต่ำ (Over/Under):", value=2.5, step=0.25)

res = calculate_analytics(home_xg, away_xg, handicap_input, total_input)

# --- กล่องสรุปผลการวิเคราะห์ (ฟันธง ชัดเจน) ---
st.markdown("---")
st.subheader("📌 สรุปฟันธงคำแนะนำการลงทุน (Direct Recommendation)")

# คำนวณฝั่งต่อ/รอง
if res['win'] >= 52.0:
    ah_status = "🟢 ฟันธง: น่าลงทุน"
    ah_action = f"**วางฝั่ง ต่อ {home_team}** (ราคา {handicap_input}) | โอกาสชนะราคา {res['win']:.1f}%"
elif res['loss'] >= 52.0:
    ah_status = "🟢 ฟันธง: น่าลงทุน"
    ah_action = f"**วางฝั่ง รอง {away_team}** | โอกาสรอดราคา/ชนะรอง {res['loss']:.1f}%"
else:
    ah_status = "🔴 ฟันธง: งดเล่น / ให้ข้ามคู่นี้ (PASS)"
    ah_action = "**ไม่แนะนำให้วางต่อหรือรอง** — บอลสูสีกันเกินไป ไม่มีฝั่งไหนได้เปรียบเชิงสถิติ"

# คำนวณฝั่งสูง/ต่ำ
if res['expected_total_goals'] > (total_input + 0.3):
    ou_status = "🟢 ฟันธง: น่าเล่นสกอร์สูง"
    ou_action = f"**กด สกอร์สูง (OVER {total_input})** | คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก"
elif res['expected_total_goals'] < (total_input - 0.3):
    ou_status = "🟢 ฟันธง: น่าเล่นสกอร์ต่ำ"
    ou_action = f"**กด สกอร์ต่ำ (UNDER {total_input})** | คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก"
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
