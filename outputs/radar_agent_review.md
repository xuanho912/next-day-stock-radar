# Radar Agency Review

- version: `radar_agency_review_v1`
- source_framework: `msitarzewski/agency-agents`
- generated_at: `2026-06-17T11:16:16.946262+00:00`
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
- evidence: market_state=attack; freshness=partial_fallback; strong_edge_count=6
- warning: 存在数据新鲜度或降级警告，需要盘前再次刷新确认。

### 板块主线代理

- status: `pass`
- conclusion: 先判断资金主线，再允许个股进入高等级机会。
- evidence: top_sector=Nuclear / Power(2); top_type=event_driven_volatility(6)

### 预期差代理

- status: `pass`
- conclusion: 验证催化、成交和价格是否真的形成超预期，而不是只靠热度。
- evidence: avg_top5_gap=79.11; min_top5_gap=68.36

### 执行质量代理

- status: `pass`
- conclusion: 检查触发价、失效价、赔率质量和流动性是否可执行。
- evidence: avg_payoff=62.49; avg_execution=68.15; avg_risk=4.8

### 当前价确认代理

- status: `warn`
- conclusion: 检查 Finnhub quote 是否支持 Top 候选仍沿主路径运行。
- evidence: confirming=0; failed=0; missing=0
- warning: 当前价确认数量偏少，盘前/盘中需要再次刷新。

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
| 1 | VST | 强共振候选 | 共振 94.58; 预期差 100.0; 赔率 61.36; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 2 | COIN | 强共振候选 | 共振 83.01; 预期差 81.77; 赔率 71.62; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 3 | MARA | 强共振候选 | 共振 80.84; 预期差 71.83; 赔率 60.79; 风险 8.0; 闸门 强共振 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 4 | ARM | 可观察候选 | 共振 79.97; 预期差 73.6; 赔率 59.8; 风险 8.0; 闸门 强共振 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 5 | RIOT | 可观察候选 | 共振 77.96; 预期差 68.36; 赔率 58.87; 风险 8.0; 闸门 可观察 | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 6 | CEG | 可观察候选 | 共振 77.14; 预期差 76.83; 赔率 61.2; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 7 | AMC | 可观察候选 | 共振 87.53; 预期差 83.84; 赔率 62.88; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 8 | AI | 可观察候选 | 共振 80.76; 预期差 80.04; 赔率 59.25; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 9 | PLTR | 可观察候选 | 共振 78.97; 预期差 80.75; 赔率 75.69; 风险 5.5; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 10 | TSLA | 可观察候选 | 共振 75.88; 预期差 67.25; 赔率 75.4; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |

这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。