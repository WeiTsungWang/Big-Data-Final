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
    # 1. 初始化狀態
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "auto"  # auto, dark, light

    # 2. 透過隱形 JavaScript 偵測瀏覽器偏好
    if "browser_theme" not in st.session_state:
        js_code = """
        <script>
            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = isDark ? 'dark' : 'light';
            parent.postMessage({type: 'streamlit:setComponentValue', value: theme}, '*');
        </script>
        """
        browser_detected = components.html(js_code, height=0, width=0)
        if browser_detected:
            st.session_state.browser_theme = browser_detected
            st.rerun()
        return

    # 3. 決定最終渲染的主題
    current_theme = st.session_state.theme_mode
    if current_theme == "auto":
        current_theme = st.session_state.get("browser_theme", "light")

    # 4. 🔥 核心修正：直接動態修改 Streamlit 全域 Theme 設定
    # 這能確保所有 selectbox, radio, dataframe 完美同步，且不用寫複雜的 CSS
    if current_theme == "dark":
        st._config.set_option("theme.base", "dark")
        st._config.set_option("theme.backgroundColor", "#0E1117")
        st._config.set_option("theme.secondaryBackgroundColor", "#262730")
        st._config.set_option("theme.textColor", "#FFFFFF")
    else:
        st._config.set_option("theme.base", "light")
        st._config.set_option("theme.backgroundColor", "#FFFFFF")
        st._config.set_option("theme.secondaryBackgroundColor", "#F0F2F6")
        st._config.set_option("theme.textColor", "#31333F")

    # 5. 在側邊欄提供手動切換按鈕
    with st.sidebar:
        current_options = ["跟隨瀏覽器 (Auto)", "深色模式 (Dark)", "淺色模式 (Light)"]
        default_idx = 0 if st.session_state.theme_mode == "auto" else (1 if st.session_state.theme_mode == "dark" else 2)
        
        selected_option = st.selectbox(
            "🎨 介面主題",
            options=current_options,
            index=default_idx,
            key="theme_selector_widget"
        )
        
        # 對應轉換
        target_mode = "auto" if selected_option == "跟隨瀏覽器 (Auto)" else ("dark" if selected_option == "深色模式 (Dark)" else "light")
        
        # 如果使用者切換了選項，立刻更新並重新整理頁面
        if target_mode != st.session_state.theme_mode:
            st.session_state.theme_mode = target_mode
            st.rerun()