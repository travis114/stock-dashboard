#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""选股适配度核心引擎(无 Streamlit 依赖,可单独测试)。
抓取 Yahoo 日线 → 属性(趋势性/动量/波动/价格/流动性)→ 适配度评分与分层。
另含 current_signal:基于最新K线判定当前是否触发买点(顺势+突破上轨+RSI>60)。"""
import os, json, math, urllib.request, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]

def load_params(path=None):
    return json.load(open(path or os.path.join(HERE, "norm_params.json")))

def fetch_yahoo(ticker, rng="2y"):
    last = ""
    for a in range(3):
        host = HOSTS[a % 2]
        url = f"{host}/v8/finance/chart/{ticker}?range={rng}&interval=1d&events=split,div"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            d = json.loads(urllib.request.urlopen(req, timeout=20).read())["chart"]["result"][0]
            ts = d["timestamp"]; q = d["indicators"]["quote"][0]
            adj = d["indicators"].get("adjclose", [{}])[0].get("adjclose")
            O, H, L, C, V, D = [], [], [], [], [], []
            for i, t in enumerate(ts):
                c = q["close"][i]
                if c is None:
                    continue
                ac = adj[i] if (adj and adj[i] is not None) else c
                r = ac / c if c else 1.0
                O.append((q["open"][i] or c) * r); H.append((q["high"][i] or c) * r)
                L.append((q["low"][i] or c) * r); C.append(ac); V.append(q["volume"][i] or 0)
                D.append(dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"))
            if len(C) < 60:
                raise ValueError("数据太少")
            return {"dates": D, "open": O, "high": H, "low": L, "close": C, "volume": V}
        except Exception as e:
            last = str(e)[:80]
    raise RuntimeError(f"抓取 {ticker} 失败: {last}")

def _sma(a, n):
    a = np.asarray(a, float); out = np.full(len(a), np.nan)
    if len(a) >= n:
        c = np.cumsum(np.insert(a, 0, 0)); out[n-1:] = (c[n:] - c[:-n]) / n
    return out

def _rsi(a, n=14):
    """Wilder RSI 全序列(与 ta.rsi 一致),返回与价格等长的数组。"""
    a = np.asarray(a, float); out = np.full(len(a), np.nan)
    if len(a) < n + 1:
        return out
    d = np.diff(a); gain = np.where(d > 0, d, 0.0); loss = np.where(d < 0, -d, 0.0)
    ag = gain[:n].mean(); al = loss[:n].mean()
    out[n] = 100.0 if al == 0 else 100 - 100/(1 + ag/al)
    for i in range(n, len(d)):
        ag = (ag*(n-1) + gain[i]) / n; al = (al*(n-1) + loss[i]) / n
        out[i+1] = 100.0 if al == 0 else 100 - 100/(1 + ag/al)
    return out

def _rsi_last(a, n=14):
    r = _rsi(a, n)
    return r[-1] if len(r) else np.nan

def compute_attrs(px, window=252):
    c = np.asarray(px["close"], float); v = np.asarray(px["volume"], float)
    ma10 = _sma(c, 10); ma30 = _sma(c, 30)
    w = min(window, len(c))
    cw = c[-w:]; vw = v[-w:]; m10 = ma10[-w:]; m30 = ma30[-w:]
    valid = ~np.isnan(m10) & ~np.isnan(m30)
    trend = float(np.mean((m10[valid] > m30[valid]))) if valid.any() else np.nan
    ret = float(cw[-1] / cw[0] - 1)
    dr = np.diff(cw) / cw[:-1]
    return {"trend": round(trend, 3), "ret": round(ret, 3),
            "vol": round(float(np.nanstd(dr) * math.sqrt(252)), 3),
            "medp": round(float(np.nanmedian(cw)), 2),
            "dolvol": round(float(np.nanmedian(cw * vw)) / 1e6, 1)}

def current_signal(px, within=7, base_look=45):
    """🔥买点 = 经样本外验证的「深基反弹+放量点火」配置(2021-23训练/2024-26样本外均跑赢基线,胜率57%):
       近 within 日内 RSI 上穿60,且同时满足:
         · base期(前45根)RSI 曾 ≤37(深超卖)
         · 价格 ≤ 52周高的97%(未追高,是从回调中恢复)
         · 前期回调 ≥11%(有像样的下跌后再起)
         · 突破当日成交量 ≥ 20日均量(放量点火)
         · 上穿后收盘站稳中轨(20MA)2根(防一日假突破)
       👀观察 = 上述点火刚发生、但'站稳2根'尚未确认。"""
    c = np.asarray(px["close"], float); v = np.asarray(px.get("volume", []), float)
    n = len(c)
    if n < base_look + 30 or len(v) != n:
        return "—"
    m20 = _sma(c, 20); rsi = _rsi(c, 14)
    i = n - 1; watch = False
    for ci in range(i, max(60, i - within), -1):
        if not (rsi[ci] > 60 and rsi[ci-1] <= 60):          # RSI 上穿60
            continue
        a = ci - base_look
        if a < 1:
            continue
        seg = rsi[a:ci+1]
        if np.isnan(seg).any():
            continue
        rsi_min_base = float(np.min(seg))                    # 深超卖
        hi52 = float(np.max(c[max(0, ci-252):ci+1])); dist52 = c[ci]/hi52 if hi52 > 0 else 1.0
        hi_before = float(np.max(c[max(0, ci-90):max(1, ci-base_look)])) if ci-base_look > 0 else c[ci]
        base_low = float(np.min(c[a:ci+1]))
        pullback = (hi_before - base_low)/hi_before if hi_before > 0 else 0.0
        volavg = float(np.mean(v[max(0, ci-19):ci+1])); vol_surge = v[ci]/volavg if volavg > 0 else 0.0
        cond = (rsi_min_base <= 37) and (dist52 <= 0.97) and (pullback >= 0.11) and (vol_surge >= 1.0)
        if not cond:
            continue
        if ci + 2 <= i:                                      # 可评估"站稳2根"
            if c[ci+1] >= m20[ci+1]*0.99 and c[ci+2] >= m20[ci+2]*0.99:
                return "买点"
        else:
            watch = True                                     # 刚点火,待确认
    return "观察" if watch else "—"

def score_attrs(a, P=None):
    P = P or load_params()
    def z(x, key): m, s = P[key]; return (x - m) / (s + 1e-9)
    zt = z(min(max(a["trend"], 0), 0.9), "trend")
    zp = z(math.log10(max(a["medp"], 0.5)), "price")
    zl = z(math.log10(max(a["dolvol"], 0.5)), "liq")
    zr = z(min(max(a["ret"], -0.9), 3), "rs")
    wsum = (P["weights"]["trend"]*zt + P["weights"]["price"]*zp +
            P["weights"]["liq"]*zl + P["weights"]["rs"]*zr)
    s100 = round(max(0, min(100, (wsum - P["score_min"]) / (P["score_max"] - P["score_min"]) * 100)), 1)
    if a["medp"] < 5 or a["dolvol"] < 8 or a["trend"] < 0.35:
        tier = "回避"
    elif a["medp"] >= 10 and a["dolvol"] >= 15 and a["trend"] >= 0.45:
        tier = "优选"
    else:
        tier = "中性"
    reasons = [
        ("价格 $%.2f" % a["medp"]) + ("  ✓≥$10" if a["medp"] >= 10 else ("  ⚠<$5 仙股" if a["medp"] < 5 else "  ~$5-10")),
        ("日成交额 $%.0fM" % a["dolvol"]) + ("  ✓≥$15M" if a["dolvol"] >= 15 else ("  ⚠<$8M 流动性差" if a["dolvol"] < 8 else "  ~中")),
        ("趋势性 %.0f%%" % (a["trend"]*100)) + ("  ✓≥45%" if a["trend"] >= 0.45 else ("  ⚠<35% 弱/震荡" if a["trend"] < 0.35 else "  ~中")),
        ("近1年涨跌 %+.0f%%" % (a["ret"]*100)) + ("  ✓正动量" if a["ret"] > 0 else "  ⚠负动量"),
    ]
    return {"score": s100, "tier": tier, "reasons": reasons}

def evaluate(ticker, P=None):
    px = fetch_yahoo(ticker)
    a = compute_attrs(px); sc = score_attrs(a, P)
    return {"ticker": ticker.upper(), "attrs": a, "signal": current_signal(px), **sc, "px": px}

def scan_universe(tickers, P=None, max_workers=8, progress=None):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    P = P or load_params()
    tickers = [t.strip().upper() for t in tickers if t and t.strip()]
    out = []; done = 0
    def one(t):
        try:
            px = fetch_yahoo(t); a = compute_attrs(px); sc = score_attrs(a, P)
            return {"ticker": t, **a, "score": sc["score"], "tier": sc["tier"], "signal": current_signal(px)}
        except Exception:
            return {"ticker": t, "error": True}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(one, t): t for t in tickers}
        for f in as_completed(futs):
            r = f.result()
            if r and not r.get("error"): out.append(r)
            done += 1
            if progress: progress(done, len(tickers))
    out.sort(key=lambda x: -x["score"])
    return out

if __name__ == "__main__":
    import sys
    P = load_params()
    for t in (sys.argv[1:] or ["NVDA", "AAPL", "OXY", "LIPO"]):
        try:
            r = evaluate(t, P)
            print(f"\n{r['ticker']}: 评分 {r['score']} [{r['tier']}] 信号<{r['signal']}>  {r['attrs']}")
        except Exception as e:
            print(f"\n{t}: 错误 {e}")
