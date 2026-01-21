import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import plotly.express as px 
import math

# --- 1. 頁面配置 (極簡化) ---
st.set_page_config(page_title="工期估算 (快速版) v7.1", layout="centered")

# CSS 美化
st.markdown("""
    <style>
    .stApp { background-color: #f5f7f9; }
    div[data-testid="stVerticalBlock"] { gap: 1rem; }
    .result-card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-top: 20px;
    }
    .stButton>button {
        width: 100%; border-radius: 10px; height: 3em; font-size: 18px; font-weight: bold;
        background-color: #FFB81C; color: #2D2926; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ 建築工期快速估算 v7.1")
st.caption("輸入關鍵 7 項數據，立即取得實務預估工期")

# ==========================================
# 1. 輸入區 (新增結構與工法)
# ==========================================
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        floors_up = st.number_input("🏙️ 地上樓層 (F)", min_value=1, value=15, step=1)
        floors_down = st.number_input("⛏️ 地下樓層 (B)", min_value=0, value=3, step=1)
        # [v7.1] 新增結構選項
        struct_above = st.selectbox("🏗️ 結構型式", ["RC造", "SRC造", "SS造", "SC造"], index=0)
        
    with col2:
        base_area_ping = st.number_input("📐 基地大小 (坪)", min_value=10.0, value=300.0, step=10.0)
        b_type = st.selectbox("🏢 建物類型", ["住宅", "辦公大樓", "飯店", "廠房"], index=0)
        # [v7.1] 新增工法選項
        method_type = st.selectbox("⚙️ 施工方式", ["順打工法", "逆打工法"], index=0)

    has_old_building = st.checkbox("🏗️ 基地現況是否有舊建物？", value=True)

    # 隱藏運算：自動推導擋土工法 (保持簡化，除非您也想手動選)
    wall_type = "鋼板樁" if floors_down <= 1 else "連續壁"
    
    # 執行按鈕
    run_calc = st.button("🚀 開始計算")

# ==========================================
# 2. 核心運算引擎 (v7.1 升級版)
# ==========================================
if run_calc:
    # --- A. 基礎參數推算 ---
    base_area_m2 = base_area_ping / 0.3025
    # 估算總樓地板 (用於權重)
    est_total_fa_ping = base_area_ping * 0.65 * (floors_up + floors_down) * 1.4
    
    # 面積權重
    base_area_factor = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
    vol_factor = 1.0
    if est_total_fa_ping > 3000:
        vol_factor = min(1 + ((est_total_fa_ping - 3000) / 5000) * 0.05, 1.2)
    area_multiplier = base_area_factor * vol_factor

    # 結構單層天數
    days_map = {"RC造": 28, "SRC造": 25, "SS造": 18, "SC造": 21}
    days_per_floor = days_map.get(struct_above, 28)
    
    # 用途係數
    k_usage = 1.1 if b_type in ["辦公大樓", "飯店"] else 1.0
    if b_type == "廠房": k_usage = 0.8

    # --- B. 分項工期計算 ---
    
    # 1. 前置
    d_prep = 120 
    
    # 2. 拆除
    d_demo = int(60 * area_multiplier) if has_old_building else 0
    
    # 3. 基礎/擋土 (含連續壁 1.75 實務係數)
    base_retain = int(60 * 1.75) if wall_type == "連續壁" else 30
    d_retain = int(base_retain * area_multiplier)
    
    # 4. 逆打中間柱 (僅逆打有)
    d_plunge = int(45 * area_multiplier) if method_type == "逆打工法" else 0
    
    # 5. 開挖 & 支撐
    total_soil = base_area_m2 * (floors_down * 3.5)
    # 簡化：順打需全挖完，逆打雖然分層但總出土時間類似，主要差在結構卡控
    d_excav_raw = int(max(total_soil / 300, floors_down * 25 * area_multiplier))
    
    # 6. 地下結構
    # 逆打地下結構較慢 (x1.3)，且不需拆撐
    days_bs_floor = 45
    if method_type == "逆打工法":
        d_struct_down = int(floors_down * days_bs_floor * 1.3 * area_multiplier)
    else:
        # 順打：每層 + 拆撐時間
        d_struct_down = int((floors_down * days_bs_floor + floors_down * 10) * area_multiplier)
    
    # 7. 地上結構
    d_struct_up = int(floors_up * days_per_floor * area_multiplier * k_usage)
    
    # 8. 裝修/外牆 (並行邏輯)
    d_ext_wall = int(floors_up * 15 * area_multiplier)
    d_fit_out_buffer = 90 # 裝修比外牆晚90天完工
    
    # 9. 驗收
    d_insp = 120

    # --- C. 排程模擬 (Timeline Simulation) ---
    current_day = 0
    schedule = []
    
    # [Step 1] 共通路徑：前置 -> 拆除 -> 擋土 -> (逆打中間柱)
    schedule.append(dict(Task="前置作業", Start=current_day, Duration=d_prep))
    current_day += d_prep
    
    if d_demo > 0:
        schedule.append(dict(Task="拆除工程", Start=current_day, Duration=d_demo))
        current_day += d_demo
        
    schedule.append(dict(Task="擋土設施", Start=current_day, Duration=d_retain))
    current_day += d_retain
    
    if method_type == "逆打工法":
        # === 逆打邏輯 (平行施工) ===
        # 1. 中間柱
        schedule.append(dict(Task="逆打中間柱", Start=current_day, Duration=d_plunge))
        current_day += d_plunge
        
        # 2. 1F 結構 (蓋子)
        d_1f_slab = int(60 * area_multiplier)
        schedule.append(dict(Task="1F結構(逆打)", Start=current_day, Duration=d_1f_slab))
        current_day += d_1f_slab
        
        # 3. 分岔點：地上與地下同時開始
        split_point = current_day
        
        # 路徑 A: 地下開挖+結構
        # 簡化：逆打的開挖與結構是交錯的，這裡用總時長表示
        # 總地下時間 = 出土時間 + 結構時間 (稍作重疊調整，這裡簡化為直接加總作為保守估計)
        # 但逆打可以邊挖邊做，通常比順打慢一點點或持平，這裡採保守累加
        path_down_duration = d_excav_raw + d_struct_down 
        schedule.append(dict(Task="地下開挖&結構", Start=split_point, Duration=path_down_duration))
        finish_down = split_point + path_down_duration
        
        # 路徑 B: 地上結構
        schedule.append(dict(Task="地上結構", Start=split_point, Duration=d_struct_up))
        finish_struct_up = split_point + d_struct_up
        
    else:
        # === 順打邏輯 (線性施工) ===
        # 1. 開挖 & 支撐
        schedule.append(dict(Task="開挖支撐", Start=current_day, Duration=d_excav_raw))
        current_day += d_excav_raw
        
        # 2. 地下結構
        schedule.append(dict(Task="地下結構", Start=current_day, Duration=d_struct_down))
        current_day += d_struct_down
        
        # 3. 地上結構
        schedule.append(dict(Task="地上結構", Start=current_day, Duration=d_struct_up))
        finish_struct_up = current_day + d_struct_up
        finish_down = current_day # 順打時，地下室早就做完了

    # [Step 2] 共通收尾：外牆 -> 裝修 -> 驗收
    # 關鍵：外牆開始時間 = 地上結構開始 + 70% 工期
    start_struct_up = finish_struct_up - d_struct_up
    start_ext = start_struct_up + int(d_struct_up * 0.7)
    finish_ext = start_ext + d_ext
    
    # 裝修完工鎖定
    finish_fitout = finish_ext + d_fit_out_buffer
    start_fitout = finish_fitout - int(d_struct_up * 0.8)
    
    schedule.append(dict(Task="外牆工程", Start=start_ext, Duration=d_ext))
    schedule.append(dict(Task="室內裝修", Start=start_fitout, Duration=finish_fitout - start_fitout))
    
    # [Step 3] 決定最終完工日 (取最大值)
    # 逆打時，有可能地下室做比較慢
    project_finish = max(finish_struct_up, finish_ext, finish_fitout, finish_down)
    
    schedule.append(dict(Task="驗收使照", Start=project_finish, Duration=d_insp))
    
    total_days = project_finish + d_insp
    
    # 日曆天換算 (x 1.15)
    final_calendar_days = int(total_days * 1.15)
    final_years = round(final_calendar_days / 365, 1)
    
    # ==========================================
    # 3. 結果顯示區
    # ==========================================
    st.markdown("---")
    
    # 顯示大卡片
    st.markdown(f"""
    <div class='result-card'>
        <h3 style='color:#888; margin:0;'>預估總工期 ({method_type})</h3>
        <h1 style='color:#2D2926; font-size: 60px; margin: 10px 0;'>{final_calendar_days} 天</h1>
        <p style='color:#FF4438; font-weight:bold; font-size: 20px;'>約 {final_years} 年</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 顯示推導參數
    wall_info = f"{wall_type} (自動推算)"
    if method_type == "逆打工法":
        wall_info += " + 中間柱"
        
    st.info(f"""
    💡 **運算依據：**
    - **結構設定**：{struct_above} ({days_per_floor}天/層)
    - **擋土工法**：{wall_info}
    - **總樓地板**：約 {int(est_total_fa_ping):,} 坪 (自動推算)
    - **工期損耗**：已包含連續壁實務係數、天候放假係數
    """)

    # 簡易甘特圖
    st.subheader("📅 工期進度條")
    df_chart = pd.DataFrame(schedule)
    df_chart['Finish'] = df_chart['Start'] + df_chart['Duration']
    
    start_date = datetime.date.today()
    df_chart['Start_Date'] = df_chart['Start'].apply(lambda x: start_date + timedelta(days=x))
    df_chart['Finish_Date'] = df_chart['Finish'].apply(lambda x: start_date + timedelta(days=x))
    
    morandi_colors = ["#8E9EAB", "#D4A5A5", "#96B3C2", "#B9C0C9", "#E0C9A6", "#A9B7C0", "#C4B7D7", "#8FA691"]
    
    fig = px.timeline(
        df_chart, 
        x_start="Start_Date", 
        x_end="Finish_Date", 
        y="Task", 
        color="Task",
        color_discrete_sequence=morandi_colors,
        height=450
    )
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(title="日期")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("查看詳細工期拆解"):
        st.dataframe(df_chart[['Task', 'Duration', 'Start', 'Finish']], use_container_width=True)