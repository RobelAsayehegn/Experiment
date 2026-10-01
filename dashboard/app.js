"use strict";
const D = window.DATA;
const $ = (id) => document.getElementById(id);
const state = { interval: null, coin: "ALL", dir: "all", sel: null, sortKey: "net", sortDir: -1 };

const LABEL = {
  ma_trend: "MA trend", breakout: "Breakout", rsi_reversion: "RSI reversion",
  bollinger_reversion: "Bollinger reversion", vol_filtered_trend: "Vol-filtered trend",
};
const base = (v) => v.replace(/_ls$/, "");
const isLS = (v) => v.endsWith("_ls");
const name = (v) => LABEL[base(v)] + (isLS(v) ? " (long/short)" : " (long-only)");

// ---------- formatting ----------
const nz = (x) => x === null || x === undefined || Number.isNaN(x);
const pct = (x, d = 1) => (nz(x) ? "n/a" : (x >= 0 ? "+" : "") + (x * 100).toFixed(d) + "%");
const num = (x, d = 2) => (nz(x) ? "n/a" : x.toFixed(d));
const cls = (x) => (nz(x) ? "" : x > 0 ? "pos" : x < 0 ? "neg" : "");
const span = (x, txt) => `<span class="${cls(x)}">${txt}</span>`;
const mean = (a) => { const v = a.filter((x) => !nz(x)); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; };
const colour = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

// ---------- data access ----------
const coins = () => Object.keys(D.intervals[state.interval]);
const shown = () => (state.coin === "ALL" ? coins() : [state.coin]);
const variantsAll = () => Object.keys(D.intervals[state.interval][coins()[0]].variants);
const variants = () => variantsAll().filter((v) => state.dir === "all" || (state.dir === "ls") === isLS(v));
const cell = (sym, v, iv = state.interval) => D.intervals[iv][sym].variants[v];
const wf = (sym, v, iv) => cell(sym, v, iv).walk_forward;

function cellStatus(r) {           // r = walk_forward block
  const m = r.metrics;
  if (m.net_return > 0 && m.expectancy_per_trade > 0 && r.percentile_vs_random >= 95) return "pass";
  if (m.net_return > 0 && m.expectancy_per_trade > 0 && r.percentile_vs_random >= 80) return "maybe";
  return "fail";
}
function aggStatus(v, syms) {
  const st = syms.map((s) => cellStatus(wf(s, v)));
  if (syms.length === 1) return st[0];
  const passes = st.filter((x) => x === "pass").length;
  if (passes >= 2) return "pass";
  if (st.some((x) => x !== "fail")) return "maybe";
  return "fail";
}
const badge = (s) => `<span class="badge ${s}">${{ pass: "Edge candidate", maybe: "Weak / unproven", fail: "No edge" }[s]}</span>`;

function agg(v, syms) {
  const R = syms.map((s) => wf(s, v)), M = R.map((r) => r.metrics);
  return {
    net: mean(M.map((m) => m.net_return)),
    bh: mean(syms.map((s) => D.intervals[state.interval][s].buy_hold.walk_forward.net_return)),
    exp: mean(M.map((m) => m.expectancy_per_trade)),
    sharpe: mean(M.map((m) => m.sharpe)),
    dd: Math.min(...M.map((m) => m.max_drawdown)),
    trades: M.reduce((s, m) => s + m.n_trades, 0),
    nlong: M.reduce((s, m) => s + m.n_long, 0), nshort: M.reduce((s, m) => s + m.n_short, 0),
    pct: mean(R.map((r) => r.percentile_vs_random)),
    profitable: M.filter((m) => m.net_return > 0).length,
    win: mean(M.map((m) => m.win_rate)), pf: mean(M.map((m) => m.profit_factor)),
    avgWin: mean(M.map((m) => m.avg_win)), avgLoss: mean(M.map((m) => m.avg_loss)),
    fees: mean(M.map((m) => m.fees_paid)), fin: mean(M.map((m) => m.financing_paid)),
    tim: mean(M.map((m) => m.time_in_market)),
    status: aggStatus(v, syms),
  };
}
function lockbox(v, syms) {
  if (!D.lockbox || state.interval !== D.lockbox.interval || isLS(v)) return null;
  const c = syms.map((s) => D.lockbox.cells[s] && D.lockbox.cells[s][v]).filter(Boolean);
  if (!c.length) return null;
  return { net: mean(c.map((x) => x.metrics.net_return)), bh: mean(c.map((x) => x.buy_hold)),
           exp: mean(c.map((x) => x.metrics.expectancy_per_trade)), pct: mean(c.map((x) => x.percentile_vs_random)),
           trades: c.reduce((s, x) => s + x.metrics.n_trades, 0), cells: c };
}

