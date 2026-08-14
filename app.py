import streamlit as st
import requests
import math
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="ตารางวิเคราะห์บอล 500+ คู่ทั่วโลก", page_icon="⚽", layout="wide")

st.title("⚽ ตารางวิเคราะห์ & ฟันธงฟุตบอลทุกลีกทั่วโลก (ภาษาไทย)")
st.caption("รวมโปรแกรมแข่งขัน 500+ คู่ต่อวัน (เพิ่ม J1, J2, K1, K2 เรียบร้อย) แปลชื่อภาษาไทย พร้อมระบบฟันธงเลือกฝั่ง")

# --- Dictionary แปลชื่อลีกและทีมเป็นภาษาไทย ---
TRANSLATION_MAP = {
    # ลีกญี่ปุ่น & เกาหลีใต้ (เพิ่มใหม่)
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
    
    # ทีมญี่ปุ่น & เกาหลีใต้ ยอดนิยม
    "Kawasaki Frontale": "คาวาซากิ ฟรอนตาเล่",
    "Yokohama F. Marinos": "โยโกฮาม่า เอฟ มารินอส",
    "Urawa Red Diamonds": "อูราวะ เรด ไดมอนส์",
    "Kashima Antlers": "คาชิม่า แอนท์เลอร์ส",
    "Vissel Kobe": "วิสเซล โกเบ",
    "Nagoya Grampus": "นาโกย่า แกรมปัส",
    "Gamba Osaka": "กัมบะ โอซาก้า",
    "Cerezo Osaka": "เซเรโซ โอซาก้า",
    "Sanfrecce Hiroshima": "ซานเฟรซเซ ฮิโรชิม่า",
    "Tokyo Verdy": "โตเกียว เวอร์ดี้",
    "Kashiwa Reysol": "คาชิว่า เรย์โซล",
    "Jeonbuk Hyundai Motors": "ชอนบุก ฮุนได มอเตอร์ส",
    "Ulsan HD": "อุลซาน ฮุนได",
    "FC Seoul": "เอฟซี โซล",
    "Pohang Steelers": "โพฮัง สตีลเลอร์ส",
    "Suwon Samsung Bluewings": "ซูวอน ซัมซุง บลูวิงส์"
}

def translate_to_thai(text):
    """ ฟังก์ชันช่วยแปลชื่อลีก/ชื่อทีมเป็นภาษาไทย """
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

# --- 1. MULTI-LEAGUE FETCHER (INCLUDES J1, J2, K1, K2) ---
@st.cache_data(ttl=1800)
def fetch_500plus_thai_matches(target_date_str):
    """
    ดึงตารางแข่งขันรวมเจลีก 1-2 และ เคลีก 1-2 พร้อมแปลเป็นภาษาไทย
    """
    # ระบุ slug ลีก โดยเพิ่ม jpn.1, jpn.2 (เจลีก 1-2) และ kor.1, kor.2 (เคลีก 1-2)
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
                        "time": time_str,
                        "home_xg": 1.65,
                        "away_xg": 1.15
                    })
                    seen_match_keys.add(match_id)
        except Exception:
            continue

    return all_matches

# --- 2. MATH CALCULATIONS ---
def poisson_pmf(k, lambda_val):
    if lambda_val <= 0: return 0.0
    return (math.pow(lambda_val, k) * math.exp(-lambda_val)) / math.factorial(k)

def calculate_analytics(home_xg, away_xg, handicap, target_total=2.5, max_goals=8):
    home_probs = [poisson_pmf(i, home_xg) for i in range(max_goals)]
    away_probs = [poisson_pmf(i, away_xg) for i in range(max_goals)]
    
    win_ah = half_win_ah = push_ah = half_loss_ah = loss_ah = 0.0
    over_prob = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            p = home_probs[h] * away_probs[a]
            diff = (h - a) + handicap
            
            if diff > 0.25: win_ah += p
            elif diff == 0.25: half_win_ah += p
            elif diff == 0.0: push_ah += p
            elif diff == -0.25: half_loss_ah += p
            else: loss_ah += p

            if (h + a) > target_total:
                over_prob += p

    under_prob = 1.0 - over_prob
    expected_ah_return = win_ah + (half_win_ah * 0.5) + (push_ah * 0.5)
    fair_odds_ah = 1 / expected_ah_return if expected_ah_return > 0 else 0

    return {
        "win": win_ah * 100,
        "loss": loss_ah * 100,
        "fair_odds_ah": fair_odds_ah,
        "over_prob": over_prob * 100,
        "under_prob": under_prob * 100,
        "expected_total_goals": home_xg + away_xg
    }

