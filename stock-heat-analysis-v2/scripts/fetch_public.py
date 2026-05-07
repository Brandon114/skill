#!/usr/bin/env python3
"""
股票热度分析 v2 - 公开数据源获取器 (fetch_public.py)
=====================================================
使用完全公开、无需认证的数据源获取A股历史K线和实时行情。

数据源优先级（历史K线）:
  1. 同花顺 d.10jqka.com.cn  ← 主力，稳定，返回近200条日线
  2. 东方财富 push2his.eastmoney.com ← 备用，HTTPS可能不稳定
  3. 报错退出（不自动降级到模拟数据，保证分析质量）

数据源（实时行情）:
  1. 新浪财经 hq.sinajs.cn  ← 主力，实时准确
  2. 东方财富实时  ← 备用

用法:
    python3 fetch_public.py --code 600000 [--days 30] [--output-dir ./data]
    python3 fetch_public.py --code 600000 --no-realtime  # 仅历史K线

输出:
    ./data/600000_kline.json    — 历史K线（含近N个交易日）
    ./data/600000_realtime.json — 今日实时行情（非交易时段为最近收盘价）
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


# ============================================================
# 工具函数
# ============================================================

def _make_request(url: str, headers: dict = None, encoding: str = "utf-8",
                  timeout: int = 12) -> str:
    """发送HTTP请求，返回文本内容。失败返回None。"""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    if headers:
        default_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return raw.decode(encoding, errors="replace")
    except Exception as e:
        return None


def _infer_market(code: str) -> str:
    """根据股票代码推断市场前缀：sh（沪）或 sz（深）"""
    code = code.strip()
    if code.startswith("6"):
        return "sh"
    elif code.startswith(("0", "3")):
        return "sz"
    elif code.startswith("8") or code.startswith("4"):
        return "bj"  # 北交所
    return "sh"  # 默认沪市


def _safe_float(val, default=0.0) -> float:
    """安全转换为float"""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ============================================================
# 数据源1：同花顺历史K线
# ============================================================

def fetch_kline_10jqka(code: str, days: int = 60) -> list:
    """
    从同花顺获取历史日线K线数据（近200条，无需认证）。

    返回: list of dict，每条包含:
      date, open, high, low, close, vol(股), amount(元), turnover(%)
    失败返回 None。
    """
    market = _infer_market(code)
    # 同花顺北交所代码格式特殊，暂用sh前缀兼容
    if market == "bj":
        market = "sh"
    url = f"http://d.10jqka.com.cn/v2/line/hs_{code}/01/last200.js"

    raw = _make_request(url)
    if not raw:
        print(f"  [同花顺] 请求失败：{url}")
        return None

    m = re.search(r'\((\{.*\})\)', raw, re.DOTALL)
    if not m:
        print(f"  [同花顺] 响应格式异常，无法解析JSON")
        return None

    try:
        jdata = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"  [同花顺] JSON解析失败: {e}")
        return None

    raw_data = jdata.get("data", "")
    if not raw_data:
        print(f"  [同花顺] 数据为空")
        return None

    records = []
    prev_close = None

    for entry in raw_data.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(",")
        if len(parts) < 7:
            continue
        try:
            rec = {
                "date":     parts[0],
                "open":     _safe_float(parts[1]),
                "high":     _safe_float(parts[2]),
                "low":      _safe_float(parts[3]),
                "close":    _safe_float(parts[4]),
                "vol":      _safe_float(parts[5]),      # 单位：股
                "amount":   _safe_float(parts[6]),      # 单位：元
                "turnover": _safe_float(parts[7]) if len(parts) > 7 else 0.0,  # %
            }
            # 计算涨跌幅
            if prev_close and prev_close > 0:
                rec["pct_chg"] = round((rec["close"] - prev_close) / prev_close * 100, 3)
            else:
                rec["pct_chg"] = 0.0
            prev_close = rec["close"]
            records.append(rec)
        except Exception:
            continue

    if not records:
        print(f"  [同花顺] 解析出0条记录")
        return None

    # 只保留最近 days*2 个自然日对应的交易日（近似）
    # 实际按交易日取，直接截取尾部 days 条
    recent = records[-days:] if len(records) > days else records
    print(f"  [同花顺] ✅ 获取 {len(recent)} 条日线（总计 {len(records)} 条）")
    return recent


# ============================================================
# 数据源2：东方财富历史K线（备用）
# ============================================================

def fetch_kline_eastmoney(code: str, days: int = 60) -> list:
    """
    从东方财富获取历史日线K线（备用数据源）。

    返回格式同 fetch_kline_10jqka。
    失败返回 None。
    """
    market = _infer_market(code)
    # 东方财富的 secid 格式：1.600519(沪) / 0.000001(深)
    secid_prefix = "1" if market == "sh" else "0"
    secid = f"{secid_prefix}.{code}"

    url = (
        f"http://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}"
        f"&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=101&fqt=1&lmt={days + 10}&end=20991231"
    )

    headers = {"Referer": "http://quote.eastmoney.com/"}
    raw = _make_request(url, headers=headers)
    if not raw:
        print(f"  [东方财富] 请求失败")
        return None

    try:
        jdata = json.loads(raw)
    except Exception:
        print(f"  [东方财富] JSON解析失败")
        return None

    klines = jdata.get("data", {})
    if not klines:
        print(f"  [东方财富] data为空")
        return None

    kline_list = klines.get("klines", [])
    if not kline_list:
        print(f"  [东方财富] klines列表为空")
        return None

    records = []
    prev_close = None
    for item in kline_list:
        parts = item.split(",")
        if len(parts) < 7:
            continue
        try:
            date_str = parts[0].replace("-", "")  # 20260428
            close = _safe_float(parts[2])
            rec = {
                "date":     date_str,
                "open":     _safe_float(parts[1]),
                "close":    close,
                "high":     _safe_float(parts[3]),
                "low":      _safe_float(parts[4]),
                "vol":      _safe_float(parts[5]) * 100,  # 东方财富单位是手，转股
                "amount":   _safe_float(parts[6]),
                "turnover": _safe_float(parts[10]) if len(parts) > 10 else 0.0,
            }
            if prev_close and prev_close > 0:
                rec["pct_chg"] = round((rec["close"] - prev_close) / prev_close * 100, 3)
            else:
                rec["pct_chg"] = 0.0
            prev_close = close
            records.append(rec)
        except Exception:
            continue

    if not records:
        print(f"  [东方财富] 解析出0条记录")
        return None

    recent = records[-days:] if len(records) > days else records
    print(f"  [东方财富] ✅ 获取 {len(recent)} 条日线（备用）")
    return recent


# ============================================================
# 数据源3：新浪财经实时行情
# ============================================================

def fetch_realtime_sina(code: str) -> dict:
    """
    从新浪财经获取实时行情（交易时段返回实时价，收盘后返回收盘价）。

    返回 dict，包含:
      name, current, prev_close, open, high, low
      vol(股), amount(元), turnover_est(换手率估算%)
      amplitude(振幅%), pct_chg(涨跌幅%), time
    失败返回 None。
    """
    market = _infer_market(code)
    # 北交所用bj前缀
    if market == "bj":
        mkt_prefix = "bj"
    else:
        mkt_prefix = market
    symbol = f"{mkt_prefix}{code}"
    url = f"http://hq.sinajs.cn/list={symbol}"

    raw = _make_request(url, headers={"Referer": "http://finance.sina.com.cn"}, encoding="gbk")
    if not raw:
        print(f"  [新浪实时] 请求失败")
        return None

    m = re.search(r'"([^"]+)"', raw)
    if not m:
        print(f"  [新浪实时] 响应格式异常")
        return None

    fields = m.group(1).split(",")
    if len(fields) < 10:
        print(f"  [新浪实时] 字段不足（{len(fields)}个）")
        return None

    try:
        cur   = _safe_float(fields[3])
        prev  = _safe_float(fields[2])
        high  = _safe_float(fields[4])
        low   = _safe_float(fields[5])
        vol   = _safe_float(fields[8])    # 股
        amt   = _safe_float(fields[9])    # 元

        pct_chg  = (cur - prev) / prev * 100 if prev > 0 else 0.0
        amplitude = (high - low) / prev * 100 if prev > 0 else 0.0

        result = {
            "name":         fields[0],
            "current":      cur,
            "prev_close":   prev,
            "open":         _safe_float(fields[1]),
            "high":         high,
            "low":          low,
            "vol":          vol,
            "amount":       amt,
            "pct_chg":      round(pct_chg, 3),
            "amplitude":    round(amplitude, 3),
            "time":         fields[31] if len(fields) > 31 else "",
        }
        print(f"  [新浪实时] ✅ {result['name']} 当前:{cur:.2f} 涨跌:{pct_chg:+.2f}%")
        return result

    except Exception as e:
        print(f"  [新浪实时] 解析失败: {e}")
        return None


# ============================================================
# 数据源4：东方财富实时行情（备用）
# ============================================================

def fetch_realtime_eastmoney(code: str) -> dict:
    """东方财富实时行情（新浪失败时备用）"""
    market = _infer_market(code)
    secid_prefix = "1" if market == "sh" else "0"
    secid = f"{secid_prefix}.{code}"
    url = (
        f"http://push2.eastmoney.com/api/qt/stock/get"
        f"?secid={secid}"
        f"&fields=f43,f44,f45,f46,f47,f48,f57,f58,f169,f170,f116,f117"
    )

    headers = {"Referer": "http://quote.eastmoney.com/"}
    raw = _make_request(url, headers=headers)
    if not raw:
        return None

    try:
        jdata = json.loads(raw)
        d = jdata.get("data", {})
        if not d:
            return None

        cur  = _safe_float(d.get("f43", 0)) / 100
        prev = _safe_float(d.get("f60", 0)) / 100
        high = _safe_float(d.get("f44", 0)) / 100
        low  = _safe_float(d.get("f45", 0)) / 100
        vol  = _safe_float(d.get("f47", 0)) * 100
        amt  = _safe_float(d.get("f48", 0)) * 10000

        pct_chg = (cur - prev) / prev * 100 if prev > 0 else 0.0
        amplitude = (high - low) / prev * 100 if prev > 0 else 0.0

        result = {
            "name":       d.get("f58", code),
            "current":    cur,
            "prev_close": prev,
            "open":       _safe_float(d.get("f46", 0)) / 100,
            "high":       high,
            "low":        low,
            "vol":        vol,
            "amount":     amt,
            "pct_chg":    round(pct_chg, 3),
            "amplitude":  round(amplitude, 3),
            "time":       "",
        }
        print(f"  [东方财富实时] ✅ {result['name']} 当前:{cur:.2f} 涨跌:{pct_chg:+.2f}% （备用）")
        return result

    except Exception as e:
        print(f"  [东方财富实时] 解析失败: {e}")
        return None


# ============================================================
# 主获取逻辑（带 fallback）
# ============================================================

def fetch_kline_with_fallback(code: str, days: int = 60) -> list:
    """历史K线获取，同花顺失败时自动切换东方财富"""
    print(f"\n  >> 获取历史K线 [{code}]，目标 {days} 个交易日...")

    # 主力：同花顺
    result = fetch_kline_10jqka(code, days)
    if result and len(result) >= 5:
        return result

    print(f"  ⚠ 同花顺失败，切换到东方财富备用源...")
    result = fetch_kline_eastmoney(code, days)
    if result and len(result) >= 5:
        return result

    print(f"  ❌ 所有历史K线数据源均失败，无法继续分析")
    return None


def fetch_realtime_with_fallback(code: str) -> dict:
    """实时行情获取，新浪失败时自动切换东方财富"""
    print(f"\n  >> 获取实时行情 [{code}]...")

    result = fetch_realtime_sina(code)
    if result:
        return result

    print(f"  ⚠ 新浪失败，切换到东方财富实时...")
    result = fetch_realtime_eastmoney(code)
    if result:
        return result

    print(f"  ⚠ 实时行情获取失败，将使用历史最新收盘价代替")
    return None


# ============================================================
# 数据整合与保存
# ============================================================

def merge_today_into_kline(kline: list, realtime: dict) -> list:
    """
    将今日实时行情合并进历史K线列表。
    如果今日日期已存在，则更新；否则追加。
    """
    if not realtime:
        return kline

    today = datetime.now().strftime("%Y%m%d")
    today_rec = {
        "date":     today,
        "open":     realtime.get("open", realtime["current"]),
        "high":     realtime.get("high", realtime["current"]),
        "low":      realtime.get("low", realtime["current"]),
        "close":    realtime["current"],
        "vol":      realtime.get("vol", 0),
        "amount":   realtime.get("amount", 0),
        "turnover": 0.0,  # 实时换手率不直接获取，留0由predict.py估算
        "pct_chg":  realtime.get("pct_chg", 0),
        "_is_realtime": True,  # 标记为实时数据
    }

    if kline and kline[-1]["date"] == today:
        kline[-1] = today_rec
        print(f"  [合并] 今日({today})实时数据已更新到K线末尾")
    else:
        kline.append(today_rec)
        print(f"  [合并] 今日({today})实时数据已追加到K线末尾")

    return kline


def save_data(code: str, kline: list, realtime: dict, output_dir: str) -> dict:
    """
    保存数据为JSON文件。

    返回文件路径字典: {"kline": "...", "realtime": "..."}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}

    kline_path = output_dir / f"{code}_kline.json"
    with open(kline_path, "w", encoding="utf-8") as f:
        json.dump(kline, f, ensure_ascii=False, indent=2)
    paths["kline"] = str(kline_path)
    print(f"  💾 历史K线 → {kline_path}")

    if realtime:
        rt_path = output_dir / f"{code}_realtime.json"
        with open(rt_path, "w", encoding="utf-8") as f:
            json.dump(realtime, f, ensure_ascii=False, indent=2)
        paths["realtime"] = str(rt_path)
        print(f"  💾 实时行情 → {rt_path}")

    return paths


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="股票热度分析 v2 — 公开数据源获取器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取近30个交易日数据
  python3 fetch_public.py --code 600000

  # 指定回溯天数
  python3 fetch_public.py --code 000001 --days 45

  # 仅获取历史K线，不获取实时行情
  python3 fetch_public.py --code 600519 --no-realtime

  # 指定输出目录
  python3 fetch_public.py --code 600000 --output-dir /tmp/stock_data
        """
    )
    parser.add_argument("--code",        type=str, required=True,
                        help="股票代码，如 600000（不带市场后缀）")
    parser.add_argument("--days",        type=int, default=40,
                        help="回溯交易日数（默认40，约2个月）")
    parser.add_argument("--output-dir",  type=str, default="./data",
                        help="数据保存目录（默认 ./data）")
    parser.add_argument("--no-realtime", action="store_true",
                        help="跳过实时行情获取")
    parser.add_argument("--merge-today", action="store_true", default=True,
                        help="将今日实时行情合并进K线（默认启用）")

    args = parser.parse_args()

    print("=" * 58)
    print("  📡 股票热度分析 v2 — 数据获取器")
    print("=" * 58)
    print(f"  股票代码: {args.code}")
    print(f"  回溯天数: {args.days}")
    print(f"  输出目录: {os.path.abspath(args.output_dir)}")
    print(f"  市场推断: {_infer_market(args.code).upper()}")

    # 获取历史K线（带fallback）
    kline = fetch_kline_with_fallback(args.code, args.days)
    if kline is None:
        print("\n❌ 数据获取失败，请检查网络连接或稍后重试")
        sys.exit(1)

    # 获取实时行情
    realtime = None
    if not args.no_realtime:
        realtime = fetch_realtime_with_fallback(args.code)

    # 合并今日实时数据
    if realtime and args.merge_today:
        kline = merge_today_into_kline(kline, realtime)

    # 保存数据
    print()
    paths = save_data(args.code, kline, realtime, args.output_dir)

    print(f"\n{'='*58}")
    print(f"  ✅ 数据获取完成！")
    print(f"  K线条数: {len(kline)} 条（含今日: {'是' if realtime else '否'}）")
    if kline:
        print(f"  时间范围: {kline[0]['date']} ~ {kline[-1]['date']}")
    print(f"\n  下一步（分析预测）:")
    print(f"    python3 predict.py --code {args.code} --data-dir {args.output_dir}")

    # 输出路径信息供上层调用读取
    result = {
        "code": args.code,
        "kline_count": len(kline),
        "has_realtime": realtime is not None,
        "paths": paths,
    }
    # 将摘要写到 stdout 最后一行（JSON格式，供run.py捕获）
    print(f"\n__RESULT__:{json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
