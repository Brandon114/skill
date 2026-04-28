#!/usr/bin/env python3
"""
生成模拟股票数据 — 用于测试和演示 stock_heat_analysis.py 分析引擎

用法:
    python3 gen_mock_data.py --output-dir ./test_data/
"""

import argparse
import json
import math
import os
import random
from datetime import datetime, timedelta
from pathlib import Path


def gen_mock_daily(ts_code: str, start_date: str, end_date: str,
                  base_price: float = 100.0, volatility: float = 0.02) -> list[dict]:
    """生成模拟日线数据（OHLCV）"""
    results = []
    
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    price = base_price
    
    current = start
    while current <= end:
        # 跳过周末
        if current.weekday() < 5:
            change_pct = random.gauss(0.0005, volatility)
            
            open_p = price * (1 + random.gauss(0, volatility * 0.5))
            close_p = price * (1 + change_pct)
            high_p = max(open_p, close_p) * (1 + abs(random.gauss(0, volatility * 0.3)))
            low_p = min(open_p, close_p) * (1 - abs(random.gauss(0, volatility * 0.3)))
            
            vol = abs(change_pct) * base_price * random.uniform(50000, 200000)
            amount = vol * (open_p + close_p) / 2 / 100  # 成交额(千元)
            
            trade_date = current.strftime("%Y%m%d")
            
            pct_chg = (close_p - price) / price * 100 if price > 0 else 0
            
            results.append({
                "ts_code": ts_code,
                "trade_date": trade_date,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "pre_close": round(price, 2),
                "change": round(close_p - price, 2),
                "pct_chg": round(pct_chg, 3),
                "vol": round(vol, 1),
                "amount": round(amount, 2),
            })
            
            price = close_p
        
        current += timedelta(days=1)
    
    return results


def gen_mock_basic(ts_code: str, daily_list: list[dict],
                   avg_turnover: float = 2.0, avg_volume_ratio: float = 1.0) -> list[dict]:
    """根据日线数据生成匹配的每日指标数据"""
    results = []
    
    for d in daily_list:
        turnover = max(0.01, random.gauss(avg_turnover, avg_turnover * 0.6))
        vr = max(0.3, random.gauss(avg_volume_ratio, 0.4))
        close = d["close"]
        total_mv = close * random.uniform(50, 800) * 10000  # 模拟总市值
        circ_mv = total_mv * random.uniform(0.7, 1.0)
        
        results.append({
            "ts_code": ts_code,
            "trade_date": d["trade_date"],
            "close": close,
            "turnover_rate": round(turnover, 4),
            "volume_ratio": round(vr, 4),
            "pe_ttm": round(random.uniform(15, 60), 2) if random.random() > 0.05 else None,
            "pb": round(random.uniform(2, 15), 2),
            "total_mv": round(total_mv, 2),
            "circ_mv": round(circ_mv, 2),
        })
    
    return results


