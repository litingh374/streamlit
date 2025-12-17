import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
from openpyxl.styles import Font, Alignment, PatternFill

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v2.4", layout="wide")

# --- 2. CSS 樣式 ---
st.markdown("""
    <style>
    :root { --main-yellow: #FFB81C; --accent-orange: #FF4438; --dark-grey: #2D2926; }
    .stApp { background-color: #ffffff; }
    h1, h2, h3, label { color: var(--dark-grey) !important; font-weight: bold !important; }
    .stButton>button { 
        background-color: var(--main-yellow); color: var(--dark-grey); 
        border: none; width: 100%; border-radius: 8px; font-size: 18px; font-weight: bold; padding: 12px;
    }
    .metric-container {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        border-left: 8px solid var(--main-yellow);
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 標題與專案名稱 ---
st.title("🏗️ 建築施工工期估算輔助系統")
project_name = st.text_input("📝 請輸入專案名稱", value="未命名專案")

# --- 4. 參數輸入區 ---
st.subheader("📋 建築規模參數")
with st.expander("點擊展開/隱藏 建築規模與基地資訊", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        b_type = st.selectbox("建物類型", ["住宅", "辦公大樓", "百貨", "廠房", "醫院"])
        b_struct = st.selectbox("結構型式", ["RC造", "SRC造", "SS造", "SC造"])
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (工期較長)", "玻璃帷幕 (工期較短)", "預鑄PC板"])
    with col2:
        b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
        base_area = st.number_input("基地面積 (坪)", min_value=10, value=500, step=10)
        floors_up = st.number_input("地上層數", min_value=1, value=12)
    with col3:
        floors_down = st.number_input("地下層數", min_value=0, value=3)
        site_condition = st.selectbox("基地現況", ["純空地 (無須拆除)", "有舊建物 (需地上物拆除)", "有舊地下室 (需額外破除)"])

st.subheader("📅 日期與排除條件 (非必要)")
with st.expander("點擊展開/隱藏 日期設定"):
    date_col1, date_col2 = st.columns([1, 2])
    with date_col1:
        # 開工日期移至此，並提供一個勾選框決定是否啟用日期計算
        enable_date = st.checkbox("啟用開工日期計算", value=True)
        start_date = st.date_input("預計開工日期", datetime.date.today()) if enable_date else None
    with date_col2:
        st.write("**不可施工日修正**")
        corr_col1, corr_col2, corr_col3 = st.columns(3)
        with corr_col1: exclude_sat = st.checkbox("排除週六 (不施工)", value=True)
        with corr_col2: exclude_sun = st.checkbox("排除週日 (不施工)", value=True)
        with corr_col3: exclude_cny = st.checkbox("扣除過年 (7天)", value=True)

# --- 5. 核心運算邏輯 ---
area_multiplier = max(0.8, min(1 + ((base_area - 500) / 100) * 0.02, 1.5))
struct_map = {"RC造": 14, "SRC造": 11, "SS造": 8, "SC造": 8}
ext_wall_map = {"標準磁磚/塗料": 1.0, "石材吊掛 (工期較長)": 1.15, "玻璃帷幕 (工期較短)": 0.85, "預鑄PC板": 0.95}
ext_wall_multiplier = ext_wall_map.get(ext_wall, 1.0)

t_demo = (45 if "舊建物" in site_condition else 80 if "舊地下室" in site_condition else 0) * area_multiplier
t_sub = floors_down * (45 if b_method == "順打工法" else 55) * area_multiplier
t_super = floors_up * struct_map.get(b_struct, 14) * area_multiplier * ext_wall_multiplier
k_usage = {"住宅": 1.0, "辦公大樓": 1.1, "百貨": 1.3, "廠房": 0.8, "醫院": 1.4}.get(b_type, 1.0)

prep_days = 120
inspection_days = 150 if b_type in ["百貨", "醫院"] else 90
main_construction_days = int((t_demo + t_sub + t_super) * k_usage)
total_work_days = int(prep_days + main_construction_days + inspection_days)

# 日期計算
def calculate_finish_date(start, work_days, skip_sat, skip_sun, skip_cny):
    if not start: return "日期未定"
    curr = start
    added = 0
    while added < work_days:
        curr += timedelta(days=1)
        if skip_sat and curr.weekday() == 5: continue
        if skip_sun and curr.weekday() == 6: continue
        if skip_cny and curr.month == 2 and 1 <= curr.day <= 7: continue
        added += 1
    return curr

calc_finish = calculate_finish_date(start_date, total_work_days, exclude_sat, exclude_sun, exclude_cny)
calendar_days = (calc_finish - start_date).days if start_date else "N/A"

# --- 6. 預估結果分析 ---
st.divider()
st.subheader("📊 預估結果分析")
res_col1, res_col2, res_col3, res_col4 = st.columns(4)
with res_col1: st.markdown(f"<div class='metric-container'><small>總工作天數</small><br><b>{total_work_days} 天</b></div>", unsafe_allow_html=True)
with res_col2: st.markdown(f"<div class='metric-container'><small>外牆工法影響</small><br><b>{int((ext_wall_multiplier-1)*100)}%</b></div>", unsafe_allow_html=True)
with res_col3: 
    color = "#FF4438" if start_date else "#2D2926"
    st.markdown(f"<div class='metric-container' style='border-left-color:{color};'><small>預計完工日期</small><br><b style='color:{color};'>{calc_finish}</b></div>", unsafe_allow_html=True)
with res_col4: st.markdown(f"<div class='metric-container'><small>總日曆天數</small><br><b>{calendar_days} 天</b></div>", unsafe_allow_html=True)

# --- 7. Excel 報表產出 ---
st.divider()
st.subheader("📥 導出報表")

report_data = [
    ["項目名稱", project_name],
    ["報告產出時間", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ["", ""],
    ["[ 建築規模 ]", ""],
    ["建物類型", b_type],
    ["結構型式", b_struct],
    ["外牆型式", ext_wall],
    ["基地面積", f"{base_area} 坪"],
    ["樓層規模", f"地上 {floors_up} F / 地下 {floors_down} B"],
    ["", ""],
    ["[ 估算結果 ]", ""],
    ["預計開工日期", str(start_date) if start_date else "未提供"],
    ["總需求工作天數", f"{total_work_days} 天"],
    ["總日曆天數", f"{calendar_days} 天"],
    ["預計完工日期", str(calc_finish)]
]
df = pd.DataFrame(report_data, columns=["參數項目", "詳細內容"])

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='工期估算報告')
    worksheet = writer.sheets['工期估算報告']
    header_font = Font(name='微軟正黑體', size=12, bold=True, color="FFB81C")
    header_fill = PatternFill(start_color="2D2926", end_color="2D2926", fill_type="solid")
    main_font = Font(name='微軟正黑體', size=11)
    worksheet.column_dimensions['A'].width = 25
    worksheet.column_dimensions['B'].width = 40
    for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=worksheet.max_row), 1):
        for cell in row:
            cell.font = main_font
            cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
            if row_idx == 1:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            if cell.value and isinstance(cell.value, str) and "[" in cell.value:
                cell.font = Font(name='微軟正黑體', size=11, bold=True)
                cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

excel_data = buffer.getvalue()
st.download_button(
    label="📊 下載 Excel 工期報告",
    data=excel_data,
    file_name=f"建築工期報告_{project_name}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)