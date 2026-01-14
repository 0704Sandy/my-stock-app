import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# --- 1. 核心設定 ---
GOOGLE_API_KEY = "AIzaSyAJn-wmeP1jAB8eyScT4Ei2Hie1Dx-8yHU" 

genai.configure(api_key=GOOGLE_API_KEY)
# 使用標準名稱
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="台股AI導航與新聞預測", layout="wide")
st.title("🛡️ 台股 AI 飆股導航與全自動新聞預測系統")

# --- 2. AI 財經新聞整理功能 ---
def get_ai_market_intelligence():
    prompt = "請整理今日最新的全球與台股重要財經新聞，分析看好與看淡的題材，並以繁體中文回答。"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 連線失敗。請確保已更新 requirements.txt 並重啟。原因: {str(e)}"

# --- 3. 數據運算邏輯 ---
def run_full_scan(vol_limit, stock_pool):
    results = []
    progress_bar = st.progress(0, text="大數據掃描中...")
    for i, symbol in enumerate(stock_pool):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="180d")
            if df.empty or len(df) < 60: continue
            current_p = df['Close'].iloc[-1]
            vol_shares = df['Volume'].iloc[-1] / 1000
            if vol_shares < vol_limit: continue
            
            ma5, ma20 = df['Close'].rolling(5).mean().iloc[-1], df['Close'].rolling(20).mean().iloc[-1]
            high_20, low_20 = df['High'].iloc[-21:-1].max(), df['Low'].iloc[-21:-1].min()
            
            is_surging = (current_p >= high_20) and (current_p > ma5 > ma20)
            short_t = current_p + (current_p - low_20)
            
            # 長線預估邏輯
            info = ticker.info
            eps = info.get('trailingEps', 0)
            long_t = eps * 35 * 1.15 if eps > 0 else current_p * 1.3
            if long_t < current_p: long_t = current_p * 1.25

            results.append({
                "代碼": symbol.replace(".TW", ""),
                "名稱": info.get('shortName', symbol),
                "現價": round(current_p, 1),
                "短線預期": round(short_t, 1),
                "長線預估": round(long_t, 1),
                "張數": int(vol_shares),
                "狀態": "🚀 推薦飆股" if is_surging else "多頭"
            })
        except: pass
        progress_bar.progress((i + 1) / len(stock_pool))
    progress_bar.empty()
    return pd.DataFrame(results)

# --- 4. 介面展示 ---
with st.expander("📌 今日 AI 深度新聞分析", expanded=True):
    if st.button("🔄 更新 AI 新聞分析"):
        with st.spinner("AI 正在分析趨勢..."):
            st.markdown(get_ai_market_intelligence())

st.divider()

with st.sidebar:
    st.header("⚙️ 篩選設定")
    vol_input = st.number_input("最低成交量 (張)", value=10000) # 預設調低到 1萬張較易選到
    stock_pool = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2603.TW", "2881.TW", "2609.TW", "2618.TW", "2303.TW"]

if st.button("🔍 執行全自動市場掃描", use_container_width=True):
    final_data = run_full_scan(vol_input, stock_pool)
    if not final_data.empty:
        st.dataframe(final_data.sort_values(by="張數", ascending=False), hide_index=True, use_container_width=True)
    else:
        st.warning("查無符合門檻標的，請嘗試調低左側成交量參數。")
