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
try:
    import plotly.graph_objects as pgo
    from plotly.subplots import make_subplots as _mksub
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

def make_chart(px, days, bbk, tk):
    """专业K线: 蜡烛 + MA10/30/50 + 布林带(中轨虚线,上下轨阴影) + 绿三角『回调后RSI上穿60』信号 + RSI(14)副图。"""
    dts = pd.to_datetime(px["dates"]); c = np.asarray(px["close"], float)
    o = px["open"]; h = px["high"]; l = px["low"]
    cser = pd.Series(c, index=dts)
    ma10 = cser.rolling(10).mean(); ma20 = cser.rolling(20).mean(); ma30 = cser.rolling(30).mean(); ma50 = cser.rolling(50).mean()
    sd = cser.rolling(20).std(ddof=0); ub = ma20 + bbk*sd; lb = ma20 - bbk*sd
    rsi = sc._rsi(c, 14); N = int(min(days, len(c))); sl = slice(-N, None); start = len(c) - N
    marks = [k for k in range(20, len(c)) if k >= start and rsi[k] > 60 and rsi[k-1] <= 60 and float(np.nanmin(rsi[k-15:k])) <= 52]
    fig = _mksub(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.74, 0.26])
    x = dts[sl]
    fig.add_trace(pgo.Scatter(x=x, y=ub.values[sl], line=dict(color="#5c6675", width=1), name="upper"), row=1, col=1)
    fig.add_trace(pgo.Scatter(x=x, y=lb.values[sl], line=dict(color="#5c6675", width=1), fill="tonexty", fillcolor="rgba(125,138,156,0.10)", name="lower"), row=1, col=1)
    fig.add_trace(pgo.Scatter(x=x, y=ma20.values[sl], line=dict(color="#e8a838", width=1.3, dash="dash"), name="mid"), row=1, col=1)
    fig.add_trace(pgo.Candlestick(x=x, open=o[-N:], high=h[-N:], low=l[-N:], close=px["close"][-N:], name=tk,
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350", increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350"), row=1, col=1)
    for nm, ma, col in [("MA10", ma10, "#5b9bd5"), ("MA30", ma30, "#9b8cff"), ("MA50", ma50, "#6b7787")]:
        fig.add_trace(pgo.Scatter(x=x, y=ma.values[sl], line=dict(color=col, width=1), name=nm), row=1, col=1)
    if marks:
        fig.add_trace(pgo.Scatter(x=[dts[k] for k in marks], y=[l[k]*0.985 for k in marks], mode="markers",
            marker=dict(symbol="triangle-up", size=11, color="#26d07c"), name="signal"), row=1, col=1)
    fig.add_trace(pgo.Scatter(x=x, y=rsi[sl], line=dict(color="#5b9bd5", width=1), name="RSI"), row=2, col=1)
    fig.add_hline(y=60, line=dict(color="#e8a838", width=1, dash="dot"), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="#ef5350", width=1, dash="dot"), row=2, col=1)
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0e14", plot_bgcolor="#0a0e14", height=520,
        margin=dict(l=6, r=6, t=26, b=6), xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10)), font=dict(color="#c9d3df", size=11),
        title=dict(text=f"{tk} — price + BB(20,{bbk}σ) + RSI(14)", font=dict(size=13, color="#c9d3df")))
    fig.update_xaxes(gridcolor="#1a212c"); fig.update_yaxes(gridcolor="#1a212c")
    return fig

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="选股适配度 Dashboard", page_icon="📈", layout="wide")

