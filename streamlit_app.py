import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="台股AI飆股預測系統", layout="wide")

st.title("📈 台股 AI 飆股篩選與價值預測系統")
st.markdown("""
此系統已針對 **AI 高成長股** 與 **短期爆發型態** 進行優化：
* **推薦短期飆股**：自動篩選「成交量 > 2萬張」、「K線多頭排列」且「股價突破近期高點」的標的。
* **中文名稱優化**：自動轉換台股中文簡稱。
* **高估值邏輯**：採用 35 倍 AI 溢價本益比，更貼近目前台積電、鴻海等行情。
""")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 篩選參數")
    vol_limit = st.number_input("最低成交量門檻 (張)", value=20000)
    
    # 擴大熱門股池
    taiwan_stocks = [
        "2330.TW", "2317.TW", "2303.TW", "2454.TW", "2382.TW", "3231.TW", 
        "2357.TW", "2301.TW", "2376.TW", "6669.TW", "2603.TW", "2609.TW", 
        "2618.TW", "2881.TW", "2882.TW", "2886.TW", "2409.TW", "3481.TW",
        "1513.TW", "1605.TW", "2313.TW", "2360.TW", "3034.TW", "3711.TW",
        "2610.TW", "2615.TW", "2344.TW", "2449.TW", "1504.TW", "1519.TW"
    ]

# --- 核心運算邏輯 ---
def analyze_market():
    results = []
    progress_bar = st.progress(0, text="大數據掃描中...")
    
    for i, symbol in enumerate(taiwan_stocks):
        try:
            ticker = yf.Ticker(symbol)
            # 獲取半年歷史數據
            df = ticker.history(period="180d")
            if df.empty or len(df) < 60:
                continue
            
            info = ticker.info
            current_price = df['Close'].iloc[-1]
            volume_shares = df['Volume'].iloc[-1] / 1000  # 換算張數
            
            # --- 基本門檻過濾 ---
            if volume_shares < vol_limit:
                continue

            # --- 計算技術指標 ---
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA60'] = df['Close'].rolling(60).mean()
            
            # 飆股 K 線型態判斷：
            # 1. 價格 > MA5 > MA20 (短線極強)
            # 2. 股價站上 MA60 (長線支撐)
            # 3. 今日收紅 K (收盤價 > 開盤價)
            is_strong_k = (current_price > df['MA5'].iloc[-1] > df['MA20'].iloc[-1]) and \
                          (current_price > df['MA60'].iloc[-1]) and \
                          (df['Close'].iloc[-1] > df['Open'].iloc[-1])
            
            # 短線對稱測幅目標
            high_20d = df['High'].iloc[-21:-1].max()
            low_20d = df['Low'].iloc[-21:-1].min()
            short_target = current_price + (current_price - low_20d)

            # 長線 AI 溢價估值 (35倍 PE)
            eps = info.get('trailingEps', 0)
            if eps <= 0:
                long_target = current_price * 1.3
            else:
                pe_ratio = max(info.get('forwardPE', 35), 35)
                long_target = eps * pe_ratio * 1.15 # 加上成長加權

            # 修正：避免財報落後導致預期過低
            if long_target < current_price:
                long_target = current_price * 1.25

            # --- 中文名稱處理 ---
            raw_name = info.get('shortName', symbol)
            # 移除常見的英文後綴，讓手機版更易讀
            display_name = raw_name.replace("TAIWAN SEMICONDUCTOR MANUFAC", "台積電")\
                                   .replace("HON HAI PRECISION IND", "鴻海")\
                                   .replace("MEDIATEK INC", "聯發科")\
                                   .replace("QUANTA COMPUTER", "廣達")\
                                   .replace("CHUNGHWA TELECOM", "中華電")\
                                   .replace("UNITED MICROELECTRONICS", "聯電")\
                                   .replace("EVERGREEN MARINE", "長榮")\
                                   .replace("YANG MING MARINE", "陽明")\
                                   .split(" ")[0] # 僅取第一個單詞

            results.append({
                "代碼": symbol.replace(".TW", ""),
                "股票名稱": display_name,
                "目前現價": round(current_price, 2),
                "短線目標": round(short_target, 2),
                "長線預估": round(long_target, 2),
                "今日成交張數": int(volume_shares),
                "飆股推薦": "🚀 推薦短期飆股" if (is_strong_k and current_price >= high_20d) else "一般走勢"
            })
        except:
            pass
        progress_bar.progress((i + 1) / len(taiwan_stocks))
    
    progress_bar.empty()
    return pd.DataFrame(results)

# --- 介面呈現 ---
if st.button("🔍 開始全自動掃描 (含飆股篩選)", use_container_width=True):
    data = analyze_market()
    
    if not data.empty:
        # 1. 顯示飆股專區
        st.subheader("🔥 推薦短期飆股專區 (成交量 > 2萬 + 強勢K線)")
        hot_stocks = data[data['飆股推薦'] == "🚀 推薦短期飆股"]
        if not hot_stocks.empty:
            st.success(f"偵測到 {len(hot_stocks)} 檔符合爆發型態標的！")
            st.dataframe(hot_stocks, hide_index=True, use_container_width=True)
        else:
            st.info("目前大盤整理中，尚未出現符合「短期飆股」型態的個股。")
        
        st.divider()
        
        # 2. 顯示所有標的
        st.subheader("📊 所有監測標的行情預測")
        st.dataframe(
            data.sort_values(by="今日成交張數", ascending=False), 
            hide_index=True, 
            use_container_width=True
        )
    else:
        st.warning("查無符合成交量門檻的標的。")

st.divider()
st.caption("💡 飆股小知識：本系統推薦之標的需符合「帶量突破」與「均線多頭排列」之技術面，適合短線操作。")
