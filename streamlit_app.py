import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 設定網頁標題與寬度
st.set_page_config(page_title="台股選股利器", layout="wide")

st.title("🇹🇼 台股 AI 自動篩選預測系統")
st.write("自動過濾成交量 > 30,000 張標的，並計算短/長線預期價。")

# --- 側邊欄與篩選 ---
with st.sidebar:
    st.header("系統設定")
    analysis_date = st.date_input("分析日期", datetime.now())
    volume_threshold = 30000  # 成交量門檻：3萬張
    
    # 常見高成交量台股清單 (確保網頁跑得快，先列出熱門 50 檔)
    taiwan_stocks = [
        "2330.TW", "2317.TW", "2303.TW", "2454.TW", "2603.TW", "2609.TW", "2610.TW", "2618.TW",
        "2881.TW", "2882.TW", "2382.TW", "3231.TW", "2353.TW", "2324.TW", "2409.TW", "3481.TW",
        "1605.TW", "1513.TW", "2357.TW", "2301.TW", "2376.TW", "6669.TW", "2313.TW", "2883.TW"
    ]

# --- 核心數據抓取與計算 ---
def get_analysis():
    data_list = []
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(taiwan_stocks):
        try:
            ticker = yf.Ticker(symbol)
            # 抓取過去 120 天數據以計算季線(60MA)
            df = ticker.history(period="120d")
            if df.empty or len(df) < 60:
                continue
                
            # 基礎數據整理
            info = ticker.info
            current_price = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1] / 1000  # 轉為「張」
            
            # 條件：成交量 > 3萬張
            if last_vol < volume_threshold:
                continue
                
            # 技術指標計算
            df['5MA'] = df['Close'].rolling(5).mean()
            df['20MA'] = df['Close'].rolling(20).mean()
            df['60MA'] = df['Close'].rolling(60).mean()
            
            high_20d = df['High'].iloc[-21:-1].max()
            low_20d = df['Low'].iloc[-21:-1].min()
            
            # A. 短線爆股判斷：當前價格突破 20 日高點
            is_burst = current_price > high_20d
            # 短線預期價公式：突破點 + (突破點 - 盤整低點)
            short_target = current_price + (current_price - low_20d)
            
            # B. 長線穩定上漲：均線多頭排列 (5 > 20 > 60)
            is_stable = df['5MA'].iloc[-1] > df['20MA'].iloc[-1] > df['60MA'].iloc[-1]
            # 長線預期價公式：EPS * PE (若抓不到則用固定 20% 增幅)
            eps = info.get('trailingEps', 0)
            pe = info.get('forwardPE', 15)
            long_target = eps * pe if eps > 0 else current_price * 1.2
            
            data_list.append({
                "代碼": symbol.replace(".TW", ""),
                "股名": info.get('shortName', "未知"),
                "現價": round(current_price, 1),
                "成交張數": int(last_vol),
                "短線訊號": "🔥 帶量突破" if is_burst else "--",
                "短線預期價": round(short_target, 1),
                "長線趨勢": "📈 多頭排列" if is_stable else "--",
                "長線預期價": round(long_target, 1)
            })
        except:
            pass
        progress_bar.progress((i + 1) / len(taiwan_stocks))
    
    return pd.DataFrame(data_list)

# --- 介面展示 ---
if st.button("點擊開始掃描台股"):
    results = get_analysis()
    
    if not results.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔥 短線爆發預選")
            short_res = results[results['短線訊號'] != "--"]
            st.dataframe(short_res[['代碼', '股名', '現價', '成交張數', '短線預期價']])
            
        with col2:
            st.subheader("🛡️ 長線穩定預選")
            long_res = results[results['長線趨勢'] != "--"]
            st.dataframe(long_res[['代碼', '股名', '現價', '成交張數', '長線預期價']])
    else:
        st.warning("今日暫無符合「成交量 > 3萬張」之標的。")

st.info("計算邏輯：短線採『測幅滿足法』；長線採『本益比估值法』。")
