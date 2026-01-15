import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 1. 網頁基本設定
st.set_page_config(page_title="台股自動導航系統", layout="wide")

st.title("📈 台股自動導航：即時新聞與飆股預測")
st.markdown("本系統已移除 API 限制，改用**即時網頁爬蟲**獲取市場最新資訊。")

# --- 2. 網頁爬蟲功能 (取代 API) ---
def get_latest_market_news():
    try:
        # 爬取 Yahoo Finance 國際財經快訊
        url = "https://finance.yahoo.com/rss/topstories"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, features="xml")
        
        items = soup.find_all('item')
        news_list = []
        for item in items[:5]: # 抓取前 5 條
            news_list.append(f"📰 **{item.title.text}**\n{item.pubDate.text}")
        return news_list
    except Exception as e:
        return ["⚠️ 無法連線至新聞源，請檢查網路。"]

# --- 3. 數據運算邏輯 ---
def run_market_scan(vol_limit, stock_pool):
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
            
            # K線與均線指標
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            high_20 = df['High'].iloc[-21:-1].max()
            low_20 = df['Low'].iloc[-21:-1].min()
            
            # 飆股判斷 (成交量 > 2萬 + 帶量突破 20日高點)
            is_surging = (current_p >= high_20) and (current_p > ma5 > ma20)
            
            # 價值預測
            short_t = current_p + (current_p - low_20)
            long_t = current_p * 1.3 # 採用固定溢價法避開複雜 API 估值

            name_map = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2603": "長榮"}
            display_name = name_map.get(symbol.split(".")[0], info.get('shortName', symbol))

            results.append({
                "代碼": symbol.replace(".TW", ""),
                "名稱": display_name,
                "現價": round(current_p, 1),
                "短線預期": round(short_t, 1),
                "長線預估": round(long_t, 1),
                "今日張數": int(vol_shares),
                "推薦": "🚀 推薦飆股" if is_surging else "穩健多頭"
            })
        except: pass
        progress_bar.progress((i + 1) / len(stock_pool))
    
    progress_bar.empty()
    return pd.DataFrame(results)

# --- 4. 介面呈現 ---
st.subheader("🌐 今日全球財經即時快訊 (不限 API)")
if st.button("🔄 重新整理最新消息"):
    news = get_latest_market_news()
    for n in news:
        st.write(n)

st.divider()

with st.sidebar:
    st.header("⚙️ 參數設定")
    vol_input = st.number_input("最低成交量 (張)", value=20000)
    stock_pool = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2603.TW", "2609.TW", "2881.TW"]

if st.button("🔍 開始全自動掃描飆股", use_container_width=True):
    data = run_market_scan(vol_input, stock_pool)
    if not data.empty:
        st.subheader("🔥 掃描結果 (含飆股篩選)")
        st.dataframe(data.sort_values(by="今日張數", ascending=False), hide_index=True, use_container_width=True)
    else:
        st.warning("查無符合門檻標的。")

st.divider()
st.caption("提示：本程式透過 BeautifulSoup 進行新聞爬取，無需 API Key，永久免費使用。")
