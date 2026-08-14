import streamlit as st
import requests
import math

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Football xG & Asian Handicap Analytics Engine",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Endpoint มาตรฐานที่ถูกต้องของ Sportmonks API v3
BASE_URL = "https://api.sportmonks.com/v3/football"

# ==========================================
# 2. HELPER & API FUNCTIONS
# ==========================================
def get_api_key():
    """ ดึง API Key จาก Streamlit Secrets หรือ Sidebar """
    if "SPORTMONKS_API_KEY" in st.secrets:
        return st.secrets["SPORTMONKS_API_KEY"]
    return st.sidebar.text_input("🔑 ใส่ Sportmonks API Key:", type="password")

@st.cache_data(ttl=1800)
def fetch_sportmonks_data(endpoint: str, api_key: str, params: dict = None):
    """ ฟังก์ชันกลางสำหรับดึงข้อมูล API """
    if not api_key:
        return None, "กรุณากรอก API Key"
    
    url = f"{BASE_URL}/{endpoint}"
    default_params = {"api_token": api_key}
    if params:
        default_params.update(params)
        
    try:
        response = requests.get(url, params=default_params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("data", []), None
    except requests.exceptions.HTTPError as err:
        return None, f"HTTP Error {err.response.status_code}: โปรดตรวจสอบ API Key หรือสิทธิ์ของแผนการใช้งาน"
    except requests.exceptions.RequestException as e:
        return None, f"Connection Error: {str(e)}"

def poisson_pmf(k: int, lambda_val: float) -> float:
    """ คำนวณความน่าจะเป็นของประตูด้วย Poisson Distribution """
    if lambda_val <= 0:
        return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

def calculate_ah_outcomes(home_xg: float, away_xg: float, handicap: float, max_goals: int = 8):
    """ คำนวณความน่าจะเป็นและ Fair Odds ของ Asian Handicap """
    home_probs = [poisson_pmf(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_pmf(i, away_xg) for i in range(max_goals)]
    
    win_ah, half_win_ah, push_ah, half_loss_ah, loss_ah = 0.0, 0.0, 0.0, 0.0, 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            diff = (h - a) + handicap
            
            if diff > 0.25:
                win_ah += p
            elif diff == 0.25:
                half_win_ah += p
            elif diff == 0.0:
                push_ah += p
            elif diff == -0.25:
                half_loss_ah += p
            else:
                loss_ah += p

    expected_return_prob = win_ah + (half_win_ah * 0.5) + (push_ah * 0.5)
    fair_odds = 1 / expected_return_prob if expected_return_prob > 0 else 0

    return {
        "win": win_ah * 100,
        "half_win": half_win_ah * 100,
        "push": push_ah * 100,
        "half_loss": half_loss_ah * 100,
        "loss": loss_ah * 100,
        "fair_odds": fair_odds
    }

# ==========================================
# 3. MAIN APPLICATION UI
# ==========================================
st.markdown('<p class="main-header">⚽ Football Analytics & Asian Handicap Engine</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">ระบบคำนวณความน่าจะเป็นและ Fair Odds จากสถิติ xG (Sportmonks API v3 Connected)</p>', unsafe_allow_html=True)

api_key = get_api_key()

if not api_key:
    st.info("💡 กรุณากรอก **Sportmonks API Key** ใน Secrets หรือในแถบเมนูด้านซ้ายเพื่อเริ่มใช้งาน")
    st.stop()

# --- SIDEBAR: MATCH SELECTOR ---
st.sidebar.header("⚙️ ตัวเลือกการวิเคราะห์")

with st.sidebar:
    with st.spinner("กำลังเชื่อมต่อตารางการแข่งขัน..."):
        # เรียกดูข้อมูลรายการนัดแข่งขันล่าสุด
        fixtures_data, error = fetch_sportmonks_data("fixtures", api_key, {
            "include": "participants;stats",
            "per_page": 20
        })

if error:
    st.sidebar.error(f"เกิดข้อผิดพลาด: {error}")
    st.stop()

if not fixtures_data:
    st.sidebar.warning("ไม่พบข้อมูลการแข่งขันในระบบขณะนี้")
    st.stop()

# แปลง Fixtures เป็นโครงสร้าง Dropdown ให้เลือกง่ายๆ
fixture_options = {}
for fix in fixtures_data:
    participants = fix.get("participants", [])
    home_name, away_name = "Home Team", "Away Team"
    
    for p in participants:
        location = p.get("meta", {}).get("location")
        if location == "home":
            home_name = p.get("name", "Home")
        elif location == "away":
            away_name = p.get("name", "Away")
            
    match_name = f"{home_name} vs {away_name}"
    fixture_options[match_name] = {
        "raw": fix,
        "home": home_name,
        "away": away_name
    }

selected_match_name = st.sidebar.selectbox("เลือกคู่แข่งขัน:", list(fixture_options.keys()))
selected_match = fixture_options[selected_match_name]

# สกัดค่า xG จาก Match Stats
stats = selected_match["raw"].get("stats", [])
home_xg_default = 1.55
away_xg_default = 1.15

for stat in stats:
    type_info = stat.get("type", {})
    if type_info.get("developer_name") == "EXPECTED_GOALS" or stat.get("type_id") == 52:
        loc = stat.get("location")
        val = float(stat.get("data", {}).get("value", 0))
        if loc == "home" and val > 0:
            home_xg_default = val
        elif loc == "away" and val > 0:
            away_xg_default = val

# --- DASHBOARD CONTENT ---
col_info1, col_info2 = st.columns([1, 1])

with col_info1:
    st.subheader("🏟️ ข้อมูลแมตช์")
    st.markdown(f"**แมตช์ที่เลือก:** `{selected_match_name}`")
    st.markdown(f"**สถานะ:** {selected_match['raw'].get('result_info', 'Scheduled / Upcoming')}")

with col_info2:
    st.subheader("📊 ค่า Expected Goals (xG)")
    c_xg1, c_xg2 = st.columns(2)
    with c_xg1:
        home_xg = st.number_input(f"xG {selected_match['home']}:", min_value=0.1, max_value=6.0, value=home_xg_default, step=0.05)
    with c_xg2:
        away_xg = st.number_input(f"xG {selected_match['away']}:", min_value=0.1, max_value=6.0, value=away_xg_default, step=0.05)

st.markdown("---")

# --- HANDICAP SELECTION & COMPUTATION ---
st.subheader("🎯 เลือกราคาต่อรอง Asian Handicap (AH)")

col_ah1, col_ah2 = st.columns([1, 2])

with col_ah1:
    handicap = st.selectbox(
        f"ราคาต่อรองของ {selected_match['home']} (ทีมเหย้า):",
        options=[-2.5, -2.25, -2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5],
        index=8 # Default -0.5
    )

res = calculate_ah_outcomes(home_xg, away_xg, handicap)

with col_ah2:
    st.subheader("📈 ผลการวิเคราะห์ความน่าจะเป็น")
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("โอกาสชนะราคา (Win)", f"{res['win']:.2f}%")
        if res['half_win'] > 0:
            st.metric("โอกาสได้ครึ่ง (Half Win)", f"{res['half_win']:.2f}%")
            
    with m2:
        st.metric("โอกาสเสมอ/ยก (Push)", f"{res['push']:.2f}%")
        
    with m3:
        st.metric("โอกาสเสียราคา (Loss)", f"{res['loss']:.2f}%")
        if res['half_loss'] > 0:
            st.metric("โอกาสเสียครึ่ง (Half Loss)", f"{res['half_loss']:.2f}%")

st.markdown("---")

# --- VALUE BET ANALYSIS ---
st.success(f"""
💡 **บทวิเคราะห์ราคาน้ำยุติธรรม (Fair Odds):**
* ทีมเหย้า **{selected_match['home']}** ที่ราคาต่อ **{handicap}** 
* ค่าน้ำ Decimal ยุติธรรมที่ควรได้คือ: **`{res['fair_odds']:.2f}`**
*(หากเว็บเปิดราคาค่าน้ำสูงกว่า `{res['fair_odds']:.2f}` แสดงว่าเป็นตัวเลือกที่มี Value ในการลงทุน)*
""")
