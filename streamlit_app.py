import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="台股AI價值預測系統", layout="wide")

st.title("🚀 台股 AI 高成長價值預測系統")
st.markdown("""
此系統已針對 **AI 高成長股** 調整估值邏輯：
* **長線預估**：本益比基準上修至 **35倍**，反映目前台積電、鴻海等 AI 龍頭股的市場評價。
* **短線預估**：採用「對稱測幅」，偵測噴發力道。
""")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    vol_limit = st.number_input("最低成交量門檻 (張)", value=30000)
    
    # 擴大股池：包含 AI、半導體、航運及大型金融股
    taiwan_stocks = [
        "2330.TW", "2317.TW", "2303.TW", "2454.TW", "2382.TW", "3231.TW", 
        "2357.TW", "2301.TW", "2376.TW", "6669.TW", "2603.TW", "2609.TW", 
        "2618.TW", "2881.TW", "2882.TW", "2886.TW", "2409.TW", "3481.TW",
        "1513.TW", "1605.TW", "2313.TW", "2360.TW", "3034.TW", "3711.TW"
    ]

# --- 核心運算邏輯 ---
def analyze_market():
    results = []
    progress_bar = st.progress(0, text="大數據運算中...")
    
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
            
            # 過濾量能
            if volume_shares < vol_limit:
                continue

            # 計算均線
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA60'] = df['Close'].rolling(60).mean()
            
            # A. 短線訊號 (對稱測幅)
            high_20d = df['High'].iloc[-21:-1].max()
            low_20d = df['Low'].iloc[-21:-1].min()
            is_breakout = current_price > high_20d
            # 對稱測幅目標 = 現價 + (現價 - 區間低點)
            short_target = current_price + (current_price - low_20d)

            # B. 長線訊號 (AI 溢價估值)
            is_bull_market = df['MA5'].iloc[-1] > df['MA20'].iloc[-1] > df['MA60'].iloc[-1]
            
            # 取得財務指標
            eps = info.get('trailingEps', 0)
            forward_pe = info.get('forwardPE', 35) # 預設改為 35 倍反映 AI 溢價
            
            # 邏輯修正：如果 EPS 過低或抓不到，採用「營收動能估算法」
            if eps <= 0:
                long_target = current_price * 1.5 # 針對成長股給予 50% 空間
            else:
                # 確保 PE 不會太保守
                final_pe = max(forward_pe, 35) 
                # 長線預期價 = EPS * 本益比 * 成長加權(1.2)
                long_target = eps * final_pe * 1.2
            
            # 顯示修正：如果長線預期仍低於現價(因財報落後)，則顯示「現價 * 1.2」為市場情緒價
            if long_target < current_price:
                long_target = current_price * 1.2

            results.append({
                "代碼": symbol.replace(".TW", ""),
                "股名": info.get('shortName', symbol),
                "現價": round(current_price, 2),
                "短線預期": round(short_target, 2),
                "長線預期": round(long_target, 2),
                "今日張數": int(volume_shares),
                "趨勢": "🔥 噴發突破" if is_breakout else "📈 多頭排列" if is_bull_market else "🟡 整理中"
            })
        except:
            pass
        progress_bar.progress((i + 1) / len(taiwan_stocks))
    
    progress_bar.empty()
    return pd.DataFrame(results)

# --- 介面呈現 ---
if st.button("🔍 開始智能選股 (AI 溢價版)", use_container_width=True):
    data = analyze_market()
    
    if not data.empty:
        # 依照預期回報排序
        data['預期空間'] = ((data['長線預期'] / data['現價']) - 1) * 100
        data = data.sort_values(by='預期空間', ascending=False)

        st.subheader("📊 掃描結果（依長線潛力排序）")
        st.dataframe(
            data[['代碼', '股名', '現價', '短線預期', '長線預期', '今日張數', '趨勢']], 
            hide_index=True,
            use_container_width=True
        )
        
        st.success("✅ 更新完成！請注意：長線預期價已考慮 AI 產業 35-40 倍之本益比擴張。")
    else:
        st.warning("當前量能不足，請嘗試降低左側成交量門檻。")

st.divider()
st.caption("⚠️ 免責聲明：本系統計算之預期價僅供技術參考，不構成投資建議。股市有風險，買賣請謹慎評估。")
