import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
import plotly.express as px
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v5.1", layout="wide")

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
    div[data-testid="stDataEditor"] { border: 1px solid #ddd; border-radius: 5px; margin-top: 5px; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 標題與專案名稱 ---
st.title("🏗️ 建築施工工期估算輔助系統")
project_name = st.text_input("📝 請輸入專案名稱", value="未命名專案")

# --- 4. 參數輸入區 ---
st.subheader("📋 建築規模參數")
with st.expander("點擊展開/隱藏 參數設定面板", expanded=True):
    # === 上半部：工程屬性 ===
    st.markdown("#### 1. 工程屬性設定")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        b_type = st.selectbox("建物類型", ["住宅", "集合住宅 (多棟)", "辦公大樓", "飯店", "百貨", "廠房", "醫院"])
        b_struct = st.selectbox("結構型式", ["RC造", "SRC造", "SS造", "SC造"])
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (工期較長)", "玻璃帷幕 (工期較短)", "預鑄PC板", "金屬三明治板 (極快)"])
    
    with col2:
        foundation_type = st.selectbox("基礎型式", ["筏式基礎 (標準)", "樁基礎 (一般)", "全套管基樁 (工期長)", "微型樁 (工期短)", "獨立基腳"])
        b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
        excavation_system = st.selectbox("開挖擋土系統", [
            "連續壁 + 型鋼內支撐 (標準)",
            "連續壁 + 地錨 (開挖動線佳)",
            "全套管切削樁 + 型鋼內支撐",
            "預壘樁/排樁 + 型鋼內支撐",
            "鋼板樁 + 型鋼內支撐 (淺開挖)",
            "放坡開挖/無支撐 (極快)"
        ])
        
    with col3:
        # 修改：細分基地現況選項
        site_condition = st.selectbox("基地現況", [
            "純空地 (無須拆除)", 
            "有舊建物 (無地下室)", 
            "有舊建物 (含舊地下室)", 
            "僅存舊地下室 (需回填/破除)"
        ])
        soil_improvement = st.selectbox("地質改良", ["無", "局部改良 (JSP/CCP)", "全區改良"])
        prep_type_select = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"])

    st.divider()

    # === 下半部：規模量體 ===
    st.markdown("#### 2. 規模量體設定")
    
    dim_c1, dim_c2, dim_c3 = st.columns(3)
    
    with dim_c1:
        base_area_m2 = st.number_input("基地面積 (m²)", min_value=1.0, value=1652.89, step=10.0)
        base_area_ping = base_area_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{base_area_ping:,.2f} 坪</div>", unsafe_allow_html=True)
        
    with dim_c2:
        floors_down = st.number_input("地下層數 (B)", min_value=0, value=3)
        
    with dim_c3:
        if "自訂" in prep_type_select:
            prep_days_custom = st.number_input("輸入自訂前置天數", min_value=0, value=120)
        else:
            prep_days_custom = None
            st.info(f"依類型自動設定：{prep_type_select}")

    st.write("") 
    
    building_details_df = None
    max_floors_up = 1
    building_count = 1

    if "集合住宅" in b_type:
        st.markdown("##### 🏙️ 集合住宅 - 各棟樓層配置")
        t_col1, t_col2 = st.columns([1, 2])
        with t_col1:
            default_data = pd.DataFrame([
                {"棟別名稱": "A棟", "地上層數": 15},
                {"棟別名稱": "B棟", "地上層數": 15},
                {"棟別名稱": "C棟", "地上層數": 12}
            ])
            edited_df = st.data_editor(
                default_data, num_rows="dynamic", use_container_width=False,
                column_config={
                    "棟別名稱": st.column_config.TextColumn("棟別", width="small", required=True),
                    "地上層數": st.column_config.NumberColumn("層數 (F)", width="small", min_value=1, max_value=100, step=1, format="%d")
                },
                key="building_editor", height=150
            )
        with t_col2:
            st.caption("👈 請在左側表格新增或修改各棟樓層。")
            if not edited_df.empty:
                max_floors_up = int(edited_df["地上層數"].max())
                building_count = len(edited_df)
                building_details_df = edited_df
                st.success(f"系統偵測共 **{building_count}** 棟，將以最高的 **{max_floors_up} F** 作為結構要徑計算基準。")
            else:
                st.error("⚠️ 請至少輸入一棟資料")
                max_floors_up = 15
    else:
        st.markdown("##### 🏢 地上層數設定")
        s_col1, s_col2 = st.columns([1, 2])
        with s_col1:
            floors_up = st.number_input("地上層數 (F)", min_value=1, value=12)
        max_floors_up = floors_up
        building_count = 1

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
k_usage_base = {"住宅": 1.0, "集合住宅 (多棟)": 1.0, "辦公大樓": 1.1, "飯店": 1.4, "百貨": 1.3, "廠房": 0.8, "醫院": 1.4}.get(b_type, 1.0)
multi_building_factor = 1.0
if "集合住宅" in b_type and building_count > 1:
    multi_building_factor = 1.0 + (building_count - 1) * 0.03
k_usage = k_usage_base * multi_building_factor
ext_wall_map = {"標準磁磚/塗料": 1.0, "石材吊掛 (工期較長)": 1.15, "玻璃帷幕 (工期較短)": 0.85, "預鑄PC板": 0.95, "金屬三明治板 (極快)": 0.6}
ext_wall_multiplier = ext_wall_map.get(ext_wall, 1.0)
excavation_map = {
    "連續壁 + 型鋼內支撐 (標準)": 1.0, "連續壁 + 地錨 (開挖動線佳)": 0.9,
    "全套管切削樁 + 型鋼內支撐": 0.95, "預壘樁/排樁 + 型鋼內支撐": 0.85,
    "鋼板樁 + 型鋼內支撐 (淺開挖)": 0.7, "放坡開挖/無支撐 (極快)": 0.5
}
excav_multiplier = excavation_map.get(excavation_system, 1.0)

# [A] 工項天數計算
if "自訂" in prep_type_select and prep_days_custom is not None:
    d_prep = int(prep_days_custom)
else:
    d_prep = 120 if "一般" in prep_type_select else 210 if "鄰捷運" in prep_type_select else 300

# 2. 拆除工程 (細分邏輯)
if "純空地" in site_condition:
    d_demo = 0
    demo_note = "純空地"
elif "有舊建物 (含舊地下室)" in site_condition:
    d_demo = int(100 * area_multiplier) # 地上+地下拆除最久
    demo_note = "全棟拆除(含地下室)"
elif "有舊建物 (無地下室)" in site_condition:
    d_demo = int(45 * area_multiplier)
    demo_note = "地上拆除"
else: # 僅存舊地下室
    d_demo = int(60 * area_multiplier)
    demo_note = "地下結構破除"

d_soil = int((30 if "局部" in soil_improvement else 60 if "全區" in soil_improvement else 0) * area_multiplier)

foundation_add = 0
if "全套管基樁" in foundation_type: foundation_add = 90
elif "樁基礎" in foundation_type: foundation_add = 60
elif "微型樁" in foundation_type: foundation_add = 30
sub_speed_factor = 1.15 if "逆打" in b_method else 1.0
d_sub = int(((floors_down * 55 * sub_speed_factor * excav_multiplier) + foundation_add) * area_multiplier)

d_struct_body = int(max_floors_up * struct_map.get(b_struct, 14) * area_multiplier * k_usage)
d_ext_wall = int(max_floors_up * 12 * area_multiplier * ext_wall_multiplier * k_usage)
d_mep = int((60 + max_floors_up * 4) * area_multiplier * k_usage) 
d_finishing = int((90 + max_floors_up * 3) * area_multiplier * k_usage)
d_insp_base = 150 if b_type in ["百貨", "醫院", "飯店"] else 90
if "集合住宅" in b_type:
    d_insp = d_insp_base + (building_count - 1) * 15
else:
    d_insp = d_insp_base

# [B] 日期推算
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

# [C] CPM 排程
p1_s = start_date_val
p1_e = get_end_date(p1_s, d_prep)
p2_s = p1_e + timedelta(days=1)
p2_e = get_end_date(p2_s, d_demo)
p_soil_s = p2_e + timedelta(days=1)
p_soil_e = get_end_date(p_soil_s, d_soil)
p3_s = p_soil_e + timedelta(days=1)
p3_e = get_end_date(p3_s, d_sub)

if "逆打" in b_method or "雙順打" in b_method:
    lag_1f_slab = int(60 * area_multiplier)
    p4_s = get_end_date(p3_s, lag_1f_slab)
    struct_note = f"併行 (要徑:{max_floors_up}F)"
else:
    p4_s = p3_e + timedelta(days=1)
    struct_note = f"順打 (要徑:{max_floors_up}F)"

p4_e = get_end_date(p4_s, d_struct_body)
lag_ext = int(d_struct_body * 0.5)
p_ext_s = get_end_date(p4_s, lag_ext)
p_ext_e = get_end_date(p_ext_s, d_ext_wall)
lag_mep = int(d_struct_body * 0.3) 
p5_s = get_end_date(p4_s, lag_mep)
p5_e = get_end_date(p5_s, d_mep)
lag_finishing = int(d_struct_body * 0.6)
p6_s = get_end_date(p4_s, lag_finishing)
p6_e = get_end_date(p6_s, d_finishing)
p7_s = p_ext_e - timedelta(days=30)
p7_e = get_end_date(p7_s, d_insp)
final_project_finish = max(p3_e, p4_e, p_ext_e, p5_e, p6_e, p7_e)
calendar_days = (final_project_finish - p1_s).days
duration_months = calendar_days / 30.44
avg_ratio = 5/7 if exclude_sat and exclude_sun else 6/7 if exclude_sun else 1.0
effective_work_days = int(calendar_days * avg_ratio)

# --- 6. 預估結果分析 ---
st.divider()
st.subheader("📊 預估結果分析")
res_col1, res_col2, res_col3, res_col4 = st.columns(4)
with res_col1: st.markdown(f"<div class='metric-container'><small>專案總有效工期</small><br><b>{effective_work_days} 天</b></div>", unsafe_allow_html=True)
with res_col2: st.markdown(f"<div class='metric-container'><small>專案日曆天 / 月數</small><br><b>{calendar_days} 天 / {duration_months:.1f} 月</b></div>", unsafe_allow_html=True)
with res_col3: 
    c_color = "#FF4438" if enable_date else "#2D2926"
    d_date = final_project_finish if enable_date else "日期未定"
    st.markdown(f"<div class='metric-container' style='border-left-color:{c_color};'><small>預計完工日期</small><br><b style='color:{c_color};'>{d_date}</b></div>", unsafe_allow_html=True)
with res_col4: 
    if "集合住宅" in b_type:
        msg = f"多棟係數 x{multi_building_factor:.2f}"
    else:
        msg = "單棟標準係數"
    st.markdown(f"<div class='metric-container'><small>規模複雜度分析</small><br><b>{msg}</b></div>", unsafe_allow_html=True)

# --- 7. 詳細進度拆解表 ---
st.subheader("📅 詳細工項進度建議表")
schedule_data = [
    {"工項階段": "1. 規劃與前期作業", "需用工作天": d_prep, "Start": p1_s, "Finish": p1_e, "備註": "要徑"},
    {"工項階段": "2. 建物拆除與整地", "需用工作天": d_demo, "Start": p2_s, "Finish": p2_e, "備註": demo_note},
    {"工項階段": "3. 地質改良工程", "需用工作天": d_soil, "Start": p_soil_s, "Finish": p_soil_e, "備註": "要徑"},
    {"工項階段": "4. 基礎/地下室工程", "需用工作天": d_sub, "Start": p3_s, "Finish": p3_e, "備註": f"要徑 ({b_method[:2]})"},
    {"工項階段": "5. 地上主體結構", "需用工作天": d_struct_body, "Start": p4_s, "Finish": p4_e, "備註": struct_note},
    {"工項階段": "6. 建物外牆工程", "需用工作天": d_ext_wall, "Start": p_ext_s, "Finish": p_ext_e, "備註": "併行"},
    {"工項階段": "7. 內裝機電/管線", "需用工作天": d_mep, "Start": p5_s, "Finish": p5_e, "備註": "併行"},
    {"工項階段": "8. 室內裝修/景觀", "需用工作天": d_finishing, "Start": p6_s, "Finish": p6_e, "備註": "併行"},
    {"工項階段": "9. 驗收取得使照", "需用工作天": d_insp, "Start": p7_s, "Finish": p7_e, "備註": f"多棟聯合驗收"},
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
    professional_colors = ["#708090", "#A52A2A", "#8B4513", "#2F4F4F", "#4682B4", "#CD5C5C", "#5F9EA0", "#2E8B57", "#DAA520"]
    fig = px.timeline(
        gantt_df, x_start="Start", x_end="Finish", y="工項階段", color="工項階段",
        color_discrete_sequence=professional_colors, text="工項階段", 
        title=f"【{project_name}】工程進度模擬 (最高 {max_floors_up}F)",
        hover_data={"需用工作天": True, "備註": True}, height=480
    )
    fig.update_traces(textposition='inside', insidetextanchor='start', width=0.5, marker_line_width=0, opacity=0.9, textfont=dict(size=14, color="white", family="Microsoft JhengHei"))
    fig.update_layout(plot_bgcolor='white', font=dict(family="Microsoft JhengHei", size=14, color="#2D2926"), xaxis=dict(title="工程期程", showgrid=True, gridcolor='#EEE', tickfont=dict(size=14)), yaxis=dict(title="", autorange="reversed", tickfont=dict(size=14)), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)), margin=dict(l=20, r=20, t=60, b=20), uniformtext_minsize=10, uniformtext_mode='hide')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("尚無工期資料，請檢查參數設定。")

