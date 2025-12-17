import streamlit as st
import datetime
from datetime import timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v1.8", layout="wide")

# --- 2. 色彩計劃 CSS ---
st.markdown("""
    <style>
    :root {
        --main-yellow: #FFB81C;
        --accent-orange: #FF4438;
        --dark-grey: #2D2926;
    }
    .stApp { background-color: #ffffff; }
    h1, h2, h3, label { color: var(--dark-grey) !important; font-weight: bold !important; }
    .stButton>button { 
        background-color: var(--main-yellow); 
        color: var(--dark-grey); 
        border: none; width: 100%; border-radius: 8px; font-size: 18px; font-weight: bold;
        padding: 10px;
    }
    .metric-container {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        border-left: 8px solid var(--main-yellow);
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏗️ 建築施工工期估算輔助系統")

# --- 3. 參數輸入區 (介面順序優化) ---
st.subheader("📋 參數設定")
with st.expander("點擊展開/隱藏 建築規模與基地資訊", expanded=True):
    # 第一排：建物基礎規模
    row1_col1, row1_col2, row1_col3 = st.columns([1, 1, 1])
    with row1_col1:
        b_type = st.selectbox("建物類型", ["住宅", "辦公大樓", "百貨", "廠房", "醫院"])
        b_struct = st.selectbox("結構型式", ["RC造", "SRC造", "SS造", "SC造"])
    with row1_col2:
        b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
        base_area = st.number_input("基地面積 (坪)", min_value=10, value=500, step=10)
    with row1_col3:
        floors_up = st.number_input("地上層數", min_value=1, value=12)
        floors_down = st.number_input("地下層數", min_value=0, value=3)

    st.divider()
    
    # 第二排：前置、結尾與日期 (順序優化)
    row2_col1, row2_col2, row2_col3 = st.columns([1, 1, 1])
    with row2_col1:
        # 前置作業
        prep_type = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"])
        if prep_type == "自訂":
            prep_days = st.number_input("自訂前置天數", value=120)
        else:
            prep_days = 120 if "一般" in prep_type else 210 if "鄰捷運" in prep_type else 300
        
        # 移動至此：消檢及使照取得 (排在前置作業下方)
        inspection_days = st.number_input("消檢及使照取得天數", value=(150 if b_type in ["百貨", "醫院"] else 90))

    with row2_col2:
        # 基地現況與改良
        site_condition = st.selectbox("基地現況", ["純空地 (無須拆除)", "有舊建物 (需地上物拆除)", "有舊地下室 (需額外破除處理)"])
        soil_improvement = st.selectbox("地質改良項目", ["無", "局部地質改良 (JSP/CCP)", "全區地質改良"])
        
    with row2_col3:
        # 開工日期
        start_date = st.date_input("預計開工日期", datetime.date.today())

    st.divider()
    
    st.write("**📅 不可施工日修正設定**")
    use_correction = st.checkbox("啟用工期修正 (排除非工作日)", value=True)
    corr_col1, corr_col2, corr_col3 = st.columns(3)
    with corr_col1:
        exclude_sat = st.checkbox("排除週六 (不施工)", value=True) if use_correction else False
    with corr_col2:
        exclude_sun = st.checkbox("排除週日 (不施工)", value=True) if use_correction else False
    with corr_col3:
        exclude_cny = st.checkbox("扣除過年 (7天)", value=True) if use_correction else False

# --- 4. 核心運算邏輯 ---
area_multiplier = max(0.8, min(1 + ((base_area - 500) / 100) * 0.02, 1.5))
t_demo = (45 if "舊建物" in site_condition else 80 if "舊地下室" in site_condition else 0) * area_multiplier
sub_days = floors_down * (45 if b_method == "順打工法" else 55) * area_multiplier
t_soil = (45 if "局部" in soil_improvement else 90 if "全區" in soil_improvement else 0) * area_multiplier
struct_map = {"RC造": 14, "SRC造": 11, "SS造": 8, "SC造": 8}
t_super = floors_up * struct_map.get(b_struct, 14) * area_multiplier
type_multiplier = {"住宅": 1.0, "辦公大樓": 1.1, "百貨": 1.3, "廠房": 0.8, "醫院": 1.4}
k = type_multiplier.get(b_type, 1.0)

main_construction_days = int((t_demo + sub_days + t_soil + t_super) * k)
total_work_days = int(prep_days + main_construction_days + inspection_days)

def calculate_date(start, work_days, skip_sat, skip_sun, skip_cny):
    curr = start
    added = 0
    while added < work_days:
        curr += timedelta(days=1)
        if skip_sat and curr.weekday() == 5: continue
        if skip_sun and curr.weekday() == 6: continue
        if skip_cny and curr.month == 2 and 1 <= curr.day <= 7: continue
        added += 1
    return curr

finish_date = calculate_date(start_date, total_work_days, exclude_sat, exclude_sun, exclude_cny)
calendar_days = (finish_date - start_date).days

# --- 5. 預估結果分析 ---
st.divider()
st.subheader("📊 預估結果分析")

res_col1, res_col2 = st.columns(2)
res_col3, res_col4 = st.columns(2)

with res_col1:
    st.markdown(f"<div class='metric-container'><small>總工作天數</small><br><span style='font-size:24px; font-weight:bold;'>{total_work_days} 天</span></div>", unsafe_allow_html=True)
with res_col2:
    st.markdown(f"<div class='metric-container'><small>預估總工期 (月)</small><br><span style='font-size:24px; font-weight:bold;'>{calendar_days / 30.44:.1f} 個月</span></div>", unsafe_allow_html=True)
with res_col3:
    st.markdown(f"<div class='metric-container' style='border-left-color:#FF4438;'><small>預計完工日期</small><br><span style='font-size:24px; font-weight:bold; color:#FF4438;'>{finish_date}</span></div>", unsafe_allow_html=True)
with res_col4:
    st.markdown(f"<div class='metric-container'><small>總日曆天數</small><br><span style='font-size:24px; font-weight:bold;'>{calendar_days} 天</span></div>", unsafe_allow_html=True)

st.progress(min(1.0, (prep_days + t_demo) / total_work_days))
st.caption("時程預估已整合：前置作業、舊建物拆除、主體結構循環工期與使照取得天數。")