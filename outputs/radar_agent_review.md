# Radar Agency Review

- version: `radar_agency_review_v1`
- source_framework: `msitarzewski/agency-agents`
- generated_at: `2026-06-22T17:00:56.894873+00:00`
- overall_decision: `防守`
- agency_quality_gate: `不通过`
- market_permission: `防守优先；候选降级，避免把弱信号当成机会。`

## Hard Warnings

- 存在 stale warning 或数据源降级，页面不得假装是完全新鲜数据。
- 强优势候选数量不足，不能强行进攻。
- 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- Top 10 没有真实共振候选，只能观察，不能进攻。

## Agent Findings

### 市场路径代理

- status: `warn`
- conclusion: 检查 SPY/QQQ/IWM/VIX 与数据新鲜度是否支持次日机会筛选。
- evidence: market_state=neutral; freshness=partial_fallback; strong_edge_count=0
- warning: 存在数据新鲜度或降级警告，需要盘前再次刷新确认。
- warning: 强优势候选数量不足，不能强行进攻。

### 板块主线代理

- status: `fail`
- conclusion: 先判断资金主线，再允许个股进入高等级机会。
- evidence: top_sector=unknown(0); top_type=unknown(0)
- warning: 没有候选，无法形成主线。

### 预期差代理

- status: `fail`
- conclusion: 验证催化、成交和价格是否真的形成超预期，而不是只靠热度。
- evidence: avg_top5_gap=0; min_top5_gap=0; confirmed_signal_count=0
- warning: 预期差不足，容易变成表面热闹但没有交易价值。

### 执行质量代理

- status: `fail`
- conclusion: 检查触发价、失效价、赔率质量和流动性是否可执行。
- evidence: avg_payoff=0; avg_execution=0; avg_risk=0
- warning: 赔率或执行质量不足，触发价没有确认前不应把它当成强机会。
- warning: 没有 Top 5 候选。

### 当前价确认代理

- status: `warn`
- conclusion: 检查 Finnhub quote 是否支持 Top 候选仍沿主路径运行。
- evidence: confirming=0; failed=0; missing=0
- warning: 当前价确认数量偏少，盘前/盘中需要再次刷新。

### 风险现实校验代理

- status: `fail`
- conclusion: 默认怀疑一切表面强势，专查旧数据、proxy、流动性、小样本和冲高回落风险。
- evidence: proxy_squeeze=0; low_sample=0; liquidity_risk=0
- warning: 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- warning: Top 10 没有真实共振候选，只能观察，不能进攻。
- warning: 没有候选可供现实校验。

### 验证代理

- status: `warn`
- conclusion: 检查 Forecast Ledger、Baseline/Challenger 和前向样本是否支持模型升级。
- evidence: validation=early_evidence; completed=96; leaderboard=validated
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

这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。