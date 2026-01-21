import streamlit as st
import datetime
from datetime import timedelta
import pandas as pd
import plotly.express as px 
import math

# --- 1. 頁面配置 (極簡化) ---
st.set_page_config(page_title="工期估算 (快速版) v7.0", layout="centered") # 改為置中佈局，更像 App

# CSS 美化：隱藏多餘邊框，放大輸入框
st.markdown("""
    <style>
    .stApp { background-color: #f5f7f9; }
    div[data-testid="stVerticalBlock"] { gap: 1rem; }
    .big-font { font-size: 20px !important; font-weight: bold; }
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

st.title("⚡ 建築工期快速估算 v7.0")
st.caption("輸入 5 項關鍵數據，立即取得實務預估工期")

# ==========================================
# 1. 極簡輸入區
# ==========================================
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        floors_up = st.number_input("🏙️ 地上樓層 (F)", min_value=1, value=15, step=1)
        floors_down = st.number_input("⛏️ 地下樓層 (B)", min_value=0, value=3, step=1)
    with col2:
        base_area_ping = st.number_input("📐 基地大小 (坪)", min_value=10.0, value=300.0, step=10.0)
        b_type = st.selectbox("🏢 建物類型", ["住宅", "辦公大樓", "飯店", "廠房"], index=0)

    has_old_building = st.checkbox("🏗️ 基地現況是否有舊建物？", value=True)

    # 隱藏的自動推導邏輯 (轉換單位)
    base_area_m2 = base_area_ping / 0.3025
    
    # 自動估算總樓地板面積 (用於權重計算)
    # 邏輯：基地 x 65%建蔽率 x 總樓層 x 1.4(公設/車位係數)
    est_total_fa_ping = base_area_ping * 0.65 * (floors_up + floors_down) * 1.4
    
    # 自動決定結構
    struct_above = "SRC造" if floors_up >= 20 else "RC造"
    
    # 自動決定擋土工法
    # B1用鋼板樁，B2以上用連續壁(含1.75倍係數)
    wall_type = "鋼板樁" if floors_down <= 1 else "連續壁"
    
    # 執行按鈕
    run_calc = st.button("🚀 開始計算")

# ==========================================
# 2. 核心運算引擎 (簡化版，邏輯同 v6.92)
# ==========================================
if run_calc:
    # --- 係數設定 ---
    # 面積係數
    base_area_factor = max(0.8, min(1 + ((base_area_ping - 500) / 100) * 0.02, 1.5))
    vol_factor = 1.0
    if est_total_fa_ping > 3000:
        vol_factor = min(1 + ((est_total_fa_ping - 3000) / 5000) * 0.05, 1.2)
    area_multiplier = base_area_factor * vol_factor

    # 結構係數
    days_per_floor = 25 if struct_above == "SRC造" else 28
    
    # 用途係數
    k_usage = 1.1 if b_type in ["辦公大樓", "飯店"] else 1.0
    if b_type == "廠房": k_usage = 0.8

    # --- 工期計算 ---
    
    # 1. 前置 (簡化)
    d_prep = 120 
    
    # 2. 拆除 (依勾選)
    d_demo = int(60 * area_multiplier) if has_old_building else 0
    
    # 3. 基礎/擋土
    # 連續壁：60 * 1.75 (實務係數)
    base_retain = int(60 * 1.75) if wall_type == "連續壁" else 30
    d_retain = int(base_retain * area_multiplier)
    
    # 4. 開挖
    # 簡化假設：每天出土量受限 vs 標準產能
    total_soil = base_area_m2 * (floors_down * 3.5)
    d_excav = int(max(total_soil / 300, floors_down * 25 * area_multiplier))
    
    # 5. 支撐
    d_strut = d_excav # 假設與開挖並行或接續
    
    # 6. 地下結構
    d_struct_down = int((floors_down * 45 + floors_down * 10) * area_multiplier) # 含拆撐
    
    # 7. 地上結構
    d_struct_up = int(floors_up * days_per_floor * area_multiplier * k_usage)
    
    # 8. 裝修/外牆/機電 (並行邏輯簡化)
    # 裝修完工日 = 結構完成日 + 裝修工期(結構的70%長度) + 90天緩衝
    d_fit_out_buffer = 90
    
    # 9. 驗收
    d_insp = 120

    # --- 排程累加 (FS 邏輯) ---
    current_day = 0
    
    schedule = []
    
    # Start -> Prep
    schedule.append(dict(Task="前置作業", Start=current_day, Duration=d_prep))
    current_day += d_prep
    
    # -> Demo
    if d_demo > 0:
        schedule.append(dict(Task="拆除工程", Start=current_day, Duration=d_demo))
        current_day += d_demo
        
    # -> Retain
    schedule.append(dict(Task="擋土設施", Start=current_day, Duration=d_retain))
    current_day += d_retain
    
    # -> Excav/Strut (視為一組)
    schedule.append(dict(Task="開挖支撐", Start=current_day, Duration=d_strut))
    current_day += d_strut
    
    # -> Struct Down
    schedule.append(dict(Task="地下結構", Start=current_day, Duration=d_struct_down))
    current_day += d_struct_down
    
    # -> Struct Up
    start_struct_up = current_day
    schedule.append(dict(Task="地上結構", Start=start_struct_up, Duration=d_struct_up))
    finish_struct_up = start_struct_up + d_struct_up
    
    # -> Finish (裝修與外牆並行，最終收尾)
    # 簡化邏輯：裝修在外牆後，外牆在結構 70% 後
    start_ext = start_struct_up + int(d_struct_up * 0.7)
    d_ext = int(floors_up * 15 * area_multiplier)
    finish_ext = start_ext + d_ext
    
    finish_fitout = finish_ext + 90 # 裝修完工鎖定
    start_fitout = finish_fitout - int(d_struct_up * 0.8) # 倒推
    
    schedule.append(dict(Task="外牆工程", Start=start_ext, Duration=d_ext))
    schedule.append(dict(Task="室內裝修", Start=start_fitout, Duration=finish_fitout - start_fitout))
    
    # -> Inspection
    start_insp = max(finish_struct_up, finish_ext, finish_fitout)
    schedule.append(dict(Task="驗收使照", Start=start_insp, Duration=d_insp))
    
    total_days = start_insp + d_insp
    
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
        <h3 style='color:#888; margin:0;'>預估總工期 (日曆天)</h3>
        <h1 style='color:#2D2926; font-size: 60px; margin: 10px 0;'>{final_calendar_days} 天</h1>
        <p style='color:#FF4438; font-weight:bold; font-size: 20px;'>約 {final_years} 年</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 顯示推導參數 (讓使用者知道系統幫他選了什麼)
    st.info(f"""
    💡 **系統自動推導參數：**
    - **結構推估**：{struct_above} (依樓層判斷)
    - **擋土推估**：{wall_type} (依地下深判斷)
    - **總樓地板**：約 {int(est_total_fa_ping):,} 坪 (自動推算)
    - **係數設定**：已內建連續壁實務調整係數 (1.75倍) 及天氣放假係數 (1.15倍)
    """)

    # 簡易甘特圖
    st.subheader("📅 工期進度條")
    df_chart = pd.DataFrame(schedule)
    df_chart['Finish'] = df_chart['Start'] + df_chart['Duration']
    
    # 為了讓 Plotly 顯示，將數字轉換為日期 (假設今天開工)
    start_date = datetime.date.today()
    df_chart['Start_Date'] = df_chart['Start'].apply(lambda x: start_date + timedelta(days=x))
    df_chart['Finish_Date'] = df_chart['Finish'].apply(lambda x: start_date + timedelta(days=x))
    
    morandi_colors = ["#8E9EAB", "#D4A5A5", "#96B3C2", "#B9C0C9", "#E0C9A6", "#A9B7C0", "#C4B7D7"]
    
    fig = px.timeline(
        df_chart, 
        x_start="Start_Date", 
        x_end="Finish_Date", 
        y="Task", 
        color="Task",
        color_discrete_sequence=morandi_colors,
        height=400
    )
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(title="日期 (預設今日開工)")
    st.plotly_chart(fig, use_container_width=True)

    # 顯示詳細列表
    with st.expander("查看詳細工期拆解"):
        st.dataframe(df_chart[['Task', 'Duration', 'Start', 'Finish']], use_container_width=True)