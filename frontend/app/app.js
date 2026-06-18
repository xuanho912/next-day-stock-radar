const DATA_FILES = {
  dashboard: ["./stock-radar-dashboard.json", "../public/stock-radar-dashboard.json", "./public/stock-radar-dashboard.json"],
};

const LABELS = {
  candidateType: {
    next_day_upside_momentum: "次日上冲动量",
    oversold_bounce: "超跌反抽",
    short_squeeze_candidate: "逼空候选",
    gap_continuation: "跳空延续",
    event_driven_volatility: "事件驱动波动",
    failed_bounce_risk: "反抽失败风险",
    downside_continuation: "下行延续",
    no_edge: "无优势",
  },
  edge: {
    STRONG_EDGE: "强优势",
    MODERATE_EDGE: "中等优势",
    HIGH_RISK_HIGH_REWARD: "高风险高弹性",
    WATCH: "观察",
    NO_EDGE: "无优势",
    AVOID: "剔除",
  },
  scenario: {
    upside_path_after_trigger: "触发后上冲路径",
    bounce_attempt_after_trigger: "触发后反抽路径",
    only_if_market_reclaims_risk_on: "仅市场转强后成立",
    risk_path_continuation: "风险路径延续",
    failed_risk_path_relief_bounce: "风险路径后的弱反抽",
    open_drive_then_gap_fill: "开盘冲高后回补缺口",
    range_extension_after_trigger: "触发后区间扩展",
    failed_breakout_or_gap_fade: "突破失败或跳空回落",
    failed_bounce_follow_through: "反抽失败后延续",
    downside_continuation: "下行延续",
    no_edge: "无优势路径",
  },
  market: { attack: "进攻", neutral: "中性", defense: "防守" },
  risk: { low: "低", medium: "中", high: "高", elevated: "偏高" },
  freshness: { fresh: "最新", partial_fallback: "部分数据降级", fallback_only: "全部降级", missing: "缺失" },
  validation: { not_yet_validated: "样本不足", early_evidence: "早期证据", validated: "已验证" },
  provider: { available: "可用", partial: "局部可用", missing: "缺失" },
  bool: { true: "是", false: "否" },
  riskFlag: {
    price_below_minimum: "价格低于过滤线",
    high_liquidity_risk: "流动性风险高",
    otc_or_pink: "OTC / 粉单过滤",
    high_risk_high_volatility: "高波动小票风险",
    fallback_or_missing_price_data: "行情缺失或降级",
    news_reversal_or_event_risk: "消息反转风险",
    gap_fade_risk: "跳空回落风险",
    weak_close_distribution_risk: "弱收盘派发风险",
    current_quote_failed_risk: "当前价确认失败风险",
  },
  evidence: {
    earnings_momentum: "财报/指引催化",
    confirmed_business_catalyst: "订单/合作催化",
    regulatory_catalyst: "监管催化",
    analyst_upgrade: "分析师上调",
    news_catalyst: "新闻催化",
    weak_or_missing_catalyst: "催化不足",
    positive_expectation_gap: "正向预期差",
    expectation_gap_not_confirmed: "预期差未确认",
    price_structure_confirmed: "价格结构确认",
    price_structure_unconfirmed: "价格结构未确认",
    volume_anomaly_confirmed: "成交确认",
    volume_or_liquidity_weak: "成交/流动性不足",
    current_price_confirming: "当前价确认",
    current_price_failed: "当前价否定",
    current_quote_missing: "当前价缺失",
    payoff_quality_confirmed: "赔率质量确认",
    payoff_quality_weak: "赔率质量不足",
    sector_context_confirmed: "板块共振",
    sector_context_weak: "板块未确认",
    risk_on_market_context: "市场支持",
    defensive_market_context: "市场防守",
    real_short_interest_missing: "真实空头数据缺失",
    real_price_data_missing: "真实行情缺失",
  },
};

let dashboard = null;
let selectedTicker = null;

document.addEventListener("DOMContentLoaded", async () => {
  dashboard = await loadJson(DATA_FILES.dashboard);
  if (!dashboard) {
    renderError();
    return;
  }
  selectedTicker = dashboard.top_candidates?.[0]?.ticker || dashboard.watch_candidates?.[0]?.ticker || null;
  renderDashboard();
});

async function loadJson(paths) {
  for (const path of paths) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (response.ok) return await response.json();
    } catch {
      // 静态部署时可能存在多种相对路径，继续尝试下一个位置。
    }
  }
  return null;
}

function renderDashboard() {
  const fresh = dashboard.data_freshness_status === "fresh";
  const marketState = dashboard.market_context?.market_state || "-";
  const actionable = dashboard.top_candidates || [];
  const topCandidate = actionable[0] || null;
  const displayedCount = dashboard.top_candidates?.length || 0;
  const watchCount = dashboard.watch_candidates?.length || 0;
  const passedCount = dashboard.top_candidate_count || actionable.length || 0;
  const attackCount = dashboard.actionable_candidate_count || 0;

  setText("radarDecision", dashboard.high_elasticity_opportunity ? "明天有高弹性候选" : displayedCount ? "有条件候选，等待触发" : "明天不强行进攻");
  setText("radarSummary", dashboard.radar_summary || "");
  setText("opportunityStatus", dashboard.high_elasticity_opportunity ? "有候选" : displayedCount ? "待触发" : "观望");
  setText("strongestCandidate", passedCount ? `${topCandidate.ticker} ${topCandidate.rating || ""}` : "无通过闸门");
  setText("strongestDirection", passedCount ? zh("candidateType", topCandidate?.candidate_type || dashboard.strongest_candidate_type) : "无进攻方向");
  setText("marketState", zh("market", marketState));
  setText("screeningStatus", marketState === "defense" ? "防守过滤" : "可筛选，等触发");
  setText("riskLevel", zh("risk", dashboard.current_risk_level));
  setText("dataDate", `${dashboard.latest_data_date || "-"} / 应有最新交易日 ${dashboard.expected_latest_trading_date || "-"} / 窗口 ${dashboard.forecast_horizon?.label || "次日"}`);
  setText("validationStatus", zh("validation", dashboard.model_validation_status));
  setText("agencyStatus", dashboard.agency_review?.agency_quality_gate || "-");
  setText("candidateCount", `${attackCount} 只重点 / ${displayedCount} 只条件候选 / ${watchCount} 只阻断 / ${dashboard.candidate_count || 0} 只总候选`);

  const freshnessBadge = document.getElementById("freshnessBadge");
  freshnessBadge.textContent = fresh ? "数据最新" : "数据警告";
  freshnessBadge.className = `badge ${fresh ? "good" : "bad"}`;

  const validationBadge = document.getElementById("validationBadge");
  validationBadge.textContent = zh("validation", dashboard.model_validation_status);
  validationBadge.className = `badge ${dashboard.model_validation_status === "validated" ? "good" : "neutral"}`;

  renderAvoidList();
  renderPrimaryVisual();
  renderOpportunityStrip();
  renderCandidateTable();
  renderDetail();
  renderValidation();
}