# --- 9. Excel 導出 ---
st.divider()
st.subheader("📥 導出詳細報表")

b_type_str = b_type
details_str = ""
if "集合住宅" in b_type and building_details_df is not None:
    b_type_str = f"{b_type} (共 {building_count} 棟)"
    details_list = []
    for idx, row in building_details_df.iterrows():
        details_list.append(f"{row['棟別名稱']}:{row['地上層數']}F")
    details_str = " / ".join(details_list)

report_rows = [
    ["項目名稱", project_name],
    ["[ 建築規模與條件 ]", ""],
    ["建物類型", b_type_str], 
    ["各棟配置", details_str],
    ["結構型式", b_struct], ["外牆型式", ext_wall],
    ["基礎型式", foundation_type], ["施工方式", b_method], ["開挖擋土", excavation_system],
    ["基地現況", site_condition], ["地質改良", soil_improvement], # 修正: 寫入新變數
    ["基地面積", f"{base_area_m2:,.2f} m² / {base_area_ping:,.2f} 坪"],
    ["樓層規模", f"地下 {floors_down} B / 最高地上 {max_floors_up} F"],
    ["", ""],
    ["[ 進度分析 ]", ""]
]

for item in schedule_data:
    if item["需用工作天"] > 0:
        s_date = str(item['Start']) if enable_date else "未定"
        e_date = str(item['Finish']) if enable_date else "未定"
        report_rows.append([item["工項階段"], f"{item['需用工作天']} 天", f"{s_date} ~ {e_date}", item['備註']])

report_rows.extend([
    ["", "", "", ""],
    ["[ 總結結果 ]", "", "", ""],
    ["專案總有效工期", f"{effective_work_days} 天", "", ""],
    ["專案總日曆天數", f"{calendar_days} 天", "", ""],
    ["預估完工日期", str(final_project_finish if enable_date else "日期未定"), "", ""]
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