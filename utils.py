import streamlit as st
import os
import sys
import subprocess
import time
import math
import pandas as pd
import sqlite3
import requests

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

# def apply_theme():
#     # 1. 初始化狀態
#     if 'theme' not in st.session_state:
#         st.session_state.theme = 'dark'

#     # 2. 定義主題 CSS 內容 (這裡不注入，只定義內容)
#     if st.session_state.theme == 'light':
#         theme_css = """
#         <style id="theme-style">
#         .stApp, [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #262730 !important; }
#         [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
#         h1, h2, h3, p, label, .stMarkdown { color: #262730 !important; }
#         div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #262730 !important; border: 1px solid #ccc !important; }
#         .stPlotlyChart, .stVegaLiteChart, .stDataFrame { background-color: #FFFFFF !important; }
#         </style>
#         """
#     else:
#         theme_css = """
#         <style id="theme-style">
#         .stApp, [data-testid="stAppViewContainer"] { background-color: #0E1117 !important; color: #FFFFFF !important; }
#         [data-testid="stSidebar"] { background-color: #262730 !important; }
#         h1, h2, h3, p, label, .stMarkdown { color: #FFFFFF !important; }
#         div[data-baseweb="select"] > div { background-color: #262730 !important; color: #FFFFFF !important; }
#         .stPlotlyChart, .stVegaLiteChart, .stDataFrame { background-color: #0E1117 !important; }
#         </style>
#         """

#     # 3. 強制執行注入 (移到這裡，確保每次呼叫都會重新覆蓋舊的 style)
#     st.markdown(theme_css, unsafe_allow_html=True)

#     # 4. 側邊欄切換器
#     def toggle_theme():
#         st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

#     st.sidebar.toggle("切換淺色模式", 
#                       value=(st.session_state.theme == 'light'), 
#                       on_change=toggle_theme, 
#                       key='theme_toggle')

# def apply_theme():
#     if 'theme' not in st.session_state:
#         st.session_state.theme = 'dark'

#     # 建立一個簡單的 Toggle
#     st.sidebar.toggle("切換淺色模式", key='theme_toggle', on_change=lambda: st.session_state.update({'theme': 'light' if st.session_state.theme == 'dark' else 'dark'}))

#     # CSS 內容
#     dark_css = "<style>.stApp {background-color: #0E1117; color: white;}</style>"
#     light_css = "<style>.stApp {background-color: white; color: black;}</style>"
    
#     st.markdown(light_css if st.session_state.theme == 'light' else dark_css, unsafe_allow_html=True)

# def apply_theme():
#     if 'theme' not in st.session_state:
#         st.session_state.theme = 'dark'

#     # 使用 Callback 邏輯更新狀態
#     def update_theme():
#         st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

#     st.sidebar.toggle("切換淺色模式", 
#                       key='theme_toggle', 
#                       value=(st.session_state.theme == 'light'),
#                       on_change=update_theme)

#     # 針對全域元件的 CSS 覆蓋
#     if st.session_state.theme == 'light':
#         theme_css = """
#         <style>
#         /* 強制背景與文字顏色 */
#         .stApp, .stAppHeader, .stSidebar { background-color: #FFFFFF !important; color: #262730 !important; }
        
#         /* 所有的文字顏色 */
#         h1, h2, h3, p, label, .stMarkdown, .stText { color: #262730 !important; }
        
#         /* 表格與圖表背景 */
#         .stDataFrame, .stPlotlyChart { background-color: #FFFFFF !important; }
        
#         /* 輸入元件 */
#         div[data-baseweb="select"], div[data-baseweb="input"] { background-color: #FFFFFF !important; }
        
#         /* 按鈕樣式 */
#         button { background-color: #F0F2F6 !important; color: #262730 !important; border: 1px solid #ccc !important; }
#         </style>
#         """
#     else:
#         theme_css = """
#         <style>
#         .stApp, .stAppHeader, .stSidebar { background-color: #0E1117 !important; color: #FFFFFF !important; }
#         h1, h2, h3, p, label, .stMarkdown, .stText { color: #FFFFFF !important; }
#         .stDataFrame, .stPlotlyChart { background-color: #0E1117 !important; }
#         div[data-baseweb="select"], div[data-baseweb="input"] { background-color: #262730 !important; }
#         button { background-color: #262730 !important; color: #FFFFFF !important; }
#         </style>
#         """
    
#     st.markdown(theme_css, unsafe_allow_html=True)

# def apply_theme():
#     if 'theme' not in st.session_state:
#         st.session_state.theme = 'dark'

#     def update_theme():
#         st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

#     st.sidebar.toggle("切換淺色模式", 
#                       key='theme_toggle', 
#                       value=(st.session_state.theme == 'light'),
#                       on_change=update_theme)

