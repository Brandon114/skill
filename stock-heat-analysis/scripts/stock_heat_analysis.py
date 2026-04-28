#!/usr/bin/env python3
"""
股票热度分析工具 (Stock Heat Analysis) - 数据处理引擎
==========================================================
基于公开A股市场数据构建热度因子体系，量化评估股票受散户关注度。

灵感来源：微信公众号文章《什么？某炒股软件把你的操作痕迹卖给了机构》

架构说明：
  数据获取层 → 由 WorkBuddy 环境通过 finance-data-retrieval skill 调用 API
  本脚本负责 → 因子计算、标准化、评分、可视化、报告生成

输入：
  --data-dir: 预获取的 JSON 数据目录（由主程序或手动调用 API 后存放在此）
  
用法:
    # 方式1: 使用预获取数据
    python3 stock_heat_analysis.py --data-dir ./fetched_data/ --output-dir ./output/
    
    # 方式2: 指定单只股票数据文件
    python3 stock_heat_analysis.py --stock-data ./600519.SH.json --output-dir ./output/
    
    # 方式3: 多股对比
    python3 stock_heat_analysis.py --data-dir ./fetched_data/ --mode compare --top-n 10

数据格式要求（JSON）:
  daily.json: [{"ts_code":"600519.SH","trade_date":"20260428","open":...,"high":...,"low":...,
                "close":...,"pct_chg":...,"vol":...,"amount":...}, ...]
  daily_basic.json: [{"ts_code":"600519.SH","trade_date":"20260428","turnover_rate":...,
                      "volume_ratio":...,"total_mv":...,"circ_mv":...}, ...]
  moneyflow.json: [{"ts_code":"600519.SH","trade_date":"20260428","buy_sm_amount":...,
                    "sell_sm_amount":...,"net_mf_amount":...}, ...]
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path


# ============================================================
# 配置区
# ============================================================

# 因子权重（等权配置，可调整）
FACTOR_WEIGHTS = {
    "F1_amount_heat":     1/7,   # 成交额热度
    "F2_turnover_heat":   1/7,   # 换手率热度
    "F3_volume_ratio":    1/7,   # 量比热度
    "F4_moneyflow":       1/7,   # 资金流向（取反）
    "F5_volatility":      1/7,   # 波动分歧
    "F6_volume_cv":       1/7,   # 成交变异系数
    "F7_retail_behavior": 1/7,   # 散户行为（取反）
}

FACTOR_NAMES = [
    "F1_amount_heat", "F2_turnover_heat", "F3_volume_ratio",
    "F4_moneyflow", "F5_volatility", "F6_volume_cv", "F7_retail_behavior"
]

FACTOR_LABELS = {
    "F1_amount_heat":     "成交额",
    "F2_turnover_heat":   "换手率",
    "F3_volume_ratio":    "量比",
    "F4_moneyflow":       "资金流",
    "F5_volatility":      "波动率",
    "F6_volume_cv":       "成交CV",
    "F7_retail_behavior": "散户",
}


# ============================================================
# 数据加载模块
# ============================================================

def load_json_file(filepath: str) -> list[dict]:
    """加载 JSON 数据文件"""
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # 可能是 {"fields":[], "items":[]} 格式
                fields = data.get("fields", [])
                items = data.get("items", [])
                result = []
                for row in items:
                    d = {}
                    for i, field in enumerate(fields):
                        d[field] = row[i] if i < len(row) else None
                    result.append(d)
                return result
            return []
    except Exception as e:
        print(f"  ⚠ 加载 {filepath} 失败: {e}")
        return []


def load_stock_data(data_dir: str, ts_code: str = None) -> tuple[list, list, list]:
    """
    从 data_dir 加载指定股票的三类数据。
    
    文件命名规则:
      - 子目录模式: {code_safe}/daily.json (如 600519_SH/daily.json)
      - 扁平模式: {ts_code}_daily.json 或 daily.json
    
    返回: (daily_list, basic_list, mf_list)
    """
    base = Path(data_dir)
    
    # 确定搜索路径
    search_dirs = []
    
    if ts_code:
        # 先尝试子目录模式
        code_safe = ts_code.replace(".", "_")
        sub_dir = base / code_safe
        if sub_dir.exists() and sub_dir.is_dir():
            search_dirs.append(sub_dir)
        
        # 再尝试扁平文件模式（在根目录）
        for suffix in [ts_code, code_safe]:
            if (base / f"{suffix}_daily.json").exists():
                search_dirs.append(base)
                break
    
    # 如果没有找到特定股票的目录/文件，直接使用 data-dir 根目录
    if not search_dirs:
        search_dirs = [base]
    
    def try_load(search_base: Path):
        daily_data, basic_data, mf_data = None, None, None
        
        for p in ["daily.json"]:
            fp = search_base / p
            if fp.exists():
                d = load_json_file(str(fp))
                if d:
                    daily_data = d
        
        for p in ["daily_basic.json"]:
            fp = search_base / p
            if fp.exists():
                d = load_json_file(str(fp))
                if d:
                    basic_data = d
        
        for p in ["moneyflow.json"]:
            fp = search_base / p
            if fp.exists():
                d = load_json_file(str(fp))
                if d:
                    mf_data = d
        
        return daily_data or [], basic_data or [], mf_data or []
    
    return try_load(search_dirs[0])


def merge_data(daily_list: list, basic_list: list, mf_list: list) -> list[dict]:
    """按日期合并三类数据"""
    merged = {}
    
    for d in daily_list:
        date_key = str(d.get("trade_date", ""))
        if date_key:
            merged.setdefault(date_key, {}).update(d)
    
    for b in basic_list:
        date_key = str(b.get("trade_date", ""))
        if date_key and date_key in merged:
            merged[date_key].update(b)
    
    for m in mf_list:
        date_key = str(m.get("trade_date", ""))
        if date_key and date_key in merged:
            merged[date_key].update(m)
    
    sorted_data = sorted(merged.values(), key=lambda x: x.get("trade_date", ""))
    return sorted_data


def discover_stocks(data_dir: str) -> list[str]:
    """自动发现 data_dir 中所有可用的股票代码（支持目录和文件两种模式）"""
    base = Path(data_dir)
    stocks = set()
    
    # 模式1: 子目录结构 (600519_SH/daily.json)
    for subdir in base.iterdir():
        if subdir.is_dir():
            for f in ["daily.json", "daily_basic.json"]:
                if (subdir / f).exists():
                    stocks.add(subdir.name)
                    break
    
    # 模式2: 文件模式 (*_daily.json, *600519.SH_daily.json 等)
    for pattern in ["*_*_daily.json", "*_daily.json"]:
        for p in base.glob(pattern):
            name = p.stem
            name = name.replace("_daily", "")
            # 还原可能的 . 替换为 _
            stocks.add(name)
    
    return sorted(stocks)


# ============================================================
# 因子计算模块
# ============================================================

def to_float(val, default=0.0):
    """安全转换为浮点数"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def rolling_median(values: list[float], window: int) -> float | None:
    """计算滚动中位数"""
    if len(values) < window:
        return None
    window_vals = values[-window:]
    sorted_vals = sorted(window_vals)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    else:
        return sorted_vals[mid]


