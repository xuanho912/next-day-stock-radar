# Radar Agency Review

- version: `radar_agency_review_v1`
- source_framework: `msitarzewski/agency-agents`
- generated_at: `2026-07-16T00:57:39.403542+00:00`
- overall_decision: `观察`
- agency_quality_gate: `谨慎通过`
- market_permission: `只观察候选，不强行追逐；等待盘前刷新和触发确认。`

## Hard Warnings

- 逼空/期权相关评分包含 proxy，不是真实 short interest / options 数据。
- 强优势候选数量不足，不能强行进攻。
- 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- 部分历史相似样本不足，不能把相似样本结论当作验证。

## Agent Findings

### 市场路径代理

- status: `warn`
- conclusion: 检查 SPY/QQQ/IWM/VIX 与数据新鲜度是否支持次日机会筛选。
- evidence: market_state=neutral; freshness=partial_fallback; strong_edge_count=0
- warning: 强优势候选数量不足，不能强行进攻。

### 板块主线代理

- status: `pass`
- conclusion: 先判断资金主线，再允许个股进入高等级机会。
- evidence: top_sector=AI / Semiconductors(2); top_type=pullback_reversal_setup(3)

### 预期差代理

- status: `warn`
- conclusion: 验证催化、成交和价格是否真的形成超预期，而不是只靠热度。
- evidence: avg_top5_gap=69.33; min_top5_gap=54.0; confirmed_signal_count=1
- warning: Top 5 平均预期差尚可，但最低预期差偏弱。

### 执行质量代理

- status: `pass`
- conclusion: 检查触发价、失效价、赔率质量和流动性是否可执行。
- evidence: avg_payoff=58.68; avg_execution=68.65; avg_risk=9.9

### 当前价确认代理

- status: `warn`
- conclusion: 检查 Finnhub quote 是否支持 Top 候选仍沿主路径运行。
- evidence: confirming=0; failed=0; missing=0
- warning: 当前价确认数量偏少，盘前/盘中需要再次刷新。

### 风险现实校验代理

- status: `warn`
- conclusion: 默认怀疑一切表面强势，专查旧数据、proxy、流动性、小样本和冲高回落风险。
- evidence: proxy_squeeze=3; low_sample=3; liquidity_risk=0
- warning: 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- warning: 部分历史相似样本不足，不能把相似样本结论当作验证。

### 验证代理

- status: `warn`
- conclusion: 检查 Forecast Ledger、Baseline/Challenger 和前向样本是否支持模型升级。
- evidence: validation=early_evidence; completed=507; leaderboard=validated
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
- evidence: static_payload=True; candidate_count=62

## Top Candidate Notes

| Rank | Ticker | Verdict | Key Check | Warnings |
| ---: | --- | --- | --- | --- |
| 1 | ASML | 可观察候选 | 共振 82; 预期差 100.0; 赔率 82.31; 风险 0; 闸门 强共振; 信号 confirmed | 历史相似样本不足 / 逼空/期权相关数据为 proxy |
| 2 | QCOM | 可观察候选 | 共振 63; 预期差 54; 赔率 46.63; 风险 13.2; 闸门 不具备高置信优势; 信号 blocked | 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：催化不足或没有确认新闻 / 技术结构未确认 / 成交量没有形成确认 / 赔率质量不足 / 预期差不足 |
| 3 | ORCL | 可观察候选 | 共振 68; 预期差 54; 赔率 47.09; 风险 16.5; 闸门 不具备高置信优势; 信号 partial | 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 |

这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。