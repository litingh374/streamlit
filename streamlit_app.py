import streamlit as st

# 設定網頁標題
st.set_page_config(page_title="建築工程工期計算", layout="wide")

st.title("建築工程工期計算設定")

# --- 第一區塊：面積設定 ---
st.subheader("基地與面積參數")
col1, col2 = st.columns(2)

with col1:
    # 基地面積
    base_area = st.number_input("基地面積 (m²)", value=1990.00, step=10.0, format="%.2f")
    # 顯示換算坪數
    st.caption(f"換算：{base_area * 0.3025:.2f} 坪")

with col2:
    # 總樓地板面積
    total_floor_area = st.number_input("總樓地板面積 (m²)", value=29671.96, step=100.0, format="%.2f")
    st.caption(f"換算：{total_floor_area * 0.3025:.2f} 坪")

st.markdown("---") # 分隔線

# --- 第二區塊：層數設定 (這裡是你要求修改的地方) ---
st.subheader("層數設定")

# 使用 st.columns(3) 將畫面分成三欄，讓它們並排
c1, c2, c3 = st.columns(3)

with c1:
    # 地上層數
    floor_above = st.number_input("地上層數 (F)", value=24, step=1)

with c2:
    # 屋突層數
    floor_roof = st.number_input("屋突層數 (R)", value=2, step=1)

with c3:
    # 地下層數 (移到這裡)
    floor_basement = st.number_input("地下層數 (B)", value=6, step=1)
    
    # 核取方塊 (放在地下層數下方)
    soil_control = st.checkbox("評估土方運棄管制?", value=False)

# --- 測試顯示結果 (可選) ---
st.markdown("---")
st.write("### 當前設定值預覽：")
st.json({
    "基地面積": base_area,
    "總樓地板": total_floor_area,
    "地上層": floor_above,
    "屋突層": floor_roof,
    "地下層": floor_basement,
    "土方管制": soil_control
})