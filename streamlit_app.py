import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
import plotly.express as px
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v4.4", layout="wide")

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
        b_type = st.selectbox("建物類型", ["住宅", "辦公大樓", "飯店", "百貨", "廠房", "醫院"])
        b_struct = st.selectbox("結構型式", ["RC造", "SRC造", "SS造", "SC造"])
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (工期較長)", "玻璃帷幕 (工期較短)", "預鑄PC板", "金屬三明治板 (極快)"])
        foundation_type = st.selectbox("基礎型式", ["筏式基礎 (標準)", "樁基礎 (一般)", "全套管基樁 (工期長)", "微型樁 (工期短)", "獨立基腳"])
    
    with col2:
        b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
        excavation_system = st.selectbox("開挖擋土系統 (整合)", [
            "連續壁 + 型鋼內支撐 (標準)",
            "連續壁 + 地錨 (開挖動線佳)",
            "全套管切削樁 + 型鋼內支撐",
            "預壘樁/排樁 + 型鋼內支撐",
            "鋼板樁 + 型鋼內支撐 (淺開挖)",
            "放坡開挖/無支撐 (極快)"
        ])
        site_condition = st.selectbox("基地現況", ["純空地 (無須拆除)", "有舊建物 (需地上物拆除)", "有舊地下室 (需額外破除)"])
        soil_improvement = st.selectbox("地質改良", ["無", "局部改良 (JSP/CCP)", "全區改良"])
    
    with col3:
        prep_type_select = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"])
        if "自訂" in prep_type_select:
            prep_days_custom = st.number_input("輸入自訂天數", min_value=0, value=120)
        else:
            prep_days_custom = None
            
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

# --- 5. 核心運算邏輯 ---
area_multiplier = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
struct_map = {"RC造": 14, "SRC造": 11, "SS造": 8, "SC造": 8}
k_usage = {"住宅": 1.0, "辦公大樓": 1.1, "飯店": 1.4, "百貨": 1.3, "廠房": 0.8, "醫院": 1.4}.get(b_type, 1.0)

# 外牆係數 (僅影響外牆工項)
ext_wall_map = {"標準磁磚/塗料": 1.0, "石材吊掛 (工期較長)": 1.15, "玻璃帷幕 (工期較短)": 0.85, "預鑄PC板": 0.95, "金屬三明治板 (極快)": 0.6}
ext_wall_multiplier = ext_wall_map.get(ext_wall, 1.0)

excavation_map = {
    "連續壁 + 型鋼內支撐 (標準)": 1.0, "連續壁 + 地錨 (開挖動線佳)": 0.9,
    "全套管切削樁 + 型鋼內支撐": 0.95, "預壘樁/排樁 + 型鋼內支撐": 0.85,
    "鋼板樁 + 型鋼內支撐 (淺開挖)": 0.7, "放坡開挖/無支撐 (極快)": 0.5
}
excav_multiplier = excavation_map.get(excavation_system, 1.0)

# [A] 工項天數計算
if "自訂" in prep_type_select:
    d_prep = int(prep_days_custom)
else:
    d_prep = 120 if "一般" in prep_type_select else 210 if "鄰捷運" in prep_type_select else 300

d_demo = int((45 if "舊建物" in site_condition else 80 if "舊地下室" in site_condition else 0) * area_multiplier)
d_soil = int((30 if "局部" in soil_improvement else 60 if "全區" in soil_improvement else 0) * area_multiplier)

foundation_add = 0
if "全套管基樁" in foundation_type: foundation_add = 90
elif "樁基礎" in foundation_type: foundation_add = 60
elif "微型樁" in foundation_type: foundation_add = 30
d_sub = int(((floors_down * (45 if b_method == "順打工法" else 55) * excav_multiplier) + foundation_add) * area_multiplier)

# 拆分結構與外牆
# 地上結構 (不含外牆係數)
d_struct_body = int(floors_up * struct_map.get(b_struct, 14) * area_multiplier * k_usage)
# 外牆工程 (基準約12天/層 * 係數)
d_ext_wall = int(floors_up * 12 * area_multiplier * ext_wall_multiplier * k_usage)

d_mep = int((60 + floors_up * 4) * area_multiplier * k_usage) 
d_finishing = int((90 + floors_up * 3) * area_multiplier * k_usage)
d_insp = 150 if b_type in ["百貨", "醫院", "飯店"] else 90

# [B] 日期推算函數
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

# [C] CPM 排程 (外牆獨立節點)
p1_s = start_date_val
p1_e = get_end_date(p1_s, d_prep)

p2_s = p1_e + timedelta(days=1)
p2_e = get_end_date(p2_s, d_demo)

