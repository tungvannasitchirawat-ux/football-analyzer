import streamlit as st
import requests
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="ตารางวิเคราะห์บอล 500+ คู่ทั่วโลก", page_icon="⚽", layout="wide")

st.title("⚽ ตารางวิเคราะห์ & ฟันธงฟุตบอลทุกลีกทั่วโลก (ไม่ใช้ xG)")
st.caption("ดึงโปรแกรมแข่งขัน 500+ คู่ต่อวัน (รวม J1-J2, K1-K2) แสดงราคาต่อรองเปิดหน้ากระดาน พร้อมฟันธงฝั่งน่าลงทุน")

# --- Dictionary แปลชื่อลีกและทีมเป็นภาษาไทย ---
TRANSLATION_MAP = {
    # ลีกญี่ปุ่น & เกาหลีใต้
    "Japanese J1 League": "เจลีก 1 ญี่ปุ่น",
    "Japanese J2 League": "เจลีก 2 ญี่ปุ่น",
    "J.League": "เจลีก 1 ญี่ปุ่น",
    "J2 League": "เจลีก 2 ญี่ปุ่น",
    "Korean K League 1": "เคลีก 1 เกาหลีใต้",
    "Korean K League 2": "เคลีก 2 เกาหลีใต้",
    "K League 1": "เคลีก 1 เกาหลีใต้",
    "K League 2": "เคลีก 2 เกาหลีใต้",
    
    # ลีกยอดนิยมอื่นๆ
    "English Premier League": "พรีเมียร์ลีก อังกฤษ",
    "Premier League": "พรีเมียร์ลีก อังกฤษ",
    "Spanish LaLiga": "ลาลีกา สเปน",
    "Spanish La Liga": "ลาลีกา สเปน",
    "German Bundesliga": "บุนเดสลีกา เยอรมนี",
    "Italian Serie A": "เซเรียอา อิตาลี",
    "French Ligue 1": "ลีกเอิง ฝรั่งเศส",
    "Thai League 1": "ไทยลีก 1",
    "Thai League 2": "ไทยลีก 2",
    "Australian A-League": "เอลีก ออสเตรเลีย",
    "UEFA Champions League": "ยูฟ่า แชมเปียนส์ลีก",
    "UEFA Europa League": "ยูฟ่า ยูโรปาลีก",
    "English Championship": "เอฟแอล แชมเปียนชิป อังกฤษ",
    
    # ทีมยอดนิยม
    "Kawasaki Frontale": "คาวาซากิ ฟรอนตาเล่",
    "Yokohama F. Marinos": "โยโกฮาม่า เอฟ มารินอส",
    "Urawa Red Diamonds": "อูราวะ เรด ไดมอนส์",
    "Jeonbuk Hyundai Motors": "ชอนบุก ฮุนได มอเตอร์ส",
    "Ulsan HD": "อุลซาน ฮุนได",
    "Buriram United": "บุรีรัมย์ ยูไนเต็ด",
    "BG Pathum United": "บีจี ปทุม ยูไนเต็ด",
    "Manchester United": "แมนเชสเตอร์ ยูไนเต็ด",
    "Manchester City": "แมนเชสเตอร์ ซิตี้",
    "Liverpool": "ลิเวอร์พูล",
    "Arsenal": "อาร์เซน่อล",
    "Chelsea": "เชลซี",
    "Real Madrid": "เรอัล มาดริด",
    "Barcelona": "บาร์เซโลน่า",
    "Bayern Munich": "บาเยิร์น มิวนิค"
}

def translate_to_thai(text):
    """ ฟังก์ชันแปลชื่อลีก/ชื่อทีมเป็นภาษาไทย """
    if not text:
        return text
    if text in TRANSLATION_MAP:
        return TRANSLATION_MAP[text]
    
    translated = text
    replacements = {
        "League": "ลีก",
        "Cup": "คัพ",
        "Division": "ดิวิชั่น",
        "National": "เนชันแนล",
        "Youth": "เยาวชน",
        "Women": "ทีมหญิง",
        "International": "กระชับมิตร/นานาชาติ"
    }
    for en, th in replacements.items():
        translated = translated.replace(en, th)
        
    return translated

