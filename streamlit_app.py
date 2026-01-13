import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import io
import plotly.express as px 
import plotly.graph_objects as go
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import math

# --- 1. 頁面配置 ---
st.set_page_config(page_title="建築工期估算系統 v6.85", layout="wide")

# ==========================================
# 🔐 簡易密碼登入功能 (v6.85)
# ==========================================
def check_password():
    """檢查密碼是否正確的函數"""
    
    # [設定] 請在此修改您的密碼
    ACTUAL_PASSWORD = "1234" 

    def password_entered():
        """檢查輸入的密碼"""
        if st.session_state["password"] == ACTUAL_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 安全起見，刪除輸入框的紀錄
        else:
            st.session_state["password_correct"] = False

    # 初始化 session_state
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # 判斷狀態
    if not st.session_state["password_correct"]:
        # 尚未登入，顯示輸入框
        st.markdown("""
        <style>
        .stTextInput > label {font-size:120%; font-weight:bold; color:#2D2926;}
        .stApp { background-color: #ffffff; } 
        </style>
        <div style='text-align: center; margin-top: 50px;'>
            <h1>🔒 建築工期估算輔助系統</h1>
            <p>本系統僅限內部授權使用，請輸入密碼登入。</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.text_input("請輸入登入密碼", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and st.session_state["password_correct"] == False:
                st.error("❌ 密碼錯誤，請重新輸入")
            
        return False
    else:
        # 已登入
        return True

# 執行檢查：如果沒過，就停止執行後續程式碼
if not check_password():
    st.stop()

# --- 2. CSS 樣式 (登入後才會載入) ---
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

# --- 3. 標題與導航 ---
st.sidebar.title("功能選單")
if st.sidebar.button("🔒 登出系統"):
    st.session_state["password_correct"] = False
    st.rerun()

page_mode = st.sidebar.radio("請選擇模式", ["單案詳細估算", "順打 vs 逆打 比較"], index=0)

st.title(f"🏗️ 建築工期估算 - {page_mode} v6.85")
if page_mode == "順打 vs 逆打 比較":
    st.caption("說明：此模式將忽略上方「施工方式」選單，自動計算並比較兩種工法的差異。")
else:
    st.caption("版本資訊：v6.85 (含密碼保護、參數校正、工具歸零)")

project_name = st.text_input("📝 請輸入專案名稱", value="", placeholder="例如：信義區A案")

# 全域變數定義
dw_reality_factor = 1.75  # 連續壁實務調整係數

# --- 4. 一般參數輸入區 (共用) ---
st.subheader("📋 建築規模參數")
with st.expander("點擊展開/隱藏 一般參數面板", expanded=True):
    
    # === [Section 1] 核心構造與工法 ===
    st.markdown("<div class='section-header'>1. 核心構造與工法</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        b_type = st.selectbox("建物類型", ["住宅", "集合住宅 (多棟)", "辦公大樓", "飯店", "百貨", "廠房", "醫院"], index=None, placeholder="請選擇...")
        
        # 依模式決定是否顯示施工方式選單
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

    # === [Section 2] 規模量體設定 ===
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

    # --- 樓層設定 ---
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
                floors_down_input = st.number_input("地下層數 (B)", min_value=0.0, value=0.0, step=0.5, key="fd_single_real")
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
            floors_down = st.number_input("地下層數 (B)", min_value=0.0, value=0.0, step=0.5, key="fd_multi")

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

    # === [Section 3] 基地現況與前置 ===
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

    # === [Section 4] 大地與基礎工程 ===
    st.markdown("<div class='section-header'>4. 大地工程與基礎 (組合式工法)</div>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3)
    selected_wall = None
    selected_support = None
    excavation_map_val = 1.0 
    rw_aux_options = []
    with g1:
        wall_type_options = ["連續壁 (Diaphragm Wall)", "全套管切削樁 (All-Casing)", "預壘樁/排樁 (PIP/Soldier Pile)", "鋼板樁 (Sheet Pile)", "無 (純明挖/放坡)"]
        selected_wall = st.selectbox("A. 擋土壁體類型", wall_type_options, index=None, placeholder="請選擇...")
        support_type_options = ["型鋼內支撐 (Strut)", "地錨 (Anchor)", "島式工法 (Island Method)", "斜坡/明挖 (Slope/Open Cut)", "結構樓板 (逆打標準)"]
        default_idx = 4 if (b_method and "逆打" in b_method) else None
        selected_support = st.selectbox("B. 支撐/開挖方式", support_type_options, index=default_idx, placeholder="請選擇...")
        excavation_system = f"{selected_wall} + {selected_support}" if (selected_wall and selected_support) else "未選擇"
        wall_factors = {"連續壁 (Diaphragm Wall)": 1.0, "全套管切削樁 (All-Casing)": 0.95, "預壘樁/排樁 (PIP/Soldier Pile)": 0.85, "鋼板樁 (Sheet Pile)": 0.70, "無 (純明挖/放坡)": 0.50}
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
        
    # 連續壁詳細試算 (隱藏/展開)
    if selected_wall and "連續壁" in selected_wall:
        with st.expander("🧱 工具：連續壁工期詳細試算 (點擊展開)", expanded=False):
            st.markdown("##### 📏 連續壁施作工期詳細估算")
            dw_col1, dw_col2 = st.columns([1, 2])
            with dw_col1:
                st.markdown("**1. 數量輸入**")
                # [v6.81] 預設值全部歸零
                qty_pile_temp = st.number_input("擋土假設樁 (M)", value=0.0)
                qty_gw_norm = st.number_input("2.0M 一般導溝 (M)", value=0.0)
                qty_gw_deep = st.number_input("7.0M 超深導溝 (M)", value=0.0)
                qty_gw_pile = st.number_input("壁樁超深導溝 (處)", value=0)
                qty_tank = st.number_input("穩定液池 (座)", value=0)
                qty_pave = st.number_input("鋪面 (M²)", value=0.0)
                qty_wash = st.number_input("洗車台 (座)", value=0)
                st.markdown("---")
                st.caption("壁體單元數量")
                qty_dw_main = st.number_input("連續壁主體 (單元)", value=0)
                qty_dw_co = st.number_input("連續壁共構樁 (單元)", value=0)
                qty_buttress = st.number_input("無筋扶壁 (單元)", value=0)
                qty_mid_wall = st.number_input("地中壁 (單元)", value=0)
                qty_rect_pile = st.number_input("矩形壁樁 (單元)", value=0)
                default_bf = int(floors_down) if floors_down > 0 else 4
                basement_floors_calc = st.number_input("結構體養護-地下室層數", value=default_bf, min_value=1)
            with dw_col2:
                st.markdown("**2. 工期計算結果**")
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
                adjusted_work_days = raw_work_days_dw # [v6.80] 修正：不重複加 1.75
                
                calendar_factor = st.slider("日曆天換算係數 (工作天 x 係數)", 1.0, 1.5, 1.15, 0.01, key="dw_factor")
                total_cal_days_dw = math.ceil(adjusted_work_days * calendar_factor)
                
                curing_1fl = 28
                curing_bs = basement_floors_calc * 10
                total_curing = curing_1fl + curing_bs

                st.markdown(f"**累計純工作天**: {raw_work_days_dw} 天")
                st.info(f"📊 **試算結果：連續壁工期約 {total_cal_days_dw} 天**")
                st.markdown(f"💡 若您希望採用此結果，請將 `{total_cal_days_dw}` 填入下方的 **「廠商工期覆蓋」** > **「擋土壁施作工期」** 欄位中。")

    # === [Section 5] 外觀與機電裝修 ===
    st.markdown("<div class='section-header'>5. 外觀與機電裝修</div>", unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        ext_wall = st.selectbox("外牆型式", ["標準磁磚/塗料", "石材吊掛 (工期較長)", "玻璃帷幕 (工期較短)", "預鑄PC板", "金屬三明治板 (極快)"], index=None, placeholder="請選擇...")
    with f2:
        scope_options = st.multiselect("納入工項", ["機電管線工程", "室內裝修工程", "景觀工程"], default=["機電管線工程", "室內裝修工程", "景觀工程"])

# 進階設定區塊
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

# ==========================================
# [v6.83 恢復] 危評/外審 警告判斷邏輯
# ==========================================
risk_reasons = []
suggested_days = 0

if manual_excav_depth_m > 0:
    check_depth = manual_excav_depth_m
elif is_complex_excavation:
    check_depth = max_depth_complex
else:
    check_depth = floors_down * 3.5

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

# ==========================================
#  核心計算邏輯 (封裝為函數)
# ==========================================
def calculate_project_schedule(is_reverse_method):
    """
    計算工期的核心函數
    input: is_reverse_method (bool) - True=逆打, False=順打
    output: (effective_work_days, calendar_days, final_date, schedule_data)
    """
    # 1. 係數計算
    base_area_factor = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
    vol_factor = 1.0
    if total_fa_ping > 3000:
        vol_factor = 1 + ((total_fa_ping - 3000) / 5000) * 0.05
        vol_factor = min(vol_factor, 1.2)
    area_multiplier = base_area_factor * vol_factor

    # 結構工期
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

    # 2. 單項工期計算
    # ------------------
    # 2.1 前期
    add_review_days = manual_review_days_input if enable_manual_review else 0
    if prep_type_select and "自訂" in prep_type_select and prep_days_custom is not None: d_prep_base = int(prep_days_custom)
    else: d_prep_base = 120 if "一般" in str(prep_type_select) else 210 if "鄰捷運" in str(prep_type_select) else 300
    d_prep = d_prep_base + add_review_days
    if add_review_days > 0: prep_note = f"含危評審查 (+{add_review_days}天)"
    else: prep_note = "要徑"

    # 2.2 拆除
    demo_note = "純空地"
    if site_condition and "純空地" in site_condition: d_demo = 0
    elif is_deep_demo or ("有舊建物" in str(site_condition)):
        if site_condition and "無地下室" in site_condition: 
            d_demo = int(55 * area_multiplier)
            demo_note = "地上拆除"
        else:
            if "全套管切削" in str(obstruction_method): 
                d_demo = int((180 + 45) * area_multiplier)
                demo_note = "全套管清障"
            elif "深導溝" in str(obstruction_method):
                if deep_gw_seq and "先回填" in deep_gw_seq: 
                    d_demo = int(180 * area_multiplier)
                    demo_note = "先回填後施作"
                else: 
                    d_demo = int(150 * area_multiplier)
                    demo_note = "邊回填邊施作"
            else: 
                d_demo = int(135 * area_multiplier)
                demo_note = "地下結構破除"
    else: d_demo = 0

    d_soil = int((30 if "局部" in str(soil_improvement) else 60 if "全區" in str(soil_improvement) else 0) * area_multiplier)

    # 2.3 基礎 & 擋土
    foundation_add = 0
    if foundation_type and "全套管" in foundation_type: foundation_add = 90
    elif foundation_type and "壁樁" in foundation_type: foundation_add = 80
    elif foundation_type and "一般鑽掘" in foundation_type: foundation_add = 60
    elif foundation_type and "微型樁" in foundation_type: foundation_add = 30

    d_aux_wall_days = int(60 * aux_wall_factor)
    d_dw_setup = 0 
    setup_note = ""
    
    # 擋土壁工期
    dw_note_str = ""
    if selected_wall and "連續壁" in selected_wall:
        base_retain = int(60 * dw_reality_factor) # 105天
        dw_note_str = "連續壁(含實務係數)"
    elif selected_wall and "全套管" in selected_wall: 
        base_retain = 50
        dw_note_str = "全套管切削樁"
    elif selected_wall and "預壘樁" in selected_wall: 
        base_retain = 40
        dw_note_str = "預壘樁"
    elif selected_wall and "鋼板樁" in selected_wall: 
        base_retain = 25
        dw_note_str = "鋼板樁"
    else: 
        base_retain = 15
        dw_note_str = "一般擋土"

    d_plunge_col = 0
    if is_reverse_method: 
        d_plunge_col = int(45 * area_multiplier) 
        dw_note_str += " + 中間柱"

    if manual_retain_days > 0: 
        d_retain_work = manual_retain_days
        excav_str_display = "依廠商預估"
    else: 
        d_retain_work = int((base_retain * area_multiplier) + d_dw_setup + d_aux_wall_days + d_plunge_col)
        excav_str_display = f"{dw_note_str}"
        if aux_wall_factor > 0: excav_str_display += " (+輔助工法)"

    # 2.4 開挖
    d_excav_std = int((floors_down * 22 * excav_multiplier) * area_multiplier) 
    excav_note = "出土/支撐"
    if enable_soil_limit and daily_soil_limit:
        if is_complex_excavation: total_soil_m3 = complex_soil_vol * 1.25 
        else: total_soil_m3 = base_area_m2 * (floors_down * 3.5) * 1.25
        d_excav_limited = math.ceil(total_soil_m3 / daily_soil_limit)
        d_excav_phase = max(d_excav_std, d_excav_limited)
        if d_excav_limited > d_excav_std: excav_note = f"受限每日{daily_soil_limit}m³"
    else:
        d_excav_phase = d_excav_std

    d_strut_install = 0
    strut_note = "開挖併行"
    if is_reverse_method: 
        d_strut_install = 0 # 逆打無內支撐
        d_earth_work = d_excav_phase
        strut_note = "樓板支撐(免架設)"
    elif (selected_support and "斜坡" in selected_support) or (selected_wall and "無" in selected_wall):
        d_strut_install = 0
        d_earth_work = d_excav_phase
        strut_note = "明挖/斜坡"
    else:
        d_strut_install = d_excav_phase
        d_earth_work = d_excav_phase

    # 2.5 結構體
    days_per_floor_bd = 45 
    days_per_strut_remove = 10
    if (selected_support and "斜坡" in selected_support) or (selected_wall and "無" in selected_wall) or is_reverse_method:
        d_strut_removal = 0
    else:
        d_strut_removal = floors_down * days_per_strut_remove

    struct_efficiency_factor = 1.3 if is_reverse_method else 1.0 # 逆打較慢
    d_struct_below_raw = ((floors_down * days_per_floor_bd * struct_efficiency_factor) + d_strut_removal + foundation_add)
    d_struct_below = int(d_struct_below_raw * area_multiplier)

    struct_note_base = f"{days_per_floor_bd}天/層"
    if is_reverse_method: struct_note_base += " x 1.3(逆打)"
    if d_strut_removal > 0: struct_note_base += f" + 拆撐{days_per_strut_remove}天"
    
    d_struct_body = int(calc_floors_struct * base_days_per_floor * area_multiplier * k_usage)
    d_ext_wall = int(calc_floors_struct * 15 * area_multiplier * ext_wall_multiplier * k_usage)

    d_mep = int((60 + calc_floors_struct * 2) * area_multiplier * k_usage) if "機電管線工程" in scope_options else 0
    d_fit_out = int((60 + calc_floors_struct * 10) * area_multiplier * k_usage) if "室內裝修工程" in scope_options else 0
    fit_out_note = "配合外牆後3個月完成"
    d_landscape = int(75 * base_area_factor) if "景觀工程" in scope_options else 0
    
    # [v6.79] Update Inspection days
    d_insp = 150 if b_type in ["百貨", "醫院", "飯店"] else 120 
    insp_note = "標準驗收流程"
    if "集合住宅" in str(b_type): 
        d_insp += (building_count - 1) * 15
        insp_note = f"多棟聯合驗收 (共{building_count}棟)"

    d_tower_crane = 60
    crane_note = "含勞檢危險性機械檢查"
    if manual_crane_days > 0: 
        d_tower_crane = manual_crane_days
        crane_note = "依廠商預估"
    
    needs_tower_crane = (struct_above in ["SS造", "SC造", "SRC造"]) or (display_max_floor >= 15)
    if not needs_tower_crane: d_tower_crane = 0

    # 3. 排程計算 (Timeline Logic)
    def get_end(start, days):
        curr = start
        if days <= 0: return curr
        added = 0
        while added < days:
            curr += timedelta(days=1)
            if exclude_sat and curr.weekday() == 5: continue
            if exclude_sun and curr.weekday() == 6: continue
            if exclude_cny and curr.month == 2 and 1 <= curr.day <= 7: continue
            added += 1
        return curr
    
    def get_start_from_end(end, days): 
        curr = end
        if days <= 0: return curr
        subtracted = 0
        while subtracted < days:
            curr -= timedelta(days=1)
            is_work = True
            if exclude_sat and curr.weekday() == 5: is_work = False
            elif exclude_sun and curr.weekday() == 6: is_work = False
            elif exclude_cny and curr.month == 2 and 1 <= curr.day <= 7: is_work = False
            if is_work: subtracted += 1
        return curr

    p1_s = start_date_val
    p1_e = get_end(p1_s, d_prep)
    p2_s = p1_e + timedelta(days=1)
    p2_e = get_end(p2_s, d_demo)
    p_soil_s = p2_e + timedelta(days=1)
    p_soil_e = get_end(p_soil_s, d_soil)
    p4_s = p_soil_e + timedelta(days=1)
    p4_e = get_end(p4_s, d_retain_work)
    p5_s = p4_e + timedelta(days=1)
    p5_e = get_end(p5_s, d_strut_install)
    p6_s = p5_s 

    # [v6.73] 逆打邏輯重構
    if is_reverse_method:
        lag_excav = int(30 * area_multiplier)
        p7_s = get_end(p6_s, lag_excav)
        p7_e = get_end(p7_s, d_struct_below)
        target_excav_end = p7_e - timedelta(days=20) 
        std_excav_end = get_end(p6_s, d_earth_work)
        p6_e = max(target_excav_end, std_excav_end) 
        
        cal_diff = (p6_e - p6_s).days
        avg_ratio = 5/7 if exclude_sat and exclude_sun else 6/7 if exclude_sun else 1.0
        d_earth_work_display = int(cal_diff * avg_ratio) 
        
        lag_1f_slab = int(60 * area_multiplier)
        p8_s_pre = get_end(p6_s, lag_1f_slab) 
        struct_note_below = f"併行 ({struct_note_base})"
        struct_note_above = f"併行 ({display_max_floor}F+{display_max_roof}R)"
        excav_note = "配合逆打逐層施作"
    else:
        p6_e = get_end(p6_s, d_earth_work)
        d_earth_work_display = d_earth_work
        p_excav_finish = max(p5_e, p6_e)
        p7_s = p_excav_finish + timedelta(days=1)
        p7_e = get_end(p7_s, d_struct_below)
        p8_s_pre = p7_e + timedelta(days=1)
        struct_note_below = f"要徑 ({struct_note_base})"
        struct_note_above = f"順打 ({display_max_floor}F+{display_max_roof}R)"
        # excav_note 已經定義

    p_tower_s = p1_s 
    p_tower_e = p1_s
    if needs_tower_crane:
        p_tower_e = p8_s_pre - timedelta(days=1)
        p_tower_s = p_tower_e - timedelta(days=25) 
        p_tower_e = get_end(p_tower_s, d_tower_crane)
        p8_s = max(p8_s_pre, p_tower_e + timedelta(days=1))
    else:
        p8_s = p8_s_pre

    p8_e = get_end(p8_s, d_struct_body)
    
    lag_ext = int(d_struct_body * 0.7) 
    p_ext_s = get_end(p8_s, lag_ext)
    p_ext_e = get_end(p_ext_s, d_ext_wall)

    lag_mep = int(d_struct_body * 0.3) 
    p10_s = get_end(p8_s, lag_mep)
    p10_e = get_end(p10_s, d_mep)

    # [v6.74] Fit-out Finish-to-Finish
    p11_e = p_ext_e + timedelta(days=90) 
    p11_s = get_start_from_end(p11_e, d_fit_out)

    p12_s = p_ext_e - timedelta(days=15) 
    p12_e = get_end(p12_s, d_landscape)

    p13_s = max(p_ext_e, p10_e, p11_e, p12_e) - timedelta(days=30)
    p13_e = get_end(p13_s, d_insp)

    final_finish = max(p7_e, p8_e, p_ext_e, p10_e, p11_e, p12_e, p13_e)
    cal_days = (final_finish - p1_s).days
    eff_days = int(cal_days * (5/7 if exclude_sat and exclude_sun else 6/7))

    # Data Construction (Include Remarks)
    s_data = [
        {"工項": "1.前期", "天數": d_prep, "Start": p1_s, "Finish": p1_e, "備註": prep_note},
        {"工項": "2.拆除", "天數": d_demo, "Start": p2_s, "Finish": p2_e, "備註": demo_note},
        {"工項": "3.地改", "天數": d_soil, "Start": p_soil_s, "Finish": p_soil_e, "備註": "地質改良"},
        {"工項": "4.擋土壁", "天數": d_retain_work, "Start": p4_s, "Finish": p4_e, "備註": excav_str_display},
        {"工項": "5.支撐", "天數": d_strut_install, "Start": p5_s, "Finish": p5_e, "備註": strut_note},
        {"工項": "6.開挖", "天數": d_earth_work_display, "Start": p6_s, "Finish": p6_e, "備註": excav_note},
        {"工項": "7.地下結構", "天數": d_struct_below, "Start": p7_s, "Finish": p7_e, "備註": struct_note_below},
        {"工項": "8.地上結構", "天數": d_struct_body, "Start": p8_s, "Finish": p8_e, "備註": struct_note_above},
        {"工項": "9.外牆", "天數": d_ext_wall, "Start": p_ext_s, "Finish": p_ext_e, "備註": f"70%進場 ({ext_wall})"},
        {"工項": "10.機電", "天數": d_mep, "Start": p10_s, "Finish": p10_e, "備註": "30%進場"},
        {"工項": "11.裝修", "天數": d_fit_out, "Start": p11_s, "Finish": p11_e, "備註": fit_out_note},
        {"工項": "12.景觀", "天數": d_landscape, "Start": p12_s, "Finish": p12_e, "備註": "收尾工程"},
        {"工項": "13.驗收", "天數": d_insp, "Start": p13_s, "Finish": p13_e, "備註": insp_note},
    ]
    if needs_tower_crane:
        s_data.append({"工項": "7.5 塔吊", "天數": d_tower_crane, "Start": p_tower_s, "Finish": p_tower_e, "備註": crane_note})
    
    return eff_days, cal_days, final_finish, s_data

# ==========================================
# 核心防呆
# ==========================================
missing_fields = []
if not b_type: missing_fields.append("建物類型")
if page_mode != "順打 vs 逆打 比較" and not b_method: missing_fields.append("施工方式")
if not struct_above: missing_fields.append("地上結構")
if not struct_below: missing_fields.append("地下結構")
has_numeric_data = (base_area_m2 > 0) and (total_fa_m2 > 0) and (calc_floors_struct > 0 or floors_down > 0)

if missing_fields or not has_numeric_data:
    st.divider()
    if missing_fields: st.error(f"❌ 請補全資料： {', '.join(missing_fields)}")
    if not has_numeric_data: st.warning("👈 請輸入 基地面積、總樓地板面積 及 樓層數")
    st.stop()

# ==========================================
# 依模式執行運算
# ==========================================
st.divider()

if page_mode == "順打 vs 逆打 比較":
    st.subheader("📊 順打 vs 逆打 工期比較分析")
    
    eff_std, cal_std, date_std, data_std = calculate_project_schedule(is_reverse_method=False)
    eff_rev, cal_rev, date_rev, data_rev = calculate_project_schedule(is_reverse_method=True)
    
    col_comp1, col_comp2, col_comp3 = st.columns(3)
    
    diff_days = cal_rev - cal_std
    diff_months = diff_days / 30.44
    
    with col_comp1:
        st.markdown("##### 🏁 順打工法 (Bottom-Up)")
        st.markdown(f"<h2 style='color:#2D2926'>{cal_std} 日曆天</h2>", unsafe_allow_html=True)
        st.write(f"預計完工：{date_std}")
        
    with col_comp2:
        st.markdown("##### 🔄 逆打工法 (Top-Down)")
        color = "#FF4438" if diff_days > 0 else "#28a745" # 紅=慢, 綠=快
        st.markdown(f"<h2 style='color:#2D2926'>{cal_rev} 日曆天</h2>", unsafe_allow_html=True)
        st.write(f"預計完工：{date_rev}")
        
    with col_comp3:
        st.markdown("##### ⚖️ 工期差異")
        if diff_days > 0:
            st.metric("逆打比較慢", f"+{diff_days} 天", f"+{diff_months:.1f} 月", delta_color="inverse")
            st.info("💡 地上樓層較多時，逆打優勢不明顯，且地下結構慢。")
        elif diff_days < 0:
            st.metric("逆打比較快", f"{diff_days} 天", f"{diff_months:.1f} 月", delta_color="normal")
            st.success("💡 逆打發揮並行施工優勢，提早完工。")
        else:
            st.metric("兩者工期相當", "0 天")

    st.subheader("📅 完工日期時間軸對比")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=['順打工法', '逆打工法'],
        x=[cal_std, cal_rev],
        orientation='h',
        marker=dict(color=['#708090', '#FFB81C']),
        text=[f"{cal_std}天", f"{cal_rev}天"],
        textposition='auto',
    ))
    fig.update_layout(title="總工期長度對比 (日曆天)", xaxis_title="天數", height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("查看詳細工項比較表"):
        df_std = pd.DataFrame(data_std)[['工項', '天數', 'Finish']].rename(columns={'天數':'順打天數', 'Finish':'順打完成'})
        df_rev = pd.DataFrame(data_rev)[['天數', 'Finish']].rename(columns={'天數':'逆打天數', 'Finish':'逆打完成'})
        df_merge = pd.concat([df_std, df_rev], axis=1)
        st.dataframe(df_merge, use_container_width=True)

else:
    # === 原有單案估算模式 ===
    is_reverse = True if b_method and ("逆打" in b_method or "雙順打" in b_method) else False
    eff_days, cal_days, final_date, s_data = calculate_project_schedule(is_reverse)
    
    st.subheader("📊 預估結果分析")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    with res_col1: st.markdown(f"<div class='metric-container'><small>專案總有效工期</small><br><b>{eff_days} 天</b></div>", unsafe_allow_html=True)
    with res_col2: st.markdown(f"<div class='metric-container'><small>專案日曆天 / 月數</small><br><b>{cal_days} 天 / {cal_days/30.44:.1f} 月</b></div>", unsafe_allow_html=True)
    with res_col3: 
        c_color = "#FF4438" if enable_date else "#2D2926"
        d_str = str(final_date) if enable_date else "日期未定"
        st.markdown(f"<div class='metric-container' style='border-left-color:{c_color};'><small>預計完工日期</small><br><b style='color:{c_color};'>{d_str}</b></div>", unsafe_allow_html=True)
    with res_col4: st.markdown(f"<div class='metric-container'><small>規模複雜度分析</small><br><b>單棟標準係數</b></div>", unsafe_allow_html=True)

    st.subheader("📅 詳細工項進度建議表")
    sched_df = pd.DataFrame(s_data)
    sched_df = sched_df[sched_df["天數"] > 0].sort_values("Start")
    sched_df["預計開始"] = sched_df["Start"].astype(str)
    sched_df["預計完成"] = sched_df["Finish"].astype(str)
    st.dataframe(sched_df[["工項", "天數", "預計開始", "預計完成", "備註"]], hide_index=True, use_container_width=True)

    st.subheader("📊 專案進度甘特圖")
    # [v6.84] 修復甘特圖配色與文字
    professional_colors = ["#708090", "#A52A2A", "#8B4513", "#2F4F4F", "#696969", "#708090", "#A0522D", "#DC143C", "#4682B4", "#CD5C5C", "#5F9EA0", "#2E8B57", "#556B2F", "#DAA520"]
    fig = px.timeline(
        sched_df, x_start="Start", x_end="Finish", y="工項", color="工項", text="工項",
        title=f"【{project_name}】工程進度模擬",
        color_discrete_sequence=professional_colors
    )
    fig.update_traces(textposition='inside', insidetextanchor='start', opacity=0.9)
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        sched_df.to_excel(writer, index=False, sheet_name='詳細工期')
    st.download_button(label="📊 下載 Excel 報表", data=buffer.getvalue(), file_name=f"{project_name}_工期.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")