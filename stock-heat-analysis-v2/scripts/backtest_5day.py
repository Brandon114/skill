#!/usr/bin/env python3
"""
回溯近5个交易日的每日预测 vs 实际涨跌
用已有K线数据，逐日截断后计算当日因子+预测，再与次日实际涨跌对比
"""
import json, sys, os, math
from pathlib import Path

# 复用 predict.py 的因子计算函数（直接内联避免import问题）

FACTOR_NAMES = [
    "F1_amount_heat", "F2_turnover_heat", "F3_volume_ratio",
    "F4_moneyflow", "F5_volatility", "F6_volume_cv", "F7_retail_behavior"
]
FACTOR_LABELS = {
    "F1_amount_heat": "成交额", "F2_turnover_heat": "换手率",
    "F3_volume_ratio": "量比", "F4_moneyflow": "资金流",
    "F5_volatility": "振幅", "F6_volume_cv": "成交CV",
    "F7_retail_behavior": "散户",
}
FACTOR_WEIGHTS = {n: 1/7 for n in FACTOR_NAMES}
SIGNAL_HIGH = 0.8
SIGNAL_LOW = -0.8

def _s(v, d=0.0):
    try: return float(v)
    except: return d

def _z(value, mean_val, std_val):
    if abs(std_val) < 1e-10: return 0.0
    z = (value - mean_val) / std_val
    return max(-4.0, min(4.0, z))

