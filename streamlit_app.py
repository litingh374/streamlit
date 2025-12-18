import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v4.0", layout="wide", page_icon="🏗️")

# --- 2. CSS 樣式優化 ---
st.markdown("""
    <style>
    :root { --main-yellow: #FFB81C; --accent-orange: #FF4438; --dark-grey: #2D2926; --blue-light: #e3f2fd; }
    .stApp { background-color: #ffffff; }
    h1, h2, h3, label { color: var(--dark-grey) !important; font-weight: bold !important; font-family: 'Microsoft JhengHei', sans-serif; }
    
    /* 按鈕樣式 */
    .stButton>button { 
        background-color: var(--main-yellow); color: var(--dark-grey); 
        border: none; width: 100%; border-radius: 8px; font-size: 18px; font-weight: bold; padding: 12px;
        transition: all 0.3s;
    }
    .stButton>button:hover { filter: brightness(0.95); box-shadow: 0 2px 5px rgba(0,0,0,0.2); }

    /* 指標卡片樣式 */
    .metric-container {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        border-left: 8px solid var(--main-yellow);
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; text-align: center;
    }
    .metric-container small { color: #666; font-size: 0.9em; }
    .metric-container b { font-size: 1.4em; display: block; margin-top: 5px; }

    /* 面積顯示 */
    .area-display {
        background-color: var(--blue-light); padding: 8px 12px; border-radius: 5px;
        font-size: 15px; color: #1565c0; margin-top: -10px; margin-bottom: 15px;
        border-left: 4px solid #1565c0; font-weight: bold;
    }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 標題與基本資訊 ---
st.title("🏗️ 建築施工工期估算輔助系統 v4.0")
st.markdown("結合 **CPM 要徑排程**、**併行施工邏輯** 與 **現金流預估** 的專業版工具")

col_name, col_budget = st.columns([2, 1])
with col_name:
    project_name = st.text_input("📝 專案名稱", value="台北信義區集合住宅案")
with col_budget:
    total_budget = st.number_input("💰 預估總造價 (萬元)", min_value=0, value=50000, step=1000, help="用於計算現金流 S-Curve")

# --- 4. 參數輸入區 ---
st.subheader("📋 建築規模與參數設定")
with st.expander("點擊展開/隱藏 詳細參數", expanded=True):
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
        floors_up = st.number_input("地上層數 (F)", min_value=1, value=15)
        floors_down = st.number_input("地下層數 (B)", min_value=0, value=4)
        base_area_m2 = st.number_input("基地面積 (m²)", min_value=1.0, value=1652.89, step=10.0)
        base_area_ping = base_area_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{base_area_ping:,.2f} 坪</div>", unsafe_allow_html=True)

st.subheader("📅 日期與排除條件")
with st.expander("點擊展開/隱藏 日期設定", expanded=False):
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

# --- 5. 核心運算邏輯 (v4.0 優化版) ---
# 係數設定
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

# 安全版日期計算函數 (防止無窮迴圈)
def get_end_date(start_date, days_needed):
    curr = start_date
    added = 0
    max_loops = days_needed * 10 + 365 # 安全閥值
    loop_count = 0
    
    while added < days_needed:
        if loop_count > max_loops:
            return curr # 強制返回避免當機
        
        curr += timedelta(days=1)
        loop_count += 1
        
        if exclude_sat and curr.weekday() == 5: continue
        if exclude_sun and curr.weekday() == 6: continue
        if exclude_cny and curr.month == 2 and 1 <= curr.day <= 7: continue
        
        added += 1
    return curr

# CPM 排程計算
p1_start = start_date_val
p1_end = get_end_date(p1_start, d_prep)

p2_start = p1_end + timedelta(days=1)
p2_end = get_end_date(p2_start, d_demo)

p3_start = p2_end + timedelta(days=1)
p3_end = get_end_date(p3_start, d_sub)

p4_start = p3_end + timedelta(days=1)
p4_end = get_end_date(p4_start, d_super)

# 併行施工邏輯
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

# --- 6. 結果顯示區 ---
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

# 資料準備
schedule_data = [
    {"工項階段": "1. 規劃與前期作業", "需用工作天": d_prep, "開始日期": p1_start, "完成日期": p1_end, "權重": 0.05, "備註": "要徑作業"},
    {"工項階段": "2. 建物拆除與整地", "需用工作天": d_demo, "開始日期": p2_start, "完成日期": p2_end, "權重": 0.05, "備註": "要徑作業"},
    {"工項階段": "3. 地下室結構/土方", "需用工作天": d_sub, "開始日期": p3_start, "完成日期": p3_end, "權重": 0.20, "備註": "要徑作業"},
    {"工項階段": "4. 地上主體結構工程", "需用工作天": d_super, "開始日期": p4_start, "完成日期": p4_end, "權重": 0.35, "備註": "要徑作業"},
    {"工項階段": "5. 內裝機電/管線工程", "需用工作天": d_mep, "開始日期": p5_start, "完成日期": p5_end, "權重": 0.15, "備註": "結構 30% 進場"},
    {"工項階段": "6. 室內裝修/景觀工程", "需用工作天": d_finishing, "開始日期": p6_start, "完成日期": p6_end, "權重": 0.15, "備註": "結構 60% 進場"},
    {"工項階段": "7. 驗收取得使照", "需用工作天": d_insp, "開始日期": p7_start, "完成日期": p7_end, "權重": 0.05, "備註": "完工後進行"},
]
sched_df = pd.DataFrame(schedule_data)

# --- 7. 進階視覺化 (Gantt & S-Curve) ---
tab1, tab2, tab3 = st.tabs(["📅 甘特圖排程", "💰 現金流 S-Curve", "📋 詳細數據表"])

with tab1:
    if enable_date:
        gantt_df = sched_df.copy()
        gantt_df['Start'] = pd.to_datetime(gantt_df['開始日期'])
        gantt_df['Finish'] = pd.to_datetime(gantt_df['完成日期'])
        
        fig_gantt = px.timeline(
            gantt_df, x_start="Start", x_end="Finish", y="工項階段", color="工項階段",
            title=f"<b>{project_name} - 施工進度甘特圖</b>",
            labels={"工項階段": "工程項目"}, hover_data=["需用工作天", "備註"],
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.warning("請先啟用「開工日期計算」以檢視甘特圖。")

with tab2:
    if enable_date and total_budget > 0:
        # 計算 S-Curve 數據
        dates = pd.date_range(start=p1_start, end=p7_end)
        cash_flow = pd.DataFrame(index=dates, columns=['Daily_Cost'])
        cash_flow['Daily_Cost'] = 0.0

        for item in schedule_data:
            s = item['開始日期']
            e = item['完成日期']
            total_days = (e - s).days + 1
            if total_days > 0:
                daily_cost = (total_budget * item['權重']) / total_days
                # 將該工項的每日成本加總到對應日期
                mask = (cash_flow.index >= pd.Timestamp(s)) & (cash_flow.index <= pd.Timestamp(e))
                cash_flow.loc[mask, 'Daily_Cost'] += daily_cost
        
        cash_flow['Cumulative_Cost'] = cash_flow['Daily_Cost'].cumsum()
        cash_flow['Progress_Pct'] = (cash_flow['Cumulative_Cost'] / total_budget) * 100
        
        # 繪製 S-Curve
        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=cash_flow.index, y=cash_flow['Cumulative_Cost'],
            mode='lines', name='預估累計現金流',
            line=dict(color='#FF4438', width=3), fill='tozeroy', fillcolor='rgba(255, 68, 56, 0.1)'
        ))
        fig_curve.update_layout(
            title=f"<b>{project_name} - 預估現金流 S-Curve (總造價: {total_budget:,} 萬)</b>",
            xaxis_title="日期", yaxis_title="累計金額 (萬元)",
            hovermode="x unified", height=400, margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig_curve, use_container_width=True)
    else:
        st.info("請輸入「總造價」並啟用日期計算以檢視 S-Curve。")

with tab3:
    display_df = sched_df.drop(columns=['權重'])
    if not enable_date:
        display_df["開始日期"] = "未定"
        display_df["完成日期"] = "未定"
    st.table(display_df)

# --- 8. Excel 導出 ---
st.divider()
st.subheader("📥 導出專業報表")

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    # 建立數據
    report_rows = [
        ["項目名稱", project_name],
        ["預估總造價", f"{total_budget:,} 萬元"],
        ["", ""],
        ["[ 建築規模 ]", ""],
        ["建物類型", b_type], ["結構型式", b_struct], ["外牆型式", ext_wall],
        ["基地面積", f"{base_area_m2:,.2f} m² / {base_area_ping:,.2f} 坪"],
        ["樓層規模", f"地上 {floors_up} F / 地下 {floors_down} B"],
        ["", ""],
        ["[ 進度分析 (採併行施工邏輯) ]", ""]
    ]
    
    headers = ["工項階段", "需用工作天", "日期區間", "備註"]
    data_rows = []
    for item in schedule_data:
        s_date = str(item['開始日期']) if enable_date else "未定"
        e_date = str(item['完成日期']) if enable_date else "未定"
        data_rows.append([item["工項階段"], f"{item['需用工作天']} 天", f"{s_date} ~ {e_date}", item['備註']])
    
    # 寫入 Excel
    df_meta = pd.DataFrame(report_rows)
    df_data = pd.DataFrame(data_rows, columns=headers)
    
    df_meta.to_excel(writer, index=False, header=False, sheet_name='詳細工期報告', startrow=0)
    df_data.to_excel(writer, index=False, header=True, sheet_name='詳細工期報告', startrow=len(report_rows)+1)
    
    # 美化樣式
    ws = writer.sheets['詳細工期報告']
    
    # 定義樣式
    header_fill = PatternFill(start_color="2D2926", end_color="2D2926", fill_type="solid")
    header_font = Font(name='微軟正黑體', size=12, bold=True, color="FFB81C")
    section_fill = PatternFill(start_color="EFEFEF", end_color="EFEFEF", fill_type="solid")
    section_font = Font(name='微軟正黑體', size=11, bold=True)
    
    # 欄寬調整
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 25
    
    # 格式化迴圈
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            if cell.row == len(report_rows) + 2: # 表頭行
                cell.fill = header_fill
                cell.font = header_font
            elif cell.value and isinstance(cell.value, str) and "[" in cell.value:
                cell.fill = section_fill
                cell.font = section_font

excel_data = buffer.getvalue()
st.download_button(
    label="📊 下載完整分析報告 (Excel)",
    data=excel_data,
    file_name=f"{project_name}_v4_工期與現金流分析.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)