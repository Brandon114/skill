#!/usr/bin/env python3
"""
股票热度分析 - 数据获取器 (Data Fetcher)
==========================================
通过 finance-data 接口获取指定股票的日线、每日指标、资金流向数据，
保存为 JSON 文件，供 stock_heat_analysis.py 分析引擎使用。

用法:
    python3 fetch_data.py --stocks "600519.SH,000858.SZ,300750.SZ" --days 30 --output-dir ./fetched_data/

输出:
  ./fetched_data/
    600519_SH/
      daily.json       — 日线行情（OHLCV）
      daily_basic.json  — 每日指标（换手率、量比、市值）
      moneyflow.json    — 资金流向（大小单、净流入）
    000858_SZ/
      ...
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# API 调用配置
# ============================================================

API_URL = "https://www.codebuddy.cn/v2/tool/financedata"

# 注意：此脚本需要在 WorkBuddy 环境内运行，
# 或者设置 CODEBUDDY_API_TOKEN 环境变量


def call_finance_api(api_name: str, params: dict, fields: str = "") -> dict:
    """调用金融数据接口"""
    try:
        import urllib.request
        
        payload = {"api_name": api_name, "params": params}
        if fields:
            payload["fields"] = fields
        
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            
        if result.get("code") != 0:
            print(f"    ⚠ API {api_name} 错误: {result.get('msg', '未知')}")
            return None
        return result.get("data", {})
    
    except Exception as e:
        # 尝试使用 requests 作为后备
        try:
            import requests as req_lib
            
            payload = {"api_name": api_name, "params": params}
            if fields:
                payload["fields"] = fields
            
            r = req_lib.post(API_URL, json=payload, timeout=60)
            result = r.json()
            
            if result.get("code") != 0:
                print(f"    ⚠ API {api_name} 错误: {result.get('msg', '未知')}")
                return None
            return result.get("data", {})
            
        except ImportError:
            pass
        
        print(f"    ⚠ API {api_name} 调用失败: {e}")
        return None


def save_json(data: dict | list, filepath: str):
    """保存数据到 JSON 文件"""
    path = Path(filepath)
    os.makedirs(path.parent, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_stock_data(ts_code: str, start_date: str, end_date: str, output_dir: str) -> bool:
    """
    获取单只股票的全部数据。
    
    返回 True 表示至少获取到了一种有效数据。
    """
    code_safe = ts_code.replace(".", "_")
    stock_dir = Path(output_dir) / code_safe
    
    has_any_data = False
    
    # 1. 日线行情
    print(f"  📥 获取 {ts_code} 日线行情...")
    daily_data = call_finance_api("daily", {
        "ts_code": ts_code,
        "start_date": start_date,
        "end_date": end_date,
    })
    
    if daily_data and daily_data.get("items"):
        save_json(daily_data, stock_dir / "daily.json")
        count = len(daily_data["items"])
        print(f"     ✅ 日线 {count} 条")
        has_any_data = True
    else:
        print(f"     ⚠ 日线无数据")
    
    # 2. 每日指标
    print(f"  📥 获取 {ts_code} 每日指标...")
    basic_data = call_finance_api("daily_basic", {
        "ts_code": ts_code,
        "start_date": start_date,
        "end_date": end_date,
        "fields": "ts_code,trade_date,close,turnover_rate,volume_ratio,"
                   "pe,pb,total_mv,circ_mv",
    })
    
    if basic_data and basic_data.get("items"):
        save_json(basic_data, stock_dir / "daily_basic.json")
        count = len(basic_data["items"])
        print(f"     ✅ 指标 {count} 条")
        has_any_data = True
    else:
        print(f"     ⚠ 指标无数据")
    
    # 3. 资金流向
    print(f"  📥 获取 {ts_code} 资金流向...")
    mf_data = call_finance_api("moneyflow", {
        "ts_code": ts_code,
        "start_date": start_date,
        "end_date": end_date,
        "fields": "ts_code,trade_date,buy_sm_amount,sell_sm_amount,"
                   "buy_lg_amount,sell_lg_amount,"
                   "buy_elg_amount,sell_elg_amount,net_mf_amount",
    })
    
    if mf_data and mf_data.get("items"):
        save_json(mf_data, stock_dir / "moneyflow.json")
        count = len(mf_data["items"])
        print(f"     ✅ 资金流 {count} 条")
        has_any_data = True
    else:
        print(f"     ⚠ 资金流无数据")
    
    return has_any_data


def main():
    parser = argparse.ArgumentParser(
        description="获取股票热度分析所需的基础数据"
    )
    parser.add_argument("--stocks", type=str, required=True,
                       help="股票代码列表（逗号分隔），如：600519.SH,000858.SZ")
    parser.add_argument("--days", type=int, default=30,
                       help="回溯交易日天数（默认30）")
    parser.add_argument("--output-dir", type=str, default="./fetched_data",
                       help="数据输出目录（默认./fetched_data）")
    
    args = parser.parse_args()
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=args.days * 2)).strftime("%Y%m%d")
    
    print("=" * 56)
    print("  🌡️  股票热度分析 — 数据获取器")
    print("=" * 56)
    print(f"  时间范围: {start_date} ~ {end_date}")
    print(f"  输出目录: {os.path.abspath(args.output_dir)}")
    print()
    
    stock_list = [s.strip() for s in args.stocks.split(",")]
    
    success_count = 0
    for i, ts_code in enumerate(stock_list):
        print(f"\n[{i+1}/{len(stock_list)}] 📊 {ts_code}")
        ok = fetch_stock_data(ts_code, start_date, end_date, args.output_dir)
        if ok:
            success_count += 1
    
    print(f"\n{'='*56}")
    if success_count > 0:
        print(f"  ✅ 数据获取完成！{success_count}/{len(stock_list)} 只股票成功")
        print(f"  📁 数据位置: {os.path.abspath(args.output_dir)}/")
        print(f"\n  下一步:")
        print(f'    python3 scripts/stock_heat_analysis.py \\')
        print(f'      --data-dir {args.output_dir} \\')
        print(f'      --mode compare --top-n 10')
    else:
        print(f"  ❌ 所有股票均未获取到数据")
        print(f"  请确认网络连接和 API 认证状态")


if __name__ == "__main__":
    main()
