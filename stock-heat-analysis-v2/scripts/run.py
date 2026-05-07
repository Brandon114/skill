#!/usr/bin/env python3
"""
股票热度分析 v2 - 主入口 (run.py)
=====================================
一条命令完成"数据获取 → 热度分析 → 预测输出"全流程。
内部串联 fetch_public.py 和 predict.py，AI 只需读取最终 JSON 即可解释结果。

用法:
    python3 run.py --code 600000
    python3 run.py --code 600000 --days 40
    python3 run.py --code 600000,000001,300750  # 批量分析多只股票

输出:
    ./output/{code}_kline.json         — K线数据
    ./output/{code}_realtime.json      — 实时行情
    ./output/{code}_predict_TODAY.json — 分析预测结果（AI重点读此文件）
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()


def run_script(script_name: str, args_list: list) -> tuple:
    """
    运行子脚本，返回 (success: bool, result_dict: dict)。
    通过捕获标准输出中 __RESULT__:... 行获取结构化结果。
    """
    cmd = [sys.executable, str(SCRIPT_DIR / script_name)] + args_list
    print(f"\n  ▶ 运行: {script_name} {' '.join(args_list)}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=False,  # 让输出直接打印到终端
            text=True,
            timeout=60,
        )

        # 重新运行一次以捕获 __RESULT__ 行（不影响终端输出）
        proc2 = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        result = {}
        for line in proc2.stdout.splitlines():
            if line.startswith("__RESULT__:"):
                try:
                    result = json.loads(line[len("__RESULT__:"):])
                except Exception:
                    pass

        success = proc.returncode == 0
        return success, result

    except subprocess.TimeoutExpired:
        print(f"  ❌ 超时（60s）")
        return False, {}
    except Exception as e:
        print(f"  ❌ 运行出错: {e}")
        return False, {}


def analyze_single(code: str, days: int, output_dir: str) -> dict:
    """
    对单只股票执行完整分析流程。
    返回分析摘要字典。
    """
    code = code.strip()
    print(f"\n{'='*62}")
    print(f"  📊 分析股票: {code}")
    print(f"{'='*62}")

    # Step 1: 获取数据
    print(f"\n[Step 1/2] 数据获取...")
    ok1, fetch_result = run_script("fetch_public.py", [
        "--code",       code,
        "--days",       str(days),
        "--output-dir", output_dir,
    ])

    if not ok1:
        # 如果实时运行有问题，让用户看到子脚本输出后中断
        print(f"  ⚠ fetch_public.py 退出码非零，尝试继续...")

    # Step 2: 因子分析与预测
    print(f"\n[Step 2/2] 热度分析与预测...")
    ok2, predict_result = run_script("predict.py", [
        "--code",             code,
        "--data-dir",         output_dir,
        "--output-dir",       output_dir,
        "--pred-history-dir", output_dir,
    ])

    if not ok2:
        print(f"  ⚠ predict.py 退出码非零")

    return {
        "code":        code,
        "success":     ok2,
        "direction":   predict_result.get("direction", ""),
        "probability": predict_result.get("probability", 0),
        "confidence":  predict_result.get("confidence", ""),
        "heat_score":  predict_result.get("heat_score", 0),
        "result_path": predict_result.get("result_path", ""),
    }


def print_batch_summary(results: list):
    """批量分析结果汇总表"""
    if len(results) <= 1:
        return

    print(f"\n{'='*62}")
    print(f"  📋 批量分析汇总")
    print(f"{'='*62}")
    print(f"  {'代码':<10} {'热度':>7} {'方向':<12} {'概率':>6} {'置信度':<8} {'状态'}")
    print("  " + "-" * 56)
    for r in results:
        status = "✅" if r["success"] else "⚠"
        heat = r.get("heat_score", 0)
        heat_str = f"{heat:+.3f}"
        prob = r.get("probability", 0)
        prob_str = f"{prob*100:.0f}%" if prob else "-"
        print(f"  {r['code']:<10} {heat_str:>7} {r['direction']:<12} "
              f"{prob_str:>6} {r['confidence']:<8} {status}")
    print("  " + "-" * 56)
    print(f"\n  输出目录: {os.path.abspath(results[0].get('result_path', '.') or '.')}")


def main():
    parser = argparse.ArgumentParser(
        description="股票热度分析 v2 — 全流程主入口（数据获取+热度分析+预测）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  # 分析单只股票
  python3 run.py --code 600000

  # 自定义天数
  python3 run.py --code 600000 --days 40

  # 批量分析多只股票（逗号分隔）
  python3 run.py --code 600000,000001,300750

  # 指定输出目录
  python3 run.py --code 600000 --output-dir /tmp/heat_output

  # AI调用后直接读取结果
  # 分析完成后，读取 ./output/{code}_predict_YYYYMMDD.json
        """
    )
    parser.add_argument("--code",       type=str, required=True,
                        help="股票代码，单只如 600000，多只用逗号分隔如 600000,000001")
    parser.add_argument("--days",       type=int, default=40,
                        help="回溯交易日天数（默认40，约2个月历史数据）")
    parser.add_argument("--output-dir", type=str, default="./output",
                        help="所有输出文件目录（默认 ./output）")

    args = parser.parse_args()

    # 解析股票列表
    codes = [c.strip() for c in args.code.split(",") if c.strip()]
    if not codes:
        print("❌ 未指定有效股票代码")
        sys.exit(1)

    output_dir = os.path.abspath(args.output_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 62)
    print("  🌡️  股票热度分析 v2 — 全流程主入口")
    print("=" * 62)
    print(f"  股票列表: {', '.join(codes)}")
    print(f"  回溯天数: {args.days}")
    print(f"  输出目录: {output_dir}")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 逐只分析
    all_results = []
    for code in codes:
        result = analyze_single(code, args.days, output_dir)
        all_results.append(result)

    # 批量汇总（多只时显示）
    print_batch_summary(all_results)

    # 完成提示
    print(f"\n{'='*62}")
    print(f"  ✅ 全部分析完成！")
    print(f"  📁 结果目录: {output_dir}")
    print(f"\n  AI 读取以下文件解释结果:")
    today = datetime.now().strftime("%Y%m%d")
    for r in all_results:
        pred_file = Path(output_dir) / f"{r['code']}_predict_{today}.json"
        print(f"    {pred_file}")
    print(f"\n  ⚠️  风险提示：本工具仅供研究参考，不构成任何投资建议")
    print(f"{'='*62}\n")

    # 汇总输出供 AI 捕获
    summary = {
        "success": all([r["success"] for r in all_results]),
        "codes": codes,
        "output_dir": output_dir,
        "results": all_results,
        "today": today,
    }
    print(f"__RESULT__:{json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
