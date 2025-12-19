import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
import plotly.express as px 
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import math

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v6.22", layout="wide")

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
    .warning-box {
        background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; 
        border-left: 6px solid #ffeeba; margin-top: 15px; font-size: 15px; line-height: 1.6;
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
        st.markdown("**結構型式**")
        c1_1, c1_2 = st.columns(2)
        with c1_1: struct_below = st.selectbox("地下結構", ["RC造", "SRC造"], index=0)
        with c1_2: struct_above = st.selectbox("地上結構", ["RC造", "SRC造", "SS造", "SC造"], index=0)
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (工期較長)", "玻璃帷幕 (工期較短)", "預鑄PC板", "金屬三明治板 (極快)"])
    
    with col2:
        foundation_type = st.selectbox("基礎型式", ["筏式基礎 (標準)", "樁基礎 (一般)", "全套管基樁 (工期長)", "壁樁 (Barrette)", "微型樁 (工期短)", "獨立基腳"])
        b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"])
        excavation_system = st.selectbox("開挖擋土系統", [
            "連續壁 + 型鋼內支撐 (標準)",
            "連續壁 + 地錨 (開挖動線佳)",
            "全套管切削樁 + 型鋼內支撐",
            "預壘樁/排樁 + 型鋼內支撐",
            "鋼板樁 + 型鋼內支撐 (淺開挖)",
            "放坡開挖/無支撐 (極快)"
        ])
        rw_aux_options = []
        if "連續壁" in excavation_system:
            rw_aux_options = st.multiselect("連續壁輔助措施", ["地中壁 (Cross Wall)", "扶壁 (Buttress Wall)"])
        
    with col3:
        site_condition = st.selectbox("基地現況", ["純空地 (無須拆除)", "有舊建物 (無地下室)", "有舊建物 (含舊地下室)", "僅存舊地下室 (需回填/破除)"
        ])
        soil_improvement = st.selectbox("地質改良", ["無", "局部改良 (JSP/CCP)", "全區改良"])
        prep_type_select = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"])
        if "自訂" in prep_type_select:
            prep_days_custom = st.number_input("輸入自訂前置天數", min_value=0, value=120)
        else:
            prep_days_custom = None
        
        st.markdown("**納入工項 (Scope)**")
        scope_options = st.multiselect(
            "請勾選本案包含之項目",
            ["機電管線工程", "室內裝修工程", "景觀工程"],
            default=["機電管線工程", "室內裝修工程", "景觀工程"]
        )

    st.divider()

    # === 下半部：規模量體 ===
    st.markdown("#### 2. 規模量體設定")
    dim_c1, dim_c2, dim_c3 = st.columns(3)
    
    with dim_c1:
        base_area_m2 = st.number_input("基地面積 (m²)", min_value=0.0, value=1652.89, step=10.0)
        base_area_ping = base_area_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{base_area_ping:,.2f} 坪</div>", unsafe_allow_html=True)
        
    est_floors = 18 
    est_fa_m2 = base_area_m2 * est_floors * 0.7 
    with dim_c2:
        total_fa_m2 = st.number_input("總樓地板面積 (m²)", min_value=0.0, value=est_fa_m2, step=100.0)
        total_fa_ping = total_fa_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{total_fa_ping:,.2f} 坪</div>", unsafe_allow_html=True)

    with dim_c3:
        floors_down = st.number_input("地下層數 (B)", min_value=0, value=3)
        enable_soil_limit = st.checkbox("評估土方運棄管制?", value=False, help="若勾選，將依據每日最大出土量計算開挖工期")
        
        if enable_soil_limit:
            est_soil_vol = base_area_m2 * (floors_down * 3.5) * 1.25 
            st.caption(f"預估總出土量(鬆方): {est_soil_vol:,.0f} m³")
            daily_soil_limit = st.number_input("每日最大出土量 (m³/日)", min_value=10, value=300, step=50, help="受棄土場或交通管制限制")
        else:
            daily_soil_limit = None

    st.write("") 
    building_details_df = None
    max_floors_up = 1
    building_count = 1
    calc_floors_struct = 1
    display_max_floor = 1
    display_max_roof = 0

    if "集合住宅" in b_type:
        st.markdown("##### 🏙️ 集合住宅 - 各棟樓層配置")
        t_col1, t_col2 = st.columns([1, 2])
        with t_col1:
            default_data = pd.DataFrame([
                {"棟別名稱": "A棟", "地上層數": 15, "屋突層數": 2}, 
                {"棟別名稱": "B棟", "地上層數": 15, "屋突層數": 2}, 
                {"棟別名稱": "C棟", "地上層數": 12, "屋突層數": 1}
            ])
            edited_df = st.data_editor(
                default_data, 
                num_rows="dynamic", 
                use_container_width=False, 
                column_config={
                    "棟別名稱": st.column_config.TextColumn("棟別", width="small", required=True),
                    "地上層數": st.column_config.NumberColumn("地上(F)", width="small", min_value=1, format="%d"),
                    "屋突層數": st.column_config.NumberColumn("屋突(R)", width="small", min_value=0, format="%d")
                }, 
                key="building_editor", height=150
            )
        with t_col2:
            st.caption("👈 請在表格設定各棟的地上與屋突層數。")
            if not edited_df.empty:
                edited_df["結構總層"] = edited_df["地上層數"] + edited_df["屋突層數"]
                max_struct_idx = edited_df["結構總層"].idxmax()
                row_max = edited_df.loc[max_struct_idx]
                calc_floors_struct = int(row_max["結構總層"])
                display_max_floor = int(row_max["地上層數"])
                display_max_roof = int(row_max["屋突層數"])
                building_count = len(edited_df)
                
                building_details_df = edited_df
                st.success(f"系統偵測共 **{building_count}** 棟。結構要徑依據 **{row_max['棟別名稱']}** 計算。")
            else:
                st.error("⚠️ 請至少輸入一棟資料")
                calc_floors_struct = 15
    else:
        st.markdown("##### 🏢 地上層數設定")
        s_col1, s_col2, s_col3 = st.columns(3) 
        with s_col1:
            floors_up = st.number_input("地上層數 (F)", min_value=1, value=12)
        with s_col2:
            floors_roof = st.number_input("屋突層數 (R)", min_value=0, value=2, help="屋突層數列入結構工期計算")
        
        calc_floors_struct = floors_up + floors_roof
        display_max_floor = floors_up
        display_max_roof = floors_roof
        building_count = 1

    # [New Feature Updated] 危評/外審 明確提示
    risk_review_msg = []
    add_review_days = 0
    
    # 邏輯 A: 結構外審 (通常 50m 以上) -> 約 16F
    if display_max_floor >= 16:
        risk_review_msg.append("📏 地上層數達 16F+ (建物高度約 50m 以上，需結構外審)")
        add_review_days = 90
        
    # 邏輯 B: 丁類危評 (通常 80m 以上) -> 約 25F
    if display_max_floor >= 25:
        risk_review_msg.append("🏗️ 地上層數達 25F+ (建物高度約 80m 以上，需丁類危評)")
        add_review_days = 120 # 若同時滿足外審與危評，直接加 120 天
    
    # 邏輯 C: 丁類危評 (開挖 15m 以上) -> 約 B4
    if floors_down >= 4:
        risk_review_msg.append("⛏️ 地下層數達 B4+ (開挖深度約 15m 以上，需丁類危評)")
        if add_review_days < 120: # 確保不重複疊加過多
            add_review_days = max(add_review_days, 60)
            if add_review_days == 90 and "結構外審" in str(risk_review_msg):
                 add_review_days = 120 # 外審+危評

    if risk_review_msg:
        msg_str = "<br>".join([f"• {m}" for m in risk_review_msg])
        st.markdown(f"""
        <div class='warning-box'>
            <b>⚠️ 自動偵測風險評估：</b><br>
            {msg_str}<br>
            <hr style="margin:5px 0; border-top:1px dashed #bba55a;">
            👉 依據法規標準，已自動於「1. 規劃與前期作業」增加 <b>{add_review_days} 天</b> 行政審查緩衝期。
        </div>
        """, unsafe_allow_html=True)

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
base_area_factor = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
vol_factor = 1.0
if total_fa_ping > 3000:
    vol_factor = 1 + ((total_fa_ping - 3000) / 5000) * 0.05
    vol_factor = min(vol_factor, 1.2)
area_multiplier = base_area_factor * vol_factor

struct_map_above = {"RC造": 25, "SRC造": 25, "SS造": 7, "SC造": 21}

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

aux_wall_factor = 0
if "地中壁" in str(rw_aux_options): aux_wall_factor += 0.20
if "扶壁" in str(rw_aux_options): aux_wall_factor += 0.10

# [A] 工項天數計算
if "自訂" in prep_type_select and prep_days_custom is not None:
    d_prep_base = int(prep_days_custom)
else:
    d_prep_base = 120 if "一般" in prep_type_select else 210 if "鄰捷運" in prep_type_select else 300

# [Key Update] 將危評天數加入前置作業
d_prep = d_prep_base + add_review_days

if "純空地" in site_condition: d_demo = 0; demo_note = "純空地"
elif "有舊建物 (含舊地下室)" in site_condition: d_demo = int(100 * area_multiplier); demo_note = "全棟拆除(含地下室)"
elif "有舊建物 (無地下室)" in site_condition: d_demo = int(45 * area_multiplier); demo_note = "地上拆除"
else: d_demo = int(60 * area_multiplier); demo_note = "地下結構破除"

d_soil = int((30 if "局部" in soil_improvement else 60 if "全區" in soil_improvement else 0) * area_multiplier)

foundation_add = 0
if "全套管" in foundation_type: foundation_add = 90
elif "壁樁" in foundation_type: foundation_add = 80
elif "樁基礎" in foundation_type: foundation_add = 60
elif "微型樁" in foundation_type: foundation_add = 30

sub_speed_factor = 1.15 if "逆打" in b_method else 1.0
d_aux_wall_days = int(60 * aux_wall_factor) 

if "連續壁" in excavation_system: base_retain = 60
elif "全套管" in excavation_system: base_retain = 50
elif "預壘樁" in excavation_system: base_retain = 40
elif "鋼板樁" in excavation_system: base_retain = 25
else: base_retain = 10 
d_retain_work = int((base_retain + d_aux_wall_days) * area_multiplier)

d_excav_std = int((floors_down * 22 * excav_multiplier) * area_multiplier) 
excav_note = "出土/支撐"

if enable_soil_limit and daily_soil_limit and base_area_m2 > 0:
    total_soil_m3 = base_area_m2 * (floors_down * 3.5) * 1.25
    d_excav_limited = math.ceil(total_soil_m3 / daily_soil_limit)
    d_excav_phase = max(d_excav_std, d_excav_limited)
    if d_excav_limited > d_excav_std:
        excav_note = f"受限每日{daily_soil_limit}m³"
else:
    d_excav_phase = d_excav_std

if "放坡" in excavation_system or "無支撐" in excavation_system:
    d_strut_install = 0
    d_earth_work = d_excav_phase
else:
    d_strut_install = d_excav_phase
    d_earth_work = d_excav_phase

d_struct_below = int(((floors_down * 35) + foundation_add) * area_multiplier)
d_struct_body = int(calc_floors_struct * struct_map_above.get(struct_above, 14) * area_multiplier * k_usage)
d_ext_wall = int(calc_floors_struct * 12 * area_multiplier * ext_wall_multiplier * k_usage)

if "機電管線工程" in scope_options:
    d_mep = int((60 + calc_floors_struct * 4) * area_multiplier * k_usage)
else: d_mep = 0

if "室內裝修工程" in scope_options:
    d_fit_out = int((60 + calc_floors_struct * 3) * area_multiplier * k_usage)
else: d_fit_out = 0

if "景觀工程" in scope_options:
    d_landscape = int(45 * base_area_factor) 
else: d_landscape = 0

d_insp_base = 150 if b_type in ["百貨", "醫院", "飯店"] else 90
if "集合住宅" in b_type: 
    d_insp = d_insp_base + (building_count - 1) * 15
    insp_note = f"多棟聯合驗收 (共{building_count}棟)" 
else: 
    d_insp = d_insp_base
    insp_note = "標準驗收流程"

# [B] 日期推算
def get_end_date(start_date, days_needed):
    curr = start_date
    if days_needed <= 0: return curr 
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

# 4. 擋土壁
p4_s = p_soil_e + timedelta(days=1)
p4_e = get_end_date(p4_s, d_retain_work)

# 5. 擋土支撐
p5_s = p4_e + timedelta(days=1)
p5_e = get_end_date(p5_s, d_strut_install)

# 6. 土方開挖
p6_s = p5_s 
p6_e = get_end_date(p6_s, d_earth_work)
p_excav_finish = max(p5_e, p6_e)

# 7. 地下結構
if "逆打" in b_method or "雙順打" in b_method:
    lag_excav = int(30 * area_multiplier)
    p7_s = get_end_date(p6_s, lag_excav)
    p7_e = get_end_date(p7_s, d_struct_below)
    
    lag_1f_slab = int(60 * area_multiplier)
    p8_s = get_end_date(p6_s, lag_1f_slab) 
    struct_note_below = f"併行 ({struct_below})"
    struct_note_above = f"併行 ({display_max_floor}F+{display_max_roof}R)"
else:
    p7_s = p_excav_finish + timedelta(days=1)
    p7_e = get_end_date(p7_s, d_struct_below)
    
    p8_s = p7_e + timedelta(days=1)
    struct_note_below = f"要徑 ({struct_below})"
    struct_note_above = f"順打 ({display_max_floor}F+{display_max_roof}R)"

p8_e = get_end_date(p8_s, d_struct_body)
lag_ext = int(d_struct_body * 0.5)
p_ext_s = get_end_date(p8_s, lag_ext)
p_ext_e = get_end_date(p_ext_s, d_ext_wall)

# 10. 機電
lag_mep = int(d_struct_body * 0.3) 
p10_s = get_end_date(p8_s, lag_mep)
p10_e = get_end_date(p10_s, d_mep)

# 11. 裝修
lag_fit_out = int(d_struct_body * 0.6)
p11_s = get_end_date(p8_s, lag_fit_out)
p11_e = get_end_date(p11_s, d_fit_out)

# 12. 景觀
p12_s = p_ext_e - timedelta(days=15) 
p12_e = get_end_date(p12_s, d_landscape)

# 13. 驗收
p13_s = max(p_ext_e, p10_e, p11_e, p12_e) - timedelta(days=30)
p13_e = get_end_date(p13_s, d_insp)

final_project_finish = max(p7_e, p8_e, p_ext_e, p10_e, p11_e, p12_e, p13_e)

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
excav_str_display = f"工法:{excavation_system}"
if rw_aux_options: excav_str_display += " (+輔助壁)"

if add_review_days > 0:
    prep_note = f"含危評審查 (+{add_review_days}天)"
else:
    prep_note = "要徑"

schedule_data = [
    {"工項階段": "1. 規劃與前期作業", "需用工作天": d_prep, "Start": p1_s, "Finish": p1_e, "備註": prep_note},
    {"工項階段": "2. 建物拆除與整地", "需用工作天": d_demo, "Start": p2_s, "Finish": p2_e, "備註": demo_note},
    {"工項階段": "3. 地質改良工程", "需用工作天": d_soil, "Start": p_soil_s, "Finish": p_soil_e, "備註": "要徑"},
    {"工項階段": "4. 擋土壁施作工程", "需用工作天": d_retain_work, "Start": p4_s, "Finish": p4_e, "備註": excav_str_display},
    {"工項階段": "5. 擋土支撐架設", "需用工作天": d_strut_install, "Start": p5_s, "Finish": p5_e, "備註": "開挖併行"},
    {"工項階段": "6. 土方開挖工程", "需用工作天": d_earth_work, "Start": p6_s, "Finish": p6_e, "備註": excav_note},
    {"工項階段": "7. 地下結構工程", "需用工作天": d_struct_below, "Start": p7_s, "Finish": p7_e, "備註": struct_note_below},
    {"工項階段": "8. 地上主體結構", "需用工作天": d_struct_body, "Start": p8_s, "Finish": p8_e, "備註": struct_note_above},
    {"工項階段": "9. 建物外牆工程", "需用工作天": d_ext_wall, "Start": p_ext_s, "Finish": p_ext_e, "備註": "併行"},
    {"工項階段": "10. 機電管線工程", "需用工作天": d_mep, "Start": p10_s, "Finish": p10_e, "備註": "併行 (選配)"},
    {"工項階段": "11. 室內裝修工程", "需用工作天": d_fit_out, "Start": p11_s, "Finish": p11_e, "備註": "併行 (選配)"},
    {"工項階段": "12. 景觀工程", "需用工作天": d_landscape, "Start": p12_s, "Finish": p12_e, "備註": "併行 (選配)"},
    {"工項階段": "13. 驗收取得使照", "需用工作天": d_insp, "Start": p13_s, "Finish": p13_e, "備註": insp_note},
]

sched_display_df = pd.DataFrame(schedule_data)
sched_display_df = sched_display_df[sched_display_df["需用工作天"] > 0]
sched_display_df["預計開始"] = sched_display_df["Start"].apply(lambda x: str(x) if enable_date else "依開工日推算")
sched_display_df["預計完成"] = sched_display_df["Finish"].apply(lambda x: str(x) if enable_date else "依開工日推算")
st.dataframe(sched_display_df[["工項階段", "需用工作天", "預計開始", "預計完成", "備註"]], hide_index=True, use_container_width=True)

# --- 8. 甘特圖 ---
st.subheader("📊 專案進度甘特圖")
if not sched_display_df.empty:
    gantt_df = sched_display_df.copy()
    professional_colors = ["#708090", "#A52A2A", "#8B4513", "#2F4F4F", "#696969", "#708090", "#A0522D", "#4682B4", "#CD5C5C", "#5F9EA0", "#2E8B57", "#556B2F", "#DAA520"]
    fig = px.timeline(
        gantt_df, x_start="Start", x_end="Finish", y="工項階段", color="工項階段",
        color_discrete_sequence=professional_colors, text="工項階段", 
        title=f"【{project_name}】工程進度模擬 (地上:{struct_above} / 地下:{struct_below})",
        hover_data={"需用工作天": True, "備註": True}, height=600
    )
    fig.update_traces(
        textposition='inside', insidetextanchor='start', width=0.5, 
        marker_line_width=0, opacity=0.9, textfont=dict(size=16, family="Microsoft JhengHei")
    )
    fig.update_layout(
        plot_bgcolor='white', font=dict(family="Microsoft JhengHei", size=14, color="#2D2926"), 
        xaxis=dict(title="工程期程", showgrid=True, gridcolor='#EEE', tickfont=dict(size=14)), 
        yaxis=dict(title="", autorange="reversed", tickfont=dict(size=14)), 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)), 
        margin=dict(l=20, r=20, t=60, b=20)
    )
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
        details_list.append(f"{row['棟別名稱']}:地上{row['地上層數']}F/屋突{row['屋突層數']}R")
    details_str = " ; ".join(details_list)