def z_score(value: float, mean_val: float, std_val: float) -> float:
    """计算 Z-Score"""
    if abs(std_val) < 1e-10:
        return 0.0
    return (value - mean_val) / std_val


def calc_f1_amount_heat(row: dict, history: list) -> float:
    """F1: 成交热度 — 当日成交额 / 20日滚动中位数"""
    amounts = [to_float(r.get("amount")) for r in history]
    current = to_float(row.get("amount"))
    med = rolling_median(amounts, 20)
    if med is None or med < 1e-10:
        return 0.0
    return current / med


def calc_f2_turnover_heat(row: dict) -> float:
    """F2: 换手热度 — 换手率原始值"""
    return to_float(row.get("turnover_rate"))


def calc_f3_volume_ratio(row: dict) -> float:
    """F3: 量比热度 — 量比（下界截断0.5）"""
    vr = to_float(row.get("volume_ratio"), 0.5)
    return max(vr, 0.5)


def calc_f4_moneyflow(row: dict) -> float:
    """F4: 资金流向 — 净流入占流通市值比例 ×(-100)，放大到合理范围"""
    net_mf = to_float(row.get("net_mf_amount"))
    circ_mv = to_float(row.get("circ_mv"), 1)
    if circ_mv < 1e-10:
        circ_mv = 1
    ratio = -(net_mf / circ_mv) * 100  # 取负号
    return ratio