st.markdown("""<style>
.stApp{background:#0a0e14;}
#MainMenu,header[data-testid="stHeader"],footer,[data-testid="stToolbar"]{display:none!important;}
.block-container{padding-top:1rem;max-width:1520px;}
[data-testid="stMetric"]{background:#11161f;border:1px solid #1e2630;border-left:3px solid #e8a838;border-radius:4px;padding:10px 14px;}
[data-testid="stMetricLabel"]{color:#7d8a9c;font-size:11px;letter-spacing:.08em;text-transform:uppercase;}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{color:#e8a838;font-weight:700;font-variant-numeric:tabular-nums;}
.term-hd{border-bottom:1px solid #1e2630;padding:2px 2px 12px;margin-bottom:14px;}
.term-hd .ttl{color:#e6edf5;font-size:20px;font-weight:700;letter-spacing:.04em;}
.term-hd .ttl b{color:#e8a838;}
.term-hd .tag{color:#0a0e14;background:#e8a838;font-size:10px;font-weight:800;padding:2px 8px;border-radius:3px;letter-spacing:.12em;margin-left:10px;}
.term-hd .sub{color:#7d8a9c;font-size:12px;margin-top:6px;}
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid #1e2630;}
.stTabs [data-baseweb="tab"]{font-size:13px;font-weight:600;color:#7d8a9c;letter-spacing:.04em;}
.stTabs [aria-selected="true"]{color:#e8a838!important;}
.stButton>button{background:#e8a838;color:#0a0e14;border:0;font-weight:700;border-radius:4px;letter-spacing:.05em;}
.stButton>button:hover{background:#f2c25b;color:#000;}
.verdict{padding:12px 16px;border-radius:4px;font-size:15px;font-weight:700;margin:8px 0;background:#11161f;border:1px solid #1e2630;font-variant-numeric:tabular-nums;}
.v-buy{border-left:4px solid #26a69a;color:#26a69a;}
.v-mid{border-left:4px solid #e8a838;color:#e8a838;}
.v-avoid{border-left:4px solid #ef5350;color:#ef5350;}
[data-testid="stDataFrame"]{border:1px solid #1e2630;border-radius:4px;}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="term-hd">
<span class="ttl">📈 EQUITY <b>MOMENTUM</b> TERMINAL<span class="tag">三周期共振</span></span>
<div class="sub">MONTHLY 强 · WEEKLY 顺 · DAILY 均线多头 + 当日突破放量 · 杠杆/反向 ETF 已剔除 · ⚠ 非投资建议,历史不代表未来</div>
</div>""", unsafe_allow_html=True)

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

tab_daily, tab1, tab_scan, tab3 = st.tabs(["📍 今日关注", "🎯 单只评分器", "🔍 批量扫描(全市场)", "ℹ️ 说明"])

