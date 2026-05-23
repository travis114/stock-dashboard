#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地选股适配度 Dashboard (Streamlit) —— 由你的历史成交"蒸馏"出的前瞻选股工具。
运行: pip install streamlit pandas numpy ; streamlit run dashboard.py
同目录需: selection_core.py, norm_params.json, universe.txt
实时联网抓 Yahoo。⚠ 非投资建议。"""
import os, re
import numpy as np, pandas as pd
import streamlit as st
import selection_core as sc

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="选股适配度 Dashboard", page_icon="📈", layout="wide")

st.markdown("""<style>
[data-testid="stMetric"]{background:#f7f9fc;border:1px solid #e6ebf2;border-radius:12px;padding:10px 14px;}
[data-testid="stMetricLabel"]{color:#5b6b7f;font-size:13px;}
[data-testid="stMetricValue"]{color:#1f3a5f;font-weight:800;}
[data-testid="stMetricValue"] *{color:#1f3a5f;}
.hero{background:linear-gradient(95deg,#1f3a5f,#2e86c1);color:#fff;padding:16px 20px;border-radius:14px;margin-bottom:14px;}
.hero h1{margin:0;font-size:25px;font-weight:800;}
.hero p{margin:5px 0 0;opacity:.92;font-size:13px;}
.stTabs [data-baseweb="tab"]{font-size:15px;font-weight:600;}
.verdict{padding:14px 18px;border-radius:12px;font-size:16px;font-weight:700;margin:6px 0;}
.v-buy{background:#eafaf0;border:1px solid #1e8449;color:#1e8449;}
.v-mid{background:#fff7e6;border:1px solid #e67e22;color:#b9650f;}
.v-avoid{background:#fdecec;border:1px solid #c0392b;color:#c0392b;}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><h1>📈 个股选股适配度 Dashboard</h1>
<p>把你 2021–2026 的成交"蒸馏"成前瞻选股工具 · 准则:<b>贵 · 活 · 强</b>(高价 / 高流动性 / 强趋势)· 实时信号:深基反弹+放量点火(经样本外验证) · ⚠ 非投资建议</p></div>""", unsafe_allow_html=True)

TIER_BADGE = {"优选": "🟢 优选", "中性": "🟡 中性", "回避": "🔴 回避"}
SIG_BADGE = {"买点": "🔥 买点(经典)", "回插买点": "⚡ 回插买点", "观察": "👀 观察", "—": "· —"}

@st.cache_data(show_spinner=False)
def params(): return sc.load_params()

@st.cache_data(ttl=900, show_spinner=False)
def evaluate_cached(tk): return sc.evaluate(tk, params())

@st.cache_data(show_spinner=False)
def load_universe():
    p = os.path.join(HERE, "universe.txt")
    return [l.strip().upper() for l in open(p)] if os.path.exists(p) else []

SCORE_COL = st.column_config.ProgressColumn("适配度", min_value=0, max_value=100, format="%d")
PRICE_COL = st.column_config.NumberColumn("中位价$", format="$%.1f")
VOL_COL = st.column_config.NumberColumn("日成交额(M)", format="$%.0fM")

tab1, tab_scan, tab3 = st.tabs(["🎯 单只评分器", "🔍 批量扫描(全市场)", "ℹ️ 说明"])

# ---------- Tab1 ----------
with tab1:
    c1, c2 = st.columns([1, 3])
    with c1:
        tk = st.text_input("股票代码(美股)", "NVDA").strip().upper()
        go = st.button("拉行情并打分", type="primary", width='stretch')
        st.caption("例:NVDA / AAPL / TSLA / COIN")
    if go and tk:
        try:
            with st.spinner(f"抓取 {tk} 行情中…"):
                r = evaluate_cached(tk)
            a = r["attrs"]
            cls = {"优选":"v-buy","中性":"v-mid","回避":"v-avoid"}[r["tier"]]
            tv = r.get("trend", {}).get("verdict", "—")
            tv_txt = {"强势突破":"🚀 强势突破", "趋势买点":"✅ 趋势买点", "—":"· 不符合趋势入场"}.get(tv, tv)
            st.markdown(f'<div class="verdict {cls}">{TIER_BADGE[r["tier"]]} &nbsp; {r["ticker"]} &nbsp; 适配度 {r["score"]}/100 &nbsp;|&nbsp; {tv_txt}</div>', unsafe_allow_html=True)
            if r.get("is_lev"):
                st.error("⛔ 红线:这是杠杆/反向 ETF —— 你历史在这类品种上净亏 −$15.7k,不做。")
            m = st.columns(5)
            m[0].metric("中位价", f"${a['medp']:,.2f}")
            m[1].metric("日成交额", f"${a['dolvol']:,.0f}M")
            m[2].metric("趋势性", f"{a['trend']*100:.0f}%")
            m[3].metric("近1年涨跌", f"{a['ret']*100:+.0f}%")
            m[4].metric("年化波动", f"{a['vol']*100:.0f}%")
            cL, cR = st.columns([3, 2])
            with cL:
                px = r["px"]
                dfp = pd.DataFrame({"收盘": px["close"]}, index=pd.to_datetime(px["dates"]))
                dfp["MA10"] = dfp["收盘"].rolling(10).mean(); dfp["MA30"] = dfp["收盘"].rolling(30).mean()
                m20 = dfp["收盘"].rolling(20).mean(); sd = dfp["收盘"].rolling(20).std(ddof=0)
                dfp["布林上轨"] = m20 + 2*sd; dfp["布林下轨"] = m20 - 2*sd
                st.line_chart(dfp.tail(180), height=300)
            with cR:
                tr = r.get("trend", {})
                st.write("**趋势入场清单(你赢家的画像)**")
                for label, ok in tr.get("checks", []):
                    st.write(("✅ " if ok else "❌ ") + label)
                if tv in ("趋势买点", "强势突破") and tr.get("stop") is not None:
                    st.success(f"进场参考 · 止损 ${tr['stop']}(−2×ATR) · 目标 ${tr['target']}(R:R≥2) · 跌破MA10离场 · 最长持有~15天 · 每笔1%权益风险")
                elif not r.get("is_lev"):
                    st.caption("当前不满足趋势入场画像(需 金叉 + 站上MA10/MA30 + RSI 58–72)。逆势/弱势不进。")
                st.markdown("---")
                st.write("**选股体检(贵·活·强)**")
                for x in r["reasons"]:
                    st.write("·", x)
                st.caption("另:深基反弹信号 = " + SIG_BADGE.get(r["signal"], r["signal"]) + "(仅参考;样本外≈买入持有,别当圣杯)")
        except Exception as e:
            st.error(f"出错:{e}(请检查代码或联网)")

# ---------- Tab 批量扫描 ----------
with tab_scan:
    src = st.radio("股票池", ["内置:S&P1500 + 你的优选 + ADR(约 1557 只)", "自定义:粘贴代码"], horizontal=False)
    if src.startswith("自定义"):
        raw = st.text_area("粘贴代码(空格 / 逗号 / 换行分隔)", "NVDA AAPL MSFT META GOOGL AMZN TSLA AMD AVGO NFLX")
        tickers = [x for x in re.split(r"[\s,;]+", raw.upper()) if x]
    else:
        tickers = load_universe()
    cga, cgb = st.columns([1, 1.6])
    only_trend = cga.checkbox("只看趋势买点", value=True, help="🚀强势突破 / ✅趋势买点(金叉+站上MA10/30+RSI 58–72)")
    minsc = cgb.slider("最低适配度", 0, 100, 60)
    st.caption(f"待扫描 {len(tickers)} 只 · 杠杆/反向 ETF 已自动剔除(红线)· 约 2–5 分钟(8 线程,结果缓存本次会话)")
    if st.button("开始扫描", type="primary", disabled=(len(tickers) == 0)):
        prog = st.progress(0.0, text="抓取行情中…")
        def cb(d, n): prog.progress(min(d/n, 1.0), text=f"已扫描 {d}/{n}")
        st.session_state["scan_res"] = sc.scan_universe(tickers, params(), max_workers=8, progress=cb)
        prog.empty()
    res = st.session_state.get("scan_res")
    if res:
        raw_df = pd.DataFrame(res)
        if "tsig" not in raw_df.columns: raw_df["tsig"] = "—"
        TBADGE = {"强势突破": "🚀 强势突破", "趋势买点": "✅ 趋势买点", "—": "· —"}
        n_trend = int(raw_df["tsig"].isin(["趋势买点", "强势突破"]).sum())
        n_break = int((raw_df["tsig"] == "强势突破").sum())
        k = st.columns(3)
        k[0].metric("有效标的", len(raw_df))
        k[1].metric("✅ 趋势买点", n_trend)
        k[2].metric("🚀 强势突破", n_break)
        sdf = raw_df.copy()
        sdf["分层"] = sdf["tier"].map(lambda x: TIER_BADGE.get(x, x))
        sdf["趋势信号"] = sdf["tsig"].map(lambda x: TBADGE.get(x, x))
        sdf = sdf.rename(columns={"ticker":"标的","score":"适配度","trend":"趋势性","ret":"近1年涨跌","medp":"中位价$","dolvol":"日成交额(M)"})
        sdf["_pri"] = sdf["tsig"].map({"强势突破": 0, "趋势买点": 1}).fillna(2)
        view = sdf
        if only_trend: view = view[view["tsig"].isin(["趋势买点", "强势突破"])]
        view = view[view["适配度"] >= minsc].sort_values(["_pri", "适配度"], ascending=[True, False])
        st.dataframe(view[["标的","适配度","分层","趋势信号","中位价$","日成交额(M)","趋势性","近1年涨跌"]],
                     width='stretch', height=520, hide_index=True,
                     column_config={"适配度": SCORE_COL, "中位价$": PRICE_COL, "日成交额(M)": VOL_COL,
                                    "趋势性": st.column_config.NumberColumn(format="%.2f"),
                                    "近1年涨跌": st.column_config.NumberColumn(format="%+.0f%%")})
        st.download_button("⬇ 下载完整扫描结果 CSV", raw_df.to_csv(index=False).encode("utf-8-sig"),
                           "scan_results.csv", "text/csv")
    else:
        st.info("点「开始扫描」后,这里按『趋势信号』排序列出候选(杠杆/反向 ETF 已自动剔除)。✅趋势买点 = 金叉 + 站上 MA10/MA30 + RSI 58–72;🚀强势突破 = 再叠加突破布林上轨。这是你赢家的入场画像——配纪律执行,不是稳赢的圣杯。")

# ---------- Tab3 说明 ----------
with tab3:
    st.markdown("""
### 这套工具在帮你做什么(诚实版)
基于你 2021–2026 全部成交的复盘 + 全市场 1500+ 只的样本外检验,结论很明确:**你赚不赚,关键不在某个神触发,而在(1)选对趋势龙头、(2)堵住自己几个亏钱的漏洞。** 本工具就是把这两件事固化下来。

### 你的入场画像(来自你赢家的真实统计)
盈利单的入场长相:**金叉(MA10>MA30)+ 站上 MA10/MA30 + RSI 约 58–70**,常伴 **突破布林上轨**(赢家里这状态胜率最高 57%)。RSI 40–60 是你的死亡区(胜率 42–44%);逆势(死叉/跌破MA30)长期净亏。
- **✅ 趋势买点** = 金叉 + 站上 MA10/MA30 + RSI 58–72
- **🚀 强势突破** = 上面再 + 突破布林上轨

### 选股(贵·活·强)
价格 ≥ \\$10(优选 ≥ \\$30)、日成交额 ≥ \\$20M、趋势性(MA10>MA30 占比)≥ 45% 且近1年正动量。低价/低流动性仙股长期净亏。

### 风控(进场即设 —— 这才是真正改变结果的部分)
−2×ATR 止损 · R:R ≥ 2 · 跌破 MA10 离场 · **最长持有 ~15 天**(你扛过 30 天的历史是 31% 胜率、大亏)· 每笔 1% 权益风险。

### 🚫 红线(你历史亏损的根因,逐条对应)
- **不碰杠杆/反向 ETF**(SQQQ/SOXS/TQQQ…)—— 这一类历史净亏 **−\\$15.7k**,扫描已自动剔除
- 不逆势接刀(死叉 / RSI 30–40 / 跌破 MA30)
- 不扛亏损单(赢家平均拿 7 天、输家拖 14 天)
- 不在 RSI 40–60 区进场

### ⚠ 必须诚实告诉你的
全市场样本外检验显示:**这个择时信号本身,几乎不跑赢"随便哪天买入持有"(超额约 +0.3pp/20天,在噪声内)。** 它真正的价值**不是 alpha,而是纪律**——帮你只做对的形态、避开上面那 4 条红线。深基反弹版的"买点"也一样(仅作参考,别当圣杯)。

---
⚠ **免责声明**:基于历史复盘归纳,**非投资建议**,历史表现(含回测)不代表未来,存在过拟合风险。交易决策请自行判断并控制风险。
""")
