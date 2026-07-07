import streamlit as st
import os
import sys
import subprocess
import time
import math
import pandas as pd
import sqlite3
import requests
import streamlit.components.v1 as components

def init_app():
    # 使用絕對路徑
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'stations.db')
    COLLECTOR_PATH = os.path.join(BASE_DIR, 'data_collector.py')
    
    # 建立一個佔位容器
    placeholder = st.empty()
    
    if not os.path.exists(DB_PATH):
        # 顯示初始化訊息
        with placeholder.container():
            st.info("偵測到尚未建立站點資料庫，正在執行初始化...")
            
        try:
            # 執行爬蟲
            subprocess.run([sys.executable, COLLECTOR_PATH], check=True)
            
            # 將內容替換為成功訊息
            with placeholder.container():
                st.success("初始化完成！")
            
            # 暫停 2 秒讓使用者看到成功訊息
            time.sleep(2)
            
        except subprocess.CalledProcessError as e:
            with placeholder.container():
                st.error(f"初始化失敗: {e}")
            time.sleep(2)
    
    # 清空容器，讓「初始化完成」的字樣消失
    placeholder.empty()

def get_station_data():
    conn = sqlite3.connect('stations.db')
    df = pd.read_sql("SELECT * FROM stations", conn)
    df['lat'] = pd.to_numeric(df['lat'])
    df['lng'] = pd.to_numeric(df['lng'])
    conn.close()
    return df

def get_realtime_info_batch(station_nos):
    """使用 POST 請求，符合 API 規範"""
    url = "https://apis.youbike.com.tw/tw2/parkingInfo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://youbike.com.tw/",
    }
    
    all_data = []
    chunk_size = 20
    for i in range(0, len(station_nos), chunk_size):
        chunk = station_nos[i:i + chunk_size]
        # POST 的參數應該放在 'data' 或 'json' 中
        payload = {'station_no[]': chunk}
        try:
            # 關鍵：改用 requests.post
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['retCode'] == 1:
                    all_data.extend(data['retVal']['data'])
            else:
                print(f"請求失敗，狀態碼: {response.status_code}")
                # 印出回應內容以便除錯
                print(response.text)
        except Exception as e:
            print(f"API 連線錯誤: {e}")
            
    return all_data

def get_weather_forecast(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&hourly=temperature_2m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia/Taipei&forecast_days=7"
    try:
        response = requests.get(url, timeout=5).json()
        return response
    except:
        return None

def get_osrm_distance(lat1, lon1, lat2, lon2, profile):
    url = f"http://router.project-osrm.org/route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}"
    res = requests.get(url).json()
    return res['routes'][0]['distance'] / 1000 # 回傳 km

def get_nearest_n_stations(lat, lon, df, n=10):
    df = df.copy()

    df["dist"] = (
        (df["lat"] - lat)**2 +
        (df["lng"] - lon)**2
    )

    return df.nsmallest(n, "dist")

def inject_theme_and_detect_browser():
    mode_map = {
        "跟隨瀏覽器 (Auto)": "auto", 
        "深色模式 (Dark)": "dark", 
        "淺色模式 (Light)": "light"
    }

    # 1. 建立設定配置器
    def apply_theme_config(mode):
        if mode == "dark":
            st._config.set_option("theme.base", "dark")
            st._config.set_option("theme.primaryColor", "#00B4D8")
            st._config.set_option("theme.backgroundColor", "#0E1117")
            st._config.set_option("theme.secondaryBackgroundColor", "#262730")
            st._config.set_option("theme.textColor", "#FFFFFF")
        elif mode == "light":
            st._config.set_option("theme.base", "light")
            st._config.set_option("theme.primaryColor", "#00B4D8")
            st._config.set_option("theme.backgroundColor", "#FFFFFF")
            st._config.set_option("theme.secondaryBackgroundColor", "#F0F2F6")
            st._config.set_option("theme.textColor", "#31333F")
        else:
            st._config.set_option("theme.base", None)
            st._config.set_option("theme.primaryColor", "#00B4D8")
            st._config.set_option("theme.backgroundColor", None)
            st._config.set_option("theme.secondaryBackgroundColor", None)
            st._config.set_option("theme.textColor", None)

    # 2. 初始化所有必要的 Session 狀態
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "auto"
    if "last_applied_theme" not in st.session_state:
        st.session_state.last_applied_theme = "auto"

    # 3. 當使用者在側邊欄轉動選單時的立即回呼
    def on_theme_change():
        chosen_label = st.session_state.theme_selector_widget
        chosen_mode = mode_map[chosen_label]
        st.session_state.theme_mode = chosen_mode

    # 4. 取得當前應套用的模式
    current_mode = st.session_state.theme_mode

    # 5. 🔥 終極同步修正：比對當前模式與上一次成功套用的模式
    # 如果兩者不一致，說明這是使用者剛剛「快速切換」觸發的新一輪執行
    # 我們在這裡直接重新套用配置，並強制觸發重新整理，徹底解決前端漏勾（慢半拍）的問題
    if current_mode != st.session_state.last_applied_theme:
        apply_theme_config(current_mode)
        st.session_state.last_applied_theme = current_mode
        # 注意：這裡的 rerun 是在主程式流程中（非 callback 內），是絕對合法且能即時重新整理前端的
        st.rerun()

    # 6. 保底確保一般頁面切換或剛載入時的配置環境正常
    apply_theme_config(current_mode)

    # 7. 提供側邊欄選單
    with st.sidebar:
        st.divider()
        options_list = list(mode_map.keys())
        current_label = next((k for k, v in mode_map.items() if v == current_mode), "跟隨瀏覽器 (Auto)")
        default_idx = options_list.index(current_label)
        
        st.selectbox(
            "🎨 介面主題", 
            options=options_list, 
            index=default_idx,
            key="theme_selector_widget",
            on_change=on_theme_change
        )