from datetime import datetime
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ตารางวิเคราะห์บอลออนไลน์", page_icon="⚽", layout="wide"
)

st.title("⚽ รายงานผลและวิเคราะห์บอลประจำวัน")

today_str = datetime.now().strftime("%Y-%m-%d")
file_path = f"data/football_analysis_{today_str}.csv"

if os.path.exists(file_path):
    df = pd.read_csv(file_path)

    # ช่องค้นหาทีม
    search = st.text_input("🔎 กรองชื่อทีมที่สนใจ:", "")
    if search:
        df = df[
            df["Home"].str.contains(search, case=False, na=False)
            | df["Away"].str.contains(search, case=False, na=False)
            | df["League"].str.contains(search, case=False, na=False)
        ]

    st.write(f"พบรายการแข่งขันทั้งหมด {len(df)} คู่")
    st.dataframe(df, use_container_width=True)
else:
    st.warning(
        f"ยังไม่พบข้อมูลของวันที่ {today_str} (รอระบบรันอัตโนมัติช่วง 07:00"
        " น.)"
    )