function renderAvoidList() {
  const target = document.getElementById("avoidList");
  if (!target) return;
  const rows = [...(dashboard.watch_candidates || []), ...(dashboard.excluded_candidates || []), ...(dashboard.avoid_candidates || [])].slice(0, 6);
  target.innerHTML = rows.length
    ? rows.map(item => `<li><strong>${safe(item.ticker)}</strong><span>${safe(avoidReason(item))}</span></li>`).join("")
    : `<li><strong>暂无</strong><span>当前没有需要额外提示的剔除项</span></li>`;
}

function renderCandidateTable() {
  const tbody = document.querySelector("#candidateTable tbody");
  const candidates = dashboard.top_candidates || [];
  if (!candidates.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="17">
          当前没有 A/B 级条件候选。无优势、存在阻断、只适合观察的股票不会进入候选榜；请看“今日不要碰/观察阻断”。
        </td>
      </tr>
    `;
    return;
  }
  tbody.innerHTML = candidates.map(candidate => `
    <tr data-ticker="${safeAttr(candidate.ticker)}" class="${candidate.ticker === selectedTicker ? "selected" : ""}">
      <td>${safe(candidate.rank)}</td>
      <td>
        <strong>${safe(candidate.ticker)}</strong>
        <small>${safe(candidate.company_name || "")}</small>
        <span class="badge ${edgeClass(candidate.edge_status)}">${safe(zh("edge", candidate.edge_status))}</span>
      </td>
      <td>${safe(zh("candidateType", candidate.candidate_type))}</td>
      <td>${price(candidate.current_price || candidate.last_close)}<small>${safe(quoteStatusText(candidate.quote_confirmation?.status))}</small></td>
      <td>${scoreBlock(pct(candidate.expected_upside_pct), "空间")}</td>
      <td>${scoreBlock(num(candidate.relative_volume), "相对量")}</td>
      <td>${scoreBlock(candidate.elasticity_score, "弹性")}</td>
      <td>${scoreBlock(candidate.confluence_score, "共振")}</td>
      <td><span class="badge ${matrixClass(candidate.confluence_matrix?.overall)}">${safe(confluenceOverallText(candidate.confluence_matrix?.overall))}</span></td>
      <td>${scoreBlock(candidate.expectation_gap_score, "预期差")}</td>
      <td>${scoreBlock(candidate.payoff_quality_score, "赔率")}</td>
      <td>${scoreBlock(candidate.risk_score, "风险")}</td>
      <td>${safe(zh("scenario", candidate.primary_scenario))}</td>
      <td>${safe(rangeLabel(candidate.next_day_expected_range))}</td>
      <td>${price(candidate.upside_trigger_level || candidate.trigger_levels?.upside_trigger_level)}</td>
      <td>${price(candidate.invalidation_level || candidate.trigger_levels?.invalidation_level || candidate.trade_plan?.invalidation_level)}</td>
      <td>${safe(candidate.reason)}</td>
    </tr>
  `).join("");

  tbody.querySelectorAll("[data-ticker]").forEach(row => {
    row.addEventListener("click", () => {
      selectedTicker = row.dataset.ticker;
      renderPrimaryVisual();
      renderOpportunityStrip();
      renderCandidateTable();
      renderDetail();
      document.querySelector(".detail-band").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function renderPrimaryVisual() {
  const target = document.getElementById("primaryVisual");
  if (!target) return;
  const candidate = (dashboard.top_candidates || []).find(item => item.ticker === selectedTicker) || dashboard.top_candidates?.[0];
  if (!candidate) {
    target.innerHTML = `<p>当前没有通过共振闸门的可用机会，因此不生成上冲路径图。</p>`;
    return;
  }

  target.innerHTML = `
    <div class="primary-chart">
      <div class="visual-title">
        <div>
          <strong>${safe(candidate.ticker)}</strong>
          <span>${safe(candidate.company_name || "")}</span>
        </div>
        <span class="badge ${edgeClass(candidate.edge_status)}">${safe(zh("edge", candidate.edge_status))}</span>
      </div>
      ${renderPriceVolumeComposite(candidate)}
    </div>
    <div class="space-panel">
      <h3>次日上涨空间</h3>
      ${spaceTiles(candidate)}
      ${renderExpectedRangeChart(candidate)}
    </div>
    <div class="space-panel">
      <h3>未来情景走势</h3>
      ${renderFutureScenarioChart(candidate)}
      ${renderVolumeAnalysis(candidate)}
    </div>
  `;
}

function renderOpportunityStrip() {
  const target = document.getElementById("topCandidateCards");
  if (!target) return;
  const candidates = dashboard.top_candidates || [];
  if (!candidates.length) {
    target.innerHTML = `<div class="empty-state">当前没有 A/B 级次日/近两交易日上涨候选。</div>`;
    return;
  }
  target.innerHTML = candidates.slice(0, 5).map(candidate => `
    <button class="opportunity-card ${candidate.ticker === selectedTicker ? "active" : ""}" data-ticker="${safeAttr(candidate.ticker)}">
      <span>${safe(candidate.rank)} · ${safe(candidate.ticker)}</span>
      <strong>${safe(pct(candidate.expected_upside_pct))}</strong>
      <small>量能 ${safe(num(candidate.relative_volume))}x · 共振 ${safe(candidate.confluence_score)}</small>
    </button>
  `).join("");

  target.querySelectorAll("[data-ticker]").forEach(card => {
    card.addEventListener("click", () => {
      selectedTicker = card.dataset.ticker;
      renderPrimaryVisual();
      renderOpportunityStrip();
      renderCandidateTable();
      renderDetail();
    });
  });
}

function renderDetail() {
  const candidate = (dashboard.top_candidates || []).find(item => item.ticker === selectedTicker) || dashboard.top_candidates?.[0];
  if (!candidate) {
    setText("detailTitle", "当前没有可用机会");
    const rating = document.getElementById("detailRating");
    rating.textContent = "观望";
    rating.className = "badge neutral";
    document.getElementById("candidateDetail").innerHTML = `<div class="detail-card">候选榜只展示 A/B 级条件候选。当前无通过项，阻断票已放入“今日不要碰/观察阻断”。</div>`;
    return;
  }

  setText("detailTitle", `${candidate.ticker} · ${candidate.company_name || "公司名称缺失"}`);
  const rating = document.getElementById("detailRating");
  rating.textContent = `${candidate.rating || "-"} · 弹性 ${candidate.elasticity_score ?? "-"}`;
  rating.className = `badge ${ratingClass(candidate.rating)}`;

  document.getElementById("candidateDetail").innerHTML = `
    <div class="detail-card chart-card wide-card">
      <h3>价格结构 + 成交量确认</h3>
      ${renderPriceVolumeComposite(candidate)}
      ${renderVolumeAnalysis(candidate)}
    </div>
    <div class="detail-card chart-card">
      <h3>次日预期图表</h3>
      ${renderExpectedRangeChart(candidate)}
      ${spaceTiles(candidate)}
    </div>
    <div class="detail-card chart-card">
      <h3>未来情景走势图</h3>
      ${renderFutureScenarioChart(candidate)}
    </div>
    <div class="detail-card">
      <h3>次日上涨空间</h3>
      ${facts([
        ["当前价", price(candidate.current_price || candidate.last_close)],
        ["昨收", price(candidate.last_close)],
        ["预期高点", price(candidate.next_day_expected_range?.expected_high)],
        ["预期低点", price(candidate.next_day_expected_range?.expected_low)],
        ["上行空间", pct(candidate.expected_upside_pct)],
        ["下行风险", pct(candidate.expected_downside_pct)],
        ["上行/下行赔率", num(candidate.risk_reward_ratio)],
        ["上冲触发价", price(candidate.trigger_levels?.upside_trigger_level || candidate.upside_trigger_level)],
        ["失效价", price(candidate.trigger_levels?.invalidation_level || candidate.invalidation_level || candidate.trade_plan?.invalidation_level)],
        ["当前价确认", quoteStatusText(candidate.quote_confirmation?.status)],
      ])}
      <p class="note">这些是概率路径点位，不是投资建议、买卖指令或仓位建议。</p>
    </div>
    <div class="detail-card">
      <h3>路径点位</h3>
      ${facts([
        ["主路径", zh("scenario", candidate.primary_scenario)],
        ["主路径概率", pct(candidate.primary_probability)],
        ["第二路径", zh("scenario", candidate.secondary_scenario)],
        ["第二路径概率", pct(candidate.secondary_probability)],
        ["风险路径", zh("scenario", candidate.risk_scenario)],
        ["风险路径概率", pct(candidate.risk_probability)],
        ["次日预期区间", rangeLabel(candidate.next_day_expected_range)],
        ["预期低点", price(candidate.next_day_expected_range?.expected_low)],
        ["预期中位", price(candidate.next_day_expected_range?.expected_mid)],
        ["预期高点", price(candidate.next_day_expected_range?.expected_high)],
        ["上冲触发价", price(candidate.trigger_levels?.upside_trigger_level || candidate.upside_trigger_level)],
        ["下行风险价", price(candidate.trigger_levels?.downside_risk_level || candidate.downside_risk_level)],
        ["失效价", price(candidate.trigger_levels?.invalidation_level || candidate.invalidation_level || candidate.trade_plan?.invalidation_level)],
        ["缺口回补位", price(candidate.trigger_levels?.gap_fill_level || candidate.gap_fill_level)],
        ["突破位", price(candidate.trigger_levels?.breakout_level || candidate.breakout_level)],
        ["破位位", price(candidate.trigger_levels?.breakdown_level || candidate.breakdown_level)],
        ["近端支撑", price(candidate.trigger_levels?.nearest_support || candidate.nearest_support)],
        ["近端压力", price(candidate.trigger_levels?.nearest_resistance || candidate.nearest_resistance)],
      ])}
    </div>
    <div class="detail-card">
      <h3>精准闸门</h3>
      ${facts([
        ["质量闸门", candidate.precision_gate?.level || "-"],
        ["是否通过", yn(candidate.precision_gate?.passed)],
        ["闸门原因", (candidate.precision_gate?.reason || []).join(" / ") || "-"],
        ["信号闸门", signalGateText(candidate.signal_quality_gate?.level)],
        ["信号缺口", (candidate.signal_quality_gate?.failures || []).join(" / ") || "-"],
        ["严重缺口", (candidate.signal_quality_gate?.critical_failures || []).join(" / ") || "-"],
        ["预期差评分", candidate.expectation_gap_score],
        ["执行质量评分", candidate.execution_quality_score],
        ["赔率质量评分", candidate.payoff_quality_score],
        ["上行/下行赔率", num(candidate.risk_reward_ratio)],
        ["预期上行", pct(candidate.expected_upside_pct)],
        ["预期下行", pct(candidate.expected_downside_pct)],
      ])}
    </div>
    <div class="detail-card wide-card">
      <h3>共振矩阵</h3>
      ${confluenceMatrix(candidate.confluence_matrix)}
    </div>
    <div class="detail-card">
      <h3>催化 / 相对强弱</h3>
      ${facts([
        ["新闻催化", zh("evidence", candidate.news?.catalyst_type) || "无确认新闻"],
        ["主新闻", candidate.news?.primary_headline || "近期没有确认主新闻"],
        ["当前价", price(candidate.current_price)],
        ["当前价相对昨收", pct(candidate.current_vs_last_close_pct)],
        ["当前价确认", quoteStatusText(candidate.quote_confirmation?.status)],
        ["确认分", candidate.quote_confirmation_score],
        ["Quote 时间", candidate.quote_confirmation?.quote_timestamp || "-"],
        ["Quote 说明", candidate.quote_confirmation?.reason || "-"],
        ["相对强弱", pct(candidate.relative_strength)],
        ["相对成交量", num(candidate.relative_volume)],
        ["成交量异常值", num(candidate.volume_z_score)],
        ["美元成交额", moneyM(candidate.dollar_volume_m)],
        ["20日均美元成交额", moneyM(candidate.avg_dollar_volume_m)],
        ["ATR", pct(candidate.atr_pct)],
        ["20日实现波动", pct(candidate.realized_volatility_20d)],
        ["优势等级", zh("edge", candidate.edge_status)],
        ["风险标记", riskFlags(candidate.risk_flags)],
        ["逼空数据状态", candidate.squeeze_data_status?.short_interest === "proxy" ? "代理数据" : "缺失"],
        ["验证状态", zh("validation", candidate.validation_status)],
      ])}
    </div>
    <div class="detail-card">
      <h3>评分结构</h3>
      ${facts([
        ["弹性评分", candidate.elasticity_score],
        ["原始波动潜力", candidate.elasticity_raw_potential],
        ["弹性确认系数", candidate.elasticity_confirmation_factor],
        ["弹性解释", zhElasticity(candidate.elasticity_interpretation)],
        ["次日明显波动概率", pct(candidate.next_day_move_probability)],
        ["上冲动量评分", candidate.upside_momentum_score],
        ["反抽评分", candidate.bounce_score],
        ["下行延续评分", candidate.downside_continuation_score],
        ["逼空评分", candidate.squeeze_score],
        ["催化评分", candidate.catalyst_score],
        ["风险评分", candidate.risk_score],
        ["共振评分", candidate.confluence_score],
      ])}
    </div>
    <div class="detail-card">
      <h3>支持证据</h3>
      ${evidence(candidate.supporting_evidence || [], false)}
    </div>
    <div class="detail-card">
      <h3>冲突证据</h3>
      ${evidence(candidate.conflicting_evidence || [], true)}
    </div>
    <div class="detail-card">
      <h3>缺失 / 代理证据</h3>
      ${evidence(candidate.missing_evidence || [], true)}
    </div>
    <div class="detail-card">
      <h3>历史相似样本</h3>
      ${analogSummary(candidate.historical_analog)}
      ${similarSamples(candidate.historical_similar_samples || [])}
    </div>
  `;
}

function renderValidation() {
  const validation = dashboard.validation || {};
  const baseline = validation.baseline || {};

  document.getElementById("validationGrid").innerHTML = [
    ["待回填预测", validation.pending_forecasts],
    ["已完成次日验证", validation.completed_next_day_forecasts],
    ["前5命中率", pct(baseline.top5_hit_rate)],
    ["前10命中率", pct(baseline.top10_hit_rate)],
    ["平均次日最高涨幅", pct(baseline.avg_next_day_high_gain)],
    ["平均次日收盘涨幅", pct(baseline.avg_next_day_close_gain)],
    ["平均最大回撤", pct(baseline.avg_max_drawdown)],
    ["触发后收益", pct(baseline.avg_trigger_condition_return)],
    ["盈利因子", num(baseline.profit_factor)],
  ].map(([label, value]) => `<div class="metric"><span>${safe(label)}</span><strong>${safe(value ?? "-")}</strong></div>`).join("");

  const compare = validation.baseline_vs_challenger || {};
  document.getElementById("modelCompare").innerHTML = facts([
    ["基准模型", dashboard.models?.baseline?.model_version],
    ["挑战模型", dashboard.models?.challenger?.model_version],
    ["是否仅影子运行", yn(compare.challenger_shadow_only)],
    ["触发收益差", pct(compare.trigger_return_delta)],
    ["前5命中率差", pct(compare.top5_hit_rate_delta)],
    ["升级状态", statusText(compare.promotion_status)],
  ]);

  const leaderboard = dashboard.model_leaderboard || {};
  const baselineModel = (leaderboard.models || []).find(model => model.role === "baseline") || {};
  const baselineMetrics = baselineModel.metrics || {};
  document.getElementById("modelLeaderboard").innerHTML = facts([
    ["当前基准", leaderboard.active_baseline],
    ["验证状态", zh("validation", leaderboard.validation_status)],
    ["已完成样本", baselineMetrics.completed_next_day_forecasts],
    ["前10平均波动", pct(baselineMetrics.top_10_avg_next_day_volatility)],
    ["方向命中率", pct(baselineMetrics.top_10_next_day_direction_hit_rate)],
    ["区间命中率", pct(baselineMetrics.range_hit_rate)],
    ["主路径命中率", pct(baselineMetrics.primary_scenario_hit_rate)],
    ["高共振是否优于低共振", yn(baselineMetrics.high_confluence_beats_low_confluence)],
    ["高预期差是否更好", yn(baselineMetrics.high_expectation_gap_beats_low)],
    ["高赔率质量是否更好", yn(baselineMetrics.high_payoff_quality_beats_low)],
    ["催化候选是否更好", yn(baselineMetrics.catalyst_candidates_beat_no_catalyst)],
    ["高风险是否更波动", yn(baselineMetrics.high_risk_candidates_more_volatile)],
  ]);

  const quality = dashboard.data_quality || {};
  document.getElementById("dataQuality").innerHTML = facts([
    ["数据质量分", quality.score],
    ["新鲜度", zh("freshness", quality.data_freshness_status)],
    ["是否警告", yn(quality.stale_warning)],
    ["Yahoo 降级数量", quality.provider_status?.yahoo?.fallback_count],
    ["Finnhub 状态", zh("provider", quality.provider_status?.finnhub?.availability_status)],
    ["Finnhub 核心可用", yn(quality.provider_status?.finnhub?.core_available)],
    ["Finnhub 局部错误数", quality.provider_status?.finnhub?.error_count],
    ["FRED 可用", yn(quality.provider_status?.fred?.available)],
  ]);

  renderAgencyReview();
}

function renderAgencyReview() {
  const target = document.getElementById("agencyReview");
  if (!target) return;

  const review = dashboard.agency_review || {};
  const findings = review.agent_findings || [];
  const warnings = review.hard_warnings || [];
  const findingHtml = findings.length
    ? `<div class="evidence">${findings.map(finding => `
      <div class="evidence-item ${finding.status === "fail" ? "conflict" : ""}">
        <strong>${safe(finding.agent_name)} · ${safe(agentStatusText(finding.status))}</strong>
        <p>${safe(finding.evidence || finding.conclusion || "")}</p>
        ${(finding.warnings || []).length ? `<p>${safe((finding.warnings || []).join(" / "))}</p>` : ""}
      </div>
    `).join("")}</div>`
    : "<p>暂无代理审查结果。</p>";

  target.innerHTML = facts([
    ["总判断", review.overall_decision],
    ["质量闸门", review.agency_quality_gate],
    ["市场许可", review.market_permission],
    ["硬警告数量", warnings.length],
    ["最重要警告", warnings[0] || "无"],
    ["方法来源", review.source_framework],
  ]) + findingHtml;
}

function analogSummary(analog) {
  if (!analog) return "<p>暂无相似样本。</p>";
  return facts([
    ["样本数", analog.sample_size],
    ["样本不足警告", yn(analog.low_sample_warning)],
    ["次日平均收益", pct(analog.next_day_return_avg)],
    ["次日命中率", pct(analog.next_day_hit_rate)],
    ["3日平均收益", pct(analog.forward_return_3d_avg)],
    ["5日平均收益", pct(analog.forward_return_5d_avg)],
    ["最大有利波动均值", pct(analog.max_favorable_excursion_avg)],
    ["最大不利波动均值", pct(analog.max_adverse_excursion_avg)],
    ["最差样本", pct(analog.worst_case)],
    ["最佳样本", pct(analog.best_case)],
  ]);
}

function spaceTiles(candidate) {
  const upside = candidate.expected_upside_pct;
  const downside = candidate.expected_downside_pct;
  const range = candidate.next_day_expected_range || {};
  return `
    <div class="space-tiles">
      <div><span>上行空间</span><strong class="green-text">${safe(pct(upside))}</strong></div>
      <div><span>下行风险</span><strong class="red-text">${safe(pct(downside))}</strong></div>
      <div><span>预期高点</span><strong>${safe(price(range.expected_high))}</strong></div>
      <div><span>触发价</span><strong>${safe(price(candidate.upside_trigger_level || candidate.trigger_levels?.upside_trigger_level))}</strong></div>
    </div>
  `;
}

function renderPriceVolumeComposite(candidate) {
  const rows = (candidate.price_history || []).slice(-70);
  if (!rows.length) return `<svg class="chart large-chart" role="img" aria-label="暂无价格成交量数据"></svg>`;
  const width = 620;
  const height = 270;
  const priceTop = 18;
  const priceBottom = 162;
  const volumeTop = 184;
  const volumeBottom = 252;
  const closes = rows.map(row => Number(row.close || 0));
  const highs = rows.map(row => Number(row.high || row.close || 0));
  const lows = rows.map(row => Number(row.low || row.close || 0));
  const volumes = rows.map(row => Number(row.volume || 0));
  const maxPrice = Math.max(...highs, Number(candidate.next_day_expected_range?.expected_high || 0), Number(candidate.upside_trigger_level || 0));
  const minPrice = Math.min(...lows, Number(candidate.next_day_expected_range?.expected_low || Infinity), Number(candidate.invalidation_level || Infinity));
  const pricePad = Math.max(0.01, (maxPrice - minPrice) * 0.08);
  const yPrice = value => priceBottom - ((Number(value) - minPrice + pricePad) / Math.max(0.0001, maxPrice - minPrice + pricePad * 2)) * (priceBottom - priceTop);
  const x = index => (index / Math.max(1, rows.length - 1)) * (width - 24) + 12;
  const maxVolume = Math.max(...volumes, 1);
  const pricePoints = closes.map((value, index) => `${x(index).toFixed(2)},${yPrice(value).toFixed(2)}`).join(" ");
  const bars = volumes.map((value, index) => {
    const barH = (value / maxVolume) * (volumeBottom - volumeTop);
    return `<rect x="${(x(index) - 2).toFixed(2)}" y="${(volumeBottom - barH).toFixed(2)}" width="3.5" height="${barH.toFixed(2)}" fill="#276c9f" opacity="${index === volumes.length - 1 ? "0.9" : "0.42"}" />`;
  }).join("");
  const support = candidate.nearest_support || candidate.trigger_levels?.nearest_support;
  const resistance = candidate.nearest_resistance || candidate.trigger_levels?.nearest_resistance;
  const trigger = candidate.upside_trigger_level || candidate.trigger_levels?.upside_trigger_level;
  const invalidation = candidate.invalidation_level || candidate.trigger_levels?.invalidation_level;
  const current = candidate.current_price;
  return `
    <svg class="chart large-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="价格结构与成交量图">
      <rect x="0" y="0" width="${width}" height="${height}" fill="#fff" rx="8" />
      ${levelLine(width, yPrice(resistance), "#9b6500", "压力")}
      ${levelLine(width, yPrice(support), "#687781", "支撑")}
      ${levelLine(width, yPrice(trigger), "#127657", "触发")}
      ${levelLine(width, yPrice(invalidation), "#b83232", "失效")}
      <polyline points="${pricePoints}" fill="none" stroke="#172026" stroke-width="2.8" />
      ${current ? `<circle cx="${x(rows.length - 1).toFixed(2)}" cy="${yPrice(current).toFixed(2)}" r="5" fill="#127657" />` : ""}
      <line x1="12" y1="${volumeTop}" x2="${width - 12}" y2="${volumeTop}" stroke="#d7e0e4" />
      ${bars}
      <text x="14" y="16" fill="#687781" font-size="12">价格结构</text>
      <text x="14" y="${volumeTop - 8}" fill="#687781" font-size="12">成交量</text>
    </svg>
  `;
}

function renderExpectedRangeChart(candidate) {
  const range = candidate.next_day_expected_range || {};
  const low = Number(range.expected_low);
  const high = Number(range.expected_high);
  const mid = Number(range.expected_mid);
  const last = Number(candidate.last_close || candidate.current_price || 0);
  const current = Number(candidate.current_price || last);
  const trigger = Number(candidate.upside_trigger_level || candidate.trigger_levels?.upside_trigger_level || 0);
  const invalidation = Number(candidate.invalidation_level || candidate.trigger_levels?.invalidation_level || 0);
  const values = [low, high, mid, last, current, trigger, invalidation].filter(Number.isFinite);
  if (values.length < 2) return `<svg class="chart" role="img" aria-label="暂无预期区间数据"></svg>`;
  const width = 520;
  const height = 190;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max(0.01, (max - min) * 0.14);
  const scale = value => 28 + ((Number(value) - min + pad) / Math.max(0.0001, max - min + pad * 2)) * (width - 56);
  const barX = scale(low);
  const barW = Math.max(2, scale(high) - barX);
  return `
    <svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="次日预期区间图">
      <rect x="0" y="0" width="${width}" height="${height}" fill="#fff" rx="8" />
      <line x1="28" y1="92" x2="${width - 28}" y2="92" stroke="#d7e0e4" stroke-width="2" />
      <rect x="${barX.toFixed(2)}" y="70" width="${barW.toFixed(2)}" height="44" rx="6" fill="#e0eff8" stroke="#276c9f" />
      ${rangeMarker(scale(low), 92, "#276c9f", "低")}
      ${rangeMarker(scale(mid), 92, "#172026", "中")}
      ${rangeMarker(scale(high), 92, "#276c9f", "高")}
      ${rangeMarker(scale(last), 134, "#687781", "昨收")}
      ${rangeMarker(scale(current), 50, "#127657", "当前")}
      ${rangeMarker(scale(trigger), 24, "#127657", "触发")}
      ${rangeMarker(scale(invalidation), 160, "#b83232", "失效")}
      <text x="28" y="182" fill="#687781" font-size="12">预期区间：${safe(rangeLabel(range))}</text>
    </svg>
  `;
}

function renderFutureScenarioChart(candidate) {
  const rows = (candidate.price_history || []).slice(-38);
  if (!rows.length) return `<svg class="chart" role="img" aria-label="暂无未来情景数据"></svg>`;
  const width = 620;
  const height = 250;
  const history = rows.map(row => Number(row.close || 0));
  const last = Number(candidate.current_price || candidate.last_close || history[history.length - 1]);
  const scenario = candidate.scenario_prices || {};
  const upsideTarget = Number(scenario.upside_case_price || candidate.next_day_expected_range?.expected_high || last);
  const baseTarget = Number(scenario.base_case_price || candidate.next_day_expected_range?.expected_mid || last);
  const downsideTarget = Number(scenario.downside_case_price || candidate.next_day_expected_range?.expected_low || last);
  const futureSteps = 6;
  const allValues = [...history, last, upsideTarget, baseTarget, downsideTarget];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const pad = Math.max(0.01, (max - min) * 0.12);
  const y = value => height - 28 - ((Number(value) - min + pad) / Math.max(0.0001, max - min + pad * 2)) * (height - 54);
  const xHistory = index => 12 + (index / Math.max(1, history.length + futureSteps - 1)) * (width - 24);
  const historyPoints = history.map((value, index) => `${xHistory(index).toFixed(2)},${y(value).toFixed(2)}`).join(" ");
  const startIndex = history.length - 1;
  const project = target => Array.from({ length: futureSteps + 1 }, (_, step) => {
    const t = step / futureSteps;
    const curve = last + (target - last) * (1 - Math.pow(1 - t, 1.25));
    return `${xHistory(startIndex + step).toFixed(2)},${y(curve).toFixed(2)}`;
  }).join(" ");
  return `
    <svg class="chart large-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="未来情景走势图">
      <rect x="0" y="0" width="${width}" height="${height}" fill="#fff" rx="8" />
      <polyline points="${historyPoints}" fill="none" stroke="#172026" stroke-width="2.5" />
      <line x1="${xHistory(startIndex).toFixed(2)}" y1="16" x2="${xHistory(startIndex).toFixed(2)}" y2="${height - 24}" stroke="#d7e0e4" stroke-dasharray="4 4" />
      <polyline points="${project(upsideTarget)}" fill="none" stroke="#127657" stroke-width="2.8" stroke-dasharray="7 4" />
      <polyline points="${project(baseTarget)}" fill="none" stroke="#276c9f" stroke-width="2.5" stroke-dasharray="5 5" />
      <polyline points="${project(downsideTarget)}" fill="none" stroke="#b83232" stroke-width="2.5" stroke-dasharray="4 5" />
      <text x="14" y="18" fill="#687781" font-size="12">历史走势 + 未来情景线</text>
      <text x="${width - 155}" y="28" fill="#127657" font-size="12">上冲 ${fmtPriceShort(upsideTarget)}</text>
      <text x="${width - 155}" y="46" fill="#276c9f" font-size="12">主路径 ${fmtPriceShort(baseTarget)}</text>
      <text x="${width - 155}" y="64" fill="#b83232" font-size="12">风险 ${fmtPriceShort(downsideTarget)}</text>
    </svg>
  `;
}

function renderVolumeAnalysis(candidate) {
  const relative = Number(candidate.relative_volume);
  const z = Number(candidate.volume_z_score);
  const score = Number(candidate.volume_score);
  const verdict = volumeVerdict(candidate);
  return `
    <div class="volume-analysis">
      <div>
        <span>成交量判断</span>
        <strong>${safe(verdict)}</strong>
      </div>
      <div>
        <span>相对成交量</span>
        <strong>${safe(Number.isFinite(relative) ? `${relative.toFixed(2)}x` : "-")}</strong>
      </div>
      <div>
        <span>量能异常</span>
        <strong>${safe(Number.isFinite(z) ? z.toFixed(2) : "-")}</strong>
      </div>
      <div>
        <span>量能评分</span>
        <strong>${safe(Number.isFinite(score) ? score.toFixed(1) : "-")}</strong>
      </div>
      <p>${safe(volumeNarrative(candidate))}</p>
    </div>
  `;
}

function renderChart(rows, field) {
  if (!rows.length) return `<svg class="chart" role="img" aria-label="暂无图表数据"></svg>`;
  const values = rows.map(row => Number(row[field] || 0));
  const max = Math.max(...values);
  const min = Math.min(...values);
  const width = 360;
  const height = 180;

  if (field === "volume") {
    const bars = values.map((value, index) => {
      const x = (index / values.length) * width;
      const h = max ? (value / max) * (height - 18) : 0;
      return `<rect x="${x.toFixed(2)}" y="${(height - h).toFixed(2)}" width="${Math.max(1, width / values.length - 1).toFixed(2)}" height="${h.toFixed(2)}" fill="#276c9f" opacity="0.62" />`;
    }).join("");
    return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="成交量图">${bars}</svg>`;
  }

  const points = values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width;
    const y = height - ((value - min) / Math.max(0.0001, max - min)) * (height - 18) - 8;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="价格图"><polyline points="${points}" fill="none" stroke="#127657" stroke-width="3"/></svg>`;
}

function facts(items) {
  return `<div class="fact-list">${items.map(([label, value]) => `<div class="fact"><span>${safe(label)}</span><strong>${safe(value ?? "-")}</strong></div>`).join("")}</div>`;
}

function evidence(items, conflict) {
  if (!items.length) return `<p>暂无证据。</p>`;
  return `<div class="evidence">${items.map(item => `
    <div class="evidence-item ${conflict ? "conflict" : ""}">
      <strong>${safe(zh("evidence", item.name) || item.source || "证据")} · ${safe(item.score ?? "-")}</strong>
      <p>${safe(item.detail || item.source || "")}</p>
    </div>
  `).join("")}</div>`;
}

function confluenceMatrix(matrix) {
  if (!matrix || !Array.isArray(matrix.items) || !matrix.items.length) {
    return `<p>暂无共振矩阵。</p>`;
  }
  const summary = [
    ["总体", confluenceOverallText(matrix.overall)],
    ["核心确认数", matrix.confirmed_core_count ?? "-"],
    ["阻断维度", (matrix.blocking_dimensions || []).join(" / ") || "无"],
  ];
  const rows = matrix.items.map(item => `
    <div class="matrix-row status-${safeAttr(item.status)}">
      <div>
        <strong>${safe(item.label || item.dimension)}</strong>
        <span>${safe(confluenceStatusText(item.status))}</span>
      </div>
      <div class="matrix-score">${safe(num(item.score))}</div>
      <p>${safe(item.reason || "-")}</p>
    </div>
  `).join("");
  return `
    ${facts(summary)}
    <div class="matrix-grid">${rows}</div>
  `;
}

function similarSamples(items) {
  if (!items.length) return `<p>暂无成熟相似样本。</p>`;
  return `<div class="sample-list">${items.map(item => `
    <div>
      <strong>${safe(item.date)}</strong>
      <span>次日 ${safe(pct(item.next_day_return))}</span>
      <span>3日 ${safe(pct(item.return_3d))}</span>
      <span>5日 ${safe(pct(item.return_5d))}</span>
      <span>最大有利 ${safe(pct(item.max_favorable_excursion))}</span>
      <span>最大不利 ${safe(pct(item.max_adverse_excursion))}</span>
    </div>
  `).join("")}</div>`;
}

function levelLine(width, y, color, label) {
  if (!Number.isFinite(y)) return "";
  return `
    <line x1="12" y1="${y.toFixed(2)}" x2="${width - 12}" y2="${y.toFixed(2)}" stroke="${color}" stroke-width="1.5" stroke-dasharray="5 5" opacity="0.75" />
    <text x="${width - 52}" y="${Math.max(14, y - 4).toFixed(2)}" fill="${color}" font-size="11">${safe(label)}</text>
  `;
}

function rangeMarker(x, y, color, label) {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return "";
  const textY = y < 95 ? y - 10 : y + 24;
  return `
    <line x1="${x.toFixed(2)}" y1="${Math.max(22, y - 22).toFixed(2)}" x2="${x.toFixed(2)}" y2="${Math.min(166, y + 22).toFixed(2)}" stroke="${color}" stroke-width="2" />
    <circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="4" fill="${color}" />
    <text x="${(x + 5).toFixed(2)}" y="${textY.toFixed(2)}" fill="${color}" font-size="11">${safe(label)}</text>
  `;
}

function volumeVerdict(candidate) {
  const relative = Number(candidate.relative_volume);
  const z = Number(candidate.volume_z_score);
  if (relative >= 1.8 && z >= 1.2) return "放量确认";
  if (relative >= 1.25 || z >= 0.8) return "温和放量";
  if (relative < 0.75 && z < -0.5) return "量能不足";
  return "量能中性";
}

function volumeNarrative(candidate) {
  const relative = Number(candidate.relative_volume);
  const z = Number(candidate.volume_z_score);
  const dollar = Number(candidate.dollar_volume_m);
  const avgDollar = Number(candidate.avg_dollar_volume_m);
  if (!Number.isFinite(relative)) return "成交量数据缺失，不能把量能当成支持证据。";
  const parts = [
    `当前相对成交量约 ${relative.toFixed(2)}x`,
    Number.isFinite(z) ? `量能异常值 ${z.toFixed(2)}` : "",
    Number.isFinite(dollar) && Number.isFinite(avgDollar) ? `美元成交额 ${dollar.toFixed(1)}M，20日均值 ${avgDollar.toFixed(1)}M` : "",
  ].filter(Boolean);
  if (relative >= 1.8 && z >= 1.2) parts.push("成交量正在给价格路径提供确认。");
  else if (relative < 0.75) parts.push("量能偏弱，若价格上冲但成交不能放大，路径质量要降级。");
  else parts.push("量能没有明显否定，但还需要触发价附近继续确认。");
  return parts.join("；");
}

function scoreBlock(value, label) {
  return `<strong>${safe(value ?? "-")}</strong><small>${safe(label)}</small>`;
}

function avoidReason(item) {
  const flags = riskFlags(item.risk_flags || Object.entries(item.pool_filter?.flags || {}).filter(([, enabled]) => enabled).map(([key]) => key));
  return flags !== "无" ? flags : item.reason || "数据不共振";
}

function riskFlags(flags) {
  if (!flags || !flags.length) return "无";
  return flags.map(flag => LABELS.riskFlag[flag] || flag).join(" / ");
}

function renderError() {
  setText("radarDecision", "未找到雷达数据");
  setText("radarSummary", "请先运行每日雷达脚本并导出静态页面。");
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value ?? "-";
}

function ratingClass(rating) {
  if (rating === "A+" || rating === "A") return "good";
  if (rating === "C") return "bad";
  return "neutral";
}

function edgeClass(edge) {
  if (edge === "STRONG_EDGE" || edge === "MODERATE_EDGE") return "good";
  if (edge === "AVOID" || edge === "NO_EDGE") return "bad";
  return "neutral";
}

function matrixClass(overall) {
  if (overall === "confirmed") return "good";
  if (overall === "blocked" || overall === "incomplete") return "bad";
  return "neutral";
}

function price(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(2)} 美元` : "-";
}