# ---------- Tab 今日关注 ----------
with tab_daily:
    st.markdown("**只列『三周期共振』(月线强 + 周线顺·周RSI≤70 + 日线均线多头)且当天『回调后 RSI 首次上穿 60』+ 放量的龙头(早入场、进在 RSI 60–65 不追高),按热度排序。其余一律不列 —— 每天只看这一屏。**")
    dtk = load_universe()
    st.caption(f"扫描池 {len(dtk)} 只 · 杠杆/反向 ETF 已剔除 · 约 2–5 分钟")
    if st.button("🔄 扫描今日关注", type="primary", disabled=(len(dtk) == 0)):
        prog = st.progress(0.0, text="抓取行情中…")
        def cbd(d, n): prog.progress(min(d/n, 1.0), text=f"已扫描 {d}/{n}")
        st.session_state["daily_res"] = sc.scan_daily(dtk, max_workers=8, progress=cbd)
        prog.empty()
    dres = st.session_state.get("daily_res")
    if dres is not None:
        if len(dres) == 0:
            st.info("今天没有符合条件的新触发 —— 空仓等待也是一种纪律。")
        else:
            st.metric("📍 今日触发", len(dres))
            ddf = pd.DataFrame(dres).head(15).rename(columns={
                "ticker":"代码","heat":"热度","price":"价$","rsi":"日RSI","wrsi":"周RSI","mrsi":"月RSI","vsurge":"放量x",
                "dist52":"离52高","trig":"今日触发","stop":"止损$","target":"目标$"})
            st.dataframe(ddf[["代码","热度","价$","日RSI","周RSI","月RSI","放量x","离52高","今日触发","止损$","目标$"]],
                         width='stretch', hide_index=True,
                         column_config={"热度": st.column_config.ProgressColumn("热度", min_value=0, max_value=100, format="%d"),
                                        "价$": st.column_config.NumberColumn(format="$%.1f"),
                                        "止损$": st.column_config.NumberColumn(format="$%.1f"),
                                        "目标$": st.column_config.NumberColumn(format="$%.1f")})
            st.caption("热度 = 相对强度60% + 放量40%。进场按『止损$』(−2×ATR)、R:R≥2、跌破MA10离场、每笔1%风险。⚠ 非投资建议。")
    else:
        st.info("点「🔄 扫描今日关注」,给你当天最多 ~15 只刚触发的票,其余不用看。")

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
            cc1, cc2 = st.columns([1, 1])
            days = cc1.slider("显示天数", 60, 400, 180, 20)
            bbk = cc2.slider("布林带 σ", 1.0, 3.0, 2.0, 0.5)
            px = r["px"]
            if HAS_PLOTLY:
                st.plotly_chart(make_chart(px, days, bbk, r["ticker"]), use_container_width=True)
            else:
                dfp = pd.DataFrame({"收盘": px["close"]}, index=pd.to_datetime(px["dates"]))
                dfp["MA10"] = dfp["收盘"].rolling(10).mean(); dfp["MA30"] = dfp["收盘"].rolling(30).mean()
                m20 = dfp["收盘"].rolling(20).mean(); sd = dfp["收盘"].rolling(20).std(ddof=0)
                dfp["布林上轨"] = m20 + bbk*sd; dfp["布林下轨"] = m20 - bbk*sd
                st.line_chart(dfp.tail(int(days)), height=340)
                st.caption("装 plotly 看专业K线: pip install plotly")
            cL, cR = st.columns([1, 1])
            with cL:
                tr = r.get("trend", {})
                st.write("**趋势入场清单(三周期共振)**")
                for label, ok in tr.get("checks", []):
                    st.write(("✅ " if ok else "❌ ") + label)
                if tv in ("趋势买点", "强势突破") and tr.get("stop") is not None:
                    st.success(f"进场参考 · 止损 ${tr['stop']}(−2×ATR) · 目标 ${tr['target']}(R:R≥2) · 跌破MA10离场 · 最长持有~15天 · 每笔1%权益风险")
                elif not r.get("is_lev"):
                    st.caption("当前不满足三周期共振(需 月线强 + 周线顺·RSI≤70 + 日线均线多头)。逆势/超买不进。")
            with cR:
                st.write("**选股体检(贵·活·强)**")
                for x in r["reasons"]:
                    st.write("·", x)
                st.caption("图上绿三角 = 历史『回调后 RSI 上穿60』触发点(早入场)。深基反弹信号 = " + SIG_BADGE.get(r["signal"], r["signal"]) + "(仅参考)。⚠ 非投资建议")
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
    only_trend = cga.checkbox("只看趋势买点", value=True, help="🚀强势突破 / ✅趋势买点 = 三周期共振(月线强+周线顺+日线均线多头)")
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
        st.info("点「开始扫描」后,这里按『趋势信号』排序列出候选(杠杆/反向 ETF 已自动剔除)。✅趋势买点 = 三周期共振(月线强 + 周线顺 + 日线均线多头);🚀强势突破 = 再叠加突破布林上轨。这是你赢家的真实长相——配纪律执行,不是稳赢的圣杯。")

# ---------- Tab3 说明 ----------
with tab3:
    st.markdown("""
### 这套工具在帮你做什么(诚实版)
基于你 2021–2026 全部成交的复盘 + 全市场 1500+ 只的样本外检验,结论很明确:**你赚不赚,关键不在某个神触发,而在(1)选对趋势龙头、(2)堵住自己几个亏钱的漏洞。** 本工具就是把这两件事固化下来。

### 你的入场画像(三周期共振 · 来自你赢家的真实统计)
拆开日/周/月线后,真正决定你赚不赚的是**高级别趋势强度**:
- **月线(最关键):** 月线RSI偏强(超买)或站上月线布林上轨时,你胜率 **74%**、几乎所有的钱都在这;月线中性时仅 45%、净亏。
- **周线:** 金叉 + 站上周MA30 + **周RSI≤70(不超买、还有上行空间)**。逆周线(死叉)或周线已超买 = 中期追高,长期净亏。
- **日线入场(不追高):** 均线多头(MA10>20>30>50)+ **回调后 RSI 首次上穿 60**(进在 RSI 60–65,不在 80 几追),放量确认。这样止损近、不站岗。RSI 40–60 是你的死亡区。
- **三周期共振时胜率最高(≈88%)**,故信号只在「月线强 + 周线顺 + 日线触发」同时满足时才给。
- **✅ 趋势买点** = 三周期共振;**🚀 强势突破** = 再叠加突破布林上轨;**RBR**(rally-base-rally)结构作加分标注。

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