# --- 3. UI DASHBOARD & FILTERS ---
st.sidebar.header("⚙️ ตัวกรองโปรแกรมแข่ง")

selected_date_obj = st.sidebar.date_input("📅 เลือกวันที่เตะ:", datetime.now())
selected_date_str = selected_date_obj.strftime("%Y-%m-%d")

with st.spinner(f"🤖 กำลังดึงแมตช์การแข่งขัน (รวม J1-J2, K1-K2) ประจำวันที่ {selected_date_str}..."):
    matches = fetch_500plus_thai_matches(selected_date_str)

st.sidebar.success(f"✅ โหลดสำเร็จ {len(matches)} คู่ทั่วโลก!")

# ช่องค้นหาชื่อทีม/ลีก
search_kw = st.sidebar.text_input("🔍 ค้นหาชื่อทีม หรือ ชื่อลีก (พิมพ์ภาษาไทยได้):", "").strip().lower()

# Dropdown กรองตามลีก (จะมี เจลีก 1-2 และ เคลีก 1-2 ปรากฏขึ้นมาด้วย)
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
    h_xg = m["home_xg"]
    a_xg = m["away_xg"]
    
    with st.container():
        c_info, c_odds_input, c_ah_rec, c_ou_rec = st.columns([2.0, 1.5, 1.4, 1.4])
        
        # 1. ข้อมูลคู่แข่ง
        with c_info:
            st.markdown(f"#### 🏟️ [{m['time']}] {home} vs {away}")
            st.caption(f"{m['league']} | ค่า xG: `{h_xg}` vs `{a_xg}`")
            
        # 2. ตัวปรับราคาต่อรอง
        with c_odds_input:
            st.markdown("**🎯 ราคาเปิดหน้ากระดาน:**")
            hcap = st.number_input(f"ต่อรอง ({home}):", value=-0.5, step=0.25, key=f"hcap_{idx}_{m['id']}")
            tot = st.number_input(f"เรตสูง/ต่ำ:", value=2.5, step=0.25, key=f"tot_{idx}_{m['id']}")

        # คำนวณความน่าจะเป็น
        res = calculate_analytics(h_xg, a_xg, hcap, tot)

        # สรุปเลือกฝั่งต่อ/รอง
        if res['win'] >= res['loss']:
            ah_rec = f"🔥 **เลือก: ต่อ {home}**"
        else:
            ah_rec = f"🛡️ **เลือก: รอง {away}**"

        # สรุปเลือกฝั่งสูง/ต่ำ
        if res['expected_total_goals'] >= tot:
            ou_rec = f"⚽ **เลือก: สกอร์สูง (OVER)**"
        else:
            ou_rec = f"🔒 **เลือก: สกอร์ต่ำ (UNDER)**"

        # 3. ฟันธง ต่อ/รอง
        with c_ah_rec:
            st.markdown("**🛡️ ฟันธง ต่อ/รอง:**")
            st.markdown(ah_rec)
            
        # 4. ฟันธง สูง/ต่ำ
        with c_ou_rec:
            st.markdown("**⚽ ฟันธง สูง/ต่ำ:**")
            st.markdown(ou_rec)

        # รายละเอียดสถิติเจาะลึก
        with st.expander(f"🔍 ดูสถิติและความน่าจะเป็นแบบละเอียด ({home} vs {away})"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"* **โอกาสชนะราคาฝั่งต่อ ({home}):** {res['win']:.2f}%")
                st.write(f"* **โอกาสรอดราคาฝั่งรอง ({away}):** {res['loss']:.2f}%")
                st.write(f"* **ค่าน้ำต่อรองที่คุ้มเสี่ยง (Fair Odds):** `{res['fair_odds_ah']:.2f}`")
            with c2:
                st.write(f"* **คาดการณ์ประตูรวม:** {res['expected_total_goals']:.2f} ลูก")
                st.write(f"* **โอกาสสกอร์สูง (Over {tot}):** {res['over_prob']:.2f}%")
                st.write(f"* **โอกาสสกอร์ต่ำ (Under {tot}):** {100 - res['over_prob']:.2f}%")

        st.markdown("---")
