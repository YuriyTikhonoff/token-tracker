#!/usr/bin/env python3
"""Minimal local web dashboard for token-tracker.

Serves a single self-contained HTML page (no external requests, no
dependencies) that fetches /api/data and renders totals + breakdowns.

    python3 dashboard.py            # http://127.0.0.1:8765
    python3 dashboard.py --port 9000
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import ingest
import queries
import usage_snapshot

DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH
DEFAULT_PRICING_PATH = queries.DEFAULT_PRICING_PATH
DEFAULT_PROJECTS_DIR = ingest.DEFAULT_PROJECTS_DIR
TOP_LIMIT = 25
PROMPT_LOG_LIMIT = 200

PAGE_TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Token Tracker</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; background: #0b0e14; color: #e6e6e6; }
  h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
  .subtitle { color: #8a8f98; margin-bottom: 1.5rem; font-size: 0.85rem; }
  .widget { background: #161a23; border: 1px solid #262b36; border-radius: 8px; padding: 1.25rem 1.5rem; margin-bottom: 2rem; }
  .widget-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .widget-cost { color: #8a8f98; font-size: 0.85rem; }
  .widget-cost .value { color: #e6e6e6; font-weight: 600; }
  .tabs { display: flex; gap: 0.5rem; }
  .tab { background: transparent; border: 1px solid #262b36; color: #8a8f98; border-radius: 6px; padding: 0.3rem 0.8rem; font-size: 0.8rem; cursor: pointer; }
  .tab.active { background: #5b8def; border-color: #5b8def; color: #fff; }
  .breakdown-row { display: grid; grid-template-columns: 120px 1fr 90px 50px; align-items: center; gap: 0.75rem; padding: 0.4rem 0; font-size: 0.85rem; }
  .breakdown-row .label { color: #c7cbd4; }
  .breakdown-row .value { text-align: right; font-variant-numeric: tabular-nums; }
  .breakdown-row .pct { text-align: right; color: #8a8f98; font-variant-numeric: tabular-nums; }
  .limit-row { display: grid; grid-template-columns: 340px 1fr 70px; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid #1d2129; }
  .limit-row:last-child { border-bottom: none; }
  .limit-row .scope { color: #c7cbd4; font-size: 0.85rem; }
  .limit-row .meta { color: #8a8f98; font-size: 0.75rem; margin-top: 2px; }
  .limit-row .meta-reset { color: #e6e6e6; font-size: 0.75rem; margin-top: 2px; }
  .limit-timing { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
  .limit-timing-lines { flex: 1; min-width: 0; }
  .limit-margin { font-size: 1.1rem; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .limit-row .pct-value { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
  .limit-bar-track { background: #1d2129; border-radius: 3px; height: 8px; overflow: hidden; }
  .limit-bar-fill { height: 100%; }
  .limit-bar-fill.ok { background: #5b8def; }
  .limit-bar-fill.warn { background: #e0a94e; }
  .limit-bar-fill.danger { background: #e05a5a; }
  .session-stats { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #262b36; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
  .session-stats .stat .label { color: #8a8f98; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; }
  .session-stats .stat .value { font-size: 0.95rem; margin-top: 2px; }
  .text-ok { color: #3ecf8e; }
  .text-warn { color: #e0a94e; }
  .text-danger { color: #e05a5a; }
  section { margin-bottom: 2rem; }
  h2 { font-size: 1rem; color: #c7cbd4; border-bottom: 1px solid #262b36; padding-bottom: 0.4rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #1d2129; }
  th { color: #8a8f98; font-weight: 500; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .bar-track { background: #1d2129; border-radius: 3px; height: 6px; margin-top: 4px; overflow: hidden; }
  .bar-fill { background: #5b8def; height: 100%; }
  .preview { color: #c7cbd4; max-width: 480px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .empty { color: #8a8f98; font-style: italic; padding: 0.5rem; }
</style>
</head>
<body>
  <h1>Token Tracker <button id="refresh-btn" class="tab" style="margin-left: 0.75rem; vertical-align: middle;">Refresh</button></h1>
  <div class="subtitle" id="refresh-status">Claude Code token usage, parsed from local session transcripts.</div>
  <div class="widget" id="limits-widget" style="display:none;">
    <div class="widget-header">
      <div class="widget-cost">Subscription limits</div>
      <div class="widget-cost" id="limits-caveat">Approximate — from local <code>claude -p "/usage"</code> snapshots</div>
    </div>
    <div id="limits"></div>
    <div id="session-stats"></div>
  </div>
  <div class="widget">
    <div class="widget-header">
      <div class="widget-cost">Estimated cost (<span id="breakdown-period-label">today</span>): <span class="value" id="breakdown-cost"></span></div>
      <div class="tabs" id="period-tabs">
        <button class="tab active" data-period="today">Today</button>
        <button class="tab" data-period="month">This month</button>
        <button class="tab" data-period="all">All time</button>
      </div>
    </div>
    <div id="breakdown"></div>
  </div>
  <section>
    <h2>Prompt log <span id="prompt-log-subtitle" class="subtitle" style="margin:0;"></span></h2>
    <table id="prompt-log-table"><thead><tr><th>Time</th><th>Session</th><th>Prompt</th><th class="num">Tokens</th><th class="num">Est. cost</th></tr></thead><tbody></tbody></table>
  </section>
  <section>
    <h2>By project</h2>
    <table id="project-table"><thead><tr><th>Project</th><th class="num">Tokens</th><th class="num">Est. cost</th></tr></thead><tbody></tbody></table>
  </section>
  <section>
    <h2>Top sessions by cost</h2>
    <table id="session-table"><thead><tr><th>Session</th><th>Project</th><th>Last activity</th><th class="num">Tokens</th><th class="num">Est. cost</th></tr></thead><tbody></tbody></table>
  </section>
  <section>
    <h2>Top prompts by cost</h2>
    <table id="prompt-table"><thead><tr><th>Prompt</th><th>Timestamp</th><th class="num">Tokens</th><th class="num">Est. cost</th></tr></thead><tbody></tbody></table>
  </section>

<script>
function fmtTokens(n) {
  if (n > 1000000) {
    const millions = n / 1000000;
    const decimals = millions < 10 ? 2 : 1;
    return millions.toLocaleString(undefined, {minimumFractionDigits: decimals, maximumFractionDigits: decimals}) + ' mln';
  }
  if (n >= 1000) {
    return (n / 1000).toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1}) + 'k';
  }
  return n.toLocaleString();
}
function fmtCost(n) { return '$' + n.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
function bar(value, max) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return `<div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>`;
}
function emptyRow(colspan, label) {
  return `<tr><td colspan="${colspan}" class="empty">${label}</td></tr>`;
}
function stackedTime(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (isNaN(date.getTime())) return iso;
  const timeStr = date.toLocaleTimeString('en-GB', { timeZone: 'Europe/Kyiv', hour: '2-digit', minute: '2-digit' });
  const dateStr = date.toLocaleDateString('en-CA', { timeZone: 'Europe/Kyiv' });
  return `<div>${timeStr}</div><div style="color:#8a8f98;font-size:0.75rem;">${dateStr}</div>`;
}

const PERIOD_LABELS = { today: 'today', month: 'this month', all: 'all time' };

function pct(part, whole) {
  return whole > 0 ? ((part / whole) * 100).toFixed(1) : '0.0';
}

function renderBreakdown(totals) {
  const breakdown = document.getElementById('breakdown');
  const rows = [
    ['Total tokens', totals.total_tokens, totals.total_tokens],
    ['Input', totals.input_tokens, totals.total_tokens],
    ['Output', totals.output_tokens, totals.total_tokens],
    ['Cache write', totals.cache_creation_tokens, totals.total_tokens],
    ['Cache read', totals.cache_read_tokens, totals.total_tokens],
  ];
  breakdown.innerHTML = rows.map(([label, value, whole]) => `
    <div class="breakdown-row">
      <div class="label">${label}</div>
      ${bar(value, rows[0][1])}
      <div class="value">${fmtTokens(value)}</div>
      <div class="pct">${pct(value, whole)}%</div>
    </div>
  `).join('');
  document.getElementById('breakdown-cost').textContent = fmtCost(totals.cost);
}

function fmtResetsAt(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (isNaN(date.getTime())) return '';
  const dateStr = date.toLocaleDateString('en-GB', { timeZone: 'Europe/Kyiv', day: 'numeric', month: 'short' });
  const timeStr = date.toLocaleTimeString('en-GB', { timeZone: 'Europe/Kyiv', hour: '2-digit', minute: '2-digit' });
  return `${dateStr} ${timeStr}`;
}

function kyivDayLabel(date) {
  const dateStr = date.toLocaleDateString('en-CA', { timeZone: 'Europe/Kyiv' });
  const todayStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/Kyiv' });
  const yesterdayStr = new Date(Date.now() - 86400000).toLocaleDateString('en-CA', { timeZone: 'Europe/Kyiv' });
  if (dateStr === todayStr) return 'Today';
  if (dateStr === yesterdayStr) return 'Yesterday';
  return date.toLocaleDateString('en-GB', { timeZone: 'Europe/Kyiv', day: 'numeric', month: 'short' });
}

function kyivTime(date) {
  return date.toLocaleTimeString('en-GB', { timeZone: 'Europe/Kyiv', hour: '2-digit', minute: '2-digit' });
}

function fmtDuration(minutesTotal) {
  const sign = minutesTotal < 0 ? '-' : '';
  const abs = Math.round(Math.abs(minutesTotal));
  const hours = Math.floor(abs / 60);
  const minutes = abs % 60;
  return `${sign}${hours} h ${String(minutes).padStart(2, '0')} min`;
}

function limitSeverity(pctUsed) {
  if (pctUsed >= 90) return 'danger';
  if (pctUsed >= 70) return 'warn';
  return 'ok';
}

const SEVERITY_COLORS = { ok: '#3ecf8e', warn: '#e0a94e', danger: '#e05a5a' };

function projectionSeverity(hoursToLimit) {
  if (hoursToLimit < 24) return 'danger';
  if (hoursToLimit < 72) return 'warn';
  return 'ok';
}

function formatDurationLabel(hoursToLimit) {
  if (hoursToLimit < 1) return `${Math.round(hoursToLimit * 60)}m`;
  if (hoursToLimit < 24) return `${hoursToLimit.toFixed(1)}h`;
  const days = Math.floor(hoursToLimit / 24);
  const remainingHours = hoursToLimit - days * 24;
  return `${days} day${days !== 1 ? 's' : ''} ${remainingHours.toFixed(1)}h`;
}

function formatSignedDuration(hours) {
  const sign = hours < 0 ? '-' : '+';
  return sign + formatDurationLabel(Math.abs(hours));
}

function projectionLines(snapshot) {
  const resetsAt = snapshot.resets_at ? new Date(snapshot.resets_at) : null;
  const hoursToReset = resetsAt ? (resetsAt.getTime() - Date.now()) / 3600000 : null;
  const resetLine = resetsAt
    ? (hoursToReset <= 0
        ? `reset overdue (${fmtResetsAt(snapshot.resets_at)})`
        : `reset    in ~${formatDurationLabel(hoursToReset)} (${fmtResetsAt(snapshot.resets_at)})`)
    : null;
  if (snapshot.hours_to_limit == null) {
    return { resetLine, exhaustionLine: resetLine ? null : 'not enough data yet for a projection', severity: null, marginHours: null };
  }
  const hoursToLimit = snapshot.hours_to_limit;
  const limitEta = new Date(Date.now() + hoursToLimit * 3600 * 1000);
  const label = formatDurationLabel(hoursToLimit);
  const willResetFirst = resetsAt && limitEta > resetsAt;
  const exhaustionLine = `exhaust in ~${label} (${fmtResetsAt(limitEta)})`;
  const severity = willResetFirst ? 'ok' : projectionSeverity(hoursToLimit);
  const marginHours = resetsAt ? (limitEta.getTime() - resetsAt.getTime()) / 3600000 : null;
  return { resetLine, exhaustionLine, severity, marginHours };
}

function renderLimits(snapshots) {
  const widget = document.getElementById('limits-widget');
  if (!snapshots.length) {
    widget.style.display = 'none';
    return;
  }
  widget.style.display = '';
  const limits = document.getElementById('limits');
  limits.innerHTML = snapshots.map(snapshot => {
    const severity = limitSeverity(snapshot.pct_used);
    const projection = projectionLines(snapshot);
    const exhaustionStyle = projection.severity ? ` style="color:${SEVERITY_COLORS[projection.severity]}"` : '';
    const resetLineHtml = projection.resetLine ? `<div class="meta-reset">${projection.resetLine}</div>` : '';
    const exhaustionLineHtml = projection.exhaustionLine ? `<div class="meta"${exhaustionStyle}>${projection.exhaustionLine}</div>` : '';
    const marginHtml = projection.marginHours != null
      ? `<div class="limit-margin" style="color:${SEVERITY_COLORS[projection.marginHours < 0 ? 'danger' : 'ok']}">${formatSignedDuration(projection.marginHours)}</div>`
      : '';
    return `
      <div class="limit-row">
        <div>
          <div class="scope">${snapshot.scope}</div>
          <div class="limit-timing">
            <div class="limit-timing-lines">
              ${resetLineHtml}
              ${exhaustionLineHtml}
            </div>
            ${marginHtml}
          </div>
        </div>
        <div class="limit-bar-track"><div class="limit-bar-fill ${severity}" style="width:${Math.min(100, snapshot.pct_used)}%"></div></div>
        <div class="pct-value">${snapshot.pct_used.toFixed(0)}%</div>
      </div>
    `;
  }).join('');
}

function renderSessionStats(stats) {
  const container = document.getElementById('session-stats');
  if (!stats) {
    container.innerHTML = '';
    return;
  }

  const startDate = new Date(stats.session_started_at);
  const resetsDate = new Date(stats.resets_at);
  const remainingMinutes = (resetsDate.getTime() - Date.now()) / 60000;
  const windowLabel = `${kyivDayLabel(startDate)} ${kyivTime(startDate)} → ${kyivTime(resetsDate)}`
    + ` (${remainingMinutes >= 0 ? fmtDuration(remainingMinutes) + ' left' : 'reset overdue'})`;

  let exhaustionText = 'not enough data';
  let exhaustionClass = '';
  if (stats.projected_exhaustion_at) {
    const exhaustionDate = new Date(stats.projected_exhaustion_at);
    const marginMinutes = (exhaustionDate.getTime() - resetsDate.getTime()) / 60000;
    const clockLabel = `${kyivDayLabel(exhaustionDate)} ${kyivTime(exhaustionDate)}`;
    if (marginMinutes < 0) {
      exhaustionClass = 'text-danger';
      exhaustionText = `~${clockLabel} (before reset)`;
    } else if (marginMinutes < 30) {
      exhaustionClass = 'text-warn';
      exhaustionText = `~${clockLabel} (${fmtDuration(marginMinutes)} after reset)`;
    } else {
      exhaustionClass = 'text-ok';
      exhaustionText = `~${clockLabel} (${fmtDuration(marginMinutes)} after reset)`;
    }
  }

  const statDefs = [
    ['Session window', windowLabel, ''],
    ['Tokens used', `${fmtTokens(stats.session_tokens)} (${fmtCost(stats.session_cost)})`, ''],
    ['Burn rate', `${fmtTokens(stats.tokens_per_hour)} tokens/hr`, ''],
    ['Projected exhaustion', exhaustionText, exhaustionClass],
  ];
  container.innerHTML = `<div class="session-stats">${statDefs.map(([label, value, valueClass]) => `
    <div class="stat">
      <div class="label">${label}</div>
      <div class="value ${valueClass}">${value}</div>
    </div>
  `).join('')}</div>`;
}

let activePeriod = 'today';
let latestData = null;

function selectPeriod(period) {
  activePeriod = period;
  document.querySelectorAll('#period-tabs .tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.period === period);
  });
  document.getElementById('breakdown-period-label').textContent = PERIOD_LABELS[period];
  if (latestData) renderBreakdown(latestData.totals_by_period[period]);
}

document.querySelectorAll('#period-tabs .tab').forEach(tab => {
  tab.addEventListener('click', () => selectPeriod(tab.dataset.period));
});

function renderAll(data) {
  latestData = data;
  renderLimits(data.usage_snapshots);
  renderSessionStats(data.current_session_stats);
  document.getElementById('breakdown-period-label').textContent = PERIOD_LABELS[activePeriod];
  renderBreakdown(data.totals_by_period[activePeriod]);

  const projectBody = document.querySelector('#project-table tbody');
  const maxProjectCost = Math.max(0, ...data.by_project.map(p => p.cost));
  projectBody.innerHTML = data.by_project.length
    ? data.by_project.map(p => `<tr>
        <td>${p.project}${bar(p.cost, maxProjectCost)}</td>
        <td class="num">${fmtTokens(p.tokens)}</td>
        <td class="num">${fmtCost(p.cost)}</td>
      </tr>`).join('')
    : emptyRow(3, 'No data yet — run ingest.py first.');

  const sessionBody = document.querySelector('#session-table tbody');
  sessionBody.innerHTML = data.by_session.length
    ? data.by_session.map(s => `<tr>
        <td title="${s.session_id}">${s.session_id.slice(0, 8)}…</td>
        <td>${s.project}</td>
        <td>${stackedTime(s.last_seen)}</td>
        <td class="num">${fmtTokens(s.tokens)}</td>
        <td class="num">${fmtCost(s.cost)}</td>
      </tr>`).join('')
    : emptyRow(5, 'No data yet.');

  const promptBody = document.querySelector('#prompt-table tbody');
  promptBody.innerHTML = data.by_prompt.length
    ? data.by_prompt.map(p => `<tr>
        <td class="preview" title="${(p.preview || '').replace(/"/g, '&quot;')}">${p.preview || '(no preview)'}</td>
        <td>${stackedTime(p.timestamp)}</td>
        <td class="num">${fmtTokens(p.tokens)}</td>
        <td class="num">${fmtCost(p.cost)}</td>
      </tr>`).join('')
    : emptyRow(4, 'No data yet.');

  const promptLogBody = document.querySelector('#prompt-log-table tbody');
  promptLogBody.innerHTML = data.prompt_log.length
    ? data.prompt_log.map(p => `<tr>
        <td>${stackedTime(p.timestamp)}</td>
        <td title="${p.session_id}">${p.session_id.slice(0, 8)}…</td>
        <td class="preview" title="${(p.preview || '').replace(/"/g, '&quot;')}">${p.preview || '(no preview)'}</td>
        <td class="num">${fmtTokens(p.tokens)}</td>
        <td class="num">${fmtCost(p.cost)}</td>
      </tr>`).join('')
    : emptyRow(5, 'No data yet.');
  document.getElementById('prompt-log-subtitle').textContent =
    data.prompt_log_total > data.prompt_log.length
      ? `(most recent ${data.prompt_log.length} of ${data.prompt_log_total})`
      : `(${data.prompt_log_total} total, most recent first)`;
}

function loadData() {
  fetch('/api/data').then(r => r.json()).then(renderAll);
}

const refreshBtn = document.getElementById('refresh-btn');
const refreshStatus = document.getElementById('refresh-status');

function refresh() {
  refreshBtn.disabled = true;
  refreshBtn.textContent = 'Refreshing…';
  fetch('/api/refresh', { method: 'POST' })
    .then(r => r.json())
    .then(result => {
      loadData();
      if (result.errors && result.errors.length) {
        refreshStatus.textContent = `Refresh completed with errors: ${result.errors.join('; ')}`;
      } else {
        refreshStatus.textContent = `Refreshed: ${result.new_prompt_count} new prompt(s) ingested` +
          (result.usage_snapshot_count != null ? `, usage snapshot updated.` : '.');
      }
    })
    .catch(error => {
      refreshStatus.textContent = `Refresh failed: ${error}`;
    })
    .finally(() => {
      refreshBtn.disabled = false;
      refreshBtn.textContent = 'Refresh';
    });
}

refreshBtn.addEventListener('click', refresh);

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>
"""