#     # 針對 Radio, Selectbox, Input, NumberInput 的強制樣式
#     if st.session_state.theme == 'light':
#         theme_css = """
#         <style>
#         /* 基礎背景 */
#         .stApp, [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; color: #262730 !important; }
        
#         /* 針對 Radio 和 Checkbox 文字 */
#         div[role="radiogroup"] label, div[data-baseweb="checkbox"] label { color: #262730 !important; }
        
#         /* 針對 Selectbox 和 Searchbox 的外層容器 */
#         div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #262730 !important; border: 1px solid #ccc !important; }
        
#         /* 針對 Input (包含 number_input) 的外層 */
#         div[data-baseweb="base-input"] { background-color: #FFFFFF !important; border: 1px solid #ccc !important; }
#         input { color: #262730 !important; background-color: #FFFFFF !important; }
        
#         /* Sidebar */
#         [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
#         </style>
#         """
#     else:
#         theme_css = """
#         <style>
#         .stApp, [data-testid="stAppViewContainer"] { background-color: #0E1117 !important; color: #FFFFFF !important; }
#         div[role="radiogroup"] label, div[data-baseweb="checkbox"] label { color: #FFFFFF !important; }
#         div[data-baseweb="select"] > div { background-color: #262730 !important; color: #FFFFFF !important; border: 1px solid #444 !important; }
#         div[data-baseweb="base-input"] { background-color: #262730 !important; border: 1px solid #444 !important; }
#         input { color: #FFFFFF !important; background-color: #262730 !important; }
#         [data-testid="stSidebar"] { background-color: #262730 !important; }
#         </style>
#         """
    
#     st.markdown(theme_css, unsafe_allow_html=True)


# -------------目前最接近理想的版本-----------------
# def apply_theme():
#     # 1. 狀態管理
#     if 'theme' not in st.session_state:
#         st.session_state.theme = 'dark'

#     def update_theme():
#         st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

#     # 2. 側邊欄切換器
#     st.sidebar.toggle("切換淺色模式", 
#                       key='theme_toggle', 
#                       value=(st.session_state.theme == 'light'),
#                       on_change=update_theme)

#     # 3. 完整版 CSS 覆蓋
#     if st.session_state.theme == 'light':
#         theme_css = """
#         <style>

#         /* 1. 確保選單彈出層的背景與文字 */
#         div[role="listbox"], div[data-baseweb="menu"], [data-testid="stSidebar"] {
#             background-color: #FFFFFF !important;
#             color: #262730 !important;
#         }
        
#         /* 2. 針對每一個選項 */
#         div[role="option"] {
#             background-color: #FFFFFF !important;
#             color: #262730 !important;
#         }
        
#         /* 3. 滑鼠懸停效果 */
#         div[role="option"]:hover {
#             background-color: #F0F2F6 !important;
#         }

#         /* 頁面全域背景 */
#         .stApp, [data-testid="stAppViewContainer"], .stAppHeader, [data-testid="stSidebar"] { 
#             background-color: #FFFFFF !important; 
#             color: #262730 !important; 
#         }
        
#         /* 文字與標籤 */
#         h1, h2, h3, p, label, .stMarkdown, .stText, .stRadio label { 
#             color: #262730 !important; 
#         }
        
#         /* 選擇框 (Selectbox / Multiselect) */
#         div[data-baseweb="select"] > div { 
#             background-color: #FFFFFF !important; 
#             color: #262730 !important; 
#             border: 1px solid #ccc !important; 
#         }
        
#         /* 輸入框 (NumberInput / TextInput / Searchbox) */
#         div[data-baseweb="base-input"] { 
#             background-color: #FFFFFF !important; 
#             border: 1px solid #ccc !important; 
#         }
#         input { color: #262730 !important; }
        
#         /* 按鈕 */
#         button { 
#             background-color: #F0F2F6 !important; 
#             color: #262730 !important; 
#             border: 1px solid #ccc !important; 
#         }
        
#         /* 資料表與圖表背景 */
#         .stDataFrame, .stPlotlyChart { background-color: #FFFFFF !important; }

#         /* 下拉選單展開後的彈出層 */
#         div[data-baseweb="menu"] { 
#             background-color: #FFFFFF !important; 
#             color: #262730 !important; 
#         }
#         div[data-baseweb="menu"] li { 
#             background-color: #FFFFFF !important; 
#             color: #262730 !important; 
#         }
#         div[data-baseweb="menu"] li:hover { background-color: #F0F2F6 !important; }
#         </style>
#         """
#     else:
#         theme_css = """
#         <style>
#         /* 1. 確保選單彈出層的背景與文字 */
#         div[role="listbox"], div[data-baseweb="menu"], [data-testid="stSidebar"] {
#             background-color: #FFFFFF !important;
#             color: #262730 !important;
#         }
        
#         /* 2. 針對每一個選項 */
#         div[role="option"] {
#             background-color: #FFFFFF !important;
#             color: #262730 !important;
#         }
        
