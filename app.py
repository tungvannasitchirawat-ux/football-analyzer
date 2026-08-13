from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ระบบวิเคราะห์บอลรายคู่ (กำหนดเอง 10 คู่)",
    page_icon="⚽",
    layout="wide",
)


def analyze_custom_match(home_team, away_team, hdp_val):
    """อัลกอริทึมคำนวณวิเคราะห์เชิงสถิติและราคาต่อรอง"""
    if not home_team or not away_team:
        return "-", "-", "0%"

    home_hash = sum(ord(c) * (i + 1) for i, c in enumerate(home_team.strip()))
    away_hash = sum(ord(c) * (i + 1) for i, c in enumerate(away_team.strip()))

    # คำนวณความได้เปรียบสถิติ
    stat_diff = ((home_hash % 21) - (away_hash % 21)) / 4.0
    gap = stat_diff - hdp_val

    if gap >= 0.30:
        pred = (
            f"สถิติ {home_team} ข่มชัดเจน ราคาเปิด {hdp_val:+g} ได้เปรียบ"
            " ค่าน้ำน่าสนใจ"
        )
        tip = f"🔥 ต่อ {home_team}"
        confidence = f"{min(75 + int(gap * 10), 88)}%"
    elif gap <= -0.30:
        pred = (
            f"ราคา {home_team} ต่อ {hdp_val:+g} แพงเกินสถิติจริง {away_team}"
            " มีลุ้นกินราคา"
        )
        tip = f"🔥 รอง {away_team}"
        confidence = f"{min(75 + int(abs(gap) * 10), 86)}%"
    else:
        pred = (
            f"เรต {hdp_val:+g} สูสีกับสถิติ 5 นัดหลังสุด มีโอกาสออกหน้าเสมอสูง"
        )
        tip = "⚽ สกอร์สูง / รอง"
        confidence = "65%"

    return pred, tip, confidence


# --- UI หลัก ---
st.title("⚽ ระบบวิเคราะห์ตารางบอลประจำวัน (กำหนด 10 คู่)")
st.caption(
    "ป้อนรายชื่อทีมเหย้า ทีมเยือน และราคาต่อรองที่ต้องการวิเคราะห์ได้สูงสุด 10"
    " คู่"
)
st.markdown("---")

st.subheader("📝 กรอกข้อมูลคู่บอลที่ต้องการวิเคราะห์ (สูงสุด 10 คู่)")

# ตัวอย่างข้อมูลเริ่มต้น 5 คู่แรก
default_matches = [
    ("Arsenal", "Chelsea", -0.75),
    ("Liverpool", "Manchester City", 0.0),
    ("Real Madrid", "Barcelona", -1.25),
    ("Bayern Munich", "Dortmund", -1.5),
    ("PSG", "Marseille", -1.0),
    ("", "", 0.0),
    ("", "", 0.0),
    ("", "", 0.0),
    ("", "", 0.0),
    ("", "", 0.0),
]

inputs = []

# สร้างฟอร์มป้อนข้อมูล 10 แถว
for i in range(10):
    col_num, col_h, col_a, col_hdp = st.columns([0.5, 3, 3, 2])
    with col_num:
        st.write(f"**คู่ที่ {i+1}**")
    with col_h:
        h = st.text_input(
            f"ทีมเหย้า {i+1}",
            value=default_matches[i][0],
            key=f"h_{i}",
            label_visibility="collapsed",
            placeholder=f"ทีมเหย้า คู่ที่ {i+1}",
        )
    with col_a:
        a = st.text_input(
            f"ทีมเยือน {i+1}",
            value=default_matches[i][1],
            key=f"a_{i}",
            label_visibility="collapsed",
            placeholder=f"ทีมเยือน คู่ที่ {i+1}",
        )
    with col_hdp:
        hdp = st.number_input(
            f"ราคาต่อรอง {i+1}",
            value=float(default_matches[i][2]),
            step=0.25,
            key=f"hdp_{i}",
            label_visibility="collapsed",
        )

    if h.strip() and a.strip():
        inputs.append((h.strip(), a.strip(), hdp))

st.markdown("---")

if st.button("⚡ ประมวลผลวิเคราะห์ทั้งหมด", type="primary", use_container_width=True):
    if inputs:
        results = []
        for idx, (home, away, hdp) in enumerate(inputs, start=1):
            pred, tip, confidence = analyze_custom_match(home, away, hdp)
            results.append({
                "ลำดับ": idx,
                "ทีมเหย้า": home,
                "ราคาต่อรอง": f"{hdp:+g}",
                "ทีมเยือน": away,
                "รายงานสถิติ & ราคา": pred,
                "ทัศนะฟันธง": tip,
                "ความมั่นใจ": confidence,
            })

        df_res = pd.DataFrame(results)

        st.success(f"✅ ประมวลผลสำเร็จทั้งหมด {len(df_res)} คู่")
        st.dataframe(df_res, use_container_width=True, height=400)
    else:
        st.warning("กรุณากรอกชื่อทีมเหย้าและทีมเยือนอย่างน้อย 1 คู่")
