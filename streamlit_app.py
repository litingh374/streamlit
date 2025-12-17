import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
from openpyxl.styles import Font, Alignment, PatternFill

# --- 1. 頁面配置與 CSS ---
st.set_page_config(page_title="建築工期估算系統 v2.3", layout="wide")
st.markdown("""
    <style>
    :root { --main-yellow: #FFB81C; --dark-grey: #2D2926; }
    .stApp { background-color: #ffffff; }
    .metric-container {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        border-left: 8px solid var(--main-yellow);
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 標題與專案名稱 ---
st.title("🏗️ 建築施工工期估算輔助系統")
project_name = st.text_input("📝 請輸入專案名稱", value="未命名專案")

# --- 3. 參數輸入區 ---
st.subheader("📋 參數設定")
with st.expander("點擊展開/隱藏 建築規模與基地資訊", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        b_type = st.selectbox("建物類型", ["住宅", "辦公大樓", "百貨", "廠房", "醫院"])
        b_struct = st.selectbox("結構型式", ["RC造", "SRC造", "SS造", "SC造"])
        # --- 新增：外牆型式 ---
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (較慢)", "玻璃帷幕 (較快)", "預鑄PC板"])
        
    with col2:
        b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
        base_area = st.number_input("基地面積 (坪)", min_value=10, value=500)
        floors_up = st.number_input("地上層數", min_value=1, value=12)
        
    with col3:
        floors_down = st.number_input("地下層數", min_value=0, value=3)
        start_date = st.date_input("預計開工日期", datetime.date.today())
        site_condition = st.selectbox("基地現況", ["純空地", "有舊建物", "有舊地下室"])

# --- 4. 核心運算邏輯 (加入外牆權重) ---
# 基礎乘數
area_multiplier = max(0.8, min(1 + ((base_area - 500) / 100) * 0.02, 1.5))
struct_map = {"RC造": 14, "SRC造": 11, "SS造": 8, "SC造": 8}

# 外牆工期修正係數
# 玻璃帷幕雖然貴，但安裝快，係數設為 0.9；石材吊掛係數 1.15
ext_wall_multiplier = {
    "標準磁磚/塗料": 1.0,
    "石材吊掛 (較慢)": 1.15,
    "玻璃帷幕 (較快)": 0.9,
    "預鑄PC板": 0.95
}.get(ext_wall, 1.0)

# 計算主體工期
t_super = floors_up * struct_map.get(b_struct, 14) * area_multiplier * ext_wall_multiplier

# 其餘維持原邏輯
prep_days = 120
inspection_days = 150 if b_type in ["百貨", "醫院"] else 90
total_work_days = int(prep_days + t_super + inspection_days)

# 日期計算邏輯 (略，維持 v2.2)
finish_date = start_date + timedelta(days=total_work_days * 1.4) # 簡易示意，實務請套用 v2.2 的跳過六日 function
calendar_days = (finish_date - start_date).days

# --- 5. 結果顯示 ---
st.divider()
st.subheader("📊 考慮「外牆型式」後的預估結果")
res_col1, res_col2, res_col3 = st.columns(3)
with res_col1: st.markdown(f"<div class='metric-container'><small>總工作天</small><br><b>{total_work_days} 天</b></div>", unsafe_allow_html=True)
with res_col2: st.markdown(f"<div class='metric-container'><small>外牆修正影響</small><br><b>{int((ext_wall_multiplier-1)*100)}%</b></div>", unsafe_allow_html=True)
with res_col3: st.markdown(f"<div class='metric-container'><small>預計完工</small><br><b>{finish_date}</b></div>", unsafe_allow_html=True)

# (後續 Excel 導出邏輯同步加入 ext_wall 欄位即可)