// ---------- rendering ----------
function init() {
  const ivs = Object.keys(D.intervals);
  $("gen").textContent = "Generated " + D.generated;
  $("f-interval").innerHTML = ivs.map((i) => `<option value="${i}">${i} candles</option>`).join("");
  state.interval = ivs.includes("1h") ? "1h" : ivs[0];
  $("f-interval").value = state.interval;
  fillCoins();
  state.sel = variants()[0];
  $("f-interval").onchange = (e) => { state.interval = e.target.value; fillCoins(); resetSel(); render(); };
  $("f-coin").onchange = (e) => { state.coin = e.target.value; render(); };
  $("f-dir").onchange = (e) => { state.dir = e.target.value; resetSel(); render(); };
  $("imgs").innerHTML = D.images.map((f) => `<a href="img/${f}" target="_blank"><img src="img/${f}" alt="${f}" loading="lazy"></a>`).join("");
  window.addEventListener("resize", () => drawDetailCharts());
  render();
}
function fillCoins() {
  $("f-coin").innerHTML = `<option value="ALL">All coins (average)</option>` +
    coins().map((c) => `<option value="${c}">${c.replace("USDT", "")}</option>`).join("");
  $("f-coin").value = state.coin = "ALL";
}
function resetSel() { if (!variants().includes(state.sel)) state.sel = variants()[0]; }

function render() {
  const m = D.meta[state.interval];
  $("period-hint").textContent = `Unseen test period: ${m.walk_forward[0].slice(0, 10)} to ${m.walk_forward[1].slice(0, 10)} (walk-forward, 6 folds)`;
  renderVerdict(); renderCards(); renderBoard(); renderDetail(); renderNotes();
}

function renderVerdict() {
  const ivs = Object.keys(D.intervals);
  let total = 0, pass = 0, maybe = 0, prof = 0, best = null;
  ivs.forEach((iv) => {
    Object.keys(D.intervals[iv]).forEach((s) => Object.keys(D.intervals[iv][s].variants).forEach((v) => {
      const r = wf(s, v, iv); total++;
      const st = cellStatus(r); if (st === "pass") pass++; if (st === "maybe") maybe++;
      if (r.metrics.net_return > 0) prof++;
      if (!best || r.metrics.net_return > best.net) best = { net: r.metrics.net_return, iv, s, v, exp: r.metrics.expectancy_per_trade, n: r.metrics.n_trades, p: r.percentile_vs_random };
    }));
  });
  const el = $("verdict");
  const falsePos = (total * 0.05).toFixed(0);
  let c = "fail", head = "Verdict so far: no evidence of an edge";
  let body = `Across all <b>${total}</b> strategy/coin/timeframe combinations tested on unseen data, <b>${pass}</b> met the edge test (net profit, positive expectancy per trade <i>and</i> better than 95% of random-entry runs). ` +
    `${prof} of ${total} were merely profitable, and ${maybe} more were weak. With this many tries, roughly ${falsePos} would pass by pure luck, so a handful of winners is not evidence.`;
  if (pass > Number(falsePos) * 2) { c = "maybe"; head = "Verdict so far: some promising candidates, still unproven"; }
  if (best) body += `<br>Best single result: <b>${name(best.v)}</b> on ${best.s.replace("USDT", "")} ${best.iv} at ${pct(best.net)} over ${best.n} trades (beat ${Math.floor(best.p)}% of random runs, short of the 95% bar). Treat it as noise until it holds up on fresh data.`;
  body += `<br><span class="small">Lockbox: ${D.lockbox ? `the 1h long-only strategies were evaluated once on ${D.lockbox.period[0]} to ${D.lockbox.period[1]} (see table). ` : ""}New long/short and 4h variants have <b>no lockbox result yet</b>: that period has already been seen, so they will be tested once on data published after it.</span>`;
  el.className = "verdict " + c;
  el.innerHTML = `<h2>${head}</h2><div>${body}</div>`;
}

