#!/usr/bin/env python3
"""
股票热度分析 v2 - 批量预测脚本 (batch_predict.py)
=====================================================
一次性对多只股票进行热度分析预测，输出汇总对比表。

用法:
    python3 batch_predict.py --codes 600000,000001,300750
    python3 batch_predict.py --codes 600000
    python3 batch_predict.py 600000 000001 300750

输出:
    - 每只股票的标准预测报告（复用predict.py逻辑）
    - 汇总对比表（方向、置信度、热度、趋势状态）
    - 所有股票的可视化图表（可选）
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 导入predict.py的核心函数
sys.path.insert(0, str(Path(__file__).parent))
from predict import (
    load_kline, load_realtime,
    compute_all_factors, time_series_zscore,
    predict_tomorrow, print_summary, save_prediction,
    track_recent_5days, calc_accuracy
)


# ============================================================
# 批量预测核心逻辑
# ============================================================

def batch_predict(codes: list, data_dir: str, output_dir: str) -> list:
    """
    对多只股票进行批量预测。
    返回每只股票的预测结果列表。
    """
    results = []
    
    for i, code in enumerate(codes):
        print("\n" + "=" * 62)
        print(f"  📊 批量处理 ({i+1}/{len(codes)}) — 股票代码: {code}")
        print("=" * 62)
        
        # 1. 读取数据
        kline = load_kline(code, data_dir)
        if not kline:
            print(f"  ❌ 跳过 {code}（K线数据加载失败）")
            results.append({
                "code": code,
                "error": "K线数据加载失败",
                "success": False,
            })
            continue
        
        realtime = load_realtime(code, data_dir)
        
        # 2. 计算因子
        print(f"  >> 计算7个热度因子...")
        factor_rows = compute_all_factors(kline)
        time_series_zscore(factor_rows)
        print(f"  ✅ 因子计算完成，综合热度: {factor_rows[-1]['heat_score']:+.3f}")
        
        # 3. 生成预测
        print(f"  >> 生成预测...")
        prediction = predict_tomorrow(factor_rows, kline)
        
        # 4. 近5日追踪
        tracking = track_recent_5days(code, output_dir, kline)
        acc = calc_accuracy(tracking)
        
        # 5. 打印摘要
        print_summary(code, kline, realtime, factor_rows, prediction, tracking)
        
        # 6. 保存结果
        result_path = save_prediction(
            code, kline, factor_rows, prediction, tracking, output_dir
        )
        
        # 7. 记录结果
        results.append({
            "code": code,
            "success": True,
            "prediction": prediction,
            "tracking": tracking,
            "accuracy": acc,
            "result_path": result_path,
            "heat_score": factor_rows[-1]['heat_score'],
        })
    
    return results


def print_batch_summary(codes: list, results: list, output_dir: str):
    """
    打印批量预测汇总对比表。
    """
    print("\n" + "=" * 78)
    print("  📊 批量预测汇总对比表")
    print("=" * 78)
    
    # 表头
    print(f"\n  {'代码':<10} {'名称':<10} {'预测方向':<15} {'概率':>6} {'置信度':<8} {'热度':>8} {'趋势状态':<18}")
    print("  " + "-" * 76)
    
    successful = 0
    for r in results:
        if not r.get("success"):
            print(f"  {r['code']:<10} {'-':<10} {'-':<15} {'-':>6} {'-':<8} {'-':>8} {'-':<18}")
            continue
        
        successful += 1
        p = r["prediction"]
        code = r["code"]
        
        # 尝试读取股票名称
        name = code
        try:
            realtime_path = Path(output_dir).parent / "data" / f"{code}_realtime.json"
            if realtime_path.exists():
                with open(realtime_path, "r", encoding="utf-8") as f:
                    rt = json.load(f)
                    name = rt.get("name", code)
        except:
            pass
        
        # 方向emoji
        dir_emoji = "📈" if "上涨" in p["direction"] or "偏多" in p["direction"] else \
                    ("📉" if "下跌" in p["direction"] or "偏空" in p["direction"] else "↔️")
        
        print(f"  {code:<10} {name[:8]:<10} {dir_emoji}{p['direction']:<14} "
              f"{p['probability']*100:>5.0f}% {p['confidence']:<8} "
              f"{p['heat_score']:>+7.3f} {p.get('trend_state', '-'):<18}")
    
    print("  " + "-" * 76)
    print(f"  成功: {successful}/{len(codes)}")
    
    # 统计：上涨/下跌/震荡分布
    up = sum(1 for r in results if r.get("success") and 
             ("上涨" in r["prediction"]["direction"] or "偏多" in r["prediction"]["direction"]))
    down = sum(1 for r in results if r.get("success") and 
               ("下跌" in r["prediction"]["direction"] or "偏空" in r["prediction"]["direction"]))
    neutral = sum(1 for r in results if r.get("success") and 
                  "震荡" in r["prediction"]["direction"])
    
    print(f"  分布: 📈上涨={up}  📉下跌={down}  ↔️震荡={neutral}")
    print("=" * 78 + "\n")
    
    # 输出JSON汇总（供程序调用）
    summary = {
        "total": len(codes),
        "successful": successful,
        "distribution": {"up": up, "down": down, "neutral": neutral},
        "results": [
            {
                "code": r["code"],
                "direction": r.get("prediction", {}).get("direction", ""),
                "probability": r.get("prediction", {}).get("probability", 0),
                "confidence": r.get("prediction", {}).get("confidence", ""),
                "heat_score": r.get("heat_score", 0),
                "trend_state": r.get("prediction", {}).get("trend_state", ""),
                "result_path": r.get("result_path", ""),
            }
            for r in results if r.get("success")
        ],
    }
    
    summary_path = Path(output_dir) / f"batch_summary_{len(codes)}stocks.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 汇总结果 → {summary_path}\n")


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="股票热度分析 v2 — 批量预测脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 批量预测3只股票
  python3 batch_predict.py --codes 002050,603885,300475
  
  # 批量预测1只股票（与predict.py类似）
  python3 batch_predict.py --codes 002050
  
  # 使用位置参数（空格分隔）
  python3 batch_predict.py 002050 603885 300475
  
  # 指定数据目录和输出目录
  python3 batch_predict.py --codes 002050,603885 --data-dir /tmp/data --output-dir ./output
        """
    )
    
    # 支持 --codes 参数或位置参数
    parser.add_argument("--codes", type=str, default=None,
                        help="股票代码列表，逗号分隔，如 002050,603885,300475")
    parser.add_argument("positional_codes", nargs="*", 
                        help="位置参数：股票代码列表（空格分隔）")
    parser.add_argument("--data-dir", type=str, default="./data",
                        help="K线数据目录（默认 ./data）")
    parser.add_argument("--output-dir", type=str, default="./output",
                        help="预测结果输出目录（默认 ./output）")
    
    args = parser.parse_args()
    
    # 解析股票代码
    codes = []
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if args.positional_codes:
        codes.extend([c.strip() for c in args.positional_codes if c.strip()])
    
    if not codes:
        print("❌ 错误: 请提供至少一个股票代码")
        print("\n使用示例:")
        print("  python3 batch_predict.py --codes 002050,603885,300475")
        sys.exit(1)
    
    # 去重
    codes = list(dict.fromkeys(codes))
    
    print("=" * 58)
    print("  🌡️  股票热度分析 v2 — 批量预测引擎")
    print("=" * 58)
    print(f"  股票代码: {', '.join(codes)}")
    print(f"  数据目录: {os.path.abspath(args.data_dir)}")
    print(f"  输出目录: {os.path.abspath(args.output_dir)}")
    print(f"  股票数量: {len(codes)}")
    
    # 批量预测
    results = batch_predict(codes, args.data_dir, args.output_dir)
    
    # 打印汇总对比表
    print_batch_summary(codes, results, args.output_dir)
    
    # 输出给调用方捕获
    summary = {
        "total": len(codes),
        "successful": sum(1 for r in results if r.get("success")),
        "codes": [r["code"] for r in results if r.get("success")],
    }
    print(f"__BATCH_RESULT__:{json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