p_soil_s = p2_e + timedelta(days=1)
p_soil_e = get_end_date(p_soil_s, d_soil)

p3_s = p_soil_e + timedelta(days=1)
p3_e = get_end_date(p3_s, d_sub)

# 4. 地上結構
p4_s = p3_e + timedelta(days=1)
p4_e = get_end_date(p4_s, d_struct_body)

# New: 建物外牆 (結構體 50% 進場)
lag_ext = int(d_struct_body * 0.5)
p_ext_s = get_end_date(p4_s, lag_ext)
p_ext_e = get_end_date(p_ext_s, d_ext_wall)

# 6. 機電 (結構體 30% 進場)
lag_mep = int(d_struct_body * 0.3) 
p5_s = get_end_date(p4_s, lag_mep)
p5_e = get_end_date(p5_s, d_mep)

# 7. 裝修 (結構體 60% 進場)
lag_finishing = int(d_struct_body * 0.6)
p6_s = get_end_date(p4_s, lag_finishing)
p6_e = get_end_date(p6_s, d_finishing)

# 完工驗收 (必須等：結構、外牆、機電、裝修 全部完成)
latest_finish = max(p4_e, p_ext_e, p5_e, p6_e)
p7_s = latest_finish + timedelta(days=1)
p7_e = get_end_date(p7_s, d_insp)

calendar_days = (p7_e - p1_s).days
duration_months = calendar_days / 30.44
sum_work_days = d_prep + d_demo + d_soil + d_sub + d_struct_body + d_ext_wall + d_mep + d_finishing + d_insp

# --- 6. 預估結果分析 ---
st.divider()
st.subheader("📊 預估結果分析")
res_col1, res_col2, res_col3, res_col4 = st.columns(4)
with res_col1: st.markdown(f"<div class='metric-container'><small>累計工項人天</small><br><b>{sum_work_days} 天</b></div>", unsafe_allow_html=True)
with res_col2: st.markdown(f"<div class='metric-container'><small>專案日曆天 / 月數</small><br><b>{calendar_days} 天 / {duration_months:.1f} 月</b></div>", unsafe_allow_html=True)
with res_col3: 
    c_color = "#FF4438" if enable_date else "#2D2926"
    d_date = p7_e if enable_date else "日期未定"
    st.markdown(f"<div class='metric-container' style='border-left-color:{c_color};'><small>預計完工日期</small><br><b style='color:{c_color};'>{d_date}</b></div>", unsafe_allow_html=True)
with res_col4: 
    overlap = (p4_e - p5_s).days
    st.markdown(f"<div class='metric-container'><small>併行施工縮短</small><br><b>約 {int(overlap/30)} 個月</b></div>", unsafe_allow_html=True)

# --- 7. 詳細進度拆解表 ---
st.subheader("📅 詳細工項進度建議表")
schedule_data = [
    {"工項階段": "1. 規劃與前期作業", "需用工作天": d_prep, "Start": p1_s, "Finish": p1_e, "備註": "要徑"},
    {"工項階段": "2. 建物拆除與整地", "需用工作天": d_demo, "Start": p2_s, "Finish": p2_e, "備註": "要徑"},
    {"工項階段": "3. 地質改良工程", "需用工作天": d_soil, "Start": p_soil_s, "Finish": p_soil_e, "備註": "要徑"},
    {"工項階段": "4. 基礎/地下室工程", "需用工作天": d_sub, "Start": p3_s, "Finish": p3_e, "備註": "要徑"},
    {"工項階段": "5. 地上主體結構", "需用工作天": d_struct_body, "Start": p4_s, "Finish": p4_e, "備註": "要徑"},
    {"工項階段": "6. 建物外牆工程", "需用工作天": d_ext_wall, "Start": p_ext_s, "Finish": p_ext_e, "備註": "併行 (結構50%)"},
    {"工項階段": "7. 內裝機電/管線", "需用工作天": d_mep, "Start": p5_s, "Finish": p5_e, "備註": "併行"},
    {"工項階段": "8. 室內裝修/景觀", "需用工作天": d_finishing, "Start": p6_s, "Finish": p6_e, "備註": "併行"},
    {"工項階段": "9. 驗收取得使照", "需用工作天": d_insp, "Start": p7_s, "Finish": p7_e, "備註": "完工後進行"},
]

sched_display_df = pd.DataFrame(schedule_data)
sched_display_df = sched_display_df[sched_display_df["需用工作天"] > 0]
sched_display_df["預計開始"] = sched_display_df["Start"].apply(lambda x: str(x) if enable_date else "依開工日推算")
sched_display_df["預計完成"] = sched_display_df["Finish"].apply(lambda x: str(x) if enable_date else "依開工日推算")
st.table(sched_display_df[["工項階段", "需用工作天", "預計開始", "預計完成", "備註"]])