function renderCards() {
  const syms = shown(), vs = variants();
  const rows = vs.map((v) => ({ v, a: agg(v, syms) }));
  const pass = rows.filter((r) => r.a.status === "pass").length;
  const prof = rows.filter((r) => r.a.net > 0).length;
  const best = rows.slice().sort((a, b) => b.a.net - a.a.net)[0];
  const bh = mean(syms.map((s) => D.intervals[state.interval][s].buy_hold.walk_forward.net_return));
  const cards = [
    ["Strategies passing the edge test", `${pass} / ${rows.length}`, "net profit + expectancy + beats 95% of random"],
    ["Strategies with positive net return", `${prof} / ${rows.length}`, "after fees, slippage, short costs"],
    ["Buy & hold, same period", span(bh, pct(bh)), "the lazy benchmark"],
    ["Best strategy (avg net return)", best ? span(best.a.net, pct(best.a.net)) : "n/a", best ? name(best.v) : ""],
  ];
  $("cards").innerHTML = cards.map(([k, v, s]) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join("");
}

const COLS = [
  ["name", "Strategy"], ["net", "Net return"], ["bh", "Buy&hold"], ["exp", "Expectancy / trade"], ["sharpe", "Sharpe"],
  ["dd", "Max drawdown"], ["trades", "Trades"], ["pct", "Beats random %"], ["profitable", "Coins profitable"],
  ["lock", "Lockbox"], ["status", "Verdict"],
];
function renderBoard() {
  const syms = shown();
  let rows = variants().map((v) => ({ v, a: agg(v, syms), l: lockbox(v, syms) }));
  const key = state.sortKey;
  const val = (r) => key === "name" ? name(r.v) : key === "lock" ? (r.l ? r.l.net : -9) : key === "status" ? ({ pass: 2, maybe: 1, fail: 0 }[r.a.status]) : r.a[key];
  rows.sort((x, y) => { const a = val(x), b = val(y); return (typeof a === "string" ? a.localeCompare(b) : (a ?? -9) - (b ?? -9)) * state.sortDir; });
  const head = COLS.map(([k, t]) => `<th data-k="${k}">${t}${state.sortKey === k ? (state.sortDir > 0 ? " ▲" : " ▼") : ""}</th>`).join("");
  const body = rows.map((r) => {
    const a = r.a;
    const lock = r.l ? `${span(r.l.net, pct(r.l.net))} <span class="small">vs ${pct(r.l.bh)}</span>` : `<span class="small" title="Not evaluated: new variant, lockbox is held back for fresh data">not run</span>`;
    return `<tr data-v="${r.v}" class="${r.v === state.sel ? "sel" : ""}">
      <td>${LABEL[base(r.v)]}<span class="tag">${isLS(r.v) ? "long/short" : "long-only"}</span></td>
      <td>${span(a.net, pct(a.net))}</td><td>${span(a.bh, pct(a.bh))}</td>
      <td>${span(a.exp, pct(a.exp, 2))}</td><td>${num(a.sharpe)}</td><td>${pct(a.dd, 0)}</td>
      <td>${a.trades}</td><td>${nz(a.pct) ? "n/a" : a.pct.toFixed(0)}</td><td>${a.profitable}/${syms.length}</td>
      <td>${lock}</td><td>${badge(a.status)}</td></tr>`;
  }).join("");
  $("board").innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
  $("board").querySelectorAll("th").forEach((th) => th.onclick = () => {
    const k = th.dataset.k; state.sortDir = state.sortKey === k ? -state.sortDir : -1; state.sortKey = k; renderBoard();
  });
  $("board").querySelectorAll("tbody tr").forEach((tr) => tr.onclick = () => { state.sel = tr.dataset.v; renderBoard(); renderDetail(); });
}

function avgCurve(syms, v) {
  const cs = syms.map((s) => wf(s, v).curve);
  const n = Math.min(...cs.map((c) => c.t.length));
  return { t: cs[0].t.slice(0, n),
           strategy: Array.from({ length: n }, (_, i) => mean(cs.map((c) => c.strategy[i]))),
           buy_hold: Array.from({ length: n }, (_, i) => mean(cs.map((c) => c.buy_hold[i]))) };
}
function renderDetail() {
  const v = state.sel, syms = shown(), a = agg(v, syms), m = D.meta[state.interval];
  const tag = syms.length > 1 ? " (average of coins)" : "";
  const first = wf(syms[0], v);
  const folds = m.folds.slice(0, -1).map((f, i) => f.slice(0, 7));
  const foldRet = folds.map((_, i) => mean(syms.map((s) => wf(s, v).fold_returns[i])));
  state.detail = { curve: avgCurve(syms, v), folds, foldRet };
  const rnd = mean(syms.map((s) => wf(s, v).random.mean_return)), p05 = mean(syms.map((s) => wf(s, v).random.p05)), p95 = mean(syms.map((s) => wf(s, v).random.p95));
  const tr = syms.map((s) => D.intervals[state.interval][s].variants[v].train_in_sample.metrics);
  const trExp = mean(tr.map((x) => x.expectancy_per_trade));
  const L = lockbox(v, syms);
  const sw = ["2023-10..2024-09", "2024-10..2025-09", "2025-10..2026-02"].map((p) => {
    const g = syms.map((s) => cell(s, v).grid_sweep[p]);
    return `<tr><td>${p}</td><td>${span(mean(g.map((x) => x.median)), pct(mean(g.map((x) => x.median))))}</td>
      <td>${(mean(g.map((x) => x.share_positive)) * 100).toFixed(0)}%</td><td>${pct(mean(g.map((x) => x.best)))}</td>
      <td>${pct(mean(g.map((x) => x.worst)))}</td><td>${span(mean(g.map((x) => x.buy_hold)), pct(mean(g.map((x) => x.buy_hold))))}</td></tr>`;
  }).join("");
  const params = syms.map((s) => `<tr><td>${s.replace("USDT", "")}</td>` + wf(s, v).chosen_params.map((c) => `<td class="small">${Object.entries(c.params).map(([k, x]) => k + "=" + x).join(" ")}</td>`).join("") + "</tr>").join("");
  const perCoin = syms.length > 1 ? `<h3>By coin</h3><table><thead><tr><th>Coin</th><th>Net return</th><th>Buy&hold</th><th>Expectancy</th><th>Trades</th><th>Verdict</th></tr></thead><tbody>` +
    syms.map((s) => { const r = wf(s, v), mm = r.metrics; return `<tr><td>${s.replace("USDT", "")}</td><td>${span(mm.net_return, pct(mm.net_return))}</td><td>${pct(D.intervals[state.interval][s].buy_hold.walk_forward.net_return)}</td><td>${span(mm.expectancy_per_trade, pct(mm.expectancy_per_trade, 2))}</td><td>${mm.n_trades}</td><td>${badge(cellStatus(r))}</td></tr>`; }).join("") + "</tbody></table>" : "";
  const lockHtml = L ? `<div class="panel"><h3>Lockbox (final exam, run once)</h3>
      <p class="small">${D.lockbox.period[0]} to ${D.lockbox.period[1]}. Parameters were frozen beforehand.</p>
      <div class="kv"><span>Net return${tag}</span><span>${span(L.net, pct(L.net))}</span><span>Buy &amp; hold</span><span>${pct(L.bh)}</span>
      <span>Expectancy / trade</span><span>${span(L.exp, pct(L.exp, 2))}</span><span>Trades</span><span>${L.trades}</span>
      <span>Beats random runs</span><span>${L.pct.toFixed(0)}%</span></div></div>`
    : `<div class="panel"><h3>Lockbox</h3><p class="small">Not evaluated for this variant. The last-6-months period was already used for the original 1h long-only test, so a clean lockbox for new variants needs fresh data published after ${D.lockbox ? D.lockbox.period[1] : "the data end"}.</p></div>`;

  $("detail").innerHTML = `<h2>2. ${name(v)}: what it does and how it performed</h2>
    <p class="note">${D.descriptions[base(v)]}</p>
    <div class="grid2">
      <div class="panel"><h3>Growth of $1 on unseen data${tag}</h3><canvas id="c-eq"></canvas>
        <div class="legend"><span><i class="sw" style="background:var(--accent)"></i>Strategy (net of costs)</span><span><i class="sw" style="background:var(--accent2)"></i>Buy &amp; hold</span></div></div>
      <div class="panel"><h3>Return in each 3-month fold${tag}</h3><canvas id="c-fold"></canvas>
        <p class="small">Consistency matters more than the total: an edge should win in most folds, not one lucky quarter.</p></div>
      <div class="panel"><h3>Key numbers${tag}</h3><div class="kv">
        <span>Verdict</span><span>${badge(a.status)}</span>
        <span>Net return</span><span>${span(a.net, pct(a.net))}</span><span>Buy &amp; hold</span><span>${pct(a.bh)}</span>
        <span>Expectancy per trade (after costs)</span><span>${span(a.exp, pct(a.exp, 2))}</span>
        <span>Win rate</span><span>${nz(a.win) ? "n/a" : (a.win * 100).toFixed(0) + "%"}</span>
        <span>Average win / average loss</span><span>${pct(a.avgWin, 2)} / ${pct(a.avgLoss, 2)}</span>
        <span>Profit factor</span><span>${num(a.pf)}</span><span>Sharpe</span><span>${num(a.sharpe)}</span>
        <span>Max drawdown (worst coin)</span><span>${pct(a.dd, 0)}</span>
        <span>Trades (long / short)</span><span>${a.trades} (${a.nlong} / ${a.nshort})</span>
        <span>Time in market</span><span>${pct(a.tim, 0).replace("+", "")}</span>
        <span>Fees paid per coin ($10k start)</span><span>$${a.fees.toFixed(0)}</span>
        ${isLS(v) ? `<span>Short holding cost per coin</span><span>$${a.fin.toFixed(0)}</span>` : ""}
      </div>${perCoin}</div>
      <div class="panel"><h3>Is it better than luck?</h3>
        <p class="small">Random entries with the same number of trades and holding time, same costs, 200 runs.</p><div class="kv">
        <span>Strategy net return</span><span>${span(a.net, pct(a.net))}</span>
        <span>Random average</span><span>${pct(rnd)}</span><span>Random 5th to 95th percentile</span><span>${pct(p05)} to ${pct(p95)}</span>
        <span>Strategy beat this share of random runs</span><span><b>${a.pct.toFixed(0)}%</b></span></div>
        <h3>In-sample vs out-of-sample</h3><div class="kv">
        <span>Expectancy on training data (optimised)</span><span>${span(trExp, pct(trExp, 2))}</span>
        <span>Expectancy on unseen data</span><span>${span(a.exp, pct(a.exp, 2))}</span></div>
        <p class="small">A big drop from the first to the second is the signature of overfitting.</p></div>
      ${lockHtml}
      <div class="panel"><h3>Does it work in any setting? (all ${cell(syms[0], v).grid_sweep["2023-10..2024-09"] ? "parameter sets" : ""})</h3>
        <table><thead><tr><th>Period</th><th>Median</th><th>% profitable</th><th>Best</th><th>Worst</th><th>Buy&amp;hold</th></tr></thead><tbody>${sw}</tbody></table>
        <p class="small">If a strategy only works for some parameters or some periods, that is luck or regime, not an edge.</p></div>
      <div class="panel" style="grid-column:1/-1"><h3>Parameters picked at each fold (using only earlier data)</h3>
        <div class="tablewrap"><table><thead><tr><th>Coin</th>${folds.map((f) => `<th>from ${f}</th>`).join("")}</tr></thead><tbody>${params}</tbody></table></div>
        <p class="small">Parameters that jump around every fold suggest the optimiser is chasing noise.</p></div>
    </div>`;
  drawDetailCharts();
}

function setupCanvas(id) {
  const c = $(id); if (!c) return null;
  const r = c.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  c.width = r.width * dpr; c.height = r.height * dpr;
  const g = c.getContext("2d"); g.scale(dpr, dpr);
  return { g, w: r.width, h: r.height };
}
function drawDetailCharts() {
  if (!state.detail) return;
  const { curve, folds, foldRet } = state.detail;
  const ink = colour("--muted"), line = colour("--line");
  let s = setupCanvas("c-eq");
  if (s) {
    const { g, w, h } = s, P = { l: 44, r: 10, t: 8, b: 22 };
    const all = curve.strategy.concat(curve.buy_hold), lo = Math.min(...all, 1) * 0.97, hi = Math.max(...all, 1) * 1.03;
    const X = (i) => P.l + (w - P.l - P.r) * i / (curve.t.length - 1), Y = (y) => P.t + (h - P.t - P.b) * (1 - (y - lo) / (hi - lo));
    g.font = "11px system-ui"; g.fillStyle = ink; g.strokeStyle = line; g.lineWidth = 1;
    for (let k = 0; k <= 4; k++) { const y = lo + (hi - lo) * k / 4; g.beginPath(); g.moveTo(P.l, Y(y)); g.lineTo(w - P.r, Y(y)); g.stroke(); g.fillText(y.toFixed(2), 4, Y(y) + 4); }
    [0, Math.floor(curve.t.length / 2), curve.t.length - 1].forEach((i) => { g.fillText(curve.t[i], Math.min(X(i) - 20, w - 70), h - 6); });
    g.setLineDash([4, 4]); g.strokeStyle = ink; g.beginPath(); g.moveTo(P.l, Y(1)); g.lineTo(w - P.r, Y(1)); g.stroke(); g.setLineDash([]);
    [[curve.buy_hold, colour("--accent2")], [curve.strategy, colour("--accent")]].forEach(([vals, col]) => {
      g.strokeStyle = col; g.lineWidth = 2; g.beginPath(); vals.forEach((y, i) => (i ? g.lineTo(X(i), Y(y)) : g.moveTo(X(i), Y(y)))); g.stroke();
    });
  }
  s = setupCanvas("c-fold");
  if (s) {
    const { g, w, h } = s, P = { l: 44, r: 10, t: 12, b: 24 };
    const mx = Math.max(0.05, ...foldRet.map(Math.abs)) * 1.15, zero = P.t + (h - P.t - P.b) / 2, half = (h - P.t - P.b) / 2;
    g.font = "11px system-ui"; g.fillStyle = ink; g.strokeStyle = line;
    g.beginPath(); g.moveTo(P.l, zero); g.lineTo(w - P.r, zero); g.stroke();
    g.fillText(pct(mx, 0), 4, P.t + 8); g.fillText(pct(-mx, 0), 4, h - P.b);
    const bw = (w - P.l - P.r) / foldRet.length;
    foldRet.forEach((x, i) => {
      const bh = half * Math.abs(x) / mx; g.fillStyle = x >= 0 ? colour("--good") : colour("--bad");
      g.fillRect(P.l + i * bw + bw * 0.2, x >= 0 ? zero - bh : zero, bw * 0.6, bh);
      g.fillStyle = ink; g.fillText(folds[i], P.l + i * bw + bw * 0.12, h - 8);
      g.fillText(pct(x, 0), P.l + i * bw + bw * 0.2, x >= 0 ? zero - bh - 3 : zero + bh + 11);
    });
  }
}

function renderNotes() {
  const m = D.meta[state.interval];
  const notes = [
    `<b>Costs are always included:</b> fee ${(m.fee * 100).toFixed(2)}% and slippage ${(m.slippage * 100).toFixed(2)}% per side, so a round trip costs ${((m.fee + m.slippage) * 200).toFixed(2)}%. Signals trade at the <i>next</i> candle's open (no peeking).`,
    `<b>Verdict rule:</b> "Edge candidate" needs a profit, a positive expectancy per trade, and a result better than 95% of random-entry runs (for all coins: at least 2 of 3 coins). "Weak" means profitable and above 80% but not 95%. Everything else is "No edge".`,
    `<b>Short selling is a modelling assumption.</b> Binance spot cannot short. Shorts are simulated like a perpetual future on the same price: same fees and slippage plus a holding cost of ${(m.short_cost_per_8h * 100).toFixed(3)}% per 8 hours. Real funding rates swing both ways, and real shorts carry liquidation and margin risk that is not modelled.`,
    `<b>Walk-forward:</b> train on the first 12 months, then repeatedly pick the best parameters on all earlier data and trade the next 3 months. ${m.combinations_per_coin} parameter combinations are tried per coin across ${m.variants} strategy variants, so some good-looking results are expected by chance.`,
    `<b>Lockbox:</b> the final 6 months (Mar-Aug 2026) were evaluated once, for the 1h long-only strategies, and cannot be re-used. New variants will be judged on data published after Aug 2026.`,
    `<b>Limits:</b> about 3 years (one market cycle), 5 simple strategies, 3 coins, long trades with no leverage, no taxes, flat slippage assumption. 5-minute data is downloaded and explored but not backtested.`,
    `<b>Phase 1 is research only.</b> No keys, no orders, no testnet. Nothing here is investment advice.`,
  ];
  $("notes").innerHTML = notes.map((n) => `<li>${n}</li>`).join("");
}

init();
