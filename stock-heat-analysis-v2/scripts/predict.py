#!/usr/bin/env python3
"""
股票热度分析 v2 - 热度因子分析与预测引擎 (predict.py)
=========================================================
读取 fetch_public.py 输出的 K线JSON，计算7个热度因子，
生成明日涨跌预测，并与历史预测文件对比追踪近5日准确率。

用法:
    python3 predict.py --code 600000 --data-dir ./data
    python3 predict.py --code 600000 --data-dir ./data --output-dir ./output

输出:
    ./output/600000_predict_YYYYMMDD.json  — 完整分析结果
    终端打印简要分析摘要
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 7因子计算核心（从 stock_heat_analysis.py 复用逻辑）
# ============================================================

FACTOR_NAMES = [
    "F1_amount_heat", "F2_turnover_heat", "F3_volume_ratio",
    "F4_moneyflow", "F5_volatility", "F6_volume_cv", "F7_retail_behavior"
]

FACTOR_LABELS = {
    "F1_amount_heat":     "成交额",
    "F2_turnover_heat":   "换手率",
    "F3_volume_ratio":    "量比",
    "F4_moneyflow":       "资金流",
    "F5_volatility":      "振幅",
    "F6_volume_cv":       "成交CV",
    "F7_retail_behavior": "散户",
}

FACTOR_WEIGHTS = {n: 1/7 for n in FACTOR_NAMES}

# 信号阈值
SIGNAL_HIGH = 0.8   # Z > 0.8 → 偏空（热度高=散户情绪过热=风险）
SIGNAL_LOW  = -0.8  # Z < -0.8 → 偏多（热度低=散户冷淡=逆向机会）


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _z_score(value: float, mean_val: float, std_val: float) -> float:
    if abs(std_val) < 1e-10:
        return 0.0
    z = (value - mean_val) / std_val
    return max(-4.0, min(4.0, z))


def _rolling_median(values: list, window: int):
    if len(values) < window:
        return None
    w = sorted(values[-window:])
    n = len(w)
    return (w[n//2 - 1] + w[n//2]) / 2 if n % 2 == 0 else w[n//2]


# --- 7个原始因子 ---

def _f1_amount_heat(row: dict, history: list) -> float:
    """F1: 当日成交额 / 20日滚动中位数"""
    amounts = [_safe_float(r.get("amount")) for r in history]
    med = _rolling_median(amounts, 20)
    if med is None or med < 1e-10:
        return 0.0
    return _safe_float(row.get("amount")) / med


def _f2_turnover_heat(row: dict) -> float:
    """F2: 换手率原始值（从kline的turnover字段取）"""
    return _safe_float(row.get("turnover"))


def _f3_volume_ratio(row: dict, history: list) -> float:
    """F3: 量比 = 今日均速成交量 / 过去5日平均每分钟成交量
    公开K线没有量比字段，用相对5日均量代替"""
    if len(history) < 6:
        return 1.0
    recent_vols = [_safe_float(r.get("vol")) for r in history[-6:-1]]
    avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else 1
    today_vol = _safe_float(row.get("vol"))
    if avg_vol < 1e-10:
        return 1.0
    vr = today_vol / avg_vol
    return max(vr, 0.5)


def _f4_moneyflow(row: dict) -> float:
    """F4: 资金流向 — 公开K线无大/小单数据，用振幅×涨跌幅代理主力行为
    上涨+大振幅 → 资金流入（取负使高热度=负值）"""
    pct = _safe_float(row.get("pct_chg"))
    amp = 0.0
    high = _safe_float(row.get("high"))
    low  = _safe_float(row.get("low"))
    close = _safe_float(row.get("close"), 1)
    if close > 1e-10:
        amp = (high - low) / close * 100
    # 正涨幅+大振幅 = 主力推涨 → 取负号（与原始因子定义一致）
    return -(pct * amp / 10)  # 除以10缩放到合理范围


def _f5_volatility(row: dict) -> float:
    """F5: 日内振幅 (%)"""
    high  = _safe_float(row.get("high"))
    low   = _safe_float(row.get("low"))
    close = _safe_float(row.get("close"), 1)
    if close < 1e-10:
        return 0.0
    return (high - low) / close * 100


def _f6_volume_cv(history: list) -> float:
    """F6: 5日成交量变异系数"""
    if len(history) < 5:
        return 0.0
    recent = [_safe_float(r.get("vol")) for r in history[-5:]]
    mean_v = sum(recent) / len(recent)
    if abs(mean_v) < 1e-10:
        return 0.0
    var = sum((v - mean_v) ** 2 for v in recent) / len(recent)
    std_v = math.sqrt(max(var, 0))
    if abs(std_v) < 1e-10:
        return 0.0
    return std_v / mean_v


def _f7_retail_behavior(row: dict, history: list) -> float:
    """F7: 散户行为代理 — 公开K线无小单数据，用涨幅+换手率联合代理
    散户追涨特征：换手率高+涨幅大，取负号"""
    pct = _safe_float(row.get("pct_chg"))
    turnover = _safe_float(row.get("turnover"))
    # 换手率高+涨幅大 = 散户追涨热情高，取负
    return -(pct * turnover / 100)


# --- 批量计算 ---

def compute_all_factors(stock_data: list) -> list:
    """对历史数据逐日计算7个原始因子值"""
    results = []
    for i, row in enumerate(stock_data):
        history = stock_data[:i + 1]
        rec = {
            "date": row.get("date", ""),
            "close": row.get("close", 0),
            "pct_chg": row.get("pct_chg", 0),
            "F1_amount_heat_raw":     _f1_amount_heat(row, history),
            "F2_turnover_heat_raw":   _f2_turnover_heat(row),
            "F3_volume_ratio_raw":    _f3_volume_ratio(row, history),
            "F4_moneyflow_raw":       _f4_moneyflow(row),
            "F5_volatility_raw":      _f5_volatility(row),
            "F6_volume_cv_raw":       _f6_volume_cv(history),
            "F7_retail_behavior_raw": _f7_retail_behavior(row, history),
        }
        results.append(rec)
    return results


def time_series_zscore(factor_rows: list):
    """时间序列Z-Score标准化（单股历史内自比较）"""
    all_series = {name: [] for name in FACTOR_NAMES}
    for row in factor_rows:
        for name in FACTOR_NAMES:
            all_series[name].append(_safe_float(row.get(f"{name}_raw")))

    for i, row in enumerate(factor_rows):
        score_sum = 0.0
        for name in FACTOR_NAMES:
            series = all_series[name][:i + 1]
            if len(series) > 1:
                m = sum(series) / len(series)
                v = sum((x - m) ** 2 for x in series) / (len(series) - 1)
                s = math.sqrt(max(v, 1e-10))
            elif series:
                m, s = series[0], 1.0
            else:
                m, s = 0.0, 1.0
            raw = _safe_float(row.get(f"{name}_raw"))
            z = _z_score(raw, m, s)
            row[f"{name}_zscore"] = round(z, 4)
            score_sum += FACTOR_WEIGHTS[name] * z
        row["heat_score"] = round(score_sum, 4)


# ============================================================
# 预测逻辑
# ============================================================

def detect_trend(kline: list, window: int = 10) -> tuple:
    """
    层面一优化：趋势强度识别器。
    返回 (trend_state, trend_score)。
    trend_state: bullish_strong / bullish_weak / neutral / bearish_weak / bearish_strong
    trend_score: -2.0 ~ +2.0，绝对值越大趋势越强
    """
    if len(kline) < window + 1:
        return "neutral", 0.0

    closes = [r.get("close", 0) for r in kline[-window:]]
    # 方法1：近window日平均涨跌幅
    pcts = [r.get("pct_chg", 0) for r in kline[-window:]]
    avg_pct = sum(pcts) / len(pcts)

    # 方法2：线性回归斜率（简化：首尾差价率）
    first_close = closes[0] if closes[0] > 1e-10 else 1.0
    slope = (closes[-1] - closes[0]) / (window * first_close) * 100

    # 综合trend_score（avg_pct单位约%，slope也约%，可直接加权）
    trend_score = avg_pct * 0.6 + slope * 0.4

    if trend_score > 0.4:
        return "bullish_strong", round(trend_score, 4)
    elif trend_score > 0.08:
        return "bullish_weak", round(trend_score, 4)
    elif trend_score < -0.4:
        return "bearish_strong", round(trend_score, 4)
    elif trend_score < -0.08:
        return "bearish_weak", round(trend_score, 4)
    else:
        return "neutral", round(trend_score, 4)


def _signal_direction(z: float) -> str:
    """Z值 → 方向信号"""
    if z > SIGNAL_HIGH:
        return "偏空"
    elif z < SIGNAL_LOW:
        return "偏多"
    return "中性"


def predict_tomorrow(factor_rows: list, kline: list) -> dict:
    """
    基于最新热度分数预测明日涨跌方向、概率、置信度。

    预测逻辑（与实战脚本保持一致）：
    - 热度得分 > +1.0  → 下跌（散户过热=风险，逆向）
    - 热度得分 < -1.0  → 上涨（散户冷淡=机会，逆向）
    - 热度得分 -0.3~+0.3 → 震荡
    - 中间区间 → 偏多或偏空，概率与得分绝对值挂钩
    - 价格位置修正：处于区间低位时给多头加成
    """
    if not factor_rows:
        return {}

    last = factor_rows[-1]
    heat = last["heat_score"]

    # === 层面一优化：趋势强度识别 ===
    trend_state, trend_score = detect_trend(kline)
    trend_override = False   # 初始化覆盖标志

    # 计算各因子信号分布
    bull_signals = 0
    bear_signals = 0
    factor_details = []
    for name in FACTOR_NAMES:
        z = _safe_float(last.get(f"{name}_zscore"))
        sig = _signal_direction(z)
        if sig == "偏多":
            bull_signals += 1
        elif sig == "偏空":
            bear_signals += 1
        factor_details.append({
            "factor": name,
            "label": FACTOR_LABELS[name],
            "z": round(z, 3),
            "signal": sig,
        })

    # 价格位置（近20日）
    closes = [r.get("close", 0) for r in kline[-20:]]
    if closes:
        p_low, p_high = min(closes), max(closes)
        p_range = p_high - p_low
        current_price = kline[-1].get("close", 0)
        price_pos = (current_price - p_low) / (p_range + 1e-8)
    else:
        price_pos = 0.5

    # 核心预测
    # 基础概率：由热度分数映射（逆向逻辑）
    if heat > 1.5:
        direction, base_prob = "下跌", 0.75
    elif heat > 0.8:
        direction, base_prob = "下跌", 0.65
    elif heat > 0.3:
        direction, base_prob = "震荡偏空", 0.55
    elif heat >= -0.3:
        direction, base_prob = "震荡", 0.50
    elif heat >= -0.8:
        direction, base_prob = "震荡偏多", 0.55
    elif heat >= -1.5:
        direction, base_prob = "上涨", 0.65
    else:
        direction, base_prob = "上涨", 0.75

    # 修正1：价格位置（低位加多/高位加空）
    pos_adj = (0.5 - price_pos) * 0.08  # 低位+4%，高位-4%
    # 修正2：多空信号投票
    signal_adj = (bull_signals - bear_signals) * 0.02

    # 最终概率
    final_prob = round(max(0.50, min(0.85, base_prob + pos_adj + signal_adj)), 2)

    # 置信度
    abs_heat = abs(heat)
    if abs_heat > 1.5 or (bull_signals + bear_signals) >= 3:
        confidence = "中高"
    elif abs_heat > 0.8 or (bull_signals + bear_signals) >= 2:
        confidence = "中"
    else:
        confidence = "低到中"

    # === 层面一优化：趋势覆盖逻辑 ===
    trend_override = False
    if trend_state == "bullish_strong" and direction in ["下跌", "震荡偏空"]:
        direction = "震荡偏多" if direction == "震荡偏空" else "上涨"
        base_prob = min(0.70, 0.50 + abs(trend_score) * 0.10)
        trend_override = True
    elif trend_state == "bearish_strong" and direction in ["上涨", "震荡偏多"]:
        direction = "震荡偏空" if direction == "震荡偏多" else "下跌"
        base_prob = min(0.70, 0.50 + abs(trend_score) * 0.10)
        trend_override = True
    elif trend_state == "bullish_weak" and direction == "下跌":
        direction = "震荡"
        base_prob = 0.52
    elif trend_state == "bearish_weak" and direction == "上涨":
        direction = "震荡"
        base_prob = 0.52

    if trend_override:
        confidence = "中低"

    # 重新计算 final_prob（因 base_prob 可能被覆盖）
    final_prob = round(max(0.50, min(0.85, base_prob + pos_adj + signal_adj)), 2)

    # 参考价位
    ref_price = kline[-1].get("close", 0)
    prev_close = kline[-2].get("close", ref_price) if len(kline) > 1 else ref_price
    support = round(p_low, 2)
    resistance = round(p_high, 2)

    return {
        "target_date": _next_trading_day(),
        "direction": direction,
        "probability": final_prob,
        "confidence": confidence,
        "heat_score": heat,
        "trend_state": trend_state,
        "trend_score": trend_score,
        "bull_signals": bull_signals,
        "bear_signals": bear_signals,
        "price_position_pct": round(price_pos * 100, 1),
        "current_price": ref_price,
        "support": support,
        "resistance": resistance,
        "factor_details": factor_details,
        "_trend_override": trend_override,
    }


def _next_trading_day() -> str:
    """简单估算下一个交易日（跳过周末，不考虑节假日）"""
    d = datetime.now()
    d += timedelta(days=1)
    while d.weekday() >= 5:  # 0=Mon, 5=Sat, 6=Sun
        d += timedelta(days=1)
    return d.strftime("%Y%m%d")


# ============================================================
# 近5日预测追踪
# ============================================================

def track_recent_5days(code: str, output_dir: str, kline: list) -> list:
    """
    读取历史预测JSON文件，对比实际涨跌，返回近5日追踪记录。

    历史预测文件命名规则: {code}_predict_{YYYYMMDD}.json
    文件中需有字段: target_date, direction
    """
    output_dir = Path(output_dir)
    records = []

    # 构建日期→实际涨跌的映射（从K线）
    actual_pct = {}
    for r in kline:
        actual_pct[r["date"]] = r.get("pct_chg", None)

    # 搜索所有预测文件
    pred_files = sorted(output_dir.glob(f"{code}_predict_*.json"))
    # 取最近5个（不含今天的）
    today = datetime.now().strftime("%Y%m%d")
    past_preds = []
    for fp in pred_files:
        stem = fp.stem  # 如 600000_predict_20260506
        date_part = stem.split("_predict_")[-1]
        if date_part < today:  # 只要今天之前的预测
            past_preds.append((date_part, fp))

    for pred_date, fp in past_preds[-5:]:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                pred = json.load(f)

            target_date = pred.get("target_date", "")
            direction = pred.get("direction", "")
            probability = pred.get("probability", 0)

            actual = actual_pct.get(target_date, None)

            if actual is None:
                result = "未知"
                is_correct = None
            else:
                # 判断是否预测正确
                if "上涨" in direction or "偏多" in direction:
                    is_correct = actual > 0
                elif "下跌" in direction or "偏空" in direction:
                    is_correct = actual < 0
                else:  # 震荡
                    is_correct = abs(actual) <= 1.5
                result = "✅" if is_correct else "❌"

            records.append({
                "pred_date":   pred_date,
                "target_date": target_date,
                "direction":   direction,
                "probability": probability,
                "actual_pct":  actual,
                "result":      result,
                "is_correct":  is_correct,
            })
        except Exception as e:
            continue

    return records


def calc_accuracy(tracking: list) -> dict:
    """计算预测准确率"""
    valid = [r for r in tracking if r["is_correct"] is not None]
    if not valid:
        return {"total": 0, "correct": 0, "accuracy": None}
    correct = sum(1 for r in valid if r["is_correct"])
    return {
        "total": len(valid),
        "correct": correct,
        "accuracy": round(correct / len(valid), 3),
    }


# ============================================================
# 数据读取
# ============================================================

def load_kline(code: str, data_dir: str) -> list:
    """从 data_dir 读取 {code}_kline.json"""
    path = Path(data_dir) / f"{code}_kline.json"
    if not path.exists():
        print(f"  ❌ K线文件不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print(f"  ❌ K线文件格式错误（期望list）")
        return None
    print(f"  [数据] 加载 {len(data)} 条K线")
    return data


def load_realtime(code: str, data_dir: str) -> dict:
    """从 data_dir 读取 {code}_realtime.json（可选）"""
    path = Path(data_dir) / f"{code}_realtime.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 报告输出
# ============================================================

def print_summary(code: str, kline: list, realtime: dict,
                  factor_rows: list, prediction: dict, tracking: list):
    """终端打印完整分析摘要"""
    print("\n" + "=" * 62)
    print(f"  📊 股票热度分析报告 — {code}")
    print("=" * 62)

    # 今日状态
    last_k = kline[-1] if kline else {}
    rt_name = realtime.get("name", code) if realtime else code
    print(f"\n【今日状态】{rt_name} ({code})")
    print(f"  当前价: {last_k.get('close', '-'):.2f}  "
          f"涨跌: {last_k.get('pct_chg', 0):+.2f}%  "
          f"振幅: {_f5_volatility(last_k):.2f}%")
    if realtime:
        amt = realtime.get("amount", 0)
        print(f"  成交额: {amt/1e8:.3f}亿  时间: {realtime.get('time', '-')}")

    # 热度因子
    if factor_rows:
        last_f = factor_rows[-1]
        print(f"\n【热度因子】综合热度: {last_f.get('heat_score', 0):+.3f}")
        print(f"  {'因子':<10} {'Z值':>7} {'信号':<8}")
        print("  " + "-" * 28)
        for name in FACTOR_NAMES:
            z   = last_f.get(f"{name}_zscore", 0)
            sig = _signal_direction(z)
            emoji = "🟢" if sig == "偏多" else ("🔴" if sig == "偏空" else "⚪")
            print(f"  {FACTOR_LABELS[name]:<10} {z:>+7.3f} {emoji}{sig}")

    # 明日预测
    if prediction:
        p = prediction
        print(f"\n【明日预测】{p['target_date']}")
        dir_emoji = "📈" if "上涨" in p["direction"] or "偏多" in p["direction"] else \
                    ("📉" if "下跌" in p["direction"] or "偏空" in p["direction"] else "↔️")
        print(f"  {dir_emoji} {p['direction']}  概率:{p['probability']*100:.0f}%  "
              f"置信度:{p['confidence']}")
        print(f"  多头信号:{p['bull_signals']} / 空头信号:{p['bear_signals']} / "
              f"价格位置:{p['price_position_pct']:.0f}%")
        print(f"  支撑:{p['support']}  压力:{p['resistance']}  当前:{p['current_price']}")
        # 趋势信息（层面一优化）
        if p.get("_trend_override"):
            print(f"  ⚡ 趋势覆盖生效：{p['trend_state']}(score={p['trend_score']:+.2f})")
        elif p.get("trend_state") and p["trend_state"] != "neutral":
            print(f"  趋势状态：{p['trend_state']}（score: {p['trend_score']:+.2f}）")

    # 近5日追踪
    if tracking:
        acc = calc_accuracy(tracking)
        print(f"\n【近{len(tracking)}日预测追踪】准确率: ", end="")
        if acc["accuracy"] is not None:
            print(f"{acc['correct']}/{acc['total']} = {acc['accuracy']*100:.0f}%")
        else:
            print("暂无有效数据")

        print(f"  {'预测日':>10} {'目标日':>10} {'方向':<10} {'概率':>5} {'实际涨跌':>8} {'结果'}")
        print("  " + "-" * 58)
        for r in tracking:
            pct_str = f"{r['actual_pct']:+.2f}%" if r['actual_pct'] is not None else "  -"
            print(f"  {r['pred_date']:>10} {r['target_date']:>10} "
                  f"{r['direction']:<10} {r['probability']*100:>4.0f}% "
                  f"{pct_str:>8} {r['result']}")

    print(f"\n{'='*62}")


def save_prediction(code: str, kline: list, factor_rows: list,
                    prediction: dict, tracking: list, output_dir: str) -> str:
    """保存完整预测结果为JSON"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    filename = f"{code}_predict_{today}.json"
    filepath = output_dir / filename

    result = {
        "code": code,
        "analysis_date": today,
        "kline_count": len(kline),
        "latest_date": kline[-1]["date"] if kline else "",
        "latest_close": kline[-1].get("close", 0) if kline else 0,
        "prediction": prediction,
        "tracking_5days": tracking,
        "accuracy": calc_accuracy(tracking),
        "factor_latest": factor_rows[-1] if factor_rows else {},
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  💾 预测结果 → {filepath}")
    return str(filepath)


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="股票热度分析 v2 — 热度因子分析与预测引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析股票，数据在 ./data 目录
  python3 predict.py --code 600000

  # 指定数据目录和输出目录
  python3 predict.py --code 000001 --data-dir /tmp/data --output-dir ./output

  # 分析时指定历史预测目录（用于近5日追踪）
  python3 predict.py --code 600000 --pred-history-dir ./output
        """
    )
    parser.add_argument("--code",             type=str, required=True,
                        help="股票代码，如 600000")
    parser.add_argument("--data-dir",         type=str, default="./data",
                        help="fetch_public.py 输出的数据目录（默认 ./data）")
    parser.add_argument("--output-dir",       type=str, default="./output",
                        help="预测结果输出目录（默认 ./output）")
    parser.add_argument("--pred-history-dir", type=str, default=None,
                        help="历史预测文件目录（用于近5日追踪，默认同 output-dir）")

    args = parser.parse_args()

    pred_history_dir = args.pred_history_dir or args.output_dir

    print("=" * 58)
    print("  🌡️  股票热度分析 v2 — 预测引擎")
    print("=" * 58)
    print(f"  股票代码: {args.code}")
    print(f"  数据目录: {os.path.abspath(args.data_dir)}")
    print(f"  输出目录: {os.path.abspath(args.output_dir)}")

    # 读取数据
    kline = load_kline(args.code, args.data_dir)
    if not kline:
        sys.exit(1)

    realtime = load_realtime(args.code, args.data_dir)

    # 计算因子
    print(f"\n  >> 计算7个热度因子（{len(kline)} 条K线）...")
    factor_rows = compute_all_factors(kline)
    time_series_zscore(factor_rows)
    print(f"  ✅ 因子计算完成，综合热度: {factor_rows[-1]['heat_score']:+.3f}")

    # 生成预测
    print(f"\n  >> 生成明日预测...")
    prediction = predict_tomorrow(factor_rows, kline)

    # 近5日追踪
    print(f"\n  >> 追踪近5日历史预测准确率...")
    tracking = track_recent_5days(args.code, pred_history_dir, kline)
    acc = calc_accuracy(tracking)
    if acc["total"] > 0:
        print(f"  近{acc['total']}日准确率: {acc['correct']}/{acc['total']} = {acc['accuracy']*100:.0f}%")
    else:
        print(f"  暂无历史预测记录")

    # 打印摘要
    print_summary(args.code, kline, realtime, factor_rows, prediction, tracking)

    # 保存结果
    print(f"\n  >> 保存预测结果...")
    result_path = save_prediction(
        args.code, kline, factor_rows, prediction, tracking, args.output_dir
    )

    # 输出给 run.py 捕获
    summary = {
        "code": args.code,
        "direction": prediction.get("direction", ""),
        "probability": prediction.get("probability", 0),
        "confidence": prediction.get("confidence", ""),
        "heat_score": factor_rows[-1]["heat_score"] if factor_rows else 0,
        "result_path": result_path,
    }
    print(f"\n__RESULT__:{json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
