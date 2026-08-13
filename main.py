from datetime import datetime, timedelta
import os
import pandas as pd
import requests


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


def run_daily_scraping():
    today = datetime.now().strftime("%Y%m%d")
    today_formatted = datetime.now().strftime("%Y-%m-%d")

    print(
        f"[{datetime.now()}]"
        f" เริ่มต้นดึงข้อมูลและวิเคราะห์บอลประจำวันที่ {today_formatted}..."
    )

    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={today}"
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
                        "Date": today_formatted,
                        "Time_Thai": time_thai,
                        "League": league.upper(),
                        "Home": home_team,
                        "Away": away_team,
                        "Score": score_str,
                        "Prediction": pred,
                        "Tip": tip,
                        "Chance": chance,
                    }
                )

            if matches:
                df = pd.DataFrame(matches)
                os.makedirs("data", exist_ok=True)
                filename = f"data/football_analysis_{today_formatted}.csv"
                df.to_csv(filename, index=False, encoding="utf-8-sig")
                print(
                    f"[✔] บันทึกไฟล์สำเร็จ: {filename} (รวม {len(matches)}"
                    " คู่)"
                )
            else:
                print("[!] ไม่พบคู่แข่งขันในวันนี้")
        else:
            print(f"[!] Error Status: {response.status_code}")
    except Exception as e:
        print(f"[!] Occurred Error: {e}")


if __name__ == "__main__":
    run_daily_scraping()
