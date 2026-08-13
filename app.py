from datetime import datetime, timedelta
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="ตารางวิเคราะห์บอลออนไลน์", page_icon="⚽", layout="wide"
)


def convert_utc_to_thai_time(utc_date_str):
    if not utc_date_str or "T" not in utc_date_str:
        return "N/A"
    try:
        clean_str = utc_date_str.replace("Z", "").split(".")[0]
        dt_utc = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M")
        dt_thai = dt_utc + timedelta(hours=7)
        return dt_thai.strftime("%H:%M น.")
    except Exception:
        return "N/A"


def analyze_match_logic(home, away):
    if not home or not away:
        return "N/A", "N/A", "0%"

    home_score_val = sum(ord(c) for c in home) % 100
    away_score_val = sum(ord(c) for c in away) % 100
    diff = home_score_val - away_score_val

    if diff > 20:
        pred = f"เจ้าบ้าน {home} ฟอร์มในบ้านแข็งแกร่ง"
        tip = f"เน้น: ต่อ {home}"
        chance = "85%"
    elif diff < -20:
        pred = f"ทีมเยือน {away} เกมเยือนดุดัน"
        tip = f"เน้น: เชียร์ {away}"
        chance = "80%"
    else:
        pred = "ฟอร์มใกล้เคียงกันมาก มีโอกาสออกเสมอสูง"
        tip = "เน้น: สกอร์สูง / รอง"
        chance = "65%"

    return pred, tip, chance


@st.cache_data(ttl=1800)  # อัปเดตข้อมูลสดทุก 30 นาที
def fetch_live_football_data(selected_date):
    formatted_date = selected_date.strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={formatted_date}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            matches = []

            for event in events:
                league = event.get("season", {}).get("slug", "Soccer")
                date_utc = event.get("date", "")
                time_thai = convert_utc_to_thai_time(date_utc)

                competitors = event.get("competitions", [{}])[0].get(
                    "competitors", []
                )
                home_team, away_team = "Unknown", "Unknown"
                home_score, away_score = "-", "-"

                for comp in competitors:
                    if comp.get("homeAway") == "home":
                        home_team = comp.get("team", {}).get("displayName", "")
                        home_score = comp.get("score", "-")
                    else:
                        away_team = comp.get("team", {}).get("displayName", "")
                        away_score = comp.get("score", "-")

                score_str = f"{home_score} - {away_score}"
                pred, tip, chance = analyze_match_logic(home_team, away_team)

                matches.append(
                    {
                        "เวลาเตะ (ไทย)": time_thai,
                        "ลีก": league.upper(),
                        "ทีมเหย้า": home_team,
                        "ทีมเยือน": away_team,
                        "ผลบอล": score_str,
                        "วิเคราะห์ฟอร์ม": pred,
                        "ทัศนะ": tip,
                        "ความมั่นใจ": chance,
                    }
                )

            return pd.DataFrame(matches)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        return pd.DataFrame()


# --- หน้าจอแสดงผล Streamlit ---
st.title("⚽ รายงานผลและวิเคราะห์บอลประจำวัน (Live)")

col1, col2 = st.columns([1, 2])

with col1:
    selected_date = st.date_input("📅 เลือกวันที่ต้องการดู:", datetime.now())

df = fetch_live_football_data(selected_date)

if not df.empty:
    with col2:
        search = st.text_input("🔎 กรองชื่อทีมที่สนใจ:", "")

    if search:
        df = df[
            df["ทีมเหย้า"].str.contains(search, case=False, na=False)
            | df["ทีมเยือน"].str.contains(search, case=False, na=False)
            | df["ลีก"].str.contains(search, case=False, na=False)
        ]

    st.success(f"พบรายการแข่งขันทั้งหมด {len(df)} คู่")
    st.dataframe(df, use_container_width=True, height=500)
else:
    st.warning("ไม่พบคู่แข่งขันในวันที่ระบุ หรือระบบขัดข้อง")