function pct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "-";
}

function num(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "-";
}

function moneyM(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)} 百万美元` : "-";
}

function fmtPriceShort(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `$${number.toFixed(2)}` : "-";
}

function rangeLabel(range) {
  if (!range) return "-";
  const low = price(range.expected_low);
  const high = price(range.expected_high);
  return low !== "-" && high !== "-" ? `${low} 至 ${high}` : "-";
}

function yn(value) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "-";
}

function zh(group, value) {
  if (value === undefined || value === null || value === "") return "-";
  return LABELS[group]?.[value] || value;
}

function statusText(value) {
  return {
    not_yet_validated: "样本不足",
    sample_insufficient: "样本不足",
    shadow_observation_required: "继续影子观察",
    active_baseline: "当前基准",
  }[value] || value || "-";
}

function agentStatusText(value) {
  return {
    pass: "通过",
    warn: "警告",
    fail: "不通过",
  }[value] || value || "-";
}

function quoteStatusText(value) {
  return {
    confirming: "当前价支持路径",
    neutral: "当前价中性",
    failed: "当前价否定路径",
    missing: "当前价缺失",
  }[value] || value || "-";
}

function signalGateText(value) {
  return {
    confirmed: "真实共振",
    partial: "部分共振",
    incomplete: "共振不足",
    blocked: "硬缺口",
  }[value] || value || "-";
}

function confluenceStatusText(value) {
  return {
    confirmed: "确认",
    partial: "部分",
    weak: "偏弱",
    blocked: "阻断",
    missing: "缺失",
  }[value] || value || "-";
}

function confluenceOverallText(value) {
  return {
    confirmed: "真实共振",
    partial: "部分共振",
    incomplete: "共振不足",
    blocked: "存在阻断",
  }[value] || value || "-";
}

function zhElasticity(value) {
  return {
    confirmed_elasticity: "确认弹性",
    partially_confirmed_elasticity: "部分确认弹性",
    unconfirmed_volatility: "未确认波动",
    normal_volatility: "普通波动",
  }[value] || value || "-";
}

function safe(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeAttr(value) {
  return safe(value).replaceAll("`", "&#096;");
}
