# 🏗️ 建築施工工期估算輔助系統 (Construction Duration Estimator)

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)

這是一個專為台北市建築開發規劃設計的**工期估算工具**。透過整合建築類型、結構形式、樓層規模以及台北市特有的前置行政作業時間，提供開發商、營造廠與建築師一個快速、直覺的施工時程參考模型。

## 🌟 核心功能

* **動態規模運算**：自動計算地上、地下層數對應不同結構型式（RC/SS/SRC）的循環工期。
* **前置作業模組**：內建台北市實務經驗，包含一般案件、鄰近捷運影響評估、環評等行政天數。
* **基礎工程評估**：整合地質改良（JSP/CCP）對基礎施工階段的時程影響。
* **智能日期修正**：可選擇性扣除週六、週日與農曆春節期間，精準換算日曆天。
* **專業視覺界面**：採用工業風格設計（PANTONE 1235C 黃色系），符合工程實務美學。

## 📊 計算邏輯說明

本系統之主體工期 $T_{total}$ 依據以下公式推估：

$$T_{total} = (T_{sub} + T_{soil} + T_{super}) \times K + T_{prep} + T_{insp}$$

* **$T_{sub}$ (地下工程)**：依開挖工法（順打/逆打）決定每層天數。
* **$T_{super}$ (地上結構)**：依結構型式決定循環天數（RC: 14天, SS: 8天...）。
* **$K$ (建物修正)**：依用途（醫院、百貨、住宅）調整機電裝修複雜度。
* **日期修正**：若啟用修正，系統將自動跳過週休二日與 2 月份之農曆春節停工期。



## 🚀 快速上手

### 1. 安裝環境
確保您的電腦已安裝 Python 3.9 或更高版本。

```bash
pip install streamlit