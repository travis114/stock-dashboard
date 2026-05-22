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
SIG_BADGE = {"买点": "🔥 买点", "观察": "👀 观察", "—": "· —"}

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
            st.markdown(f'<div class="verdict {cls}">{TIER_BADGE[r["tier"]]} &nbsp; {r["ticker"]} &nbsp; 适配度 {r["score"]}/100 &nbsp;|&nbsp; 当前信号 {SIG_BADGE[r["signal"]]}</div>', unsafe_allow_html=True)
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
                st.write("**逐项体检**")
                for x in r["reasons"]:
                    st.write("·", x)
                if r["signal"] == "买点":
                    st.success("🔥 触发买点(深基反弹+放量点火):base期RSI曾深跌(≤37)、价未追高、放量上穿60、且站稳中轨2根。样本外验证胜率约57%、20日中位+1.5%。配 −2×ATR止损、R:R≥2、跌破MA10离场。")
                elif r["signal"] == "观察":
                    st.info("👀 深基放量点火刚发生,正等「站稳中轨2根」确认;确认后转买点。")
                else:
                    st.caption("当前无买点信号(非顺势或未突破上轨)。")
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
    cga, cgb, cgc, cgd = st.columns([1, 1, 1, 1.4])
    only_pref = cga.checkbox("只看「优选」", value=True)
    only_sig = cgb.checkbox("只看有信号", value=False, help="买点 / 观察")
    minsc = cgc.slider("最低适配度", 0, 100, 60)
    st.caption(f"待扫描 {len(tickers)} 只 · 约需 2–5 分钟(8 线程并发,结果缓存到本次会话)")
    if st.button("开始扫描", type="primary", disabled=(len(tickers) == 0)):
        prog = st.progress(0.0, text="抓取行情中…")
        def cb(d, n): prog.progress(min(d/n, 1.0), text=f"已扫描 {d}/{n}")
        st.session_state["scan_res"] = sc.scan_universe(tickers, params(), max_workers=8, progress=cb)
        prog.empty()
    res = st.session_state.get("scan_res")
    if res:
        raw_df = pd.DataFrame(res)
        n_buy = int((raw_df["signal"] == "买点").sum()); n_watch = int((raw_df["signal"] == "观察").sum())
        n_pref = int((raw_df["tier"] == "优选").sum())
        k = st.columns(4)
        k[0].metric("有效标的", len(raw_df))
        k[1].metric("🟢 优选", n_pref)
        k[2].metric("🔥 今日买点", n_buy)
        k[3].metric("👀 观察", n_watch)
        sdf = raw_df.copy()
        sdf["分层"] = sdf["tier"].map(lambda x: TIER_BADGE.get(x, x))
        sdf["信号"] = sdf["signal"].map(lambda x: SIG_BADGE.get(x, x))
        sdf = sdf.rename(columns={"ticker":"标的","score":"适配度","trend":"趋势性","ret":"近1年涨跌","medp":"中位价$","dolvol":"日成交额(M)"})
        view = sdf
        if only_pref: view = view[view["tier"] == "优选"]
        if only_sig: view = view[view["signal"].isin(["买点", "观察"])]
        view = view[view["适配度"] >= minsc].sort_values(["signal", "适配度"], ascending=[True, False])
        st.dataframe(view[["标的","适配度","分层","信号","中位价$","日成交额(M)","趋势性","近1年涨跌"]],
                     width='stretch', height=520, hide_index=True,
                     column_config={"适配度": SCORE_COL, "中位价$": PRICE_COL, "日成交额(M)": VOL_COL,
                                    "趋势性": st.column_config.NumberColumn(format="%.2f"),
                                    "近1年涨跌": st.column_config.NumberColumn(format="%+.0f%%")})
        st.download_button("⬇ 下载完整扫描结果 CSV", raw_df.to_csv(index=False).encode("utf-8-sig"),
                           "scan_results.csv", "text/csv")
    else:
        st.info("点「开始扫描」后,这里按信号(买点优先)+适配度排序列出候选。🔥买点 = 近7日内「深基反弹+放量点火」且站稳2根(样本外验证);👀观察 = 刚点火、待2根确认。")

# ---------- Tab3 说明 ----------
with tab3:
    st.markdown("""
### 这套工具是怎么"蒸馏"出来的
对你 2021–2026 的全部个股成交做复盘,提炼出**决定赚不赚的关键不在择时、而在选对标的**,并把规律固化成评分参数(`norm_params.json`)。本工具只做**向前看**:给任意股票打分、扫全市场找候选,不再回看你的历史持仓。

### 选股准则(三条硬标准)
| 维度 | 标准 | 依据 |
|---|---|---|
| **价格** | ≥ \\$10(优选 ≥ \\$30) | 策略净盈亏随价格单调上升:<\\$3 几乎不赚,>\\$100 平均每只 **+\\$289** |
| **流动性** | 日成交额 ≥ \\$20M | 盈利股中位 \\$34M vs 亏损股 \\$22M |
| **趋势性** | MA10>MA30 占比 ≥ 45%、近1年正动量 | <40% 的股票策略 −\\$24/只;0.4–0.8 才赚 |

**适配度评分** = 趋势性35% + 价格30% + 流动性20% + 相对强度15% → 0–100。验证:评分四分位下策略每股净盈亏从 Q1 **−\\$66** 单调升到 Q4 **+\\$304**。

### 当前信号(择时)
- **🔥 买点(深基反弹+放量点火,样本外验证)**:近7日内 RSI 上穿60,且 base期RSI曾≤37(深超卖)+ 价≤52周高97%(未追高)+ 前期回调≥11% + 放量≥20日均量 + 上穿后站稳中轨2根。2021–23训练/2024–26样本外均跑赢基线,胜率约57%、20日中位约+1.5%。
- **👀 观察**:上述点火刚发生、「站稳2根」尚未确认。
- 注:经验证「W底清晰度/布林收窄/横盘紧度」不加 edge,真正有效的是 **深超卖 + 未追高 + 回调 + 放量**;故未硬性要求 W 形。
- 进场后:−2×ATR 止损、R:R≥2、跌破 MA10 离场、每笔 1% 权益风险。

### 一句话
**只做"贵、活、强"的趋势龙头,放弃低价微盘仙股。** 这正是从你的成交里提炼出来、且能弥补你过去短板的核心。

---
⚠ **免责声明**:基于历史成交复盘归纳,**非投资建议**,历史表现(含回测)不代表未来,存在过拟合风险。交易决策请自行判断并控制风险。
""")
