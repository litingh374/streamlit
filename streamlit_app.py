import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v3.4", layout="wide")

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
    .area-display {
        background-color: #e3f2fd; padding: 5px 10px; border-radius: 5px;
        font-size: 14px; color: #1565c0; margin-top: -10px; margin-bottom: 10px;
        border-left: 3px solid #1565c0;
    }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -5px; }
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
        site_condition = st.selectbox("基地現況", ["純空地 (無須拆除)", "有舊建物 (需地上物拆除)", "有舊地下室 (需額外破除)"])
        prep_type = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"])
    with col3:
        floors_up = st.number_input("地上層數 (F)", min_value=1, value=12)
        floors_down = st.number_input("地下層數 (B)", min_value=0, value=3)
        base_area_m2 = st.number_input("基地面積 (m²)", min_value=1.0, value=1652.89, step=10.0)
        base_area_ping = base_area_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{base_area_ping:,.2f} 坪</div>", unsafe_allow_html=True)

st.subheader("📅 日期與排除條件")
with st.expander("點擊展開/隱藏 日期設定"):
    date_col1, date_col2 = st.columns([1, 2])
    with date_col1:
        enable_date = st.checkbox("啟用開工日期計算", value=True)
        start_date_val = st.date_input("預計開工日期", datetime.date.today())
    with date_col2:
        st.write("**不可施工日修正**")
        corr_col1, corr_col2, corr_col3 = st.columns(3)
        with corr_col1: exclude_sat = st.checkbox("排除週六 (不施工)", value=True)
        with corr_col2: exclude_sun = st.checkbox("排除週日 (不施工)", value=True)
        with corr_col3: exclude_cny = st.checkbox("扣除過年 (7天)", value=True)

# --- 5. 核心運算邏輯 (v3.3 併行邏輯) ---
area_multiplier = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
struct_map = {"RC造": 14, "SRC造": 11, "SS造": 8, "SC造": 8}
ext_wall_map = {"標準磁磚/塗料": 1.0, "石材吊掛 (工期較長)": 1.15, "玻璃帷幕 (工期較短)": 0.85, "預鑄PC板": 0.95}
ext_wall_multiplier = ext_wall_map.get(ext_wall, 1.0)
k_usage = {"住宅": 1.0, "辦公大樓": 1.1, "百貨": 1.3, "廠房": 0.8, "醫院": 1.4}.get(b_type, 1.0)

# 工項工作天 (Man-days)
d_prep = 120 if "一般" in prep_type else 210 if "鄰捷運" in prep_type else 300
d_demo = int((45 if "舊建物" in site_condition else 80 if "舊地下室" in site_condition else 0) * area_multiplier)
d_sub = int(floors_down * (45 if b_method == "順打工法" else 55) * area_multiplier)
d_super = int(floors_up * struct_map.get(b_struct, 14) * area_multiplier * ext_wall_multiplier * k_usage)
d_mep = int((60 + floors_up * 4) * area_multiplier * k_usage) 
d_finishing = int((90 + floors_up * 3) * area_multiplier * k_usage)
d_insp = 150 if b_type in ["百貨", "醫院"] else 90

# 日期計算
def get_end_date(start_date, days_needed):
    curr = start_date
    added = 0
    while added < days_needed:
        curr += timedelta(days=1)
        if exclude_sat and curr.weekday() == 5: continue
        if exclude_sun and curr.weekday() == 6: continue
        if exclude_cny and curr.month == 2 and 1 <= curr.day <= 7: continue
        added += 1
    return curr

# CPM 排程
p1_start = start_date_val
p1_end = get_end_date(p1_start, d_prep)

p2_start = p1_end + timedelta(days=1)
p2_end = get_end_date(p2_start, d_demo)

p3_start = p2_end + timedelta(days=1)
p3_end = get_end_date(p3_start, d_sub)

p4_start = p3_end + timedelta(days=1)
p4_end = get_end_date(p4_start, d_super)

lag_mep = int(d_super * 0.3) 
p5_start = get_end_date(p4_start, lag_mep)
p5_end = get_end_date(p5_start, d_mep)

lag_finishing = int(d_super * 0.6)
p6_start = get_end_date(p4_start, lag_finishing)
p6_end = get_end_date(p6_start, d_finishing)

latest_finish_date = max(p4_end, p5_end, p6_end)
p7_start = latest_finish_date + timedelta(days=1)
p7_end = get_end_date(p7_start, d_insp)

calendar_days = (p7_end - p1_start).days
duration_months = calendar_days / 30.44
sum_work_days = d_prep + d_demo + d_sub + d_super + d_mep + d_finishing + d_insp

# --- 6. 預估結果分析 ---
st.divider()
st.subheader("📊 預估結果分析")
res_col1, res_col2, res_col3, res_col4 = st.columns(4)

with res_col1: 
    st.markdown(f"<div class='metric-container'><small>累計工項人天</small><br><b>{sum_work_days} 天</b></div>", unsafe_allow_html=True)
with res_col2: 
    st.markdown(f"<div class='metric-container'><small>專案日曆天 / 月數</small><br><b>{calendar_days} 天 / {duration_months:.1f} 月</b></div>", unsafe_allow_html=True)
with res_col3: 
    color = "#FF4438" if enable_date else "#2D2926"
    display_date = p7_end if enable_date else "日期未定"
    st.markdown(f"<div class='metric-container' style='border-left-color:{color};'><small>預計完工日期</small><br><b style='color:{color};'>{display_date}</b></div>", unsafe_allow_html=True)
