import streamlit as st
import requests
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Global Football & Value Bet Predictor", page_icon="⚽", layout="wide")

st.title("⚽ Global Football & Value Bet Predictor")
st.caption("ดึงข้อมูลแมตช์ทุกลีกฮอตทั่วโลก คำนวณ xG + Poisson พร้อมสรุปคำแนะนำ (ฝั่งน่าต่อ/รอง & สูง/ต่ำ)")

# --- 1. FUNCTION รายชื่อ "ลีกฮอต" ตามรูป + ดึงทุกลีกเสริม ---
@st.cache_data(ttl=3600)
def get_all_soccer_sports(api_key):
    """ รายชื่อลีกฮอตตามรูปภาพ + ดึงทุกลีกเสริมจาก API """
    
    # กำหนดรายการ "ลีกฮอต" ตามรูปภาพของผู้ใช้
    hot_leagues = [
        {"title": "🔥 ไทยลีก (Thai League 1)", "key": "soccer_thailand_league1"},
        {"title": "🔥 พรีเมียร์ลีก (English Premier League)", "key": "soccer_epl"},
        {"title": "🔥 เซเรียอา (Italian Serie A)", "key": "soccer_italy_serie_a"},
        {"title": "🔥 ลาลีกา (Spanish La Liga)", "key": "soccer_spain_la_liga"},
        {"title": "🔥 บุนเดสลีกา (German Bundesliga)", "key": "soccer_germany_bundesliga"},
        {"title": "🔥 ลีกเอิง ฝรั่งเศส (French Ligue 1)", "key": "soccer_france_ligue_one"},
        {"title": "🔥 ฟุตบอล ยูโร (UEFA European Championship)", "key": "soccer_uefa_european_championship"},
        {"title": "🔥 ยูฟ่าแชมเปียนส์ลีก (UEFA Champions League)", "key": "soccer_uefa_champs_league"},
        {"title": "🔥 ยูฟ่ายูโรปาลีก (UEFA Europa League)", "key": "soccer_uefa_europa_league"},
        {"title": "🔥 ฟุตบอลชิงแชมป์สโมสรโลก (FIFA Club World Cup)", "key": "soccer_fifa_club_world_cup"},
        {"title": "🔥 EFLแชมเปียนชิป (English Championship)", "key": "soccer_efl_champ"},
        {"title": "🔥 บุนเดสลีก้า 2 (German Bundesliga 2)", "key": "soccer_germany_bundesliga2"},
        {"title": "🔥 ลีกเดอช (French Ligue 2)", "key": "soccer_france_ligue_two"},
    ]
    
    # ดึงลีกอื่นๆ ทั่วโลกจาก API เข้ามาเสริม
    url = "https://api.the-odds-api.com/v4/sports"
    params = {"apiKey": api_key}
    
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            api_leagues = [s for s in res.json() if s.get("group") == "Soccer"]
            
            # ตรวจสอบเพื่อไม่ให้ชื่อลีกซ้ำกับลีกฮอต
            hot_keys = {hl["key"] for hl in hot_leagues}
            for al in api_leagues:
                if al.get("key") not in hot_keys:
                    hot_leagues.append({
                        "title": f"🌐 {al.get('title')}",
                        "key": al.get("key")
                    })
    except Exception:
        pass

    return hot_leagues

@st.cache_data(ttl=600)
def fetch_odds_for_league(api_key, sport_key):
    """ ดึงตารางแข่ง, ค่าน้ำ Asian Handicap (spreads) และ สูง/ต่ำ (totals) """
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu,uk",
        "markets": "h2h,spreads,totals",  # ดึงทั้งราคาต่อรองและสูง/ต่ำ
        "oddsFormat": "decimal"
    }
    try:
        res = requests.get(url, params=params, timeout=12)
        res.raise_for_status()
        return res.json()
    except Exception:
        return []

# --- 2. MATH & PROBABILITY CALCULATIONS ---
def poisson_pmf(k, lambda_val):
    if lambda_val <= 0: return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