def _rmedian(values, window):
    if len(values) < window: return None
    w = sorted(values[-window:])
    n = len(w)
    return (w[n//2-1]+w[n//2])/2 if n%2==0 else w[n//2]

def f1(row, history):
    a = [_s(r.get("amount")) for r in history]
    m = _rmedian(a, 20)
    if m is None or m<1e-10: return 0.0
    return _s(row.get("amount"))/m

def f2(row): return _s(row.get("turnover"))

def f3(row, history):
    if len(history)<6: return 1.0
    rv = [_s(r.get("vol")) for r in history[-6:-1]]
    av = sum(rv)/len(rv) if rv else 1
    tv = _s(row.get("vol"))
    if av<1e-10: return 1.0
    return max(tv/av, 0.5)

def f4(row):
    pct = _s(row.get("pct_chg"))
    h,l,c = _s(row.get("high")), _s(row.get("low")), _s(row.get("close"),1)
    amp = (h-l)/c*100 if c>1e-10 else 0.0
    return -(pct*amp/10)

def f5(row):
    h,l,c = _s(row.get("high")), _s(row.get("low")), _s(row.get("close"),1)
    return (h-l)/c*100 if c>1e-10 else 0.0

def f6(history):
    if len(history)<5: return 0.0
    r = [_s(r.get("vol")) for r in history[-5:]]
    mv = sum(r)/len(r)
    if abs(mv)<1e-10: return 0.0
    v = sum((x-mv)**2 for x in r)/len(r)
    s = math.sqrt(max(v,0))
    return s/mv if abs(s)>1e-10 else 0.0

def f7(row):
    pct = _s(row.get("pct_chg"))
    to = _s(row.get("turnover"))
    return -(pct*to/100)

def compute_factors(data):
    results = []
    for i, row in enumerate(data):
        hist = data[:i+1]
        rec = {
            "date": row.get("date",""),
            "close": row.get("close",0),
            "pct_chg": row.get("pct_chg",0),
            "f1_raw": f1(row,hist), "f2_raw": f2(row),
            "f3_raw": f3(row,hist), "f4_raw": f4(row),
            "f5_raw": f5(row), "f6_raw": f6(hist),
            "f7_raw": f7(row),
        }
        results.append(rec)
    
    # Z-Score
    series = {n: [] for n in FACTOR_NAMES}
    raw_map = {"f1_raw":"F1_amount_heat","f2_raw":"F2_turnover_heat",
               "f3_raw":"F3_volume_ratio","f4_raw":"F4_moneyflow",
               "f5_raw":"F5_volatility","f6_raw":"F6_volume_cv","f7_raw":"F7_retail_behavior"}
    for rec in results:
        for rk, name in raw_map.items():
            series[name].append(_s(rec[rk]))
    
    for i, rec in enumerate(results):
        hs = 0.0
        for rk, name in raw_map.items():
            s = series[name][:i+1]
            if len(s)>1:
                m = sum(s)/len(s)
                v = sum((x-m)**2 for x in s)/(len(s)-1)
                st = math.sqrt(max(v,1e-10))
            elif s: m, st = s[0], 1.0
            else: m, st = 0.0, 1.0
            z = round(_z(_s(rec[rk]), m, st), 4)
            rec[rk+"_z"] = z
            hs += FACTOR_WEIGHTS[name]*z
        rec["heat"] = round(hs, 4)
    return results

def sig_dir(z):
    if z > SIGNAL_HIGH: return "偏空"
    if z < SIGNAL_LOW: return "偏多"
    return "中性"

def detect_trend(kline, window=10):
    """层面一：趋势识别（与predict.py保持一致）"""
    if len(kline) < window+1: return "neutral", 0.0
    closes = [r.get("close",0) for r in kline[-window:]]
    pcts = [r.get("pct_chg",0) for r in kline[-window:]]
    avg_pct = sum(pcts)/len(pcts)
    first_c = closes[0] if closes[0] > 1e-10 else 1.0
    slope = (closes[-1]-closes[0])/(window*first_c)*100
    ts = avg_pct*0.6 + slope*0.4
    if ts>0.4: return "bullish_strong", round(ts,4)
    elif ts>0.08: return "bullish_weak", round(ts,4)
    elif ts<-0.4: return "bearish_strong", round(ts,4)
    elif ts<-0.08: return "bearish_weak", round(ts,4)
    else: return "neutral", round(ts,4)

def predict_from_row(frow, kline_subset):
    """用某一天的因子数据预测次日方向（含趋势覆盖）"""
    heat = frow["heat"]
    bull = bear = 0
    details = []
    raw_keys = ["f1_raw_z","f2_raw_z","f3_raw_z","f4_raw_z","f5_raw_z","f6_raw_z","f7_raw_z"]
    for rk, name in zip(raw_keys, FACTOR_NAMES):
        z = _s(frow.get(rk))
        sd = sig_dir(z)
        if sd=="偏多": bull+=1
        elif sd=="偏空": bear+=1
        details.append({"factor":name,"label":FACTOR_LABELS[name],"z":round(z,3),"signal":sd})
    
    closes = [r.get("close",0) for r in kline_subset[-20:]]
    if closes:
        pl,ph = min(closes),max(closes)
        cp = kline_subset[-1].get("close",0)
        ppos = (cp-pl)/(ph-pl+1e-8)
    else:
        ppos=0.5
    
    # === 趋势识别（层面一优化）===
    trend_state, trend_score = detect_trend(kline_subset)
    trend_override = False
    
    if heat > 1.5: d, bp = "下跌", 0.75
    elif heat > 0.8: d, bp = "下跌", 0.65
    elif heat > 0.3: d, bp = "震荡偏空", 0.55
    elif heat >= -0.3: d, bp = "震荡", 0.50
    elif heat >= -0.8: d, bp = "震荡偏多", 0.55
    elif heat >= -1.5: d, bp = "上涨", 0.65
    else: d, bp = "上涨", 0.75
    
    # === 趋势覆盖逻辑 ===
    if trend_state == "bullish_strong" and d in ["下跌","震荡偏空"]:
        d = "震荡偏多" if d=="震荡偏空" else "上涨"
        bp = min(0.70, 0.50+abs(trend_score)*0.10)
        trend_override = True
    elif trend_state == "bearish_strong" and d in ["上涨","震荡偏多"]:
        d = "震荡偏空" if d=="震荡偏多" else "下跌"
        bp = min(0.70, 0.50+abs(trend_score)*0.10)
        trend_override = True
    elif trend_state == "bullish_weak" and d == "下跌":
        d, bp = "震荡", 0.52
    elif trend_state == "bearish_weak" and d == "上涨":
        d, bp = "震荡", 0.52
    
    padj = (0.5-ppos)*0.08
    sadj = (bull-bear)*0.02
    fp = round(max(0.50,min(0.85,bp+padj+sadj)),2)
    
    ah = abs(heat)
    if trend_override: conf="中低"
    elif ah>1.5 or (bull+bear)>=3: conf="中高"
    elif ah>0.8 or (bull+bear)>=2: conf="中"
    else: conf="低到中"
    
    return {
        "direction":d, "probability":fp, "confidence":conf,
        "heat_score":heat, "bull_signals":bear, "bear_signals":bear,
        "price_position_pct":round(ppos*100,1),
        "current_price":kline_subset[-1].get("close",0),
        "support":round(pl,2), "resistance":round(ph,2),
        "factor_details":details,
        "trend_state":trend_state, "trend_score":trend_score,
        "_trend_override":trend_override,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="回溯近5日预测vs实际")
    parser.add_argument("--code", required=True, help="股票代码")
    parser.add_argument("--data-dir", default="./output", help="K线数据目录")
    parser.add_argument("--days", type=int, default=5, help="回溯天数(默认5)")
    args = parser.parse_args()
    
    kpath = Path(args.data_dir)/f"{args.code}_kline.json"
    with open(kpath,"r") as f:
        kline = json.load(f)
    
    # 去掉最后一条（今天的实时数据，用它来验证倒数第二天的预测）
    # 我们需要的是：用第N天的数据预测N+1天，然后看N+1天实际涨跌
    total = len(kline)
    lookback = args.days
    
    print(f"\n{'='*70}")
    print(f"  📊 {args.code} 近{lookback}日回溯预测 vs 实际涨跌")
    print(f"{'='*70}")
    print(f"  K线总条数: {total}, 时间范围: {kline[0]['date']} ~ {kline[-1]['date']}")
    
    results = []
    # 从倒数第 (lookback+1) 天开始，到倒数第2天为止
    # 用第 i 天的数据预测第 i+1 天
    start_idx = total - lookback - 1  # 预测日的起始索引
    
    for i in range(start_idx, total - 1):
        # 截取到第 i 天的数据（含第i天）
        subset = kline[:i+1]
        factors = compute_factors(subset)
        pred = predict_from_row(factors[-1], subset)
        
        target_date = kline[i+1]["date"]
        actual_pct = kline[i+1].get("pct_chg", 0)
        
        # 判断正确性
        direction = pred["direction"]
        if "上涨" in direction or "偏多" in direction:
            correct = actual_pct > 0
        elif "下跌" in direction or "偏空" in direction:
            correct = actual_pct < 0
        else:  # 震荡
            correct = abs(actual_pct) <= 1.5
        
        result_mark = "✅" if correct else "❌"
        
        rec = {
            "pred_date": kline[i]["date"],
            "target_date": target_date,
            "close_that_day": kline[i]["close"],
            "direction": direction,
            "probability": pred["probability"],
            "confidence": pred["confidence"],
            "heat_score": pred["heat_score"],
            "actual_pct": actual_pct,
            "correct": correct,
            "result": result_mark,
        }
        results.append(rec)
        
        print(f"\n--- 第{len(results)}天: {rec['pred_date']} 预测 {rec['target_date']} ---")
        print(f"  当日收盘: {rec['close_that_day']:.2f}  |  热度: {pred['heat_score']:+.3f}")
        print(f"  预测方向: {direction} ({pred['probability']*100:.0f}%, {pred['confidence']})")
        print(f"  实际涨跌: {actual_pct:+.2f}%  |  结果: {result_mark}")
        # 因子摘要
        bull_n = sum(1 for fd in pred["factor_details"] if fd["signal"]=="偏多")
        bear_n = sum(1 for fd in pred["factor_details"] if fd["signal"]=="偏空")
        neut_n = 7-bull_n-bear_n
        print(f"  多/空/中性: {bull_n}/{bear_n}/{neut_n}")
    
    # 汇总
    correct_count = sum(1 for r in results if r["correct"])
    total_count = len(results)
    acc = correct_count/total_count if total_count>0 else 0
    
    print(f"\n{'='*70}")
    print(f"  📋 汇总: {args.code} 近{total_count}日预测准确率 {correct_count}/{total_count} = {acc*100:.0f}%")
    print(f"{'='*70}")
    print(f"  {'预测日期':>12} {'目标日期':>12} {'收盘价':>8} {'预测方向':<10} {'概率':>5} {'热度':>7} {'实际%':>8} {'结果'}")
    print(f"  {'-'*68}")
    for r in results:
        print(f"  {r['pred_date']:>12} {r['target_date']:>12} {r['close_that_day']:>8.2f} "
              f"{r['direction']:<10} {r['probability']*100:>4.0f}% "
              f"{r['heat_score']:>+7.3f} {r['actual_pct']:>+7.2f}%  {r['result']}")
    
    # 再加上今日的明日预测
    print(f"\n{'-'*68}")
    # 用全部数据算今日预测
    all_factors = compute_factors(kline)
    today_pred = predict_from_row(all_factors[-1], kline)
    print(f"  {'(今日)':>12} {'(明日05/08)':>12} {kline[-1]['close']:>8.2f} "
          f"{today_pred['direction']:<10} {today_pred['probability']*100:>4.0f}% "
          f"{today_pred['heat_score']:>+7.3f} {'(待验)':>8}  --")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