def calc_f5_volatility(row: dict) -> float:
    """F5: 波动分歧 — 日内振幅 (%)"""
    high = to_float(row.get("high"))
    low = to_float(row.get("low"))
    close = to_float(row.get("close"), 1)
    if close < 1e-10:
        close = 1
    return ((high - low) / close) * 100


def calc_f6_volume_cv(history: list) -> float:
    """F6: 成交波动 — 5日成交量变异系数"""
    if len(history) < 5:
        return 0.0
    recent = [to_float(r.get("vol")) for r in history[-5:]]
    mean_v = sum(recent) / len(recent)
    if abs(mean_v) < 1e-10:
        return 0.0
    var = sum((v - mean_v) ** 2 for v in recent) / len(recent)
    std_v = math.sqrt(max(var, 0))
    if abs(std_v) < 1e-10:
        return 0.0
    return std_v / mean_v


def calc_f7_retail_behavior(row: dict) -> float:
    """F7: 散户行为 — 小单净买入占比（取负号：散户集中买入=风险信号）"""
    buy_sm = to_float(row.get("buy_sm_amount"))
    sell_sm = to_float(row.get("sell_sm_amount"))
    total = abs(buy_sm) + abs(sell_sm)
    if total < 1e-10:
        return 0.0
    retail_net = -(buy_sm - sell_sm) / total
    return retail_net


def compute_all_factors(stock_data: list[dict], ts_code: str) -> list[dict]:
    """计算所有因子的原始值"""
    results = []
    for i, row in enumerate(stock_data):
        history = stock_data[:i+1]
        
        factor_row = {
            "ts_code": ts_code,
            "trade_date": row.get("trade_date"),
            "F1_amount_raw":       calc_f1_amount_heat(row, history),
            "F2_turnover_raw":     calc_f2_turnover_heat(row),
            "F3_volume_ratio_raw": calc_f3_volume_ratio(row),
            "F4_moneyflow_raw":    calc_f4_moneyflow(row),
            "F5_volatility_raw":   calc_f5_volatility(row),
            "F6_volume_cv_raw":    calc_f6_volume_cv(history),
            "F7_retail_raw":       calc_f7_retail_behavior(row),
        }
        results.append(factor_row)
    
    return results


# ============================================================
# 标准化模块
# ============================================================

def cross_sectional_zscore(factor_rows: list[dict], factor_names: list[str]):
    """多只股票截面标准化"""
    latest_values = {name: [] for name in factor_names}
    for row in factor_rows:
        for name in factor_names:
            val = to_float(row.get(f"{name}_raw"))
            latest_values[name].append(val)
    
    stats = {}
    for name in factor_names:
        vals = latest_values[name]
        if len(vals) > 1:
            m = sum(vals) / len(vals)
            v = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
            s = math.sqrt(max(v, 1e-10))
        elif vals:
            m = vals[0]
            s = 1.0
        else:
            m, s = 0, 1
        stats[name] = (m, s)
    
    for row in factor_rows:
        score_sum = 0.0
        for name in factor_names:
            raw = to_float(row.get(f"{name}_raw"))
            z = z_score(raw, stats[name][0], stats[name][1])
            z = max(-4.0, min(4.0, z))
            row[f"{name}_zscore"] = round(z, 4)
            
            w = FACTOR_WEIGHTS.get(name, 1/7)
            score_sum += w * z
        
        row["heat_score"] = round(score_sum, 4)