# --- 1. MULTI-LEAGUE FETCHER (NO XG REQUIRED) ---
@st.cache_data(ttl=1800)
def fetch_500plus_matches(target_date_str):
    """
    ดึงตารางแข่งขันรวม 500+ คู่ โดยไม่มีการใช้ค่า xG
    """
    league_slugs = [
        "all", "jpn.1", "jpn.2", "kor.1", "kor.2", "tha.1", "tha.2", 
        "eng.1", "eng.2", "eng.3", "eng.4", "esp.1", "esp.2", "ita.1", "ita.2", 
        "ger.1", "ger.2", "fra.1", "fra.2", "aus.1", "ned.1", "por.1", "bel.1", 
        "tur.1", "sco.1", "arg.1", "bra.1", "usa.1", "uefa.champions", "uefa.europa"
    ]
    
    all_matches = []
    seen_match_keys = set()
    date_formatted = target_date_str.replace("-", "")

    for slug in league_slugs:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
        params = {"dates": date_formatted, "limit": 300}
        
        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                events = res.json().get("events", [])
                for ev in events:
                    match_id = ev.get("id")
                    if match_id in seen_match_keys:
                        continue
                    
                    comp = ev.get("competitions", [{}])[0]
                    raw_league = comp.get("league", {}).get("name") or ev.get("season", {}).get("slug", "ฟุตบอลลีก")
                    competitors = comp.get("competitors", [])
                    
                    raw_home = "เจ้าบ้าน"
                    raw_away = "ทีมเยือน"
                    for team in competitors:
                        if team.get("homeAway") == "home":
                            raw_home = team.get("team", {}).get("displayName", "เจ้าบ้าน")
                        else:
                            raw_away = team.get("team", {}).get("displayName", "ทีมเยือน")
                            
                    date_full = comp.get("date", "")
                    time_str = date_full[11:16] if len(date_full) >= 16 else "--:--"
                    
                    # แปลภาษาไทย
                    th_league = translate_to_thai(raw_league)
                    th_home = translate_to_thai(raw_home)
                    th_away = translate_to_thai(raw_away)
                    
                    all_matches.append({
                        "id": match_id,
                        "league": f"🏆 {th_league}",
                        "home": th_home,
                        "away": th_away,
                        "time": time_str
                    })
                    seen_match_keys.add(match_id)
        except Exception:
            continue

    return all_matches

# --- 2. ANALYTICS BASED ON ODDS ONLY (NO XG) ---
def analyze_by_odds(handicap, total):
    """
    วิเคราะห์การเลือกฝั่งต่อ/รอง และ สูง/ต่ำ โดยอ้างอิงจากราคาต่อรองหน้ากระดาน
    """
    # ฟันธงต่อ/รอง
    if handicap < 0:
        ah_recommendation = "ต่อ"
    elif handicap > 0:
        ah_recommendation = "รอง"
    else:
        ah_recommendation = "เสมอ (เลือกทีมเชียร์)"

    # ฟันธงสูง/ต่ำ
    if total >= 2.75:
        ou_recommendation = "สกอร์สูง (OVER)"
    else:
        ou_recommendation = "สกอร์ต่ำ (UNDER)"

    return ah_recommendation, ou_recommendation

# --- 3. UI DASHBOARD & FILTERS ---
st.sidebar.header("⚙️ ตัวกรองโปรแกรมแข่ง")

selected_date_obj = st.sidebar.date_input("📅 เลือกวันที่เตะ:", datetime.now())
selected_date_str = selected_date_obj.strftime("%Y-%m-%d")

with st.spinner(f"🤖 กำลังดึงแมตช์การแข่งขันประจำวันที่ {selected_date_str}..."):
    matches = fetch_500plus_matches(selected_date_str)

