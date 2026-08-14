import streamlit as st
import math

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Football xG & Asian Handicap Analytics Engine",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Football Analytics & Asian Handicap Engine")
st.caption("ระบบคำนวณความน่าจะเป็นและ Fair Odds จากสถิติ xG (Asian Handicap Calculator)")

# ==========================================
# 2. CALCULATION FUNCTIONS
# ==========================================
def poisson_pmf(k: int, lambda_val: float) -> float:
    """ คำนวณ Poisson Distribution """
    if lambda_val <= 0:
        return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

def calculate_ah_outcomes(home_xg: float, away_xg: float, handicap: float, max_goals: int = 8):
    """ คำนวณความน่าจะเป็น Asian Handicap """
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
# 3. UI DASHBOARD
# ==========================================
st.sidebar.header("⚙️ ตัวเลือกการวิเคราะห์")

# รายการคู่แข่งตัวอย่าง
sample_matches = {
    "Arsenal vs Chelsea": {"home": "Arsenal", "away": "Chelsea", "home_xg": 1.85, "away_xg": 1.10},
    "Real Madrid vs Barcelona": {"home": "Real Madrid", "away": "Barcelona", "home_xg": 1.65, "away_xg": 1.50},
    "Man City vs Liverpool": {"home": "Man City", "away": "Liverpool", "home_xg": 1.90, "away_xg": 1.35},
    "กำหนดค่าเอง (Custom Team)": {"home": "ทีมเหย้า", "away": "ทีมเยือน", "home_xg": 1.50, "away_xg": 1.20}
}

selected_match_key = st.sidebar.selectbox("เลือกคู่แข่งขันตัวอย่าง:", list(sample_matches.keys()))
selected_match = sample_matches[selected_match_key]

st.markdown("---")
col_info1, col_info2 = st.columns([1, 1])

with col_info1:
    st.subheader("🏟️ คู่แข่งขัน")
    home_name = st.text_input("ชื่อทีมเหย้า:", value=selected_match["home"])
    away_name = st.text_input("ชื่อทีมเยือน:", value=selected_match["away"])

with col_info2:
    st.subheader("📊 กำหนดค่า Expected Goals (xG)")
    c_xg1, c_xg2 = st.columns(2)
    with c_xg1:
        home_xg = st.number_input(f"xG {home_name}:", min_value=0.1, max_value=6.0, value=selected_match["home_xg"], step=0.05)
    with c_xg2:
        away_xg = st.number_input(f"xG {away_name}:", min_value=0.1, max_value=6.0, value=selected_match["away_xg"], step=0.05)

st.markdown("---")

# --- ASIAN HANDICAP COMPUTATION ---
st.subheader("🎯 วิเคราะห์ราคาต่อรอง (Asian Handicap)")

col_ah1, col_ah2 = st.columns([1, 2])

with col_ah1:
    handicap = st.selectbox(
        f"ราคาต่อรองของ {home_name} (ทีมเหย้า):",
        options=[-2.5, -2.25, -2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5],
        index=8 # Default -0.5
    )

res = calculate_ah_outcomes(home_xg, away_xg, handicap)

with col_ah2:
    st.subheader("📈 ผลลัพธ์ความน่าจะเป็น")
    
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

st.success(f"""
💡 **บทวิเคราะห์ราคาน้ำยุติธรรม (Fair Odds):**
* ทีมเหย้า **{home_name}** ที่ราคาต่อ **{handicap}** 
* ค่าน้ำ Decimal ยุติธรรมที่ควรได้คือ: **`{res['fair_odds']:.2f}`**
*(หากค่าน้ำบนเว็บสูงกว่า `{res['fair_odds']:.2f}` แสดงว่ามีความคุ้มค่าเชิงสถิติ หรือ Value Bet)*
""")
