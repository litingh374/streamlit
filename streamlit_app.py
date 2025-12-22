import streamlit as st

# 這才是 Streamlit (Python) 的寫法
col1, col2 = st.columns(2)
with col1:
    base_area = st.number_input("基地面積 (m²)", value=1990.00)
with col2:
    floor_area = st.number_input("總樓地板面積 (m²)", value=29671.96)

st.subheader("層數設定")
c1, c2, c3 = st.columns(3)
with c1:
    ground_floors = st.number_input("地上層數 (F)", value=24)
with c2:
    roof_floors = st.number_input("屋突層數 (R)", value=2)
with c3:
    # 把地下層數移到這裡
    basement_floors = st.number_input("地下層數 (B)", value=6)
    soil_control = st.checkbox("評估土方運棄管制?")