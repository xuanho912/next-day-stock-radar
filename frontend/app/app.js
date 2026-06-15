const DATA_FILES = {
  dashboard: ["./stock-radar-dashboard.json", "../public/stock-radar-dashboard.json", "./public/stock-radar-dashboard.json"],
  validation: ["./validation-scorecard.json", "../public/validation-scorecard.json", "./public/validation-scorecard.json"],
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
      // Try the next static location.
    }
  }
  return null;
}

function renderDashboard() {
  const fresh = dashboard.data_freshness_status === "fresh";
  setText("radarDecision", dashboard.high_elasticity_opportunity ? "明天有可观察的高弹性机会" : "明天不强行进攻");
  setText("radarSummary", dashboard.radar_summary || "");
  setText("opportunityStatus", dashboard.high_elasticity_opportunity ? "YES" : "NO / WAIT");
  setText("marketState", dashboard.market_context?.market_state || "-");
  setText("candidateType", dashboard.strongest_candidate_type || "-");
  setText("riskLevel", dashboard.current_risk_level || "-");
  setText("dataDate", `${dashboard.latest_data_date || "-"} / expected ${dashboard.expected_latest_trading_date || "-"}`);
  setText("validationStatus", dashboard.model_validation_status || "not_yet_validated");
  setText("candidateCount", `${dashboard.candidate_count || 0} candidates`);

  const freshnessBadge = document.getElementById("freshnessBadge");
  freshnessBadge.textContent = fresh ? "fresh data" : "STALE WARNING";
  freshnessBadge.className = `badge ${fresh ? "good" : "bad"}`;
  const validationBadge = document.getElementById("validationBadge");
  validationBadge.textContent = dashboard.model_validation_status || "not_yet_validated";
  validationBadge.className = `badge ${dashboard.model_validation_status === "validated" ? "good" : "neutral"}`;

  renderTopPreview();
  renderCandidateTable();
  renderDetail();
  renderValidation();
}

function renderTopPreview() {
  const container = document.getElementById("topPreview");
  const rows = dashboard.top_candidates || [];
  container.innerHTML = rows.slice(0, 5).map(candidate => `
    <article class="top-card" data-card="${candidate.ticker}">
      <div class="section-heading">
        <strong>${candidate.rank}. ${candidate.ticker}</strong>
        <span class="badge ${ratingClass(candidate.rating)}">${candidate.rating} · ${candidate.elasticity_score}</span>
      </div>
      <p>${candidate.reason}</p>
      <p>Trigger ${price(candidate.upside_trigger_level)} | Invalidation ${price(candidate.invalidation_level)} | ${candidate.next_day_expected_range?.label || "-"}</p>
    </article>
  `).join("") || `<div class="top-card"><strong>No actionable candidates</strong><p>Current confluence gates did not pass enough names.</p></div>`;
  container.querySelectorAll("[data-card]").forEach(card => {
    card.addEventListener("click", () => {
      selectedTicker = card.dataset.card;
      renderDetail();
    });
  });
}