def time_series_zscore(factor_rows: list[dict], factor_names: list[str]):
    """单只股票时间序列Z-Score标准化"""
    all_series = {name: [] for name in factor_names}
    for row in factor_rows:
        for name in factor_names:
            all_series[name].append(to_float(row.get(f"{name}_raw")))
    
    for i, row in enumerate(factor_rows):
        score_sum = 0.0
        
        for name in factor_names:
            series = all_series[name][:i+1]
            if len(series) > 1:
                m = sum(series) / len(series)
                v = sum((x - m) ** 2 for x in series) / (len(series) - 1)
                s = math.sqrt(max(v, 1e-10))
            elif series:
                m, s = series[0], 1.0
            else:
                m, s = 0, 1
            
            raw = to_float(row.get(f"{name}_raw"))
            z = z_score(raw, m, s)
            z = max(-4.0, min(4.0, z))
            row[f"{name}_zscore"] = round(z, 4)
            
            w = FACTOR_WEIGHTS.get(name, 1/7)
            score_sum += w * z
        
        row["heat_score"] = round(score_sum, 4)


# ============================================================
# 可视化模块
# ============================================================

def check_matplotlib():
    """检查并导入 matplotlib，自动配置中文字体"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 配置中文字体（macOS 优先，Linux次之，Windows备用）
        import matplotlib.font_manager as fm
        
        chinese_font = None
        # macOS 常见中文字体
        for font in ["PingFang SC", "Hiragino Sans GB", "STHeiti",
                     "Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei"]:
            try:
                fp = fm.findfont(fm.FontProperties(family=font), fallback_to_default=False)
                if fp and "DejaVu" not in fp:
                    chinese_font = font
                    break
            except Exception:
                continue
        
        if chinese_font:
            plt.rcParams["font.family"] = [chinese_font, "DejaVu Sans"]
        else:
            # 尝试系统字体目录查找
            system_fonts = fm.findSystemFonts(fontpaths=None)
            for fp in system_fonts:
                fname = os.path.basename(fp).lower()
                if any(kw in fname for kw in ["pingfang", "hiragino", "heiti", "songti", "simhei"]):
                    fe = fm.FontEntry(fname=fp, name=fname)
                    fm.fontManager.ttflist.insert(0, fe)
                    plt.rcParams["font.family"] = [fname, "DejaVu Sans"]
                    chinese_font = fname
                    break
        
        plt.rcParams["axes.unicode_minus"] = False
        
        return plt, np
    except ImportError:
        print("  ⚠ 未安装 matplotlib/numpy，跳过图表。运行: pip3 install matplotlib numpy")
        return None, None


def plot_factor_correlation(all_factor_rows: list[dict], output_dir: str):
    """因子相关性热力图"""
    plt, np = check_matplotlib()
    if plt is None or not all_factor_rows:
        return
    
    labels_short = [FACTOR_LABELS[n].replace(" ", "_") for n in FACTOR_NAMES]
    
    matrix = []
    for fi in range(len(FACTOR_NAMES)):
        row_vals = []
        for fj in range(len(FACTOR_NAMES)):
            vi = [to_float(r.get(f"{FACTOR_NAMES[fi]}_zscore")) for r in all_factor_rows]
            vj = [to_float(r.get(f"{FACTOR_NAMES[fj]}_zscore")) for r in all_factor_rows]
            corr = float(np.corrcoef(vi, vj)[0, 1]) if len(vi) > 1 else 0.0
            row_vals.append(round(corr, 3))
        matrix.append(row_vals)
    
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(np.array(matrix), cmap="RdYlBu_r", vmin=-1, vmax=1)
    
    ax.set_xticks(range(len(labels_short)))
    ax.set_yticks(range(len(labels_short)))
    ax.set_xticklabels(labels_short, fontsize=11)
    ax.set_yticklabels(labels_short, fontsize=11)
    
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            color = "white" if abs(matrix[i][j]) > 0.5 else "black"
            ax.text(j, i, str(matrix[i][j]), ha="center", va="center", fontsize=10, color=color)
    
    plt.colorbar(im, label="Pearson 相关系数")
    ax.set_title("热度因子相关性矩阵", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    fp = os.path.join(output_dir, "factor_correlation.png")
    plt.savefig(fp, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ 相关性热力图 → {fp}")


def plot_timeline_heatmap(factor_rows: list[dict], output_dir: str, stock_name: str = ""):
    """时间线因子热力图"""
    plt, np = check_matplotlib()
    if plt is None or not factor_rows:
        return
    
    dates = [str(r.get("trade_date", ""))[-4:] for r in factor_rows]
    
    data_matrix = []
    for fname in FACTOR_NAMES:
        col = [to_float(r.get(f"{fname}_zscore")) for r in factor_rows]
        data_matrix.append(col)
    
    fig_w = max(len(dates) * 0.6, 8)
    fig, ax = plt.subplots(figsize=(fig_w, 6))
    im = ax.imshow(np.array(data_matrix), cmap="RdYlBu_r", aspect="auto", vmin=-2.5, vmax=2.5)
    
    step = max(1, len(dates) // 15)
    tick_pos = list(range(0, len(dates), step))
    tick_labels = [dates[i] for i in tick_pos]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=8)
    
    labels = [FACTOR_LABELS[n] for n in FACTOR_NAMES]
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=11)
    
    plt.colorbar(im, label="Z-Score")
    title = f"热度因子时间演变 — {stock_name}" if stock_name else "热度因子时间演变"
    ax.set_title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    
    safe_name = stock_name.replace(".", "_").replace("/", "") if stock_name else "timeline"
    fp = os.path.join(output_dir, f"heatmap_{safe_name}.png")
    plt.savefig(fp, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ 时间线热力图 → {fp}")


def plot_radar_compare(all_results: dict, output_dir: str):
    """多股雷达图对比"""
    plt, np = check_matplotlib()
    if plt is None or len(all_results) < 2:
        return
    
    labels = [FACTOR_LABELS[n] for n in FACTOR_NAMES]
    N = len(labels)
    angles = [n / N * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    
    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6',
              '#1ABC9C', '#E67E22', '#34495E']
    
    for idx, (ts_code, rows) in enumerate(all_results.items()):
        if rows:
            last = rows[-1]
            values = [to_float(last.get(f"{n}_zscore")) for n in FACTOR_NAMES]
            values += values[:1]
            c = colors[idx % len(colors)]
            ax.plot(angles, values, linewidth=2, label=ts_code, color=c)
            ax.fill(angles, values, alpha=0.12, color=c)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_title("多股热度雷达图对比（最新交易日）", fontsize=14, fontweight="bold", pad=25)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.0), fontsize=10)
    plt.tight_layout()
    fp = os.path.join(output_dir, "radar_chart.png")
    plt.savefig(fp, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ 雷达对比图 → {fp}")


# ============================================================
# 报告输出模块
# ============================================================

def generate_report(all_results: dict, mode: str, output_dir: str, top_n: int = 20):
    """生成 JSON + CSV 报告和终端排行摘要"""
    os.makedirs(output_dir, exist_ok=True)
    
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "stocks_analyzed": list(all_results.keys()),
        "factor_weights": {k: round(v, 4) for k, v in FACTOR_WEIGHTS.items()},
        "details": {},
    }
    
    for ts_code, factor_rows in all_results.items():
        recent = factor_rows[-7:] if len(factor_rows) > 7 else factor_rows
        report["details"][ts_code] = {
            "total_days": len(factor_rows),
            "latest_score": factor_rows[-1]["heat_score"] if factor_rows else 0,
            "latest_date": factor_rows[-1]["trade_date"] if factor_rows else "",
            "recent_data": recent,
        }
    
    with open(os.path.join(output_dir, "heat_summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  ✅ JSON报告 → {output_dir}/heat_summary.json")
    
    # CSV 排行榜
    ranking = []
    for ts_code, factor_rows in all_results.items():
        if factor_rows:
            last = factor_rows[-1]
            ranking.append({
                "rank": 0,
                "ts_code": ts_code,
                "heat_score": last.get("heat_score", 0),
                "date": str(last.get("trade_date", "")),
                "F1_成交额":   round(to_float(last.get("F1_amount_heat_zscore")), 3),
                "F2_换手率":   round(to_float(last.get("F2_turnover_heat_zscore")), 3),
                "F3_量比":     round(to_float(last.get("F3_volume_ratio_zscore")), 3),
                "F4_资金流":   round(to_float(last.get("F4_moneyflow_zscore")), 3),
                "F5_波动率":   round(to_float(last.get("F5_volatility_zscore")), 3),
                "F6_成交CV":   round(to_float(last.get("F6_volume_cv_zscore")), 3),
                "F7_散户":     round(to_float(last.get("F7_retail_behavior_zscore")), 3),
            })
    
    ranking.sort(key=lambda x: x["heat_score"], reverse=True)
    for i, item in enumerate(ranking):
        item["rank"] = i + 1
    
    csv_path = os.path.join(output_dir, "heat_ranking.csv")
    if ranking:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(ranking[0].keys()))
            writer.writeheader()
            writer.writerows(ranking)
        print(f"  ✅ CSV排行榜 → {csv_path}")
        
        show_n = min(top_n, len(ranking))
        print(f"\n{'='*72}")
        print(f'📊 热度排名 TOP-{show_n}  （越高越热 → 散户关注度越高 → 越需警惕）')
        print(f"{'='*72}")
        print(f"{'排名':<4} {'代码':<12} {'得分':>7} {'日期':<10} "
              f"{'成交额':>7} {'换手率':>7} {'量比':>6} {'资金流':>7}")
        print("-"*72)
        
        for item in ranking[:show_n]:
            score = item["heat_score"]
            if score > 1.5:
                flag = "🔥🔥"
            elif score > 0.5:
                flag = "⚠️ "
            elif score >= 0:
                flag = "✅ "
            else:
                flag = "❄️ "
            
            print(f'{item["rank"]:<4} {item["ts_code"]:<12} {score:>+7.2f} '
                  f'{item["date"]:<10} '
                  f'{item["F1_成交额"]:>+7.2f} {item["F2_换手率"]:>+7.2f} '
                  f'{item["F3_量比"]:>+6.2f} {item["F4_资金流"]:>+7.2f} {flag}')
        
        print("-"*72)
        print("  🔥🔥 过热 | ⚠️ 偏高 | ✅ 正常 | ❄️ 冷门")
        print("  （基于原文结论：高热度→散户情绪过热→后续收益倾向为负）")
    
    return ranking


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="股票热度分析工具 — 基于公开市场数据量化评估散户关注度",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
数据准备:
  先使用 finance-data-retrieval skill 获取数据并存为JSON文件，
  然后用本脚本进行因子分析和可视化。
  
示例:
  python3 stock_heat_analysis.py --data-dir ./fetched_data/600519/ --mode single
  python3 stock_heat_analysis.py --data-dir ./fetched_data/ --mode compare
        """)
    parser.add_argument("--data-dir", type=str, required=True,
                       help="预获取数据所在目录（必填）")
    parser.add_argument("--stock-code", type=str, default=None,
                       help="指定分析哪只股票（可选，不指定则自动发现）")
    parser.add_argument("--output-dir", type=str, default="./heat_output",
                       help="输出目录。默认: ./heat_output")
    parser.add_argument("--mode", type=str, default="single",
                       choices=["single", "compare"],
                       help="分析模式: single(单股详情) / compare(多股对比)")
    parser.add_argument("--top-n", type=int, default=20,
                       help="展示Top数量")
    
    args = parser.parse_args()
    
    _START = time.time()
    
    print("=" * 62)
    print("  🌡️  股票热度分析工具 v1.0 — 数据处理引擎")
    print("=" * 62)
    print(f"  数据目录:  {args.data_dir}")
    print(f"  分析模式:  {args.mode.upper()}")
    print(f"  输出目录:  {os.path.abspath(args.output_dir)}")
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 发现或指定股票
    if args.stock_code:
        stock_codes = [args.stock_code]
    else:
        stock_codes = discover_stocks(args.data_dir)
    
    if not stock_codes:
        print("\n❌ 未找到任何股票数据！请先获取数据放入 data-dir")
        sys.exit(1)
    
    print(f"\n  发现股票: {', '.join(stock_codes)} ({len(stock_codes)} 只)")
    
    # 数据加载与因子计算
    all_merged = {}
    all_factors = {}
    
    for ts_code in stock_codes:
        print(f"\n📊 [{ts_code}] 加载数据...")
        daily, basic, mf = load_stock_data(args.data_dir, ts_code)
        
        if not daily:
            print(f"  ⚠ {ts_code} 无日线数据，跳过")
            continue
        
        print(f"  合并: 日线{len(daily)}条 + 指标{len(basic)}条 + 资金{len(mf)}条")
        
        merged = merge_data(daily, basic, mf)
        print(f"  合并后有效记录: {len(merged)} 天")
        
        if not merged:
            continue
        
        factors = compute_all_factors(merged, ts_code)
        all_merged[ts_code] = merged
        all_factors[ts_code] = factors
    
    if not all_factors:
        print("\n❌ 没有有效的股票数据进行处理")
        sys.exit(1)
    
    # 标准化
    print(f"\n📐 标准化处理...")
    
    if args.mode == "compare" and len(all_factors) >= 2:
        latest_per_stock = [rows[-1] for rows in all_factors.values() if rows]
        cross_sectional_zscore(latest_per_stock, FACTOR_NAMES)
        
        for ts_code, rows in all_factors.items():
            time_series_zscore(rows, FACTOR_NAMES)
        print(f"  采用: 截面 + 时间序列混合标准化")
    else:
        for ts_code, rows in all_factors.items():
            time_series_zscore(rows, FACTOR_NAMES)
        print(f"  采用: 时间序列标准化（各股独立计算）")
    
    print(f"  ✅ {len(all_factors)} 只股票因子计算完毕")
    
    # 可视化
    print(f"\n📈 生成可视化...")
    
    combined_for_corr = []
    for rows in all_factors.values():
        combined_for_corr.extend(rows)
    
    if combined_for_corr:
        plot_factor_correlation(combined_for_corr, args.output_dir)
        
        if args.mode == "single":
            for ts_code, rows in all_factors.items():
                plot_timeline_heatmap(rows, args.output_dir, ts_code)
        else:
            for ts_code, rows in all_factors.items():
                plot_timeline_heatmap(rows, args.output_dir, ts_code)
    
    if args.mode == "compare" and len(all_factors) >= 2:
        plot_radar_compare(all_factors, args.output_dir)
    
    # 报告
    print(f"\n📝 生成分析报告...")
    generate_report(all_factors, args.mode, args.output_dir, args.top_n)
    
    # 风险提示
    elapsed = time.time() - _START
    print(f"\n{'='*62}")
    print("  ⚠️  风险提示 & 解读指南")
    print(f"{'='*62}")
    print("""
  【热度得分为正且较高】→ 散户关注度高 → 文章观点认为后续收益倾向为负
  【热度得分为负】→ 冷门股 → 逆向策略可能有机会
  
  本工具使用的7个代理因子：
    F1 成交额热度   F2 换手率热度   F3 量比热度
    F4 资金流向     F5 波动分歧    F6 成交波动
    F7 散户行为
  
  重要声明：
  • 公开市场数据 ≠ 软件内部用户行为数据，结果仅供参考研究
  • 本工具不构成任何投资建议
  • 历史规律不代表未来表现，投资有风险
    """)
    print(f"\n✅ 分析完成！耗时 {elapsed:.1f}s | 输出: {os.path.abspath(args.output_dir)}/")


if __name__ == "__main__":
    main()
