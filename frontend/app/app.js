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
  selectedTicker = dashboard.top_candidates?.[0]?.ticker || null;
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
  const topCandidate = dashboard.top_candidates?.[0] || null;

  setText("radarDecision", dashboard.high_elasticity_opportunity ? "明天有高弹性候选" : "明天不强行进攻");
  setText("radarSummary", dashboard.radar_summary || "");
  setText("opportunityStatus", dashboard.high_elasticity_opportunity ? "有候选" : "观望");
  setText("strongestCandidate", topCandidate ? `${topCandidate.ticker} ${topCandidate.rating || ""}` : "-");
  setText("strongestDirection", zh("candidateType", topCandidate?.candidate_type || dashboard.strongest_candidate_type));
  setText("marketState", zh("market", marketState));
  setText("screeningStatus", marketState === "defense" ? "防守过滤" : "可筛选，等触发");
  setText("riskLevel", zh("risk", dashboard.current_risk_level));
  setText("dataDate", `${dashboard.latest_data_date || "-"} / 应有最新交易日 ${dashboard.expected_latest_trading_date || "-"}`);
  setText("validationStatus", zh("validation", dashboard.model_validation_status));
  setText("candidateCount", `${dashboard.top_candidates?.length || 0} 只展示 / ${dashboard.candidate_count || 0} 只总候选`);

  const freshnessBadge = document.getElementById("freshnessBadge");
  freshnessBadge.textContent = fresh ? "数据最新" : "数据警告";
  freshnessBadge.className = `badge ${fresh ? "good" : "bad"}`;

  const validationBadge = document.getElementById("validationBadge");
  validationBadge.textContent = zh("validation", dashboard.model_validation_status);
  validationBadge.className = `badge ${dashboard.model_validation_status === "validated" ? "good" : "neutral"}`;

  renderAvoidList();
  renderCandidateTable();
  renderDetail();
  renderValidation();
}

function renderAvoidList() {
  const target = document.getElementById("avoidList");
  if (!target) return;
  const rows = [...(dashboard.excluded_candidates || []), ...(dashboard.avoid_candidates || [])].slice(0, 6);
  target.innerHTML = rows.length
    ? rows.map(item => `<li><strong>${safe(item.ticker)}</strong><span>${safe(avoidReason(item))}</span></li>`).join("")
    : `<li><strong>暂无</strong><span>当前没有需要额外提示的剔除项</span></li>`;
}

function renderCandidateTable() {
  const tbody = document.querySelector("#candidateTable tbody");
  tbody.innerHTML = (dashboard.top_candidates || []).map(candidate => `
    <tr data-ticker="${safeAttr(candidate.ticker)}">
      <td>${safe(candidate.rank)}</td>
      <td>
        <strong>${safe(candidate.ticker)}</strong>
        <small>${safe(candidate.company_name || "")}</small>
        <span class="badge ${edgeClass(candidate.edge_status)}">${safe(zh("edge", candidate.edge_status))}</span>
      </td>
      <td>${safe(zh("candidateType", candidate.candidate_type))}</td>
      <td>${scoreBlock(candidate.elasticity_score, "弹性")}</td>
      <td>${scoreBlock(candidate.confluence_score, "共振")}</td>
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
      renderDetail();
      document.querySelector(".detail-band").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function renderDetail() {
  const candidate = (dashboard.top_candidates || []).find(item => item.ticker === selectedTicker) || dashboard.top_candidates?.[0];
  if (!candidate) {
    document.getElementById("candidateDetail").innerHTML = `<div class="detail-card">没有候选。</div>`;
    return;
  }

  setText("detailTitle", `${candidate.ticker} · ${candidate.company_name || "公司名称缺失"}`);
  const rating = document.getElementById("detailRating");
  rating.textContent = `${candidate.rating || "-"} · 弹性 ${candidate.elasticity_score ?? "-"}`;
  rating.className = `badge ${ratingClass(candidate.rating)}`;

  document.getElementById("candidateDetail").innerHTML = `
    <div class="detail-card chart-card">
      <h3>价格 / 成交量</h3>
      ${renderChart(candidate.price_history || [], "close")}
      ${renderChart(candidate.price_history || [], "volume")}
    </div>
    <div class="detail-card">
      <h3>次日概率路径</h3>
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
      <p class="note">这些是概率路径点位，不是投资建议、买卖指令或仓位建议。</p>
    </div>
    <div class="detail-card">
      <h3>精准闸门</h3>
      ${facts([
        ["质量闸门", candidate.precision_gate?.level || "-"],
        ["是否通过", yn(candidate.precision_gate?.passed)],
        ["闸门原因", (candidate.precision_gate?.reason || []).join(" / ") || "-"],
        ["预期差评分", candidate.expectation_gap_score],
        ["执行质量评分", candidate.execution_quality_score],
        ["赔率质量评分", candidate.payoff_quality_score],
        ["上行/下行赔率", num(candidate.risk_reward_ratio)],
        ["预期上行", pct(candidate.expected_upside_pct)],
        ["预期下行", pct(candidate.expected_downside_pct)],
      ])}
    </div>
    <div class="detail-card">
      <h3>催化 / 相对强弱</h3>
      ${facts([
        ["新闻催化", zh("evidence", candidate.news?.catalyst_type) || "无确认新闻"],
        ["主新闻", candidate.news?.primary_headline || "近期没有确认主新闻"],
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
