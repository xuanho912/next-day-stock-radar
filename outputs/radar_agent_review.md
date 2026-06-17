# Radar Agency Review

- version: `radar_agency_review_v1`
- source_framework: `msitarzewski/agency-agents`
- generated_at: `2026-06-17T09:55:47.826608+00:00`
- overall_decision: `进攻`
- agency_quality_gate: `谨慎通过`
- market_permission: `允许筛选高弹性机会，但只能按触发价和失效价确认。`

## Hard Warnings

- 存在 stale warning 或数据源降级，页面不得假装是完全新鲜数据。
- 逼空/期权相关评分包含 proxy，不是真实 short interest / options 数据。
- 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- 部分历史相似样本不足，不能把相似样本结论当作验证。

## Agent Findings

### 市场路径代理

- status: `warn`
- conclusion: 检查 SPY/QQQ/IWM/VIX 与数据新鲜度是否支持次日机会筛选。
- evidence: market_state=attack; freshness=partial_fallback; strong_edge_count=8
- warning: 存在数据新鲜度或降级警告，需要盘前再次刷新确认。

### 板块主线代理

- status: `pass`
- conclusion: 先判断资金主线，再允许个股进入高等级机会。
- evidence: top_sector=Nuclear / Power(2); top_type=event_driven_volatility(4)

### 预期差代理

- status: `pass`
- conclusion: 验证催化、成交和价格是否真的形成超预期，而不是只靠热度。
- evidence: avg_top5_gap=81.15; min_top5_gap=71.14

### 执行质量代理

- status: `pass`
- conclusion: 检查触发价、失效价、赔率质量和流动性是否可执行。
- evidence: avg_payoff=63.06; avg_execution=66.26; avg_risk=3.2

### 风险现实校验代理

- status: `warn`
- conclusion: 默认怀疑一切表面强势，专查旧数据、proxy、流动性、小样本和冲高回落风险。
- evidence: proxy_squeeze=10; low_sample=10; liquidity_risk=0
- warning: 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- warning: 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- warning: 部分历史相似样本不足，不能把相似样本结论当作验证。

### 验证代理

- status: `warn`
- conclusion: 检查 Forecast Ledger、Baseline/Challenger 和前向样本是否支持模型升级。
- evidence: validation=early_evidence; completed=34; leaderboard=early_evidence
- warning: 已有早期样本，但还没有达到 30-60 个交易日前向验证标准。

### 数据质量代理

- status: `warn`
- conclusion: 检查 provider 状态、降级数量、最新交易日和数据质量分。
- evidence: score=66; freshness=partial_fallback; yahoo_fallback=1; finnhub=partial
- warning: 存在数据源降级，候选已被过滤或压制，但仍需人工确认。
- warning: Finnhub 非完全可用，新闻/事件催化可能不完整。

### 中文仪表盘代理

- status: `pass`
- conclusion: 确认前端只读取静态 JSON，并把复杂推理放到后面。
- evidence: static_payload=True; candidate_count=39

## Top Candidate Notes

| Rank | Ticker | Verdict | Key Check | Warnings |
| ---: | --- | --- | --- | --- |
| 1 | VST | 强共振候选 | 共振 93.47; 预期差 100.0; 赔率 61.15; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 2 | COIN | 强共振候选 | 共振 84.69; 预期差 82.35; 赔率 71.94; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 3 | ARM | 强共振候选 | 共振 80.5; 预期差 74.96; 赔率 59.67; 风险 8.0; 闸门 强共振 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 4 | MARA | 可观察候选 | 共振 79.69; 预期差 71.14; 赔率 60.57; 风险 8.0; 闸门 强共振 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 5 | CEG | 可观察候选 | 共振 78.77; 预期差 77.31; 赔率 61.97; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 6 | AMD | 可观察候选 | 共振 77.88; 预期差 72.73; 赔率 56.01; 风险 8.0; 闸门 可观察 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 7 | RIOT | 可观察候选 | 共振 76.8; 预期差 67.67; 赔率 58.66; 风险 8.0; 闸门 可观察 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 8 | HOOD | 可观察候选 | 共振 76.35; 预期差 68.83; 赔率 60.3; 风险 11.0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 9 | AMC | 可观察候选 | 共振 86.92; 预期差 83.36; 赔率 62.66; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 10 | AI | 可观察候选 | 共振 79.54; 预期差 79.24; 赔率 58.7; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |

这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。