function renderCandidateTable() {
  const tbody = document.querySelector("#candidateTable tbody");
  tbody.innerHTML = (dashboard.top_candidates || []).map(candidate => `
    <tr data-ticker="${candidate.ticker}">
      <td>${candidate.rank}</td>
      <td><strong>${candidate.ticker}</strong><br><span class="badge ${ratingClass(candidate.rating)}">${candidate.rating}</span></td>
      <td>${candidate.company_name}</td>
      <td>${price(candidate.last_close)}</td>
      <td>${candidate.candidate_type}</td>
      <td><span class="badge ${edgeClass(candidate.edge_status)}">${candidate.edge_status || "-"}</span></td>
      <td>${candidate.elasticity_score}</td>
      <td>${candidate.confluence_score}</td>
      <td>${candidate.catalyst_score}</td>
      <td>${candidate.risk_score}</td>
      <td>${candidate.primary_scenario}</td>
      <td>${candidate.next_day_expected_range?.label || "-"}</td>
      <td>${price(candidate.upside_trigger_level)}</td>
      <td>${price(candidate.invalidation_level)}</td>
      <td>${candidate.reason}</td>
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
    document.getElementById("candidateDetail").innerHTML = `<div class="detail-card">No candidate selected.</div>`;
    return;
  }
  setText("detailTitle", `${candidate.ticker} · ${candidate.company_name}`);
  const rating = document.getElementById("detailRating");
  rating.textContent = `${candidate.rating} · ${candidate.elasticity_score}`;
  rating.className = `badge ${ratingClass(candidate.rating)}`;
  document.getElementById("candidateDetail").innerHTML = `
    <div class="detail-card">
      <h3>历史价格 / 成交量</h3>
      ${renderChart(candidate.price_history || [], "close")}
      ${renderChart(candidate.price_history || [], "volume")}
    </div>
    <div class="detail-card">
      <h3>预测路径</h3>
      ${facts([
        ["主路径", candidate.primary_scenario],
        ["主路径概率", pct(candidate.primary_probability)],
        ["第二路径", candidate.secondary_scenario],
        ["第二路径概率", pct(candidate.secondary_probability)],
        ["风险路径", candidate.risk_scenario],
        ["风险路径概率", pct(candidate.risk_probability)],
        ["次日区间", candidate.next_day_expected_range?.label],
        ["Expected low", price(candidate.next_day_expected_range?.expected_low)],
        ["Expected mid", price(candidate.next_day_expected_range?.expected_mid)],
        ["Expected high", price(candidate.next_day_expected_range?.expected_high)],
        ["上冲触发价", price(candidate.trigger_levels?.upside_trigger_level || candidate.upside_trigger_level)],
        ["下行风险价", price(candidate.trigger_levels?.downside_risk_level || candidate.downside_risk_level)],
        ["失效价", price(candidate.trade_plan?.invalidation_level)],
        ["Gap fill", price(candidate.trigger_levels?.gap_fill_level || candidate.gap_fill_level)],
        ["Breakout", price(candidate.trigger_levels?.breakout_level || candidate.breakout_level)],
        ["Breakdown", price(candidate.trigger_levels?.breakdown_level || candidate.breakdown_level)],
        ["Support", price(candidate.trigger_levels?.nearest_support || candidate.nearest_support)],
        ["Resistance", price(candidate.trigger_levels?.nearest_resistance || candidate.nearest_resistance)],
      ])}
    </div>
    <div class="detail-card">
      <h3>催化 / 相对强弱</h3>
      ${facts([
        ["新闻催化", candidate.news?.catalyst_type || "none"],
        ["主新闻", candidate.news?.primary_headline || "No recent confirmed headline"],
        ["相对强弱", pct(candidate.relative_strength)],
        ["相对成交量", candidate.relative_volume],
        ["Volume Z", candidate.volume_z_score],
        ["美元成交额", `${candidate.dollar_volume_m || "-"}M`],
        ["20日均美元成交额", `${candidate.avg_dollar_volume_m || "-"}M`],
        ["ATR%", pct(candidate.atr_pct)],
        ["20日实现波动", pct(candidate.realized_volatility_20d)],
        ["Edge", candidate.edge_status],
        ["Risk flags", (candidate.risk_flags || []).join(" / ") || "none"],
        ["Squeeze data", candidate.squeeze_data_status?.short_interest || "missing"],
        ["验证状态", candidate.validation_status],
      ])}
    </div>
    <div class="detail-card">
      <h3>评分结构</h3>
      ${facts([
        ["elasticity_score", candidate.elasticity_score],
        ["next_day_move_probability", pct(candidate.next_day_move_probability)],
        ["upside_momentum_score", candidate.upside_momentum_score],
        ["bounce_score", candidate.bounce_score],
        ["downside_continuation_score", candidate.downside_continuation_score],
        ["squeeze_score", candidate.squeeze_score],
        ["catalyst_score", candidate.catalyst_score],
        ["risk_score", candidate.risk_score],
        ["confluence_score", candidate.confluence_score],
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
      <h3>缺失 / Proxy 证据</h3>
      ${evidence(candidate.missing_evidence || [], true)}
    </div>
    <div class="detail-card">
      <h3>历史类似样本</h3>
      ${analogSummary(candidate.historical_analog)}
      ${similarSamples(candidate.historical_similar_samples || [])}
    </div>
  `;
}

function renderValidation() {
  const validation = dashboard.validation || {};
  const baseline = validation.baseline || {};
  document.getElementById("validationGrid").innerHTML = [
    ["Pending", validation.pending_forecasts],
    ["Completed next-day", validation.completed_next_day_forecasts],
    ["Top 5 hit rate", pct(baseline.top5_hit_rate)],
    ["Top 10 hit rate", pct(baseline.top10_hit_rate)],
    ["Avg high gain", pct(baseline.avg_next_day_high_gain)],
    ["Avg close gain", pct(baseline.avg_next_day_close_gain)],
    ["Avg max drawdown", pct(baseline.avg_max_drawdown)],
    ["Trigger-buy return", pct(baseline.avg_trigger_buy_return)],
    ["Profit factor", num(baseline.profit_factor)],
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value ?? "-"}</strong></div>`).join("");

  const compare = validation.baseline_vs_challenger || {};
  document.getElementById("modelCompare").innerHTML = facts([
    ["Baseline", dashboard.models?.baseline?.model_version],
    ["Challenger", dashboard.models?.challenger?.model_version],
    ["Shadow only", compare.challenger_shadow_only],
    ["Trigger return delta", pct(compare.trigger_return_delta)],
    ["Top5 hit delta", pct(compare.top5_hit_rate_delta)],
    ["Promotion", compare.promotion_status],
  ]);

  const leaderboard = dashboard.model_leaderboard || {};
  const baselineModel = (leaderboard.models || []).find(model => model.role === "baseline") || {};
  const baselineMetrics = baselineModel.metrics || {};
  document.getElementById("modelLeaderboard").innerHTML = facts([
    ["Active baseline", leaderboard.active_baseline],
    ["Leaderboard status", leaderboard.validation_status],
    ["Completed", baselineMetrics.completed_next_day_forecasts],
    ["Top10 avg volatility", pct(baselineMetrics.top_10_avg_next_day_volatility)],
    ["Direction hit", pct(baselineMetrics.top_10_next_day_direction_hit_rate)],
    ["Range hit", pct(baselineMetrics.range_hit_rate)],
    ["Primary hit", pct(baselineMetrics.primary_scenario_hit_rate)],
    ["High conf > low conf", baselineMetrics.high_confluence_beats_low_confluence],
    ["Catalyst > no catalyst", baselineMetrics.catalyst_candidates_beat_no_catalyst],
    ["High risk more volatile", baselineMetrics.high_risk_candidates_more_volatile],
  ]);

  const quality = dashboard.data_quality || {};
  document.getElementById("dataQuality").innerHTML = facts([
    ["Score", quality.score],
    ["Freshness", quality.data_freshness_status],
    ["Stale warning", quality.stale_warning],
    ["Yahoo fallback count", quality.provider_status?.yahoo?.fallback_count],
    ["Finnhub available", quality.provider_status?.finnhub?.available],
    ["FRED available", quality.provider_status?.fred?.available],
  ]);
}

function analogSummary(analog) {
  if (!analog) return "";
  return facts([
    ["sample_size", analog.sample_size],
    ["low_sample_warning", analog.low_sample_warning],
    ["next_day_return_avg", pct(analog.next_day_return_avg)],
    ["next_day_hit_rate", pct(analog.next_day_hit_rate)],
    ["3d forward avg", pct(analog.forward_return_3d_avg)],
    ["5d forward avg", pct(analog.forward_return_5d_avg)],
    ["MFE avg", pct(analog.max_favorable_excursion_avg)],
    ["MAE avg", pct(analog.max_adverse_excursion_avg)],
    ["worst_case", pct(analog.worst_case)],
    ["best_case", pct(analog.best_case)],
  ]);
}

function renderChart(rows, field) {
  if (!rows.length) return `<svg class="chart" role="img"></svg>`;
  const values = rows.map(row => Number(row[field] || 0));
  const max = Math.max(...values);
  const min = Math.min(...values);
  const width = 360;
  const height = 180;
  if (field === "volume") {
    const bars = values.map((value, index) => {
      const x = (index / values.length) * width;
      const h = max ? (value / max) * (height - 18) : 0;
      return `<rect x="${x.toFixed(2)}" y="${height - h}" width="${Math.max(1, width / values.length - 1)}" height="${h}" fill="#276c9f" opacity="0.62" />`;
    }).join("");
    return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="volume chart">${bars}</svg>`;
  }
  const points = values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width;
    const y = height - ((value - min) / Math.max(0.0001, max - min)) * (height - 18) - 8;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="price chart"><polyline points="${points}" fill="none" stroke="#127657" stroke-width="3"/></svg>`;
}

function facts(items) {
  return `<div class="fact-list">${items.map(([label, value]) => `<div class="fact"><span>${label}</span><strong>${value ?? "-"}</strong></div>`).join("")}</div>`;
}

function evidence(items, conflict) {
  if (!items.length) return `<p>No evidence.</p>`;
  return `<div class="evidence">${items.map(item => `
    <div class="evidence-item ${conflict ? "conflict" : ""}">
      <strong>${item.name} · ${item.score}</strong>
      <p>${item.detail || item.source}</p>
    </div>
  `).join("")}</div>`;
}

function similarSamples(items) {
  if (!items.length) return `<p>No mature similar sample support yet.</p>`;
  return facts(items.map(item => [item.date, pct(item.forward_5d_return)]));
}

function renderError() {
  setText("radarDecision", "未找到 dashboard JSON");
  setText("radarSummary", "请先运行 python scripts/run_daily_radar.py 和 python scripts/export_static_dashboard.py。");
}

function setText(id, value) {
  document.getElementById(id).textContent = value ?? "-";
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
  return Number.isFinite(number) ? `$${number.toFixed(2)}` : "-";
}

function pct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "-";
}

function num(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "-";
}