#         /* 3. 滑鼠懸停效果 */
#         div[role="option"]:hover {
#             background-color: #F0F2F6 !important;
#         }

#         .stApp, [data-testid="stAppViewContainer"], .stAppHeader, [data-testid="stSidebar"] { 
#             background-color: #0E1117 !important; 
#             color: #FFFFFF !important; 
#         }
#         h1, h2, h3, p, label, .stMarkdown, .stText, .stRadio label { 
#             color: #FFFFFF !important; 
#         }
#         div[data-baseweb="select"] > div { 
#             background-color: #262730 !important; 
#             color: #FFFFFF !important; 
#             border: 1px solid #444 !important; 
#         }
#         div[data-baseweb="base-input"] { 
#             background-color: #262730 !important; 
#             border: 1px solid #444 !important; 
#         }
#         input { color: #FFFFFF !important; }
#         button { 
#             background-color: #262730 !important; 
#             color: #FFFFFF !important; 
#             border: 1px solid #444 !important; 
#         }
#         .stDataFrame, .stPlotlyChart { background-color: #0E1117 !important; }

#         /* 針對下拉選單展開後的彈出層 */
#         div[data-baseweb="menu"] { 
#             background-color: #262730 !important; 
#             color: #FFFFFF !important; 
#         }
#         div[data-baseweb="menu"] li { 
#             background-color: #262730 !important; 
#             color: #FFFFFF !important; 
#         }
#         div[data-baseweb="menu"] li:hover { background-color: #3D3F47 !important; }
#         </style>
#         """
    
#     st.markdown(theme_css, unsafe_allow_html=True)
# ------------------------------------------------------------------------------------

def apply_theme():
    # 1. 狀態持久化
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'

    # 2. 定義更新主題的函式 (不需要 st.rerun())
    def update_theme():
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

    # 3. 側邊欄切換開關
    st.sidebar.toggle("切換淺色模式", 
                      key='theme_toggle', 
                      value=(st.session_state.theme == 'light'),
                      on_change=update_theme)

    # 4. 極致 CSS 注入：涵蓋所有元件與其彈出層 (menu, listbox, option)
    if st.session_state.theme == 'light':
        theme_css = """
        <style>
        /* 基礎全域 */
        .stApp, [data-testid="stAppViewContainer"], .stAppHeader, [data-testid="stSidebar"] { 
            background-color: #FFFFFF !important; color: #262730 !important; 
        }
        h1, h2, h3, p, label, .stMarkdown, .stText { color: #262730 !important; }
        
        /* 輸入與選單元件 (Dropdown / Searchbox) */
        div[data-baseweb="select"] > div, div[data-baseweb="base-input"] { 
            background-color: #FFFFFF !important; color: #262730 !important; border: 1px solid #ccc !important; 
        }
        div[role="listbox"], div[data-baseweb="menu"], div[role="option"] { 
            background-color: #FFFFFF !important; color: #262730 !important; 
        }
        div[role="option"]:hover { background-color: #F0F2F6 !important; }
        
        /* 按鈕與圖表 */
        button { background-color: #F0F2F6 !important; color: #262730 !important; border: 1px solid #ccc !important; }
        .stDataFrame, .stPlotlyChart { background-color: #FFFFFF !important; }
        </style>
        """
    else:
        theme_css = """
        <style>
        .stApp, [data-testid="stAppViewContainer"], .stAppHeader, [data-testid="stSidebar"] { 
            background-color: #0E1117 !important; color: #FFFFFF !important; 
        }
        h1, h2, h3, p, label, .stMarkdown, .stText { color: #FFFFFF !important; }
        div[data-baseweb="select"] > div, div[data-baseweb="base-input"] { 
            background-color: #262730 !important; color: #FFFFFF !important; border: 1px solid #444 !important; 
        }
        div[role="listbox"], div[data-baseweb="menu"], div[role="option"] { 
            background-color: #262730 !important; color: #FFFFFF !important; 
        }
        div[role="option"]:hover { background-color: #3D3F47 !important; }
        button { background-color: #262730 !important; color: #FFFFFF !important; border: 1px solid #444 !important; }
        .stDataFrame, .stPlotlyChart { background-color: #0E1117 !important; }
        <style>
        /* 強制表格容器背景與文字 */
        div[data-testid="stDataFrame"], .stDataFrame {{ 
            background-color: {'#FFFFFF' if st.session_state.theme == 'light' else '#0E1117'} !important; 
        }}
        /* 針對表格內部的儲存格顏色 */
        div[data-testid="stDataFrame"] div[data-testid="stDataEditor"] {{
            background-color: {'#FFFFFF' if st.session_state.theme == 'light' else '#0E1117'} !important;
        }}
        </style>
        """
    
    st.markdown(theme_css, unsafe_allow_html=True)