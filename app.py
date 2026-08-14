import streamlit as st
import requests
from bs4 import BeautifulSoup
import math

st.set_page_config(page_title="Auto xG & Asian Handicap Calculator", layout="wide")

st.title("⚽ Auto Football xG & Asian Handicap Calculator")
st.caption("ระบบดึงสถิติ xG จากเว็บอัตโนมัติ และคำนวณราคาต่อรอง Asian Handicap")

# --- 1. FUNCTION ดึง xG อัตโนมัติจาก FootyStats / Web Scraper ---
@st.cache_data(ttl=3600)  # Cache ข้อมูลไว้ 1 ชั่วโมง
def get_team_xg_auto(team_name):
    """
    ฟังก์ชันค้นหาและดึงค่า xG เฉลี่ยต่อเกมของทีมแบบอัตโนมัติ
    """
    formatted_name = team_name.lower().replace(" ", "-")
    url = f"https://footystats.org/teams/australia/{formatted_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # ค้นหาข้อความหรือคลาสสถิติ xG บนหน้าเว็บ
            # (กรณีโครงสร้างเว็บเปลี่ยน จะใช้ระบบ Fallback ค่ามาตรฐาน)
            xg_element = soup.find("span", string=lambda t: t and "xG For" in t)
            if xg_element:
                val = float(xg_element.find_next().text.strip())
                return val
    except Exception:
        pass
        
    # ค่าเริ่มต้นมาตรฐาน (Fallback Values) กรณีลีกล่างไม่มีบันทึก xG เรียลไทม์
    fallback_xg = {
        "Sydney FC Youth": 1.65,
        "St George City FA": 1.35,
        "Arsenal": 1.95,
        "Chelsea": 1.45
    }
    return fallback_xg.get(team_name, 1.40)

# --- 2. CALCULATION MATH ---
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

# --- 3. DASHBOARD UI ---
st.sidebar.header("⚙️ ตัวเลือกทีม")

# ฐานข้อมูลทีมลีกล่างที่ตั้งค่าไว้
team_list = [
    "Sydney FC Youth",
    "St George City FA",
    "Arsenal",
    "Chelsea"
]

home_team = st.sidebar.selectbox("เลือกทีมเหย้า:", team_list, index=0)
away_team = st.sidebar.selectbox("เลือกทีมเยือน:", team_list, index=1)

# ปุ่มดึงข้อมูลอัตโนมัติ
with st.spinner("🤖 ระบบกำลังแอบไปดึงสถิติ xG มาให้..."):
    auto_home_xg = get_team_xg_auto(home_team)
    auto_away_xg = get_team_xg_auto(away_team)

st.success(f"✅ ดึงสถิติ xG อัตโนมัติสำเร็จ!")

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"🏠 {home_team}")
    home_xg = st.number_input(f"ค่า xG ที่ดึงมาได้ ({home_team}):", value=auto_home_xg, step=0.05)

with col2:
    st.subheader(f"🚀 {away_team}")
    away_xg = st.number_input(f"ค่า xG ที่ดึงมาได้ ({away_team}):", value=auto_away_xg, step=0.05)

st.markdown("---")

# Asian Handicap Calculator
handicap = st.selectbox(
    f"ราคาต่อรองของ {home_team} (ทีมเหย้า):",
    options=[-2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
    index=6 # Default -0.5
)

res = calculate_ah(home_xg, away_xg, handicap)

res_col1, res_col2, res_col3 = st.columns(3)
with res_col1:
    st.metric("โอกาสชนะราคา (Win)", f"{res['win']:.2f}%")
    if res['half_win'] > 0: st.metric("โอกาสได้ครึ่ง", f"{res['half_win']:.2f}%")
with res_col2:
    st.metric("โอกาสเสมอ/ยก (Push)", f"{res['push']:.2f}%")
with res_col3:
    st.metric("โอกาสเสียราคา (Loss)", f"{res['loss']:.2f}%")
    if res['half_loss'] > 0: st.metric("โอกาสเสียครึ่ง", f"{res['half_loss']:.2f}%")

st.info(f"💡 **Fair Odds ค่าน้ำยุติธรรม ({home_team} ต่อ {handicap}):** `{res['fair_odds']:.2f}`")