with res_col4: 
    overlap_days = (p4_end - p5_start).days
    st.markdown(f"<div class='metric-container'><small>併行施工縮短</small><br><b>約 {int(overlap_days/30)} 個月</b></div>", unsafe_allow_html=True)

# --- 7. 詳細進度拆解表 ---
st.subheader("📅 詳細工項進度建議表")
schedule_data = [
    {"工項階段": "1. 規劃與前期作業", "需用工作天": d_prep, "開始日期": p1_start, "完成日期": p1_end, "備註": "要徑作業"},
    {"工項階段": "2. 建物拆除與整地", "需用工作天": d_demo, "開始日期": p2_start, "完成日期": p2_end, "備註": "要徑作業"},
    {"工項階段": "3. 地下室結構/土方", "需用工作天": d_sub, "開始日期": p3_start, "完成日期": p3_end, "備註": "要徑作業"},
    {"工項階段": "4. 地上主體結構工程", "需用工作天": d_super, "開始日期": p4_start, "完成日期": p4_end, "備註": "要徑作業"},
    {"工項階段": "5. 內裝機電/管線工程", "需用工作天": d_mep, "開始日期": p5_start, "完成日期": p5_end, "備註": "結構體 30% 進場"},
    {"工項階段": "6. 室內裝修/景觀工程", "需用工作天": d_finishing, "開始日期": p6_start, "完成日期": p6_end, "備註": "結構體 60% 進場"},
    {"工項階段": "7. 驗收取得使照", "需用工作天": d_insp, "開始日期": p7_start, "完成日期": p7_end, "備註": "完工後進行"},
]
sched_df = pd.DataFrame(schedule_data)
if not enable_date:
    sched_df["開始日期"] = "未定"
    sched_df["完成日期"] = "未定"
st.table(sched_df)

# --- 8. Excel 導出 (美化版) ---
st.divider()
st.subheader("📥 導出詳細報表")

# 準備資料
report_rows = [
    ["項目名稱", project_name],
    ["[ 建築規模 ]", ""],
    ["建物類型", b_type], ["結構型式", b_struct], ["外牆型式", ext_wall],
    ["基地面積", f"{base_area_m2:,.2f} m² / {base_area_ping:,.2f} 坪"],
    ["樓層規模", f"地上 {floors_up} F / 地下 {floors_down} B"],
    ["", ""],
    ["[ 進度分析 (採併行施工邏輯) ]", ""]
]
for item in schedule_data:
    s_date = str(item['開始日期']) if enable_date else "未定"
    e_date = str(item['完成日期']) if enable_date else "未定"
    report_rows.append([item["工項階段"], f"{item['需用工作天']} 天", f"{s_date} ~ {e_date}", item['備註']])

report_rows.extend([
    ["", "", "", ""],
    ["[ 總結結果 ]", "", "", ""],
    ["累計工項人天", f"{sum_work_days} 天", "", ""],
    ["專案總日曆天數", f"{calendar_days} 天", "", ""],
    ["預估完工日期", str(p7_end if enable_date else "日期未定"), "", ""]
])

# 轉換 DataFrame (4欄結構)
df_export = pd.DataFrame(report_rows, columns=["項目", "數值/天數", "日期區間", "備註"])

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_export.to_excel(writer, index=False, sheet_name='詳細工期報告')
    worksheet = writer.sheets['詳細工期報告']
    
    # === 樣式定義 (色彩計劃) ===
    # 深灰底 (K85) + 黃字 (1235C) - 用於大標題
    header_fill = PatternFill(start_color="2D2926", end_color="2D2926", fill_type="solid")
    header_font = Font(name='微軟正黑體', size=12, bold=True, color="FFB81C")
    
    # 淺灰底 - 用於區段分隔
    section_fill = PatternFill(start_color="EFEFEF", end_color="EFEFEF", fill_type="solid")
    section_font = Font(name='微軟正黑體', size=11, bold=True, color="000000")
    
    # 黃色底 - 用於強調結果
    highlight_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    
    # 一般文字
    normal_font = Font(name='微軟正黑體', size=11)
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    
    # 設定欄寬
    worksheet.column_dimensions['A'].width = 25
    worksheet.column_dimensions['B'].width = 20
    worksheet.column_dimensions['C'].width = 30
    worksheet.column_dimensions['D'].width = 25

    # 逐行套用樣式
    for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=worksheet.max_row), 1):
        for cell in row:
            cell.font = normal_font
            cell.alignment = left_align
            
            # 1. 表頭 (第一行)
            if row_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align
            
            # 2. 區段標題 (有中括號的)
            if cell.value and isinstance(cell.value, str) and "[" in cell.value:
                cell.fill = section_fill
                cell.font = section_font
                
            # 3. 總結結果區塊 (最後幾行)
            if cell.value == "[ 總結結果 ]":
                cell.fill = header_fill # 再用一次深灰底
                cell.font = header_font
            
            # 4. 完工日期 (紅字強調)
            if cell.value == "預估完工日期" or (isinstance(cell.value, str) and "日期未定" in cell.value):
                cell.font = Font(name='微軟正黑體', size=12, bold=True, color="FF4438")
                cell.fill = highlight_fill

excel_data = buffer.getvalue()
st.download_button(label="📊 下載專業版 Excel 報表", data=excel_data, file_name=f"{project_name}_工期分析.xlsx")