# --- 8. 甘特圖 ---
st.subheader("📊 專案進度甘特圖")
if not sched_display_df.empty:
    gantt_df = sched_display_df.copy()
    
    # 新增外牆的顏色 (IndianRed)
    professional_colors = ["#708090", "#A52A2A", "#8B4513", "#2F4F4F", "#4682B4", "#CD5C5C", "#5F9EA0", "#2E8B57", "#DAA520"]
    
    fig = px.timeline(
        gantt_df, 
        x_start="Start", 
        x_end="Finish", 
        y="工項階段", 
        color="工項階段",
        color_discrete_sequence=professional_colors,
        text="工項階段", 
        title=f"【{project_name}】工程進度模擬",
        hover_data={"需用工作天": True, "備註": True},
        height=480 # 稍微加高以容納新工項
    )
    
    fig.update_traces(
        textposition='inside', 
        insidetextanchor='start', 
        width=0.5, 
        marker_line_width=0, 
        opacity=0.9,
        textfont=dict(size=14, color="white", family="Microsoft JhengHei") 
    )
    
    fig.update_layout(
        plot_bgcolor='white',
        font=dict(family="Microsoft JhengHei", size=14, color="#2D2926"),
        xaxis=dict(title="工程期程", showgrid=True, gridcolor='#EEE', tickfont=dict(size=14)),
        yaxis=dict(title="", autorange="reversed", tickfont=dict(size=14)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)),
        margin=dict(l=20, r=20, t=60, b=20),
        uniformtext_minsize=10, 
        uniformtext_mode='hide'
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("尚無工期資料，請檢查參數設定。")

# --- 9. Excel 導出 ---
st.divider()
st.subheader("📥 導出詳細報表")

report_rows = [
    ["項目名稱", project_name],
    ["[ 建築規模與條件 ]", ""],
    ["建物類型", b_type], ["結構型式", b_struct], ["外牆型式", ext_wall],
    ["基礎型式", foundation_type], ["開挖擋土", excavation_system], ["地質改良", soil_improvement],
    ["基地面積", f"{base_area_m2:,.2f} m² / {base_area_ping:,.2f} 坪"],
    ["樓層規模", f"地上 {floors_up} F / 地下 {floors_down} B"],
    ["", ""],
    ["[ 進度分析 (採併行施工邏輯) ]", ""]
]

for item in schedule_data:
    if item["需用工作天"] > 0:
        s_date = str(item['Start']) if enable_date else "未定"
        e_date = str(item['Finish']) if enable_date else "未定"
        report_rows.append([item["工項階段"], f"{item['需用工作天']} 天", f"{s_date} ~ {e_date}", item['備註']])

report_rows.extend([
    ["", "", "", ""],
    ["[ 總結結果 ]", "", "", ""],
    ["累計工項人天", f"{sum_work_days} 天", "", ""],
    ["專案總日曆天數", f"{calendar_days} 天", "", ""],
    ["預估完工日期", str(p7_e if enable_date else "日期未定"), "", ""]
])

df_export = pd.DataFrame(report_rows, columns=["項目", "數值/天數", "日期區間", "備註"])
buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df_export.to_excel(writer, index=False, sheet_name='詳細工期報告')
    worksheet = writer.sheets['詳細工期報告']
    
    header_fill = PatternFill(start_color="2D2926", end_color="2D2926", fill_type="solid")
    header_font = Font(name='微軟正黑體', size=12, bold=True, color="FFB81C")
    section_fill = PatternFill(start_color="EFEFEF", end_color="EFEFEF", fill_type="solid")
    section_font = Font(name='微軟正黑體', size=11, bold=True)
    highlight_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    normal_font = Font(name='微軟正黑體', size=11)
    
    worksheet.column_dimensions['A'].width = 30
    worksheet.column_dimensions['B'].width = 20
    worksheet.column_dimensions['C'].width = 30
    worksheet.column_dimensions['D'].width = 25

    for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=worksheet.max_row), 1):
        for cell in row:
            cell.font = normal_font
            cell.alignment = Alignment(horizontal='left', vertical='center')
            if row_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            if cell.value and isinstance(cell.value, str) and "[" in cell.value:
                cell.fill = section_fill
                cell.font = section_font
            if cell.value == "[ 總結結果 ]":
                cell.fill = header_fill
                cell.font = header_font
            if cell.value == "預估完工日期":
                cell.font = Font(name='微軟正黑體', size=12, bold=True, color="FF4438")
                cell.fill = highlight_fill

excel_data = buffer.getvalue()
st.download_button(
    label="📊 下載專業版 Excel 報表",
    data=excel_data,
    file_name=f"{project_name}_工期分析.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)