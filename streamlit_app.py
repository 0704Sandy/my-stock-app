import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# --- 1. 核心設定 ---
GOOGLE_API_KEY = "AIzaSyAJn-wmeP1jAB8eyScT4Ei2Hie1Dx-8yHU" 

# 清除舊的配置並重新設定
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # 強制指定最穩定的模型名稱
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"AI 配置失敗: {e}")

st.set_page_config(page_title="台股AI導航與新聞預測", layout="wide")

st.title("🛡️ 台股 AI 飆股導航與全自動新聞預測系統")

# --- 2. AI 財經新聞整理功能 ---
def get_ai_market_intelligence():
    prompt = """
    你是專業的財經分析師。請整理今日最新的全球財經新聞、美股趨勢與台股消息：
    1. 總結 3 條最重要的世界新聞。
    2. 分析哪些題材目前被看好。
    3. 分析哪些新聞可能導致哪些股票下跌。
    4. 推薦 3-5 個今日最值得關注的台股題材關鍵字。
    請用繁體中文回答，內容精簡。
    """
    try:
        # 使用最基礎的生成呼叫
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # 如果還是失敗，嘗試切換模型
        return f"❌ 連線失敗，請稍後再試。原因: {str(e)}"

# --- 3. 數據運算邏輯 ---
def run_full_scan(vol_limit, stock_pool):
    results = []
    progress_bar = st.progress(0, text="大數據掃描中...")
    for i, symbol in enumerate(stock_pool):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="180d")
            if df.empty or len(df) < 60: continue
            
            info = ticker.info
            current_p = df['Close'].iloc[-1]
            vol_shares = df['Volume'].iloc[-1] / 1000
            if vol_shares < vol_limit: continue
            
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            high_20 = df['High'].iloc[-21:-1].max()
            low_20 = df['Low'].iloc[-21:-1].min()
            
            is_surging = (current_p >= high_20) and (current_p > ma5 > ma20)
            short_t = current_p + (current_p - low_20)
            eps = info.get('trailingEps', 0)
            long_t = eps * 35 * 1.15 if eps > 0 else current_p * 1.3
            if long_t < current_p: long_t = current_p * 1.25

            name_map = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2603": "長榮", "2881": "富邦金"}
            display_name = name_map.get(symbol.split(".")[0], info.get('shortName', symbol))

            results.append({
                "代碼": symbol.replace(".TW", ""),
                "名稱": display_name,
                "現價": round(current_p, 1),
                "短線預期": round(short_t, 1),
                "長線預估": round(long_t, 1),
                "今日張數": int(vol_shares),
                "狀態": "🚀 推薦飆股" if is_surging else "多頭排列"
            })
        except: pass
        progress_bar.progress((i + 1) / len(stock_pool))
    progress_bar.empty()
    return pd.DataFrame(results)

# --- 4. 介面展示 ---
st.subheader("🌐 AI 每日財經快訊與影響預測")
with st.expander("📌 點擊展開今日 AI 深度新聞分析", expanded=True):
    if st.button("🔄 更新 AI 新聞分析"):
        with st.spinner("AI 正在分析全球趨勢..."):
            ai_news = get_ai_market_intelligence()
            st.markdown(ai_news)

st.divider()

with st.sidebar:
    st.header("⚙️ 篩選設定")
    vol_input = st.number_input("最低成交量 (張)", value=20000)
    stock_pool = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2603.TW", "2881.TW", "2303.TW", "2609.TW", "2409.TW"]

if st.button("🔍 執行全自動市場掃描", use_container_width=True):
    final_data = run_full_scan(vol_input, stock_pool)
    if not final_data.empty:
        st.subheader("🔥 掃描結果")
        st.dataframe(final_data, hide_index=True, use_container_width=True)
    else:
        # 如果顯示查無標的，可能是量能過低
        st.warning("查無標的。請檢查『成交量門檻』是否設得太高（目前為 2萬張）。")
