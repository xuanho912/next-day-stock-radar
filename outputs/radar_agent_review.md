# Radar Agency Review

- version: `radar_agency_review_v1`
- source_framework: `msitarzewski/agency-agents`
- generated_at: `2026-06-17T09:50:36.468370+00:00`
- overall_decision: `观察`
- agency_quality_gate: `谨慎通过`
- market_permission: `只观察候选，不强行追逐；等待盘前刷新和触发确认。`

## Hard Warnings

- 存在 stale warning 或数据源降级，页面不得假装是完全新鲜数据。
- 逼空/期权相关评分包含 proxy，不是真实 short interest / options 数据。
- 强优势候选数量不足，不能强行进攻。
- 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- 部分历史相似样本不足，不能把相似样本结论当作验证。

## Agent Findings

### 市场路径代理

- status: `warn`
- conclusion: 检查 SPY/QQQ/IWM/VIX 与数据新鲜度是否支持次日机会筛选。
- evidence: market_state=attack; freshness=partial_fallback; strong_edge_count=0
- warning: 存在数据新鲜度或降级警告，需要盘前再次刷新确认。
- warning: 强优势候选数量不足，不能强行进攻。

### 板块主线代理

- status: `pass`
- conclusion: 先判断资金主线，再允许个股进入高等级机会。
- evidence: top_sector=Biotech(2); top_type=event_driven_volatility(4)

### 预期差代理

- status: `pass`
- conclusion: 验证催化、成交和价格是否真的形成超预期，而不是只靠热度。
- evidence: avg_top5_gap=73.62; min_top5_gap=64.17

### 执行质量代理

- status: `pass`
- conclusion: 检查触发价、失效价、赔率质量和流动性是否可执行。
- evidence: avg_payoff=69.93; avg_execution=70.86; avg_risk=2.2

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
| 1 | PLTR | 可观察候选 | 共振 68; 预期差 76.95; 赔率 72.71; 风险 11.0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 2 | ACHR | 可观察候选 | 共振 68; 预期差 64.17; 赔率 69.53; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 3 | CRSP | 可观察候选 | 共振 68; 预期差 67.88; 赔率 69.26; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 4 | CEG | 可观察候选 | 共振 68; 预期差 77.86; 赔率 69.21; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 5 | RKLB | 可观察候选 | 共振 68; 预期差 81.23; 赔率 68.96; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 6 | XPEV | 可观察候选 | 共振 68; 预期差 71.99; 赔率 68.94; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 7 | GME | 可观察候选 | 共振 68; 预期差 80.8; 赔率 68.91; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 8 | TSLA | 可观察候选 | 共振 68; 预期差 62.21; 赔率 67.73; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 9 | OKLO | 可观察候选 | 共振 68; 预期差 65.11; 赔率 67.6; 风险 0; 闸门 可观察 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 10 | BEAM | 可观察候选 | 共振 68; 预期差 77.92; 赔率 66.56; 风险 0; 闸门 强共振 | 历史相似样本不足 / 逼空/期权相关数据为 proxy |

这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。