import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 設定網頁標題與寬度
st.set_page_config(page_title="台股AI選股預測器", layout="wide")

st.title("📈 台股智能篩選與目標價預測系統")
st.markdown("""
### 篩選標準：
1. **每日成交量 > 30,000 張** (確保流動性，過濾殭屍股)
2. **短線爆發**：股價創近期新高，利用「對稱測幅」預測下一波高點。
3. **長線穩定**：均線多頭排列，利用「成長性本益比估值」預測目標價。
""")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 參數微調")
    volume_threshold = st.number_input("成交量門檻 (張)", value=30000)
    # 將台股熱門股池擴大，增加篩選機會
    taiwan_stocks = [
        "2330.TW", "2317.TW", "2303.TW", "2454.TW", "2603.TW", "2609.TW", "2610.TW", "2618.TW",
        "2881.TW", "2882.TW", "2382.TW", "3231.TW", "2353.TW", "2324.TW", "2409.TW", "3481.TW",
        "1605.TW", "1513.TW", "2357.TW", "2301.TW", "2376.TW", "6669.TW", "2313.TW", "2883.TW",
        "2308.TW", "2337.TW", "2344.TW", "2449.TW", "2615.TW", "2884.TW", "2885.TW", "2886.TW"
    ]

# --- 核心分析邏輯 ---
def run_stock_analysis():
    results = []
    progress_text = "正在掃描台股大數據，請稍候..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, symbol in enumerate(taiwan_stocks):
        try:
            ticker = yf.Ticker(symbol)
            # 抓取過去半年的數據
            df = ticker.history(period="180d")
            if df.empty or len(df) < 60:
                continue
                
            info = ticker.info
            current_price = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1] / 1000  # 換算成張數
            
            # 1. 成交量篩選
            if last_vol < volume_threshold:
                continue
            
            # 2. 技術指標計算
            df['5MA'] = df['Close'].rolling(5).mean()
            df['20MA'] = df['Close'].rolling(20).mean()
            df['60MA'] = df['Close'].rolling(60).mean()
            
            high_20d = df['High'].iloc[-21:-1].max() # 前20天最高價
            low_20d = df['Low'].iloc[-21:-1].min()   # 前20天最低價
            
            # --- A. 短線邏輯：突破偵測 ---
            # 判斷是否站上所有均線且突破20日高點
            is_breakout = (current_price > high_20d) and (current_price > df['5MA'].iloc[-1])
            # 短線目標價：對稱測幅滿足 (突破點 + 區間高度)
            short_target = current_price + (current_price - low_20d)
            
            # --- B. 長線邏輯：價值估值 ---
            # 判斷均線是否呈現多頭排列
            is_long_trend = df['5MA'].iloc[-1] > df['20MA'].iloc[-1] > df['60MA'].iloc[-1]
            
            # 長線目標價優化公式：
            # 我們使用 Forward PE (預估本益比)，若無則給予 20 倍(台股強勢股平均)
            eps = info.get('trailingEps', 0)
            if eps <= 0: # 如果沒抓到EPS，用現價的 1.3 倍作為樂觀預期
                long_target = current_price * 1.3
            else:
                # 調高 PE 權重：使用預期本益比或預設 22 倍
                pe_ratio = info.get('forwardPE', 22) 
                if pe_ratio < 15: pe_ratio = 20 # 修正過低的估值
                long_target = eps * pe_ratio * 1.1 # 額外加上 10% 的成長溢價
            
            results.append({
                "代碼": symbol.replace(".TW", ""),
                "股名": info.get('shortName', symbol),
                "現價": round(current_price, 2),
                "成交張數": int(last_vol),
                "短線訊號": "🔥 強力突破" if is_breakout else "整理中",
                "短線預期價": round(short_target, 2),
                "長線趨勢": "📈 多頭排列" if is_long_trend else "趨勢不明",
                "長線預期價": round(long_target, 2)
            })
        except Exception:
            pass
        my_bar.progress((i + 1) / len(taiwan_stocks), text=progress_text)
    
    my_bar.empty()
    return pd.DataFrame(results)

# --- 網頁前端顯示 ---
if st.button("🚀 開始掃描強勢標的", use_container_width=True):
    data = run_stock_analysis()
    
    if not data.empty:
        # 分成左右兩欄顯示
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔥 短線爆發名單")
            short_hits = data[data['短線訊號'] == "🔥 強力突破"]
            if not short_hits.empty:
                st.dataframe(short_hits[['代碼', '股名', '現價', '短線預期價', '成交張數']], hide_index=True)
            else:
                st.write("目前無符合強力突破標的")
                
        with col2:
            st.subheader("🛡️ 長線穩定名單")
            long_hits = data[data['長線趨勢'] == "📈 多頭排列"]
            if not long_hits.empty:
                st.dataframe(long_hits[['代碼', '股名', '現價', '長線預期價', '成交張數']], hide_index=True)
            else:
                st.write("目前無符合多頭排列標的")
        
        st.success("掃描完成！")
    else:
        st.warning("符合成交量門檻的股票目前無顯著訊號。")

st.divider()
st.write("💡 **投資小百科**")
st.caption("1. 短線目標價採用「型態對稱原理」，當股價突破平台，預期會有等距的漲幅。")
st.caption("2. 長線目標價結合「每股盈餘(EPS)」與「成長本益比」，反映公司未來一年的內在價值。")
st.caption("3. 注意：若長線預期價仍低於現價，通常代表該股目前處於歷史高點，建議等回踩均線再行佈局。")
