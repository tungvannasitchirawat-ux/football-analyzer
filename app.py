import streamlit as st
import math

st.set_page_config(page_title="Football Asian Handicap & Probability Calculator", layout="wide")
st.title("⚽ Football Asian Handicap & Probability Calculator")

# ฟังก์ชันคำนวณ Poisson โดยใช้ math (ไม่ต้องง้อ scipy)
def poisson_pmf(k, lambda_val):
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 กำหนดค่า Expected Goals (xG)")
    home_xg = st.number_input("xG ทีมเหย้า (Home xG)", min_value=0.1, max_value=5.0, value=1.65, step=0.05)
    away_xg = st.number_input("xG ทีมเยือน (Away xG)", min_value=0.1, max_value=5.0, value=1.10, step=0.05)

with col2:
    st.subheader("🎯 ราคาต่อรอง (Asian Handicap)")
    handicap = st.selectbox(
        "ราคาต่อรองทีมเหย้า (Home Handicap)",
        options=[-2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        index=6
    )

# --- คำนวณความน่าจะเป็น ---
max_goals = 8
home_probs = [poisson_pmf(i, home_xg) for i in range(max_goals)]
away_probs = [poisson_pmf(i, away_xg) for i in range(max_goals)]

# คำนวณ Asian Handicap Outcome
win_ah = 0.0
half_win_ah = 0.0
push_ah = 0.0
half_loss_ah = 0.0
loss_ah = 0.0

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

st.markdown("---")
st.subheader("📈 ผลการวิเคราะห์ความน่าจะเป็น")

res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.metric("โอกาสชนะราคา (Win Full)", f"{win_ah*100:.2f}%")
    if half_win_ah > 0:
        st.metric("โอกาสได้ครึ่ง (Half Win)", f"{half_win_ah*100:.2f}%")

with res_col2:
    st.metric("โอกาสเสมอ/ยก (Push)", f"{push_ah*100:.2f}%")

with res_col3:
    st.metric("โอกาสเสียราคา (Loss Full)", f"{loss_ah*100:.2f}%")
    if half_loss_ah > 0:
        st.metric("โอกาสเสียครึ่ง (Half Loss)", f"{half_loss_ah*100:.2f}%")

expected_return_prob = win_ah + (half_win_ah * 0.5) + (push_ah * 0.5)
fair_odds = 1 / expected_return_prob if expected_return_prob > 0 else 0

st.success(f"💡 **Fair Odds (ราคาน้ำที่คุ้มค่าสำหรับทีมเหย้าที่ต่อ {handicap}):** {fair_odds:.2f}")
