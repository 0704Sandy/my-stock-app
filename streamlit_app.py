import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime

# --- 1. 核心設定 ---
# 請在此輸入你的 Gemini API Key
GOOGLE_API_KEY = "AIzaSyAJn-wmeP1jAB8eyScT4Ei2Hie1Dx-8yHU" 
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="台股AI導航與新聞預測", layout="wide")

st.title("🛡️ 台股 AI 飆股導航與全自動新聞預測系統")

# --- 2. AI 財經新聞整理與分析功能 ---
def get_ai_market_intelligence():
    prompt = """
    你是專業的財經分析師。請整理今日（2026年1月）最新的全球財經新聞、美股趨勢與台股消息：
    1. 總結 3 條最重要的世界新聞。
    2. 分析哪些題材（例如 AI、半導體、航運等）目前被看好。
    3. 分析哪些新聞可能導致哪些股票或板塊下跌（風險提示）。
    4. 推薦 3-5 個今日最值得關注的台股題材關鍵字。
    請用繁體中文回答，內容要精簡，適合手機閱讀。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ AI 新聞連線暫時失敗，請檢查 API Key 是否正確。"

# --- 3. 數據運算邏輯 ---
def run_full_scan(vol_limit, stock_list):
    results = []
    progress_bar = st.progress(0, text="大數據與 AI 運算中...")
    
    for i, symbol in enumerate(stock_list):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="180d")
            if df.empty or len(df) < 60: continue
            
            info = ticker.info
            current_p = df['Close'].iloc[-1]
            vol_shares = df['Volume'].iloc[-1] / 1000
            
            if vol_shares < vol_limit: continue
            
            # K線指標
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            ma60 = df['Close'].rolling(60).mean().iloc[-1]
            high_20 = df['High'].iloc[-21:-1].max()
            low_20 = df['Low'].iloc[-21:-1].min()
            
            # 飆股 K 線判斷 (突破 20 日高點 + 均線多頭)
            is_surging = (current_p >= high_20) and (current_p > ma5 > ma20)
            
            # 預期價計算 (AI 高成長溢價)
            short_t = current_p + (current_p - low_20)
            eps = info.get('trailingEps', 0)
            long_t = eps * 35 * 1.15 if eps > 0 else current_p * 1.3
            if long_t < current_p: long_t = current_p * 1.25 # 保底溢價

            # 中文名映射
            name_map = {"2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2382": "廣達", "2603": "長榮", "3231": "緯創", "2303": "聯電"}
            display_name = name_map.get(symbol.split(".")[0], info.get('shortName', symbol))

            results.append({
                "代碼": symbol.replace(".TW", ""),
                "名稱": display_name,
                "現價": round(current_p, 1),
                "短線預期": round(short_t, 1),
                "長線預估": round(long_t, 1),
                "今日張數": int(vol_shares),
                "狀態": "🚀 推薦飆股" if is_surging else "多頭排列" if (ma5 > ma20) else "整理中"
            })
        except: pass
        progress_bar.progress((i + 1) / len(stock_list))
    
    progress_bar.empty()
    return pd.DataFrame(results)

# --- 4. 網頁介面展示 ---
# 每日新聞看板
st.subheader("🌐 AI 每日財經快訊與影響預測")
with st.expander("📌 點擊展開今日 AI 深度新聞分析", expanded=True):
    if st.button("🔄 更新 AI 新聞分析"):
        ai_news = get_ai_market_intelligence()
        st.write(ai_news)
    else:
        st.write("點擊按鈕獲取今日 AI 財經解讀。")

st.divider()

# 側邊欄設定
with st.sidebar:
    st.header("⚙️ 篩選設定")
    vol_input = st.number_input("最低成交量門檻 (張)", value=20000)
    stock_pool = [
        "2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2301.TW", 
        "2357.TW", "6669.TW", "2603.TW", "2609.TW", "2618.TW", "2881.TW", 
        "2882.TW", "1513.TW", "1605.TW", "3034.TW", "2376.TW", "2303.TW"
    ]

# 執行選股
if st.button("🔍 執行全自動市場掃描", use_container_width=True):
    final_data = run_full_scan(vol_input, stock_pool)
    
    if not final_data.empty:
        # 飆股專區
        st.subheader("🔥 本日推薦短期飆股 (帶量突破型)")
        surging_df = final_data[final_data['狀態'] == "🚀 推薦飆股"]
        if not surging_df.empty:
            st.success(f"發現 {len(surging_df)} 檔爆發標的！")
            st.dataframe(surging_df, hide_index=True, use_container_width=True)
        else:
            st.info("今日無標的符合飆股爆發型態。")
            
        # 完整列表
        st.subheader("📊 監控池完整分析預測")
        st.dataframe(final_data.sort_values(by="今日張數", ascending=False), hide_index=True, use_container_width=True)
    else:
        st.warning("查無符合門檻之標的。")

st.divider()
st.caption("💡 提示：AI 新聞分析會根據當前世界動態，自動判斷『受惠標的』與『受害標的』。")
