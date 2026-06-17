# Radar Agency Review

- version: `radar_agency_review_v1`
- source_framework: `msitarzewski/agency-agents`
- generated_at: `2026-06-17T17:11:24.732072+00:00`
- overall_decision: `防守`
- agency_quality_gate: `不通过`
- market_permission: `防守优先；候选降级，避免把弱信号当成机会。`

## Hard Warnings

- 存在 stale warning 或数据源降级，页面不得假装是完全新鲜数据。
- Top 候选存在当前价确认失败，需要等待重新确认。
- 逼空/期权相关评分包含 proxy，不是真实 short interest / options 数据。
- 强优势候选数量不足，不能强行进攻。
- Top 候选中存在当前价确认失败，必须降级或等待下一次刷新。
- 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- 部分历史相似样本不足，不能把相似样本结论当作验证。
- Top 10 中存在当前价确认失败，不能继续按原路径看待。
- Top 10 没有真实共振候选，只能观察，不能进攻。

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
- evidence: top_sector=AI / Semiconductors(2); top_type=event_driven_volatility(7)

### 预期差代理

- status: `warn`
- conclusion: 验证催化、成交和价格是否真的形成超预期，而不是只靠热度。
- evidence: avg_top5_gap=62.59; min_top5_gap=50.0; confirmed_signal_count=0
- warning: Top 5 平均预期差尚可，但最低预期差偏弱。

### 执行质量代理

- status: `pass`
- conclusion: 检查触发价、失效价、赔率质量和流动性是否可执行。
- evidence: avg_payoff=54.77; avg_execution=57.45; avg_risk=10.0

### 当前价确认代理

- status: `fail`
- conclusion: 检查 Finnhub quote 是否支持 Top 候选仍沿主路径运行。
- evidence: confirming=1; failed=1; missing=0
- warning: Top 候选中存在当前价确认失败，必须降级或等待下一次刷新。

### 风险现实校验代理

- status: `warn`
- conclusion: 默认怀疑一切表面强势，专查旧数据、proxy、流动性、小样本和冲高回落风险。
- evidence: proxy_squeeze=10; low_sample=10; liquidity_risk=0
- warning: 页面必须显示 stale warning；不能把降级数据伪装成今日预测。
- warning: 部分逼空/期权信号仍是 proxy，不能当成真实空头或期权数据。
- warning: 部分历史相似样本不足，不能把相似样本结论当作验证。
- warning: Top 10 中存在当前价确认失败，不能继续按原路径看待。
- warning: Top 10 没有真实共振候选，只能观察，不能进攻。

### 验证代理

- status: `warn`
- conclusion: 检查 Forecast Ledger、Baseline/Challenger 和前向样本是否支持模型升级。
- evidence: validation=early_evidence; completed=42; leaderboard=early_evidence
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
| 1 | JOBY | 共振不足 | 共振 58; 预期差 50; 赔率 59.81; 风险 0; 闸门 不具备高置信优势; 信号 blocked | 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：催化不足或没有确认新闻 / 技术结构未确认 / 预期差不足 |
| 2 | PLTR | 共振不足 | 共振 58; 预期差 58; 赔率 56.14; 风险 22.0; 闸门 不具备高置信优势; 信号 blocked | 风险标记：news_reversal_or_event_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：技术结构未确认 / 成交量没有形成确认 / 板块主线不够强 |
| 3 | BABA | 共振不足 | 共振 58; 预期差 88.95; 赔率 53.04; 风险 12.0; 闸门 不具备高置信优势; 信号 blocked | 风险标记：current_quote_failed_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 当前价确认失败 / 信号闸门：技术结构未确认 / 板块主线不够强 / 当前价确认失败 |
| 4 | AVGO | 共振不足 | 共振 58; 预期差 58; 赔率 52.94; 风险 8.0; 闸门 不具备高置信优势; 信号 blocked | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：技术结构未确认 / 成交量没有形成确认 |
| 5 | NVDA | 共振不足 | 共振 58.0; 预期差 58; 赔率 51.93; 风险 8.0; 闸门 不具备高置信优势; 信号 blocked | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：技术结构未确认 / 成交量没有形成确认 / 赔率质量不足 |
| 6 | RKLB | 共振不足 | 共振 58.0; 预期差 58; 赔率 51.14; 风险 36.48; 闸门 不具备高置信优势; 信号 blocked | 风险标记：news_reversal_or_event_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：技术结构未确认 / 成交量没有形成确认 / 赔率质量不足 |
| 7 | TSLA | 共振不足 | 共振 58; 预期差 58; 赔率 51.08; 风险 0; 闸门 不具备高置信优势; 信号 blocked | 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：技术结构未确认 / 成交量没有形成确认 / 赔率质量不足 |
| 8 | COIN | 共振不足 | 共振 58; 预期差 58; 赔率 50.62; 风险 0; 闸门 不具备高置信优势; 信号 blocked | 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：技术结构未确认 / 成交量没有形成确认 / 赔率质量不足 |
| 9 | HOOD | 共振不足 | 共振 58; 预期差 58; 赔率 50.17; 风险 0; 闸门 不具备高置信优势; 信号 blocked | 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：成交量没有形成确认 / 赔率质量不足 / 逼空逻辑只有 proxy，不能作为强共振 |
| 10 | MARA | 共振不足 | 共振 58; 预期差 58; 赔率 49.48; 风险 8.0; 闸门 不具备高置信优势; 信号 blocked | 风险标记：weak_close_distribution_risk / 历史相似样本不足 / 逼空/期权相关数据为 proxy / 精准闸门未通过 / 信号闸门：成交量没有形成确认 / 赔率质量不足 / 逼空逻辑只有 proxy，不能作为强共振 |

这是次日高弹性概率雷达，不是投资建议、买卖指令或仓位建议。