aux_str = ", ".join(rw_aux_options) if rw_aux_options else "無"
excavation_str = f"{excavation_system}"
if rw_aux_options: excavation_str += f" (輔助: {aux_str})"

report_rows = [
    ["項目名稱", project_name],
    ["[ 建築規模與條件 ]", ""],
    ["建物類型", b_type_str], 
    ["各棟配置", details_str],
    ["地上結構", struct_above], ["地下結構", struct_below],
    ["外牆型式", ext_wall],
    ["基礎型式", foundation_type], ["施工方式", b_method], 
    ["開挖擋土", excavation_str],
    ["基地現況", site_condition], ["地質改良", soil_improvement],
    ["基地面積", f"{base_area_m2:,.2f} m² / {base_area_ping:,.2f} 坪"],
    ["總樓地板面積", f"{total_fa_m2:,.2f} m² / {total_fa_ping:,.2f} 坪"],
    ["樓層規模", f"地下 {floors_down} B / 最高地上 {display_max_floor} F (屋突 {display_max_roof} R)"],
    ["納入工項", ", ".join(scope_options)],
    ["土方管制", f"每日限 {daily_soil_limit} m³" if enable_soil_limit else "無"],
    ["危評/外審", f"增加 {add_review_days} 天 (前期)" if add_review_days > 0 else "無"],
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