def build_handler(db_path, pricing):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format_string, *args):
            pass

        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self._send(200, "text/html; charset=utf-8", PAGE_TEMPLATE.encode("utf-8"))
                return
            if self.path.startswith("/api/data"):
                self._send_json()
                return
            self._send(404, "text/plain", b"not found")

        def do_POST(self):
            if self.path.startswith("/api/refresh"):
                self._send_refresh()
                return
            self._send(404, "text/plain", b"not found")

        def _send_refresh(self):
            errors = []
            new_prompt_count = 0
            usage_snapshot_count = None
            try:
                ingest_result = ingest.run(DEFAULT_PROJECTS_DIR, db_path)
                new_prompt_count = ingest_result["new_prompt_count"]
            except Exception as error:
                errors.append(f"ingest: {error}")
            try:
                usage_snapshot_count = len(usage_snapshot.run(db_path))
            except Exception as error:
                errors.append(f"usage_snapshot: {error}")
            payload = {
                "new_prompt_count": new_prompt_count,
                "usage_snapshot_count": usage_snapshot_count,
                "errors": errors,
            }
            self._send(200, "application/json", json.dumps(payload).encode("utf-8"))

        def _send_json(self):
            if not db_path.exists():
                empty_totals = {"input_tokens": 0, "output_tokens": 0, "cache_creation_tokens": 0,
                                 "cache_read_tokens": 0, "total_tokens": 0, "cost": 0.0}
                self._send(200, "application/json", json.dumps({
                    "totals": empty_totals,
                    "totals_by_period": {"today": empty_totals, "month": empty_totals, "all": empty_totals},
                    "daily_usage": [], "weekly_usage": [], "monthly_usage": [],
                    "usage_snapshots": [],
                    "current_session_stats": None,
                    "by_project": [], "by_session": [], "by_prompt": [],
                    "prompt_log": [], "prompt_log_total": 0,
                }).encode("utf-8"))
                return
            connection = queries.connect(db_path)
            full_prompt_log = queries.get_prompt_log(connection, pricing)
            payload = {
                "totals": queries.get_totals(connection, pricing),
                "totals_by_period": queries.get_totals_by_period(connection, pricing),
                "daily_usage": queries.get_daily_usage(connection, pricing),
                "weekly_usage": queries.get_weekly_usage(connection, pricing),
                "monthly_usage": queries.get_monthly_usage(connection, pricing),
                "usage_snapshots": queries.get_usage_snapshots_trend(connection),
                "current_session_stats": queries.get_current_session_stats(connection, pricing),
                "by_project": queries.get_by_project(connection, pricing),
                "by_session": queries.get_by_session(connection, pricing, TOP_LIMIT),
                "by_prompt": queries.get_by_prompt(connection, pricing, TOP_LIMIT),
                "prompt_log": full_prompt_log[:PROMPT_LOG_LIMIT],
                "prompt_log_total": len(full_prompt_log),
            }
            connection.close()
            self._send(200, "application/json", json.dumps(payload).encode("utf-8"))

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors_headers()
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _send_cors_headers(self):
            origin = self.headers.get("Origin")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)

        def _send(self, status, content_type, body):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING_PATH)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    pricing = queries.load_pricing(args.pricing)
    handler = build_handler(args.db, pricing)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Token Tracker dashboard: http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
