import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
import plotly.express as px 
import plotly.graph_objects as go
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import math
import sqlite3

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v6.89", layout="wide")

# ==========================================
# 💾 資料庫管理模組 (SQLite) - v2
# ==========================================
DB_NAME = "construction_history_v2.db"

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_date TEXT,
            project_name TEXT,
            location TEXT,
            design_unit TEXT,
            b_type TEXT,
            struct_above TEXT,
            base_area REAL,
            floors_up INTEGER,
            floors_down REAL,
            total_cal_days INTEGER,
            final_finish_date TEXT,
            note TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(data_dict):
    """儲存資料"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO projects (save_date, project_name, location, design_unit, b_type, struct_above, base_area, floors_up, floors_down, total_cal_days, final_finish_date, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        data_dict['project_name'],
        data_dict['location'],
        data_dict['design_unit'],
        data_dict['b_type'],
        data_dict['struct_above'],
        data_dict['base_area'],
        data_dict['floors_up'],
        data_dict['floors_down'],
        data_dict['total_cal_days'],
        data_dict['final_finish_date'],
        data_dict['note']
    ))
    conn.commit()
    conn.close()

def load_from_db():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM projects ORDER BY id DESC", conn)
    conn.close()
    return df

def delete_from_db(project_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🔐 密碼登入
# ==========================================
def check_password():
    ACTUAL_PASSWORD = "1234" 
    def password_entered():
        if st.session_state["password"] == ACTUAL_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<div style='text-align: center; margin-top: 50px;'><h1>🔒 系統登入</h1></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.text_input("請輸入密碼", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and st.session_state["password_correct"] == False:
                st.error("❌ 密碼錯誤")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- CSS ---
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
    .section-header {
        font-size: 18px; font-weight: bold; color: #2D2926; 
        border-bottom: 2px solid #FFB81C; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px;
    }
    .warning-box {
        background-color: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 5px; color: #856404; margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; color: #0c5460; margin: 10px 0;
    }
    div[data-testid="stDataEditor"] { border: 1px solid #ddd; border-radius: 5px; margin-top: 5px; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 導航 ---
st.sidebar.title("功能選單")
if st.sidebar.button("🔒 登出系統"):
    st.session_state["password_correct"] = False
    st.rerun()

page_mode = st.sidebar.radio("請選擇功能", ["單案詳細估算", "順打 vs 逆打 比較", "🗄️ 歷史專案資料庫"], index=0)

# ==========================================
# 🗄️ 歷史專案資料庫
# ==========================================
if page_mode == "🗄️ 歷史專案資料庫":
    st.title("🗄️ 歷史專案資料庫")
    df_history = load_from_db()
    
    if not df_history.empty:
        search_query = st.text_input("🔍 搜尋專案名稱", "")
        if search_query:
            df_history = df_history[df_history['project_name'].str.contains(search_query, case=False)]
        
        st.dataframe(
            df_history, 
            column_config={
                "save_date": "儲存日期",
                "project_name": "工程名稱",
                "location": "地點",
                "design_unit": "設計單位",
                "total_cal_days": "工期(天)",
                "final_finish_date": "完工日"
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("### 🗑️ 管理資料")
        d1, d2 = st.columns([3, 1])
        with d1:
            project_to_delete = st.selectbox("選擇要刪除的專案", df_history['project_name'] + " (ID:" + df_history['id'].astype(str) + ")")
        with d2:
            if st.button("確認刪除"):
                if project_to_delete:
                    pid = project_to_delete.split("ID:")[-1].replace(")", "")
                    delete_from_db(pid)
                    st.success("已刪除！")
                    st.rerun()
    else:
        st.info("尚無歷史資料，請先至計算頁面儲存。")
    st.stop()

# ==========================================
# 主計算頁面
# ==========================================
st.title(f"🏗️ 建築工期估算 - {page_mode} v6.89")
st.caption("參數更新：新增「鋼軌樁」工法選項 (v6.89)")

# 基本資料
st.subheader("📝 基本標案資料")
info_c1, info_c2, info_c3 = st.columns(3)
with info_c1:
    project_name = st.text_input("工程名稱", placeholder="例如：信義區A案")
with info_c2:
    project_location = st.text_input("地號位置", placeholder="例如：信義段一小段")
with info_c3:
    design_unit = st.text_input("設計單位", placeholder="例如：某某建築師事務所")

# 全域變數
dw_reality_factor = 1.75

# --- 參數輸入區 ---
st.subheader("📋 建築規模參數")
with st.expander("點擊展開/隱藏 一般參數面板", expanded=True):
    
    # Section 1
    st.markdown("<div class='section-header'>1. 核心構造與工法</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        b_type = st.selectbox("建物類型", ["住宅", "集合住宅 (多棟)", "辦公大樓", "飯店", "百貨", "廠房", "醫院"], index=None, placeholder="請選擇...")
        if page_mode == "順打 vs 逆打 比較":
            b_method = "自動比較模式" 
            st.selectbox("施工方式", ["(比較模式自動設定)"], disabled=True)
        else:
            b_method = st.selectbox("施工方式", ["順打工法", "逆打工法", "雙順打工法"], index=None, placeholder="請選擇...")
    with c2:
        struct_above = st.selectbox("地上結構", ["RC造", "SRC造", "SS造", "SC造"], index=None, placeholder="請選擇...")
        struct_below = st.selectbox("地下結構", ["RC造", "SRC造"], index=None, placeholder="請選擇...")
    with c3:
        st.write("###### 樓版工法")
        slab_type = st.radio("樓版型式", ["一般 RC 樓版", "鋼承板 (Deck)"], index=0, help="Deck 版工期較短，業界標準約 15 天/層")
    with c4:
        st.empty()

    # Section 2
    st.markdown("<div class='section-header'>2. 規模量體設定</div>", unsafe_allow_html=True)
    dim_c1, dim_c2 = st.columns(2)
    with dim_c1:
        base_area_m2 = st.number_input("基地面積 (m²)", min_value=0.0, value=0.0, step=10.0)
        base_area_ping = base_area_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{base_area_ping:,.2f} 坪</div>", unsafe_allow_html=True)
    with dim_c2:
        total_fa_m2 = st.number_input("總樓地板面積 (m²)", min_value=0.0, value=0.0, step=100.0)
        total_fa_ping = total_fa_m2 * 0.3025
        st.markdown(f"<div class='area-display'>換算：{total_fa_ping:,.2f} 坪</div>", unsafe_allow_html=True)

    # 樓層
    building_details_df = None
    max_floors_up = 1
    building_count = 1
    calc_floors_struct = 0
    display_max_floor = 0
    display_max_roof = 0
    floors_down = 0.0
    is_complex_excavation = False
    weighted_avg_depth = 0.0
    complex_soil_vol = 0.0
    max_depth_complex = 0.0
    daily_soil_limit = 300

    if b_type and "集合住宅" in b_type:
        st.markdown("##### 🏙️ 集合住宅 - 各棟樓層配置")
        t_col1, t_col2 = st.columns([1, 2])
        with t_col1:
            default_data = pd.DataFrame([{"棟別名稱": "A棟", "地上層數": 0, "屋突層數": 0}, {"棟別名稱": "B棟", "地上層數": 0, "屋突層數": 0}])
            edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=False, key="building_editor", height=150)
        with t_col2:
            if not edited_df.empty and edited_df["地上層數"].sum() > 0:
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
                st.warning("⚠️ 請輸入至少一棟的樓層資料")
                calc_floors_struct = 0
        st.markdown("---")
        st.markdown("##### ⛏️ 地下開挖與樓層設定")
    else:
        st.markdown("##### 🏢 層數設定")
        s_col1, s_col2, s_col3 = st.columns(3) 
        with s_col1:
            toggle_state = st.session_state.get("complex_toggle_single", False)
            is_complex_excavation = toggle_state
            if toggle_state:
                floors_down_input = st.number_input("加權平均層數 (B)", value=0.0, disabled=True, key="fd_disabled_view")
            else:
                floors_down_input = st.number_input("地下層數 (B)", min_value=0.0, value=0.0, step=1.0, key="fd_single_real")
                floors_down = floors_down_input
            st.checkbox("啟用分區開挖 (深淺不一)", key="complex_toggle_single")
        with s_col2: 
            floors_up = st.number_input("地上層數 (F)", min_value=0, value=0, key="fu_single")
        with s_col3: 
            floors_roof = st.number_input("屋突層數 (R)", min_value=0, value=0, key="fr_single")
        calc_floors_struct = floors_up + floors_roof
        display_max_floor = floors_up
        display_max_roof = floors_roof
        building_count = 1

    if b_type and "集合住宅" in b_type:
        is_complex_excavation = st.checkbox("啟用分區開挖深度設定 (深淺不一)", value=False, key="complex_toggle_multi")
        if not is_complex_excavation:
            floors_down = st.number_input("地下層數 (B)", min_value=0.0, value=0.0, step=1.0, key="fd_multi")

    if is_complex_excavation:
        st.info("📋 請輸入各分區的面積與開挖深度：")
        ce_col1, ce_col2 = st.columns([2, 1])
        with ce_col1:
            complex_data = pd.DataFrame([{"分區說明": "A區", "面積 (m²)": 0.0, "開挖深度 (m)": 0.0}, {"分區說明": "B區", "面積 (m²)": 0.0, "開挖深度 (m)": 0.0}])
            complex_df = st.data_editor(complex_data, num_rows="dynamic", use_container_width=True, key="excav_editor")
        with ce_col2:
            if not complex_df.empty:
                complex_df["體積"] = complex_df["面積 (m²)"] * complex_df["開挖深度 (m)"]
                total_complex_area = complex_df["面積 (m²)"].sum()
                complex_soil_vol = complex_df["體積"].sum()
                max_depth_complex = complex_df["開挖深度 (m)"].max()
                if total_complex_area > 0: weighted_avg_depth = complex_soil_vol / total_complex_area
                else: weighted_avg_depth = 0
                floors_down_equiv = weighted_avg_depth / 3.5
                floors_down = float(floors_down_equiv)
                st.markdown(f"**加權平均深度:** `{weighted_avg_depth:.2f} m`")
                st.success(f"**換算等效層數:** `B{floors_down_equiv:.1f}`")
            else: floors_down = 0.0

    enable_soil_limit = st.checkbox("評估土方運棄管制?", value=False, key="sl_common")
    if enable_soil_limit:
        daily_soil_limit = st.number_input("每日限出土 (m³)", min_value=10, value=300, key="dl_common")

    st.markdown("##### 📏 建物高度與開挖深度 (選填)")
    dim_c4, dim_c5, dim_c6 = st.columns(3)
    with dim_c4:
        if is_complex_excavation: default_depth_val = max_depth_complex
        else: default_depth_val = floors_down * 3.5
        manual_excav_depth_m = st.number_input(f"最大開挖深度 (m)", value=0.0, step=0.1)
    with dim_c5:
        manual_height_m = st.number_input(f"建物全高 (m)", value=0.0, step=0.1)
    with dim_c6:
        manual_roof_height_m = st.number_input(f"屋突高度 (m)", value=0.0, step=0.1)

    # Section 3
    st.markdown("<div class='section-header'>3. 基地現況與前置作業</div>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        site_condition = st.selectbox("基地現況", ["純空地 (無須拆除)", "有舊建物 (無地下室)", "有舊建物 (含舊地下室)", "僅存舊地下室 (需回填/破除)"], index=None, placeholder="請選擇...")
        is_deep_demo = site_condition and "舊地下室" in site_condition
        obstruction_method = "一般怪手破除"
        backfill_method = "回填舊地下室 (標準)"
        deep_gw_seq = "無"
        obs_strategy = "無"
        if is_deep_demo:
            backfill_method = st.radio("施工平台建置", ["回填舊地下室 (標準)", "不回填 (架設施工構台)"], horizontal=True)
            obstruction_method = st.selectbox("地中障礙清障方式", ["一般怪手破除", "深導溝 (Deep Guide Wall)", "全套管切削 (All-Casing)"], index=None, placeholder="請選擇...")
            obs_strategy = obstruction_method
            if obstruction_method and "深導溝" in obstruction_method:
                deep_gw_seq = st.selectbox("深導溝施作順序", ["先回填後施作 (標準)", "邊回填邊施作 (重疊)"], index=None, placeholder="請選擇...")
    with s2:
        soil_improvement = st.selectbox("地質改良", ["無", "局部改良 (JSP/CCP)", "全區改良"], index=None, placeholder="請選擇...")
    with s3:
        prep_type_select = st.selectbox("前置作業類型", ["一般 (120天)", "鄰捷運 (180-240天)", "大型公共工程/環評 (300天+)", "自訂"], index=None, placeholder="請選擇...")
        if prep_type_select and "自訂" in prep_type_select:
            prep_days_custom = st.number_input("輸入自訂前置天數", min_value=0, value=120)
        else: prep_days_custom = None
        enable_manual_review = st.checkbox("納入危評/外審緩衝期", value=False)
        manual_review_days_input = 0
        if enable_manual_review:
            manual_review_days_input = st.number_input("輸入緩衝天數", min_value=0, value=90, step=30, label_visibility="collapsed")

    # Section 4
    st.markdown("<div class='section-header'>4. 大地工程與基礎 (組合式工法)</div>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3)
    selected_wall = None
    selected_support = None
    excavation_map_val = 1.0 
    rw_aux_options = []
    with g1:
        # [v6.89] 新增 鋼軌樁 選項
        wall_type_options = ["連續壁 (Diaphragm Wall)", "全套管切削樁 (All-Casing)", "預壘樁/排樁 (PIP/Soldier Pile)", "鋼板樁 (Sheet Pile)", "鋼軌樁 (H-Pile)", "無 (純明挖/放坡)"]
        selected_wall = st.selectbox("A. 擋土壁體類型", wall_type_options, index=None, placeholder="請選擇...")
        support_type_options = ["型鋼內支撐 (Strut)", "地錨 (Anchor)", "島式工法 (Island Method)", "斜坡/明挖 (Slope/Open Cut)", "結構樓板 (逆打標準)"]
        default_idx = 4 if (b_method and "逆打" in b_method) else None
        selected_support = st.selectbox("B. 支撐/開挖方式", support_type_options, index=default_idx, placeholder="請選擇...")
        excavation_system = f"{selected_wall} + {selected_support}" if (selected_wall and selected_support) else "未選擇"
        
        # [v6.89] 鋼軌樁係數 0.75
        wall_factors = {
            "連續壁 (Diaphragm Wall)": 1.0, 
            "全套管切削樁 (All-Casing)": 0.95, 
            "預壘樁/排樁 (PIP/Soldier Pile)": 0.85, 
            "鋼板樁 (Sheet Pile)": 0.70, 
            "鋼軌樁 (H-Pile)": 0.75, 
            "無 (純明挖/放坡)": 0.50
        }
        support_factors = {"型鋼內支撐 (Strut)": 1.0, "地錨 (Anchor)": 0.8, "結構樓板 (逆打標準)": 1.0, "島式工法 (Island Method)": 1.25, "斜坡/明挖 (Slope/Open Cut)": 0.6}
        
        if selected_wall and selected_support:
            w_fac = wall_factors.get(selected_wall, 1.0)
            s_fac = support_factors.get(selected_support, 1.0)
            if "島式" in selected_support: excavation_map_val = w_fac * s_fac 
            else: excavation_map_val = (w_fac + s_fac) / 2
        if selected_wall and "連續壁" in selected_wall:
            rw_aux_options = st.multiselect("連續壁輔助措施", ["地中壁 (Cross Wall)", "扶壁 (Buttress Wall)"])
    with g2:
        foundation_type = st.selectbox("基礎型式", ["標準筏式基礎 (無基樁)", "筏式基礎 + 一般鑽掘/預力樁", "筏式基礎 + 全套管基樁 (工期長)", "筏式基礎 + 壁樁 (Barrette)", "筏式基礎 + 微型樁 (工期短)", "獨立基腳 (無地下室)"], index=None, placeholder="請選擇...")
        
    # 連續壁詳細
    if selected_wall and "連續壁" in selected_wall:
        with st.expander("🧱 工具：連續壁工期詳細試算 (點擊展開)", expanded=False):
            st.markdown("##### 📏 連續壁施作工期詳細估算")
            dw_col1, dw_col2 = st.columns([1, 2])
            with dw_col1:
                qty_pile_temp = st.number_input("擋土假設樁 (M)", value=0.0)
                qty_gw_norm = st.number_input("2.0M 一般導溝 (M)", value=0.0)
                qty_gw_deep = st.number_input("7.0M 超深導溝 (M)", value=0.0)
                qty_gw_pile = st.number_input("壁樁超深導溝 (處)", value=0)
                qty_tank = st.number_input("穩定液池 (座)", value=0)
                qty_pave = st.number_input("鋪面 (M²)", value=0.0)
                qty_wash = st.number_input("洗車台 (座)", value=0)
                st.markdown("---")
                qty_dw_main = st.number_input("連續壁主體 (單元)", value=0)
                qty_dw_co = st.number_input("連續壁共構樁 (單元)", value=0)
                qty_buttress = st.number_input("無筋扶壁 (單元)", value=0)
                qty_mid_wall = st.number_input("地中壁 (單元)", value=0)
                qty_rect_pile = st.number_input("矩形壁樁 (單元)", value=0)
                default_bf = int(floors_down) if floors_down > 0 else 4
                basement_floors_calc = st.number_input("結構體養護-地下室層數", value=default_bf, min_value=1)
            with dw_col2:
                schedule_dw_data = [
                    {"項目": "擋土假設樁", "數量": qty_pile_temp, "單位": "M", "工率": "200 M/天", "工作天": math.ceil(qty_pile_temp/200)},
                    {"項目": "2.0M 一般導溝", "數量": qty_gw_norm, "單位": "M", "工率": "10 M/天", "工作天": math.ceil(qty_gw_norm/10)},
                    {"項目": "7.0M 超深導溝", "數量": qty_gw_deep, "單位": "M", "工率": "1 M/天 (5M/5天)", "工作天": math.ceil(qty_gw_deep/1)},
                    {"項目": "壁樁超深導溝", "數量": qty_gw_pile, "單位": "處", "工率": "5 天/處", "工作天": math.ceil(qty_gw_pile * 5)},
                    {"項目": "穩定液池", "數量": qty_tank, "單位": "座", "工率": "1 天/座", "工作天": math.ceil(qty_tank * 1)},
                    {"項目": "鋪面", "數量": qty_pave, "單位": "M²", "工率": "固定工期", "工作天": 8 if qty_pave > 0 else 0},
                    {"項目": "洗車台", "數量": qty_wash, "單位": "座", "工率": "2 天/座", "工作天": math.ceil(qty_wash * 2)},
                    {"項目": "機具組裝試挖", "數量": 1 if qty_dw_main > 0 else 0, "單位": "式", "工率": "固定", "工作天": 2 if qty_dw_main > 0 else 0},
                    {"項目": "連續壁主體", "數量": qty_dw_main, "單位": "單元", "工率": "3 天/單元", "工作天": math.ceil(qty_dw_main * 3)},
                    {"項目": "連續壁共構樁", "數量": qty_dw_co, "單位": "單元", "工率": "4 天/單元", "工作天": math.ceil(qty_dw_co * 4)},
                    {"項目": "無筋扶壁", "數量": qty_buttress, "單位": "單元", "工率": "1 天/單元", "工作天": math.ceil(qty_buttress * 1)},
                    {"項目": "地中壁", "數量": qty_mid_wall, "單位": "單元", "工率": "1 天/單元", "工作天": math.ceil(qty_mid_wall * 1)},
                    {"項目": "矩形壁樁", "數量": qty_rect_pile, "單位": "單元", "工率": "4 天/單元", "工作天": math.ceil(qty_rect_pile * 4)},
                    {"項目": "退場", "數量": 1 if qty_dw_main > 0 else 0, "單位": "式", "工率": "固定", "工作天": 2 if qty_dw_main > 0 else 0},
                ]
                df_schedule_dw = pd.DataFrame(schedule_dw_data)
                df_display = df_schedule_dw[df_schedule_dw['數量'] > 0] if not df_schedule_dw[df_schedule_dw['數量'] > 0].empty else pd.DataFrame(columns=["項目", "數量", "單位", "工率", "工作天"])
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                raw_work_days_dw = df_schedule_dw["工作天"].sum()
                adjusted_work_days = raw_work_days_dw 
                calendar_factor = st.slider("日曆天換算係數 (工作天 x 係數)", 1.0, 1.5, 1.15, 0.01, key="dw_factor")
                total_cal_days_dw = math.ceil(adjusted_work_days * calendar_factor)
                st.markdown(f"**累計純工作天**: {raw_work_days_dw} 天")
                st.info(f"📊 **試算結果：連續壁工期約 {total_cal_days_dw} 天**")
                st.markdown(f"💡 若您希望採用此結果，請將 `{total_cal_days_dw}` 填入下方的 **「廠商工期覆蓋」** > **「擋土壁施作工期」** 欄位中。")

    # Section 5
    st.markdown("<div class='section-header'>5. 外觀與機電裝修</div>", unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (工期較長)", "玻璃帷幕 (工期較短)", "預鑄PC板", "金屬三明治板 (極快)"], index=None, placeholder="請選擇...")
    with f2:
        scope_options = st.multiselect("納入工項", ["機電管線工程", "室內裝修工程", "景觀工程"], default=["機電管線工程", "室內裝修工程", "景觀工程"])

# 進階
st.write("") 
manual_retain_days = 0
manual_crane_days = 0
with st.expander("🔧 進階：廠商工期覆蓋 (選填/點擊展開)", expanded=False):
    with st.warning(""): 
        st.markdown("<div class='adv-header'>👷 廠商工期覆蓋 (強制採用)</div>", unsafe_allow_html=True)
        over_c1, over_c2 = st.columns(2)
        with over_c1:
            manual_retain_days = st.number_input("擋土壁施作工期 (天)", min_value=0, help="覆蓋系統計算")
        with over_c2:
            manual_crane_days = st.number_input("塔吊/鋼構吊裝工期 (天)", min_value=0, help="覆蓋系統計算")

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

# 風險提示
risk_reasons = []
suggested_days = 0
if manual_excav_depth_m > 0: check_depth = manual_excav_depth_m
elif is_complex_excavation: check_depth = max_depth_complex
else: check_depth = floors_down * 3.5
check_height = manual_height_m if manual_height_m > 0 else (display_max_floor * 3.3)

if check_height >= 50:
    risk_reasons.append(f"📏 建物高度達 {check_height:.1f}m (≥50m 需結構外審)")
    suggested_days = 90
if check_height >= 80:
    risk_reasons.append(f"🏗 建物高度達 {check_height:.1f}m (≥80m 需丁類危評)")
    suggested_days = 120
if check_depth >= 15:
    risk_reasons.append(f"⛏️ 開挖深度達 {check_depth:.1f}m (≥15m 需丁類危評)")
    if suggested_days < 120:
        suggested_days = max(suggested_days, 60)
        if suggested_days == 90 and "結構外審" in str(risk_reasons):
                suggested_days = 120
if risk_reasons:
    reasons_str = "<br>".join([f"• {m}" for m in risk_reasons])
    if not enable_manual_review:
        st.markdown(f"""<div class='warning-box'><b>⚠️ 系統建議：</b>偵測到本案符合以下條件：<br>{reasons_str}<br><hr style="margin:5px 0; border-top:1px dashed #bba55a;">建議至「3. 基地現況」區塊勾選「納入危評/外審緩衝期」，預估需增加 <b>{suggested_days} 天</b>。</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='info-box'><b>✅ 設定完成：</b>已針對以下條件納入緩衝期：<br>{reasons_str}<br>已加入 <b>{manual_review_days_input} 天</b>。</div>""", unsafe_allow_html=True)

# 核心運算
def calculate_project_schedule(is_reverse_method):
    base_area_factor = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
    vol_factor = 1.0
    if total_fa_ping > 3000:
        vol_factor = 1 + ((total_fa_ping - 3000) / 5000) * 0.05
        vol_factor = min(vol_factor, 1.2)
    area_multiplier = base_area_factor * vol_factor

    struct_map_above = {"RC造": 28, "SRC造": 25, "SS造": 18, "SC造": 21}
    if slab_type == "鋼承板 (Deck)": base_days_per_floor = 15  
    else: base_days_per_floor = struct_map_above.get(struct_above, 28)

    k_usage_base = {"住宅": 1.0, "集合住宅 (多棟)": 1.0, "辦公大樓": 1.1, "飯店": 1.4, "百貨": 1.1, "廠房": 0.8, "醫院": 1.4}.get(b_type, 1.0)
    multi_building_factor = 1.0
    if "集合住宅" in str(b_type) and building_count > 1:
        multi_building_factor = 1.0 + (building_count - 1) * 0.03
    k_usage = k_usage_base * multi_building_factor

    ext_wall_map = {"標準磁磚/塗料": 1.3, "石材吊掛 (工期較長)": 1.1, "玻璃帷幕 (工期較短)": 0.8, "預鑄PC板": 0.85, "金屬三明治板 (極快)": 0.85}
    ext_wall_multiplier = ext_wall_map.get(ext_wall, 1.0)
    excav_multiplier = excavation_map_val
    aux_wall_factor = 0
    if "地中壁" in str(rw_aux_options): aux_wall_factor += 0.20
    if "扶壁" in str(rw_aux_options): aux_wall_factor += 0.10

    add_review_days = manual_review_days_input if enable_manual_review else 0
    if prep_type_select and "自訂" in prep_type_select and prep_days_custom is not None: d_prep_base = int(prep_days_custom)
    else: d_prep_base = 120 if "一般" in str(prep_type_select) else 210 if "鄰捷運" in str(