def calculate_analytics(home_xg, away_xg, handicap, target_total=2.5, max_goals=8):
    """ คำนวณ Asian Handicap และ สูง/ต่ำ (Over/Under) """
    home_probs = [poisson_pmf(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_pmf(i, away_xg) for i in range(max_goals)]
    
    win_ah = half_win_ah = push_ah = half_loss_ah = loss_ah = 0.0
    over_prob = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            diff = (h - a) + handicap
            
            # คำนวณ Handicap
            if diff > 0.25: win_ah += p
            elif diff == 0.25: half_win_ah += p
            elif diff == 0.0: push_ah += p
            elif diff == -0.25: half_loss_ah += p
            else: loss_ah += p

            # คำนวณ สูง/ต่ำ (Totals)
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
st.sidebar.header("⚙️ ตั้งค่าระบบ")

api_key = st.secrets.get("ODDS_API_KEY") if "ODDS_API_KEY" in st.secrets else st.sidebar.text_input("🔑 ใส่ Odds API Key:", type="password")

if not api_key:
    st.info("👈 กรุณากรอก **Odds API Key** ในแถบเมนูด้านซ้ายเพื่อเริ่มใช้งาน")
    st.stop()

# ดึงทุกลีกฮอต + ลีกทั่วโลก
all_leagues = get_all_soccer_sports(api_key)

if not all_leagues:
    st.error("ไม่สามารถดึงข้อมูลลีกได้ โปรดตรวจสอบ API Key")
    st.stop()

# Dropdown เลือกลีก (ลีกฮอตจะอยู่ด้านบนสุด)
league_dict = {l['title']: l['key'] for l in all_leagues}
selected_league_label = st.sidebar.selectbox("เลือกลีกฮอต / ลีกที่ต้องการ:", list(league_dict.keys()))
selected_sport_key = league_dict[selected_league_label]

# ดึงแมตช์ในลีกที่เลือก
with st.spinner(f"กำลังดึงตารางแข่งและราคาบอลของ {selected_league_label}..."):
    matches = fetch_odds_for_league(api_key, selected_sport_key)

if not matches:
    st.warning(f"ไม่พบแมตช์สด/โปรแกรมล่วงหน้าในลีก {selected_league_label} ขณะนี้")
    st.stop()

# Dropdown เลือก คู่แข่งขัน
match_dict = {f"{m['home_team']} vs {m['away_team']}": m for m in matches}
selected_match_label = st.sidebar.selectbox("เลือกคู่แข่งขันสด:", list(match_dict.keys()))
selected_match = match_dict[selected_match_label]

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

# --- DISPLAY MATCH DATA ---
st.markdown("---")
st.subheader(f"🏟️ {home_team} vs {away_team}")
st.caption(f"🏆 ลีก: {selected_league_label} | เวลาแข่ง: {selected_match.get('commence_time')[:16].replace('T', ' ')}")

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

# --- กล่องสรุปผลการวิเคราะห์ (สีกรอบเหลืองเน้นการตัดสินใจ) ---
st.markdown("---")

# คำนวณฝั่งน่าเลือกลงทุน
ah_recommendation = ""
if res['win'] >= 52.0:
    ah_recommendation = f"🔥 **แนะนำเลือกฝั่ง:** **ต่อ {home_team}** (ที่ราคา {handicap_input}) — มีโอกาสชนะราคา {res['win']:.1f}%"
elif res['loss'] >= 52.0:
    ah_recommendation = f"🛡️ **แนะนำเลือกฝั่ง:** **รอง {away_team}** — มีโอกาสรอดราคา/ชนะรอง {res['loss']:.1f}%"
else:
    ah_recommendation = f"⚠️ **แนะนำเลือกฝั่ง:** **สูสี (ไม่แนะนำลงทุนฝั่งต่อรอง)** — โอกาสกินราคาพอๆ กัน"

# คำนวณสูง/ต่ำ (Over/Under)
ou_recommendation = ""
if res['expected_total_goals'] > (live_total_point + 0.3):
    ou_recommendation = f"⚽ **แนะนำเลือกสกอร์:** **สกอร์สูง (OVER {live_total_point})** — คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก (โอกาสสูง {res['over_prob']:.1f}%)"
elif res['expected_total_goals'] < (live_total_point - 0.3):
    ou_recommendation = f"🔒 **แนะนำเลือกสกอร์:** **สกอร์ต่ำ (UNDER {live_total_point})** — คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก (โอกาสต่ำ {res['under_prob']:.1f}%)"
else:
    ou_recommendation = f"⚖️ **แนะนำเลือกสกอร์:** **ก้ำกึ่งใกล้เคียงราคาเปิด** (ประตูคาดการณ์ {res['expected_total_goals']:.2f} ลูก)"

st.warning(f"""
### 💡 สรุปผลวิเคราะห์ & คำแนะนำการลงทุน (Value Decision)

1. **การเลือกฝั่ง (Asian Handicap):**
   * {ah_recommendation}
   * *ค่าน้ำยุติธรรมที่ควรได้ (Fair Odds):* `{res['fair_odds_ah']:.2f}`

2. **การเลือกสกอร์สูง / สกอร์ต่ำ (Over / Under):**
   * {ou_recommendation}
   * *ค่าน้ำยุติธรรม Over:* `{res['fair_odds_over']:.2f}` | *Under:* `{res['fair_odds_under']:.2f}`
""")
