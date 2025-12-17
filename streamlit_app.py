import streamlit as st
import datetime
from datetime import timedelta

# --- 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v1.2", layout="wide")

# --- 色彩計劃 CSS ---
st.markdown("""
    <style>
    :root {
        --main-yellow: #FFB81C;    /* PANTONE 1235C */
        --accent-orange: #FF4438;  /* Warm Red / 172U */
        --dark-grey: #2D2926;      /* K85 */
    }
    .stApp { background-color: #ffffff; }
    h1, h2, h3, label { color: var(--dark-grey) !important; font-weight: bold !important; }
    .stButton>button { 
        background-color: var(--main-yellow); 
        color: var(--dark-grey); 
        border: none; width: 100%; border-radius: 5px; font-size: 18px;
    }
    .metric-container {
        background-color: #f8f9fa; padding: 20px; border-radius: 10px;
        border-left: 10px solid var(--main-yellow);
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏗️ 建築施工工期估算輔助系統")

# --- 側邊欄：核心參數 ---
with st.sidebar:
    st.header("🏢 建築規模與資訊")
    b_type = st.selectbox("建物類型", ["住宅", "辦公大樓", "百貨", "廠房", "醫院"])
    b_struct = st.selectbox("結構型式", ["RC造", "SRC造", "SS造", "SC造"])
    b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
    
    st.divider()
    base_area = st.number_input("基地面積 (坪)", min_value=10, value=500, step=10)
    floors_up = st.number_input("地上層數", min_value=1, value=12)
    floors_down = st.number_input("地下層數", min_value=0, value=3)
    
    st.divider()
    st.header("🧱 基地現況與基礎")
    # 新增項目：基地現況
    site_condition = st.selectbox("基地現況", [
        "純空地 (無須拆除)", 
        "有舊建物 (需地上物拆除)", 
        "有舊地下室 (需額外破除處理)"
    ])
    soil_improvement = st.selectbox("地質改良項目", ["無", "局部地質改良 (JSP/CCP)", "全區地質改良"])

# --- 主要區域 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏁 階段一：前置作業")
    prep_type = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"])
    if prep_type == "一般 (120天)": prep_days = 120
    elif "鄰捷運" in prep_type: prep_days = 210
    elif "環評" in prep_type: prep_days = 300
    else: prep_days = st.number_input("前置天數", value=120)

    st.subheader("📝 結尾階段")
    inspection_days = 90 if b_type in ["住宅", "廠房"] else 150
    st.write(f"預估消檢與使照天數：**{inspection_days}** 天")

with col2:
    st.subheader("📅 時間修正設定")
    start_date = st.date_input("預計開工日期", datetime.date.today())
    use_correction = st.checkbox("啟用工期修正 (排除非工作日)", value=True)
    exclude_weekend = st.checkbox("排除週六、週日", value=True) if use_correction else False
    exclude_cny = st.checkbox("扣除農曆過年 (10天)", value=True) if use_correction else False

# --- 核心運算邏輯 ---

# 1. 基地面積係數 (以 500 坪為基準)
area_multiplier = 1 + ((base_area - 500) / 100) * 0.02
area_multiplier = max(0.8, min(area_multiplier, 1.5))

# 2. 基地現況拆除工期 (T_demolition)
t_demo = 0
if "舊建物" in site_condition:
    t_demo = 45 * area_multiplier
elif "舊地下室" in site_condition:
    t_demo = 80 * area_multiplier

# 3. 地下室工程 (考慮工法與面積)
sub_days_per_floor = 45 if b_method == "順打工法" else 55
t_sub = floors_down * sub_days_per_floor * area_multiplier

# 4. 地質改良加成
t_soil = 0
if "局部" in soil_improvement: t_soil = 45 * area_multiplier
elif "全區" in soil_improvement: t_soil = 90 * area_multiplier

# 5. 地上層結構工期
struct_map = {"RC造": 14, "SRC造": 11, "SS造": 8, "SC造": 8}
t_super = floors_up * struct_map.get(b_struct, 14) * area_multiplier

# 6. 建物用途修正係數
type_multiplier = {"住宅": 1.0, "辦公大樓": 1.1, "百貨": 1.3, "廠房": 0.8, "醫院": 1.4}
k = type_multiplier.get(b_type, 1.0)

# 總天數計算 (加入拆除工期)
main_construction_days = int((t_demo + t_sub + t_soil + t_super) * k)
total_work_days = int(prep_days + main_construction_days + inspection_days)

# --- 日期運算 ---
def get_final_date(start, work_days, skip_weekend, skip_cny):
    curr = start
    done = 0
    while done < work_days:
        curr += timedelta(days=1)
        if skip_weekend and curr.weekday() >= 5: continue
        if skip_cny and curr.month == 2 and 1 <= curr.day <= 10: continue
        done += 1
    return curr

finish_date = get_final_date(start_date, total_work_days, exclude_weekend, exclude_cny)

# --- 結果呈現 ---
st.divider()
st.subheader("📊 預估結果分析")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='metric-container'><small>拆除與地下加成天數</small><br><span style='font-size:24px; font-weight:bold;'>+{int(t_demo)} 天</span></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-container' style='border-left-color:#FF4438;'><small>預計完工日期</small><br><span style='font-size:24px; font-weight:bold; color:#FF4438;'>{finish_date}</span></div>", unsafe_allow_html=True)
with c3:
    calendar_days = (finish_date - start_date).days
    st.markdown(f"<div class='metric-container'><small>總日曆天數</small><br><span style='font-size:24px; font-weight:bold;'>{calendar_days} 天</span></div>", unsafe_allow_html=True)

# 進度條分配
st.write(f"總預估工作天：**{total_work_days}** 天")
st.progress(min(1.0, (prep_days + t_demo) / total_work_days))
st.caption(f"前置與拆除: {int(prep_days + t_demo)}d | 結構工程: {int(t_sub+t_soil+t_super)}d | 裝修與使照: {int(total_work_days - prep_days - t_demo - t_sub - t_soil - t_super)}d")

with st.expander("🛠️ 基地現況處理建議"):
    if "舊地下室" in site_condition:
        st.warning("提醒：舊有地下室破除需注意鄰房安全監測，且清運成本較高。")
    elif "舊建物" in site_condition:
        st.info("提醒：拆除工程需先申請拆除執照，並注意石棉瓦等廢棄物處理規範。")
    else:
        st.success("純空地現況，可直接進行測量放樣與圍籬工程。")