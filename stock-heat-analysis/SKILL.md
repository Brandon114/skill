---
name: stock-heat-analysis
description: 股票热度分析工具，基于公开市场数据构建热度因子体系，量化评估股票受散户关注度。触发词包括：股票热度、热度分析、散户关注度、热股分析、热度因子、关注度评分
category: 金融分析
version: 1.0.0

---

# 股票热度分析 (Stock Heat Analysis)

基于热度因子概念，利用**公开可获取的A股市场数据**，构建代理热度因子体系，实现对股票散户关注度的量化分析和可视化。

## 核心原理

### 原始文章的7个热度因子

文章中提到的7个内部热度因子（软件用户行为数据）：
1. **点击量** - 用户查看该股票详情页的次数
2. **新闻点击量** - 用户阅读该股票相关新闻的次数
3. **自选操作** - 用户将该股票加入/移出自选的操作
4. **加仓信号** - 模拟持仓加仓行为
5. **搜索量** - 用户主动搜索该股票的频次
6. **分享数** - 用户分享该股票信息的次数
7. **讨论量** - 用户在社区讨论该股票的活跃度

这些因子的核心特征：**IC值（信息系数）均为负** → 高热度 = 散户情绪过热 = 后续收益倾向为负

### 公开数据代理映射

由于我们无法获取炒股软件内部数据，使用以下公开市场数据作为代理指标：

| 原始因子 | 公开代理 | 数据来源 | 理论依据 |
|---------|---------|---------|---------|
| 点击量 | 成交额 (amount) | daily 接口 | 高关注度→高交易参与度 |
| 新闻点击量 | 换手率 (turnover_rate) | daily_basic 接口 | 信息传播→换手率上升 |
| 自选操作 | 量比 (volume_ratio) | daily_basic 接口 | 关注变化→相对放量 |
| 加仓信号 | 大单净流入 (net_mf_amount) | moneyflow 接口 | 主力资金动向 |
| 搜索量 | 振幅 (high-low)/close | daily 接口（计算） | 多空分歧程度 |
| 分享数 | 成交量变异系数 | 日线vol序列计算 | 讨论扩散→成交波动 |
| 讨论量 | 小单净流入 (buy_sm-sell_sm) | moneyflow 接口 | 散户交易行为 |

## 使用方法

### 运行脚本

```bash
python3 scripts/stock_heat_analysis.py [选项]
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--stocks` | `600519.SH,000858.SZ,300750.SZ` | 待分析的股票代码列表（逗号分隔） |
| `--days` | `30` | 回溯天数（约1个月交易日） |
| `--output-dir` | `./heat_output` | 输出目录 |
| `--top-n` | `20` | 展示Top-N热门/冷门股票 |
| `--mode` | `single` | 分析模式: single(单股), compare(对比), screen(全市场筛选) |
| `--help` | - | 显示帮助信息 |

### 示例

```bash
# 分析单只股票近1个月热度
python3 scripts/stock_heat_analysis.py --stocks 600519.SH --days 30

# 对比多只股票热度
python3 scripts/stock_heat_analysis.py --stocks "600519.SH,000858.SZ,300750.SZ" --mode compare

# 全市场筛选（需要较长时间）
python3 scripts/stock_heat_analysis.py --mode screen --top-n 30
```

## 因子计算公式

### 1. 成交热度因子 (F1_amount_heat)

$$F_1 = \text{ZScore}\left(\frac{\text{amount}_t}{\text{median}(\text{amount}_{t-20:t}})\right)$$

对当日成交额进行20日滚动中位数标准化，反映相对历史水平的交易热度。

### 2. 换手热度因子 (F2_turnover_heat)

$$F_2 = \text{ZScore}(\text{turnover\_rate}_t)$$

直接对换手率进行截面Z-Score标准化（全市场排名），反映筹码交换活跃度。

### 3. 量比热度因子 (F3_volume_ratio)

$$F_3 = \text{ZScore}(\max(\text{volume\_ratio}, 0.5))$$

量比>1表示当日放量，<1表示缩放。用0.5作为下界截断后标准化。

### 4. 资金流向因子 (F4_moneyflow)

$$F_4 = -\text{ZScore}\left(\frac{\text{net\_mf\_amount}_t}{\text{circ\_mv}}\right)$$

净流入占流通市值比例取负号（与原始文章一致：散户追入=风险信号），再标准化。

### 5. 波动分歧因子 (F5_volatility)

$$F_5 = \text{ZScore}\left(\frac{\text{high}_t - \text{low}_t}{\text{close}_t}\right)$$

日内振幅标准化，反映多空博弈激烈程度。

### 6. 成交波动因子 (F6_volume_cv)

$$F_6 = \text{ZScore}\left(\frac{\text{std}(\text{vol}_{t-5:t})}{\text{mean}(\text{vol}_{t-5:t}) + \epsilon}\right)$$

5日成交量变异系数，衡量近期交易波动性。

### 7. 散户行为因子 (F7_retail_behavior)

$$F_7 = -\text{ZScore}\left(\frac{\text{buy\_sm\_amount} - \text{sell\_sm\_amount}}{\text{total\_amount}}\right)$$

小单（散户）净买入占比取负号，反映散户集中买入的风险。

### 综合热度得分 (Heat Score)

$$H = w_1 F_1 + w_2 F_2 + w_3 F_3 + w_4 F_4 + w_5 F_5 + w_6 F_6 + w_7 F_7$$

默认等权配置：$w_i = \frac{1}{7}$

最终输出范围为 **[-3, +3]** 的标准分，正值越高表示热度越高（散户关注度越集中）。

## 输出内容

运行完成后在 `--output-dir` 目录下生成：

| 文件 | 说明 |
|------|------|
| `heat_summary.json` | 完整的热度因子数据和综合得分 |
| `heat_ranking.csv` | 热度排行榜（CSV格式） |
| `factor_correlation.png` | 各因子间相关性热力图 |
| `heatmap_timeline.png` | 热度时间线热力图 |
| `radar_chart.png` | 多股雷达图对比（compare模式） |

## 风险提示

1. 本工具仅用于教学和研究目的，不构成投资建议
2. 公开数据代理因子与原始软件内部因子存在差异，结果仅供参考
3. 历史热度不代表未来走势，因子有效性会随市场环境变化
4. IC为负的统计规律是群体层面的，个别股票可能不符合