def gen_mock_moneyflow(ts_code: str, daily_list: list[dict],
                       retail_bias: float = 0.0) -> list[dict]:
    """
    生成资金流向数据
    retail_bias > 0 表示散户偏多买入（高热度特征）
    """
    results = []
    
    for i, d in enumerate(daily_list):
        total_amount = d.get("amount", 100000) / 10  # 转为万元级别
        
        sm_ratio = 0.25 + retail_bias * random.uniform(-0.1, 0.15)
        md_ratio = 0.30
        lg_ratio = 0.28 - retail_bias * 0.05
        elg_ratio = 0.17 - retail_bias * 0.08
        
        buy_sm = total_amount * sm_ratio * random.uniform(0.35, 0.65)
        sell_sm = total_amount * sm_ratio - buy_sm
        
        buy_md = total_amount * md_ratio * random.uniform(0.40, 0.60)
        sell_md = total_amount * md_ratio - buy_md
        
        buy_lg = total_amount * lg_ratio * random.uniform(0.42, 0.58)
        sell_lg = total_amount * lg_ratio - buy_lg
        
        buy_elg = total_amount * elg_ratio * random.uniform(0.45, 0.55)
        sell_elg = total_amount * elg_ratio - buy_elg
        
        net_mf = (buy_sm + buy_md + buy_lg + buy_elg) - \
                 (sell_sm + sell_md + sell_lg + sell_elg)
        
        results.append({
            "ts_code": ts_code,
            "trade_date": d["trade_date"],
            "buy_sm_vol": int(buy_sm * 100 / 100),  # 近似
            "buy_sm_amount": round(buy_sm, 2),
            "sell_sm_amount": round(sell_sm, 2),
            "buy_md_amount": round(buy_md, 2),
            "sell_md_amount": round(sell_md, 2),
            "buy_lg_amount": round(buy_lg, 2),
            "sell_lg_amount": round(sell_lg, 2),
            "buy_elg_amount": round(buy_elg, 2),
            "sell_elg_amount": round(sell_elg, 2),
            "net_mf_amount": round(net_mf, 2),
        })
    
    return results


def main():
    parser = argparse.ArgumentParser(description="生成模拟股票数据")
    parser.add_argument("--output-dir", type=str, default="./test_data",
                       help="输出目录")
    parser.add_argument("--days", type=int, default=30,
                       help="交易日数量")
    args = parser.parse_args()
    
    random.seed(42)  # 固定随机种子保证可复现
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    end = datetime.now()
    start = end - timedelta(days=args.days * 2)
    
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")
    
    # 定义三只不同特征的股票
    stocks_config = [
        {
            "code": "600519.SH",
            "name": "贵州茅台",
            "base_price": 1700.0,
            "volatility": 0.015,
            "avg_turnover": 0.8,
            "retail_bias": 0.1,   # 中等散户关注度
        },
        {
            "code": "000858.SZ",
            "name": "五粮液",
            "base_price": 145.0,
            "volatility": 0.022,
            "avg_turnover": 1.8,
            "retail_bias": 0.3,   # 较高散户关注度
        },
        {
            "code": "300750.SZ",
            "name": "宁德时代",
            "base_price": 220.0,
            "volatility": 0.030,
            "avg_turnover": 3.5,
            "retail_bias": 0.5,   # 高散户关注度（热门股）
        },
    ]
    
    for cfg in stocks_config:
        code_safe = cfg["code"].replace(".", "_")
        out_dir = Path(args.output_dir) / code_safe
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📝 生成 {cfg['name']} ({cfg['code']}) 模拟数据...")
        
        daily = gen_mock_daily(cfg["code"], start_str, end_str,
                               cfg["base_price"], cfg["volatility"])
        basic = gen_mock_basic(cfg["code"], daily, cfg["avg_turnover"])
        mf = gen_mock_moneyflow(cfg["code"], daily, cfg["retail_bias"])
        
        with open(out_dir / "daily.json", "w") as f:
            json.dump({"fields": list(daily[0].keys()), "items": [list(d.values()) for d in daily]}, f, ensure_ascii=False)
        
        with open(out_dir / "daily_basic.json", "w") as f:
            json.dump({"fields": list(basic[0].keys()), "items": [list(b.values()) for b in basic]}, f, ensure_ascii=False)
        
        with open(out_dir / "moneyflow.json", "w") as f:
            json.dump({"fields": list(mf[0].keys()), "items": [list(m.values()) for m in mf]}, f, ensure_ascii=False)
        
        print(f"   日线: {len(daily)} 天 | 指标: {len(basic)} | 资金流: {len(mf)} → {out_dir}/")
    
    print(f"\n✅ 模拟数据生成完成！输出到: {args.output_dir}")
    print("\n下一步:")
    print(f"  python3 scripts/stock_heat_analysis.py \\")
    print(f"    --data-dir {args.output_dir} \\")
    print(f"    --mode compare")


if __name__ == "__main__":
    main()