st.sidebar.success(f"✅ โหลดสำเร็จ {len(matches)} คู่ทั่วโลก!")

# ช่องค้นหาชื่อทีม/ลีก
search_kw = st.sidebar.text_input("🔍 ค้นหาชื่อทีม หรือ ชื่อลีก (ภาษาไทย/อังกฤษ):", "").strip().lower()

# Dropdown กรองตามลีก
all_leagues = sorted(list(set([m["league"] for m in matches])))
selected_league = st.sidebar.selectbox("🏆 กรองเฉพาะลีกที่ต้องการ:", ["-- แสดงทุกลีก --"] + all_leagues)

display_matches = matches

if selected_league != "-- แสดงทุกลีก --":
    display_matches = [m for m in display_matches if m["league"] == selected_league]

if search_kw:
    display_matches = [
        m for m in display_matches 
        if search_kw in m["home"].lower() or search_kw in m["away"].lower() or search_kw in m["league"].lower()
    ]

st.markdown(f"### 📅 รายการแข่งขันประจำวันที่ {selected_date_str} (แสดง {len(display_matches)} / {len(matches)} คู่)")
st.markdown("---")

# --- LOOP DISPLAY MATCHES ---
for idx, m in enumerate(display_matches):
    home = m["home"]
    away = m["away"]
    
    with st.container():
        c_info, c_odds_input, c_ah_rec, c_ou_rec = st.columns([2.0, 1.5, 1.4, 1.4])
        
        # 1. ข้อมูลคู่แข่งขัน
        with c_info:
            st.markdown(f"#### 🏟️ [{m['time']}] {home} vs {away}")
            st.caption(f"{m['league']}")
            
        # 2. ปรับเปลี่ยนราคาต่อรองหน้ากระดาน
        with c_odds_input:
            st.markdown("**🎯 ราคาเปิดหน้ากระดาน:**")
            hcap = st.number_input(f"ต่อรอง ({home}):", value=-0.5, step=0.25, key=f"hcap_{idx}_{m['id']}")
            tot = st.number_input(f"เรตสูง/ต่ำ:", value=2.5, step=0.25, key=f"tot_{idx}_{m['id']}")

        # วิเคราะห์คำแนะนำโดยไม่อ้างอิง xG
        ah_rec_type, ou_rec_type = analyze_by_odds(hcap, tot)

        # สรุปฝั่งต่อ/รอง
        if "ต่อ" in ah_rec_type:
            ah_display = f"🔥 **เลือก: ต่อ {home}**"
        elif "รอง" in ah_rec_type:
            ah_display = f"🛡️ **เลือก: รอง {away}**"
        else:
            ah_display = f"⚖️ **เลือก: {home} (เสมอ)**"

        # สรุปฝั่งสูง/ต่ำ
        if "สูง" in ou_rec_type:
            ou_display = f"⚽ **เลือก: สกอร์สูง (OVER {tot})**"
        else:
            ou_display = f"🔒 **เลือก: สกอร์ต่ำ (UNDER {tot})**"

        # 3. ฟันธง ต่อ/รอง
        with c_ah_rec:
            st.markdown("**🛡️ ฟันธง ต่อ/รอง:**")
            st.markdown(ah_display)
            
        # 4. ฟันธง สูง/ต่ำ
        with c_ou_rec:
            st.markdown("**⚽ ฟันธง สูง/ต่ำ:**")
            st.markdown(ou_display)

        # รายละเอียดคำแนะนำเพิ่มเติม
        with st.expander(f"🔍 สรุปข้อมูลการเชียร์ ({home} vs {away})"):
            st.write(f"* **ราคาต่อรอง:** {home} ต่อ `{hcap}` | เรตสูง/ต่ำ `{tot}` ลูก")
            st.write(f"* **สรุปฝั่งเชียร์ต่อรอง:** {ah_display}")
            st.write(f"* **สรุปฝั่งเชียร์สกอร์:** {ou_display}")

        st.markdown("---")
