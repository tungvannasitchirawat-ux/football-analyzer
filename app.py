# --- กล่องสรุปผลการวิเคราะห์ (เวอร์ชันฟันธง อ่านง่าย ชัดเจน) ---
st.markdown("---")
st.subheader("📌 สรุปฟันธงคำแนะนำการลงทุน (Direct Recommendation)")

# 1. คำนวณฝั่ง Asian Handicap (ต่อ/รอง)
ah_status = ""
ah_action = ""
ah_color = "warning"

if res['win'] >= 52.0:
    ah_status = "🟢 ฟันธง: น่าลงทุน"
    ah_action = f"**วางฝั่ง ต่อ {home_team}** (ราคา {handicap_input}) | โอกาสชนะราคา {res['win']:.1f}%"
    ah_color = "success"
elif res['loss'] >= 52.0:
    ah_status = "🟢 ฟันธง: น่าลงทุน"
    ah_action = f"**วางฝั่ง รอง {away_team}** | โอกาสรอดราคา/ชนะรอง {res['loss']:.1f}%"
    ah_color = "success"
else:
    ah_status = "🔴 ฟันธง: งดเล่น / ให้ข้ามคู่นี้ (PASS)"
    ah_action = "**ไม่แนะนำให้วางต่อหรือรอง** — บอลสูสีกันเกินไป ไม่มีฝั่งไหนได้เปรียบเชิงสถิติ"
    ah_color = "error"

# 2. คำนวณฝั่ง Over/Under (สูง/ต่ำ)
ou_status = ""
ou_action = ""

if res['expected_total_goals'] > (live_total_point + 0.3):
    ou_status = "🟢 ฟันธง: น่าเล่นสกอร์สูง"
    ou_action = f"**กด สกอร์สูง (OVER {live_total_point})** | คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก"
elif res['expected_total_goals'] < (live_total_point - 0.3):
    ou_status = "🟢 ฟันธง: น่าเล่นสกอร์ต่ำ"
    ou_action = f"**กด สกอร์ต่ำ (UNDER {live_total_point})** | คาดการณ์ประตูรวมประมาณ {res['expected_total_goals']:.2f} ลูก"
else:
    ou_status = "🔴 ฟันธง: งดเล่นสกอร์สูง/ต่ำ (PASS)"
    ou_action = f"**ไม่แนะนำให้เล่นสูง/ต่ำ** — ประตูคาดการณ์ ({res['expected_total_goals']:.2f} ลูก) ใกล้เคียงราคาเปิดมากเกินไป"

# แสดงผลแบบการ์ดแยก 2 ฝั่งชัดเจน
col_rec1, col_rec2 = st.columns(2)

with col_rec1:
    st.markdown(f"### 🛡️ ฝั่งต่อ/รอง (Asian Handicap)")
    if "🟢" in ah_status:
        st.success(f"{ah_status}\n\n👉 {ah_action}\n\n*ค่าน้ำที่คุ้มเสี่ยง (Fair Odds):* `{res['fair_odds_ah']:.2f}` ขึ้นไป")
    else:
        st.error(f"{ah_status}\n\n👉 {ah_action}")

with col_rec2:
    st.markdown(f"### ⚽ ฝั่งสกอร์สูง/ต่ำ (Over/Under)")
    if "🟢" in ou_status:
        st.success(f"{ou_status}\n\n👉 {ou_action}\n\n*ค่าน้ำที่คุ้มเสี่ยง:* Over `{res['fair_odds_over']:.2f}` | Under `{res['fair_odds_under']:.2f}`")
    else:
        st.error(f"{ou_status}\n\n👉 {ou_action}")
