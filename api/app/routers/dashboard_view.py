"""Server-rendered enterprise ops dashboard at /dashboard.

Public (no auth) — exposes aggregated metrics + recent-call audit rows. Reads internal
aggregation functions directly (no HTTP round-trip; no token in browser).

Single page, no build step. Tailwind + Chart.js from CDN. Vanilla JS only.

Audience: enterprise ops manager at Acme Logistics — command center to MANAGE +
REVIEW the AI voice agents. Filter bar drives all aggregations server-side; recent
calls table + drilldown panel for per-call human audit.
"""

import json
from datetime import datetime, timezone
from string import Template
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.routers.dashboard import economics, funnel, operational, quality
from app.services.calls_store import list_calls
from app.services.dashboard_aggregations import (
    agent_version_metrics,
    apply_filters,
    apply_rate_histogram,
    audit_remarks_clusters,
    call_volume_heatmap,
    carrier_rollup,
    chs_distribution,
    fmcsa_decline_breakdown,
    outcome_trend,
    system_alerts,
)

router = APIRouter()


_HTML = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Inbound Carrier Sales — Agent Operations · Acme Logistics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .metric { transition: transform 0.15s; }
    .metric:hover { transform: translateY(-2px); }
    .heatmap-cell { width: 22px; height: 22px; display: inline-block; border-radius: 3px; }
    .sortable { cursor: pointer; user-select: none; }
    .sortable:hover { background-color: #f1f5f9; }
    .chip { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: 600; }
    .row-clickable { cursor: pointer; }
    .row-clickable:hover { background-color: #f8fafc; }
    .stoplight { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: 600; }
    details.transcript summary { cursor: pointer; color: #2563eb; font-size: 0.8rem; }
  </style>
</head>
<body class="bg-slate-50 min-h-screen">
  <div class="container mx-auto p-4 md:p-6 max-w-7xl">

    <!-- ===== HEADER ===== -->
    <header class="mb-6 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
      <div>
        <h1 class="text-2xl md:text-3xl font-bold text-slate-900">Inbound Carrier Sales — Agent Operations</h1>
        <p class="text-sm text-slate-500 mt-1">
          ${TOTAL_CALLS} calls processed · last ${WINDOW_DAYS} days · updated ${NOW}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span class="inline-block px-3 py-1 rounded-full text-xs font-semibold ${API_STATUS_CLASS}">
          ${API_STATUS}
        </span>
        <label class="inline-flex items-center gap-2 text-xs text-slate-600">
          <input id="liveToggle" type="checkbox" class="rounded">
          Live (30s refresh)
        </label>
      </div>
    </header>

    <!-- ===== FILTER BAR ===== -->
    <form method="GET" action="/dashboard" class="sticky top-0 z-10 bg-white border border-slate-200 rounded-xl shadow-sm p-3 mb-6">
      <div class="grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
        <div>
          <label class="block text-[10px] uppercase tracking-wider text-slate-500 mb-1">From</label>
          <input type="date" name="from" value="${F_FROM}" class="w-full text-sm border border-slate-300 rounded px-2 py-1">
        </div>
        <div>
          <label class="block text-[10px] uppercase tracking-wider text-slate-500 mb-1">To</label>
          <input type="date" name="to" value="${F_TO}" class="w-full text-sm border border-slate-300 rounded px-2 py-1">
        </div>
        <div>
          <label class="block text-[10px] uppercase tracking-wider text-slate-500 mb-1">Outcome</label>
          <select name="outcome" class="w-full text-sm border border-slate-300 rounded px-2 py-1">
            <option value="" ${F_OUT_ALL}>All</option>
            <option value="load_booked" ${F_OUT_LB}>Load booked</option>
            <option value="no_match" ${F_OUT_NM}>No match</option>
            <option value="carrier_not_qualified" ${F_OUT_CNQ}>Carrier not qualified</option>
            <option value="call_abandoned" ${F_OUT_CA}>Call abandoned</option>
          </select>
        </div>
        <div>
          <label class="block text-[10px] uppercase tracking-wider text-slate-500 mb-1">Sentiment</label>
          <select name="sentiment" class="w-full text-sm border border-slate-300 rounded px-2 py-1">
            <option value="" ${F_SEN_ALL}>All</option>
            <option value="positive" ${F_SEN_POS}>Positive</option>
            <option value="neutral" ${F_SEN_NEU}>Neutral</option>
            <option value="negative" ${F_SEN_NEG}>Negative</option>
          </select>
        </div>
        <div>
          <label class="block text-[10px] uppercase tracking-wider text-slate-500 mb-1">Search MC / carrier</label>
          <input type="text" name="q" value="${F_Q}" placeholder="MC# or name" class="w-full text-sm border border-slate-300 rounded px-2 py-1">
        </div>
        <div class="flex gap-2">
          <button type="submit" class="flex-1 text-sm bg-slate-900 text-white rounded px-3 py-1.5 hover:bg-slate-800">Apply</button>
          <button type="button" id="resetBtn" class="flex-1 text-sm bg-slate-100 text-slate-700 rounded px-3 py-1.5 hover:bg-slate-200">Reset</button>
        </div>
      </div>
    </form>

    ${EMPTY_BANNER}

    <!-- ===== KPI STRIP ===== -->
    <section class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <div class="metric bg-white rounded-xl border border-slate-200 p-4">
        <p class="text-[10px] uppercase tracking-wider text-slate-500">Total calls</p>
        <p class="text-3xl font-bold text-slate-900 mt-1">${KPI_TOTAL}</p>
      </div>
      <div class="metric bg-white rounded-xl border border-slate-200 p-4">
        <p class="text-[10px] uppercase tracking-wider text-slate-500">Booked</p>
        <p class="text-3xl font-bold text-emerald-600 mt-1">${KPI_BOOKED}</p>
      </div>
      <div class="metric bg-white rounded-xl border border-slate-200 p-4">
        <p class="text-[10px] uppercase tracking-wider text-slate-500">Booking rate</p>
        <p class="text-3xl font-bold text-emerald-600 mt-1">${KPI_RATE}%</p>
      </div>
      <div class="metric bg-white rounded-xl border border-slate-200 p-4">
        <p class="text-[10px] uppercase tracking-wider text-slate-500">Avg CHS</p>
        <p class="text-3xl font-bold text-slate-900 mt-1">${KPI_CHS}<span class="text-base text-slate-400">/100</span></p>
      </div>
    </section>

    <!-- ===== SECTION 1: System Health ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">System Health</h2>
        <p class="text-xs text-slate-500">Why this matters: catch agent issues fast, before booking rate craters.</p>
      </div>
      <div id="alertChips" class="flex flex-wrap gap-2 mb-4"></div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">CHS rolling (last 50)</p>
          <div class="h-24"><canvas id="sparkChs"></canvas></div>
        </div>
        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Booking rate rolling (last 50)</p>
          <div class="h-24"><canvas id="sparkBookRate"></canvas></div>
        </div>
      </div>
      <div>
        <p class="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Top auditor remarks</p>
        <div id="tagCloud" class="flex flex-wrap gap-2"></div>
      </div>
    </section>

    <!-- ===== SECTION 2: Funnel + Trend ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">Funnel &amp; Outcome Trend</h2>
        <p class="text-xs text-slate-500">Why this matters: business impact at a glance.</p>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
        <div class="metric">
          <p class="text-[10px] uppercase tracking-wider text-slate-500">Booking rate</p>
          <p class="text-5xl font-bold text-emerald-600 mt-2">${BOOKING_RATE}%</p>
          <p class="text-sm text-slate-500 mt-1">${BOOKED_COUNT} booked / ${TOTAL_CALLS} calls</p>
        </div>
        <div class="h-56"><canvas id="funnelChart"></canvas></div>
        <div class="h-56"><canvas id="trendChart"></canvas></div>
      </div>
    </section>

    <!-- ===== SECTION 3: Economics ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">Economics</h2>
        <p class="text-xs text-slate-500">Why this matters: margin discipline. Track discount drift.</p>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div class="metric bg-slate-50 rounded-lg p-4">
          <p class="text-[10px] uppercase tracking-wider text-slate-500">Avg loadboard rate</p>
          <p class="text-2xl font-bold text-slate-900 mt-2">${AVG_LOADBOARD}</p>
        </div>
        <div class="metric bg-slate-50 rounded-lg p-4">
          <p class="text-[10px] uppercase tracking-wider text-slate-500">Avg agreed rate</p>
          <p class="text-2xl font-bold text-slate-900 mt-2">${AVG_AGREED}</p>
        </div>
        <div class="metric bg-slate-50 rounded-lg p-4">
          <p class="text-[10px] uppercase tracking-wider text-slate-500">Avg discount</p>
          <p class="text-2xl font-bold text-slate-900 mt-2">${AVG_DISCOUNT}%</p>
        </div>
        <div class="metric bg-emerald-50 rounded-lg p-4">
          <p class="text-[10px] uppercase tracking-wider text-emerald-600">Booked revenue</p>
          <p class="text-2xl font-bold text-emerald-700 mt-2">${TOTAL_REVENUE}</p>
        </div>
      </div>
      <div>
        <p class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Agreed rate distribution</p>
        <div class="h-48"><canvas id="agreedHistogram"></canvas></div>
      </div>
    </section>

    <!-- ===== SECTION 4: Operational + Quality grid ===== -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

      <section class="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
        <div class="mb-3">
          <h2 class="text-lg font-semibold text-slate-800">Operational</h2>
          <p class="text-xs text-slate-500">Why this matters: negotiation discipline and call duration patterns.</p>
        </div>
        <div class="space-y-2 mb-4">
          <div class="flex justify-between border-b border-slate-100 pb-2">
            <span class="text-sm text-slate-600">Avg negotiation rounds (booked)</span>
            <span class="font-semibold text-slate-900">${AVG_ROUNDS}</span>
          </div>
          <div class="flex justify-between border-b border-slate-100 pb-2">
            <span class="text-sm text-slate-600">% booked without negotiation</span>
            <span class="font-semibold text-slate-900">${PCT_NO_NEG}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-slate-600">% used max rounds (3)</span>
            <span class="font-semibold text-slate-900">${PCT_MAX_ROUNDS}%</span>
          </div>
        </div>
      </section>

      <section class="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
        <div class="mb-3">
          <h2 class="text-lg font-semibold text-slate-800">Quality</h2>
          <p class="text-xs text-slate-500">Why this matters: sentiment and case-health drift.</p>
        </div>
        <div class="grid grid-cols-2 gap-4 items-center mb-4">
          <div class="h-44"><canvas id="sentimentChart"></canvas></div>
          <div class="metric bg-slate-50 rounded-lg p-4 text-center">
            <p class="text-[10px] uppercase tracking-wider text-slate-500">Avg case health</p>
            <p class="text-4xl font-bold text-slate-900 mt-2">${AVG_HEALTH}<span class="text-lg text-slate-400">/100</span></p>
          </div>
        </div>
        <p class="text-[10px] uppercase tracking-wider text-slate-500 mb-1">CHS bucket distribution</p>
        <div class="h-40"><canvas id="chsDistChart"></canvas></div>
      </section>
    </div>

    <!-- ===== SECTION 5: FMCSA & Compliance ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">FMCSA &amp; Compliance</h2>
        <p class="text-xs text-slate-500">Why this matters: see who's getting blocked, and why.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
        <div class="metric bg-rose-50 rounded-lg p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-rose-600">FMCSA decline rate</p>
          <p class="text-4xl font-bold text-rose-700 mt-2">${DECLINE_RATE}%</p>
          <p class="text-xs text-slate-500 mt-1">% of calls blocked by eligibility</p>
        </div>
        <div class="md:col-span-2 h-56"><canvas id="fmcsaChart"></canvas></div>
      </div>
    </section>

    <!-- ===== SECTION 6: Call Volume Heatmap ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">Call Volume Heatmap</h2>
        <p class="text-xs text-slate-500">Why this matters: when do calls peak — staff accordingly.</p>
      </div>
      <div id="heatmap" class="overflow-x-auto"></div>
    </section>

    <!-- ===== SECTION 7: Top Carriers ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">Top Carriers</h2>
        <p class="text-xs text-slate-500">Why this matters: relationship intelligence. Click a row to filter to that MC.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th class="text-left p-2">MC</th>
              <th class="text-left p-2">Carrier</th>
              <th class="text-right p-2">Calls</th>
              <th class="text-right p-2">Booked</th>
              <th class="text-right p-2">Booking rate</th>
              <th class="text-right p-2">Avg CHS</th>
              <th class="text-left p-2">Last call</th>
            </tr>
          </thead>
          <tbody id="carriersBody"></tbody>
        </table>
      </div>
    </section>

    <!-- ===== SECTION 8: Agent Version ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">Agent Versions</h2>
        <p class="text-xs text-slate-500">Why this matters: monitor / compare agent versions over time.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th class="text-left p-2">Version</th>
              <th class="text-right p-2">Calls</th>
              <th class="text-right p-2">Booking rate</th>
              <th class="text-right p-2">Avg CHS</th>
            </tr>
          </thead>
          <tbody id="versionsBody"></tbody>
        </table>
      </div>
    </section>

    <!-- ===== SECTION 9: Recent Calls ===== -->
    <section class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200">
      <div class="mb-3">
        <h2 class="text-lg font-semibold text-slate-800">Recent Calls</h2>
        <p class="text-xs text-slate-500">Why this matters: per-call human audit. Click a row for full detail.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm" id="recentTable">
          <thead class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
            <tr>
              <th class="sortable text-left p-2" data-sort="created_at">Created</th>
              <th class="sortable text-left p-2" data-sort="mc_number">MC</th>
              <th class="sortable text-left p-2" data-sort="carrier_name">Carrier</th>
              <th class="sortable text-left p-2" data-sort="outcome">Outcome</th>
              <th class="sortable text-left p-2" data-sort="sentiment">Sentiment</th>
              <th class="sortable text-right p-2" data-sort="case_health_score">CHS</th>
              <th class="sortable text-right p-2" data-sort="call_duration_seconds">Duration</th>
              <th class="sortable text-right p-2" data-sort="apply_rate">Agreed</th>
            </tr>
          </thead>
          <tbody id="recentBody"></tbody>
        </table>
      </div>
    </section>

    <!-- ===== SECTION 10: Drilldown Panel ===== -->
    <section id="call-detail" class="bg-white rounded-xl shadow-sm p-6 mb-6 border border-slate-200 hidden">
      <div class="flex justify-between items-start mb-3">
        <div>
          <h2 class="text-lg font-semibold text-slate-800">Call Detail</h2>
          <p class="text-xs text-slate-500">Why this matters: deep call review for QA + escalation.</p>
        </div>
        <button id="closeDetail" class="text-xs text-slate-500 hover:text-slate-900">Close ✕</button>
      </div>
      <div id="detailBody"></div>
    </section>

    <footer class="mt-10 pt-6 border-t border-slate-200 text-center text-xs text-slate-400">
      <p>FastAPI · Tailwind · Chart.js · Fly.io · Bearer auth · Docker · Built for Acme Logistics</p>
      <p class="mt-1">Powered by HappyRobot</p>
    </footer>
  </div>

  <script>
    // ===== INLINED DATA =====
    const FILTERED = ${FILTERED_JSON};
    const FUNNEL = ${FUNNEL_JSON};
    const ECONOMICS = ${ECONOMICS_JSON};
    const OPERATIONAL = ${OPERATIONAL_JSON};
    const QUALITY = ${QUALITY_JSON};
    const OBSERVABILITY = ${OBSERVABILITY_JSON};
    const TREND = ${TREND_JSON};
    const HISTOGRAM = ${HISTOGRAM_JSON};
    const CHS_DIST = ${CHS_DIST_JSON};
    const FMCSA = ${FMCSA_JSON};
    const HEATMAP = ${HEATMAP_JSON};
    const CARRIERS = ${CARRIERS_JSON};
    const VERSIONS = ${VERSIONS_JSON};
    const TAGS = ${TAGS_JSON};
    const RECENT_CALLS = ${RECENT_JSON};

    const outcomeColors = {
      load_booked: '#10b981',
      no_match: '#f59e0b',
      carrier_not_qualified: '#ef4444',
      call_abandoned: '#94a3b8',
      unknown: '#cbd5e1'
    };
    const sentimentColors = {
      positive: '#10b981',
      neutral: '#94a3b8',
      negative: '#ef4444'
    };
    const severityColors = {
      info:  { bg: '#dbeafe', fg: '#1e40af' },
      warn:  { bg: '#fef3c7', fg: '#92400e' },
      page:  { bg: '#fee2e2', fg: '#991b1b' }
    };

    function fmtMoney(v) {
      if (v == null || v === '') return '—';
      const n = Number(v);
      if (isNaN(n)) return '—';
      return '$$' + Math.round(n).toLocaleString();
    }
    function fmtNum(v, suffix = '') {
      if (v == null || v === '') return '—';
      const n = Number(v);
      if (isNaN(n)) return '—';
      return n.toFixed(2).replace(/\\.00$$/, '') + suffix;
    }
    function fmtDate(s) {
      if (!s) return '—';
      try { return new Date(s).toLocaleString(); } catch (e) { return s; }
    }
    function fmtDuration(s) {
      if (s == null || s === '') return '—';
      const n = Number(s);
      if (isNaN(n)) return '—';
      const m = Math.floor(n / 60);
      const sec = Math.round(n % 60);
      return m + ':' + (sec < 10 ? '0' : '') + sec;
    }
    function escHtml(s) {
      if (s == null) return '';
      return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }

    // ===== INIT CHARTS =====
    function initCharts() {
      // --- Funnel bar ---
      const funnelLabels = Object.keys(FUNNEL.by_outcome || {});
      const funnelValues = Object.values(FUNNEL.by_outcome || {});
      if (document.getElementById('funnelChart')) {
        new Chart(document.getElementById('funnelChart'), {
          type: 'bar',
          data: {
            labels: funnelLabels,
            datasets: [{
              label: 'Calls',
              data: funnelValues,
              backgroundColor: funnelLabels.map(l => outcomeColors[l] || '#cbd5e1'),
              borderRadius: 6
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { ticks: { maxRotation: 30, minRotation: 30, font: { size: 9 } } },
              y: { beginAtZero: true, ticks: { precision: 0 } }
            }
          }
        });
      }

      // --- Outcome trend line ---
      if (document.getElementById('trendChart') && TREND && TREND.labels) {
        const tdatasets = Object.keys(TREND.series || {}).map(k => ({
          label: k,
          data: TREND.series[k],
          borderColor: outcomeColors[k] || '#94a3b8',
          backgroundColor: 'transparent',
          tension: 0.25,
          borderWidth: 2,
          pointRadius: 0
        }));
        new Chart(document.getElementById('trendChart'), {
          type: 'line',
          data: { labels: TREND.labels, datasets: tdatasets },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { font: { size: 9 } } } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
          }
        });
      }

      // --- Sentiment doughnut ---
      const sentimentLabels = Object.keys(QUALITY.sentiment_distribution || {});
      const sentimentValues = Object.values(QUALITY.sentiment_distribution || {});
      if (document.getElementById('sentimentChart')) {
        new Chart(document.getElementById('sentimentChart'), {
          type: 'doughnut',
          data: {
            labels: sentimentLabels,
            datasets: [{
              data: sentimentValues,
              backgroundColor: sentimentLabels.map(l => sentimentColors[l] || '#cbd5e1')
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }
          }
        });
      }

      // --- Agreed rate histogram ---
      if (document.getElementById('agreedHistogram') && HISTOGRAM && HISTOGRAM.bin_edges) {
        const labels = [];
        for (let i = 0; i < HISTOGRAM.bin_edges.length - 1; i++) {
          labels.push(Math.round(HISTOGRAM.bin_edges[i]) + '-' + Math.round(HISTOGRAM.bin_edges[i + 1]));
        }
        new Chart(document.getElementById('agreedHistogram'), {
          type: 'bar',
          data: { labels, datasets: [{ data: HISTOGRAM.counts || [], backgroundColor: '#10b981', borderRadius: 4 }] },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
          }
        });
      }

      // --- CHS distribution ---
      if (document.getElementById('chsDistChart') && CHS_DIST && CHS_DIST.buckets) {
        new Chart(document.getElementById('chsDistChart'), {
          type: 'bar',
          data: {
            labels: CHS_DIST.buckets,
            datasets: [{
              data: CHS_DIST.counts || [],
              backgroundColor: ['#ef4444', '#f59e0b', '#fbbf24', '#84cc16', '#10b981'],
              borderRadius: 4
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
          }
        });
      }

      // --- FMCSA decline pie ---
      if (document.getElementById('fmcsaChart') && FMCSA && FMCSA.reasons) {
        new Chart(document.getElementById('fmcsaChart'), {
          type: 'pie',
          data: {
            labels: FMCSA.reasons,
            datasets: [{
              data: FMCSA.counts || [],
              backgroundColor: ['#ef4444', '#f59e0b', '#a855f7', '#0ea5e9', '#94a3b8', '#22c55e']
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { font: { size: 10 } } } }
          }
        });
      }

      // --- Sparklines ---
      function spark(id, data, color) {
        const el = document.getElementById(id);
        if (!el || !data || !data.length) return;
        new Chart(el, {
          type: 'line',
          data: { labels: data.map((_, i) => i), datasets: [{ data, borderColor: color, backgroundColor: color + '22', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0 }] },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: { x: { display: false }, y: { display: false } }
          }
        });
      }
      if (OBSERVABILITY) {
        spark('sparkChs', OBSERVABILITY.chs_spark || [], '#10b981');
        spark('sparkBookRate', OBSERVABILITY.booking_rate_spark || [], '#3b82f6');
      }
    }

    // ===== ALERT CHIPS =====
    function renderAlerts() {
      const el = document.getElementById('alertChips');
      if (!el) return;
      const alerts = OBSERVABILITY && OBSERVABILITY.alerts ? OBSERVABILITY.alerts : [];
      if (!alerts.length) {
        el.innerHTML = '<span class="text-xs text-slate-400">No alert rules configured.</span>';
        return;
      }
      el.innerHTML = alerts.map(a => {
        const sev = severityColors[a.severity] || severityColors.info;
        const icon = a.fired ? '✗' : '✓';
        const bg = a.fired ? sev.bg : '#dcfce7';
        const fg = a.fired ? sev.fg : '#166534';
        const detail = a.detail ? ' · ' + a.detail : '';
        return '<span class="stoplight" style="background:' + bg + ';color:' + fg + ';" title="' + escHtml(a.name + detail) + '">' + icon + ' ' + escHtml(a.name) + '</span>';
      }).join('');
    }

    // ===== TAG CLOUD =====
    function renderTags() {
      const el = document.getElementById('tagCloud');
      if (!el) return;
      if (!TAGS || !TAGS.length) {
        el.innerHTML = '<span class="text-xs text-slate-400">No remarks captured.</span>';
        return;
      }
      const max = Math.max(...TAGS.map(t => t.count));
      el.innerHTML = TAGS.map(t => {
        const scale = 0.75 + (t.count / max) * 0.6;
        return '<span class="px-2 py-1 bg-slate-100 text-slate-700 rounded" style="font-size:' + scale + 'rem;">' + escHtml(t.tag) + ' <span class="text-slate-400">' + t.count + '</span></span>';
      }).join('');
    }

    // ===== HEATMAP =====
    function renderHeatmap() {
      const el = document.getElementById('heatmap');
      if (!el || !HEATMAP || !HEATMAP.matrix) return;
      const matrix = HEATMAP.matrix;
      const days = HEATMAP.days || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      const hours = HEATMAP.hours || Array.from({ length: 24 }, (_, i) => i);
      let max = 0;
      matrix.forEach(row => row.forEach(v => { if (v > max) max = v; }));

      let html = '<table class="text-[10px]"><thead><tr><th></th>';
      hours.forEach(h => { html += '<th class="px-0.5 text-slate-400">' + h + '</th>'; });
      html += '</tr></thead><tbody>';
      matrix.forEach((row, ri) => {
        html += '<tr><td class="pr-2 text-slate-500 font-medium">' + escHtml(days[ri] || '') + '</td>';
        row.forEach((v, ci) => {
          const intensity = max ? v / max : 0;
          const alpha = intensity === 0 ? 0.05 : 0.15 + intensity * 0.85;
          html += '<td class="px-0.5"><div class="heatmap-cell" style="background-color:rgba(16,185,129,' + alpha.toFixed(2) + ');" title="' + escHtml(days[ri]) + ' ' + ci + ':00 — ' + v + ' calls"></div></td>';
        });
        html += '</tr>';
      });
      html += '</tbody></table>';
      el.innerHTML = html;
    }

    // ===== CARRIER ROLLUP =====
    function renderCarriers() {
      const tb = document.getElementById('carriersBody');
      if (!tb) return;
      if (!CARRIERS || !CARRIERS.length) {
        tb.innerHTML = '<tr><td colspan="7" class="p-4 text-center text-slate-400">No carrier data yet.</td></tr>';
        return;
      }
      tb.innerHTML = CARRIERS.map(c => (
        '<tr class="row-clickable border-b border-slate-100" data-mc="' + escHtml(c.mc_number) + '">' +
          '<td class="p-2 font-mono">' + escHtml(c.mc_number || '—') + '</td>' +
          '<td class="p-2">' + escHtml(c.carrier_name || '—') + '</td>' +
          '<td class="p-2 text-right">' + (c.call_count ?? 0) + '</td>' +
          '<td class="p-2 text-right">' + (c.booked_count ?? 0) + '</td>' +
          '<td class="p-2 text-right">' + fmtNum(c.booking_rate_pct, '%') + '</td>' +
          '<td class="p-2 text-right">' + fmtNum(c.avg_chs) + '</td>' +
          '<td class="p-2 text-slate-500">' + fmtDate(c.last_call_at) + '</td>' +
        '</tr>'
      )).join('');
    }

    // ===== VERSIONS =====
    function renderVersions() {
      const tb = document.getElementById('versionsBody');
      if (!tb) return;
      if (!VERSIONS || !VERSIONS.length) {
        tb.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-slate-400">No version data.</td></tr>';
        return;
      }
      tb.innerHTML = VERSIONS.map(v => (
        '<tr class="border-b border-slate-100">' +
          '<td class="p-2 font-mono">' + escHtml(v.version || 'unknown') + '</td>' +
          '<td class="p-2 text-right">' + (v.call_count ?? 0) + '</td>' +
          '<td class="p-2 text-right">' + fmtNum(v.booking_rate_pct, '%') + '</td>' +
          '<td class="p-2 text-right">' + fmtNum(v.avg_chs) + '</td>' +
        '</tr>'
      )).join('');
    }

    // ===== RECENT CALLS =====
    let recentRows = (RECENT_CALLS || []).slice();
    let sortKey = 'created_at';
    let sortDir = -1;

    function renderRecent() {
      const tb = document.getElementById('recentBody');
      if (!tb) return;
      if (!recentRows.length) {
        tb.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-slate-400">No calls match.</td></tr>';
        return;
      }
      tb.innerHTML = recentRows.map(r => {
        const outcome = r.call_outcome || r.outcome || 'unknown';
        const sentiment = r.sentiment || 'neutral';
        const oc = outcomeColors[outcome] || '#cbd5e1';
        const sc = sentimentColors[sentiment] || '#94a3b8';
        return (
          '<tr class="row-clickable border-b border-slate-100" data-call-id="' + escHtml(r.call_id || r.id || '') + '">' +
            '<td class="p-2 text-slate-500">' + fmtDate(r.created_at) + '</td>' +
            '<td class="p-2 font-mono">' + escHtml(r.mc_number || '—') + '</td>' +
            '<td class="p-2">' + escHtml(r.carrier_name || r.legal_name || '—') + '</td>' +
            '<td class="p-2"><span class="chip" style="background:' + oc + '22;color:' + oc + ';">' + escHtml(outcome) + '</span></td>' +
            '<td class="p-2"><span class="chip" style="background:' + sc + '22;color:' + sc + ';">' + escHtml(sentiment) + '</span></td>' +
            '<td class="p-2 text-right">' + fmtNum(r.case_health_score) + '</td>' +
            '<td class="p-2 text-right">' + fmtDuration(r.call_duration_seconds) + '</td>' +
            '<td class="p-2 text-right">' + fmtMoney(r.apply_rate) + '</td>' +
          '</tr>'
        );
      }).join('');
    }

    function wireSort() {
      document.querySelectorAll('#recentTable th.sortable').forEach(th => {
        th.addEventListener('click', () => {
          const k = th.getAttribute('data-sort');
          if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }
          recentRows.sort((a, b) => {
            const av = a[k]; const bv = b[k];
            if (av == null && bv == null) return 0;
            if (av == null) return 1;
            if (bv == null) return -1;
            const an = Number(av), bn = Number(bv);
            if (!isNaN(an) && !isNaN(bn)) return (an - bn) * sortDir;
            return String(av).localeCompare(String(bv)) * sortDir;
          });
          renderRecent();
        });
      });
    }

    function wireRowClick() {
      document.getElementById('recentBody').addEventListener('click', (e) => {
        const tr = e.target.closest('tr[data-call-id]');
        if (!tr) return;
        const id = tr.getAttribute('data-call-id');
        const row = recentRows.find(r => String(r.call_id || r.id) === id);
        if (!row) return;
        showDrilldown(row);
      });
    }

    function showDrilldown(r) {
      const sec = document.getElementById('call-detail');
      const body = document.getElementById('detailBody');
      const transcript = r.transcript || r.transcript_text || '';
      const tShort = transcript.slice(0, 500);
      const tHasMore = transcript.length > 500;
      body.innerHTML = (
        '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">' +
          '<div><p class="text-[10px] uppercase text-slate-500">Call ID</p><p class="font-mono">' + escHtml(r.call_id || r.id || '—') + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">MC</p><p class="font-mono">' + escHtml(r.mc_number || '—') + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">Carrier</p><p>' + escHtml(r.carrier_name || r.legal_name || '—') + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">Outcome</p><p>' + escHtml(r.call_outcome || r.outcome || '—') + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">Sentiment</p><p>' + escHtml(r.sentiment || '—') + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">CHS</p><p>' + fmtNum(r.case_health_score) + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">Agreed rate</p><p>' + fmtMoney(r.apply_rate) + '</p></div>' +
          '<div><p class="text-[10px] uppercase text-slate-500">FMCSA decline</p><p>' + escHtml(r.fmcsa_eligibility_failure_reason || '—') + '</p></div>' +
        '</div>' +
        '<div class="mb-4"><p class="text-[10px] uppercase text-slate-500 mb-1">Audit remarks</p><p class="text-sm bg-slate-50 rounded p-3 whitespace-pre-wrap">' + escHtml(r.audit_remarks || '—') + '</p></div>' +
        (transcript ?
          '<details class="transcript"><summary>Transcript snippet</summary>' +
          '<p class="text-sm bg-slate-50 rounded p-3 mt-2 whitespace-pre-wrap">' + escHtml(tShort) + (tHasMore ? '…' : '') + '</p>' +
          (tHasMore ? '<button id="expandTranscript" class="mt-2 text-xs text-blue-600">Expand full transcript</button><pre id="fullTranscript" class="hidden mt-2 text-xs bg-slate-50 p-3 rounded whitespace-pre-wrap"></pre>' : '') +
          '</details>'
          : '<p class="text-xs text-slate-400">No transcript captured.</p>')
      );
      sec.classList.remove('hidden');
      window.location.hash = 'call-detail';

      const expandBtn = document.getElementById('expandTranscript');
      if (expandBtn) {
        expandBtn.addEventListener('click', () => {
          const full = document.getElementById('fullTranscript');
          full.textContent = transcript;
          full.classList.remove('hidden');
          expandBtn.classList.add('hidden');
        });
      }
    }

    function wireCloseDetail() {
      const btn = document.getElementById('closeDetail');
      if (btn) btn.addEventListener('click', () => {
        document.getElementById('call-detail').classList.add('hidden');
      });
    }

    function wireCarrierClick() {
      const tb = document.getElementById('carriersBody');
      if (!tb) return;
      tb.addEventListener('click', (e) => {
        const tr = e.target.closest('tr[data-mc]');
        if (!tr) return;
        const mc = tr.getAttribute('data-mc');
        if (mc) window.location = '/dashboard?q=' + encodeURIComponent(mc);
      });
    }

    function wireFilterReset() {
      const btn = document.getElementById('resetBtn');
      if (btn) btn.addEventListener('click', () => { window.location = '/dashboard'; });
    }

    function wireLiveToggle() {
      const cb = document.getElementById('liveToggle');
      if (!cb) return;
      const stored = localStorage.getItem('dashLive') === '1';
      const url = new URL(window.location);
      const fromUrl = url.searchParams.get('live') === '1';
      cb.checked = stored || fromUrl;
      let timer = null;
      function arm() {
        if (cb.checked) {
          timer = setInterval(() => window.location.reload(), 30000);
        } else if (timer) {
          clearInterval(timer); timer = null;
        }
      }
      cb.addEventListener('change', () => {
        localStorage.setItem('dashLive', cb.checked ? '1' : '0');
        const u = new URL(window.location);
        if (cb.checked) u.searchParams.set('live', '1'); else u.searchParams.delete('live');
        window.history.replaceState({}, '', u);
        arm();
      });
      arm();
    }

    // ===== BOOT =====
    document.addEventListener('DOMContentLoaded', () => {
      try { initCharts(); } catch (e) { console.error('initCharts', e); }
      renderAlerts();
      renderTags();
      renderHeatmap();
      renderCarriers();
      renderVersions();
      renderRecent();
      wireSort();
      wireRowClick();
      wireCloseDetail();
      wireCarrierClick();
      wireFilterReset();
      wireLiveToggle();
    });
  </script>
</body>
</html>
"""
)


def _fmt_money(v: float | None) -> str:
    if v is None:
        return "—"
    return f"${int(round(v)):,}"


def _fmt_num(v: float | None, default: str = "—") -> str:
    if v is None:
        return default
    return str(v)


def _selected(condition: bool) -> str:
    return "selected" if condition else ""


def _q(request: Request, key: str) -> str | None:
    v = request.query_params.get(key)
    if v is None or v == "":
        return None
    return v


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_view(request: Request) -> HTMLResponse:
    # ===== Filter inputs =====
    f_from = _q(request, "from")
    f_to = _q(request, "to")
    f_outcome = _q(request, "outcome")
    f_sentiment = _q(request, "sentiment")
    f_q = _q(request, "q")

    # ===== Source rows + filter =====
    try:
        all_rows: list[dict[str, Any]] = await list_calls(limit=500) or []
    except Exception:
        all_rows = []
    try:
        rows = apply_filters(
            all_rows,
            from_=f_from,
            to_=f_to,
            outcome=f_outcome,
            sentiment=f_sentiment,
            q=f_q,
        )
    except Exception:
        rows = all_rows

    # ===== Aggregations (filtered, in-memory row-mode) =====
    f = (await funnel(rows=rows)).model_dump()
    e = (await economics(rows=rows)).model_dump()
    o = (await operational(rows=rows)).model_dump()
    q = (await quality(rows=rows)).model_dump()

    # ===== New aggregation slices =====
    try:
        trend = outcome_trend(rows, days=30)
    except Exception:
        trend = {"labels": [], "series": {}}
    try:
        chs_dist = chs_distribution(rows)
    except Exception:
        chs_dist = {"buckets": [], "counts": []}
    try:
        histogram = apply_rate_histogram(rows, bins=10)
    except Exception:
        histogram = {"bin_edges": [], "counts": []}
    try:
        fmcsa = fmcsa_decline_breakdown(rows)
    except Exception:
        fmcsa = {"reasons": [], "counts": [], "decline_rate_pct": 0.0}
    try:
        heatmap = call_volume_heatmap(rows)
    except Exception:
        heatmap = {
            "matrix": [[0] * 24 for _ in range(7)],
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "hours": list(range(24)),
        }
    try:
        carriers = carrier_rollup(rows, top_n=10)
    except Exception:
        carriers = []
    try:
        versions = agent_version_metrics(rows)
    except Exception:
        versions = []
    try:
        tags = audit_remarks_clusters(rows, top_n=5)
    except Exception:
        tags = []
    try:
        alerts = system_alerts(rows, recent_window=20, baseline_window=200)
    except Exception:
        alerts = []

    # Sparklines: derive from latency p90 + chs trajectory + booking rate trajectory if not supplied
    chs_spark: list[float] = []
    book_spark: list[float] = []
    try:
        recent50 = rows[-50:] if rows else []
        chs_spark = [float(r["case_health_score"]) for r in recent50 if r.get("case_health_score") not in (None, "")]
        # rolling booking rate over last 50, window of 10
        outs = [
            1.0 if (r.get("call_outcome") or r.get("outcome")) == "load_booked" else 0.0
            for r in recent50
        ]
        for i in range(len(outs)):
            window = outs[max(0, i - 9): i + 1]
            book_spark.append(round(sum(window) / len(window) * 100, 2) if window else 0.0)
    except Exception:
        pass

    observability = {
        "alerts": alerts,
        "chs_spark": chs_spark,
        "booking_rate_spark": book_spark,
    }

    # ===== Recent calls (last 25, newest first) — full row objects for drilldown =====
    sorted_rows = sorted(
        rows or [],
        key=lambda r: r.get("created_at") or "",
        reverse=True,
    )
    recent = sorted_rows[:25]

    # ===== KPI strip values =====
    total_calls = f.get("total_calls", 0)
    booked_count = f.get("by_outcome", {}).get("load_booked", 0)
    booking_rate = f.get("booking_rate_pct", 0.0)
    avg_chs = q.get("avg_case_health_score")

    # ===== Empty-state banner =====
    if total_calls == 0:
        empty_banner = (
            '<div class="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-3 mb-6 text-sm flex justify-between items-center">'
            "<span>No calls match the current filters.</span>"
            '<a href="/dashboard" class="underline font-semibold">Reset filters</a>'
            "</div>"
        )
    else:
        empty_banner = ""

    html = _HTML.substitute(
        # Header
        TOTAL_CALLS=total_calls,
        WINDOW_DAYS=30,
        NOW=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        API_STATUS="API live",
        API_STATUS_CLASS="bg-green-100 text-green-700",
        # Filter echo
        F_FROM=(f_from or ""),
        F_TO=(f_to or ""),
        F_Q=(f_q or ""),
        F_OUT_ALL=_selected(not f_outcome),
        F_OUT_LB=_selected(f_outcome == "load_booked"),
        F_OUT_NM=_selected(f_outcome == "no_match"),
        F_OUT_CNQ=_selected(f_outcome == "carrier_not_qualified"),
        F_OUT_CA=_selected(f_outcome == "call_abandoned"),
        F_SEN_ALL=_selected(not f_sentiment),
        F_SEN_POS=_selected(f_sentiment == "positive"),
        F_SEN_NEU=_selected(f_sentiment == "neutral"),
        F_SEN_NEG=_selected(f_sentiment == "negative"),
        EMPTY_BANNER=empty_banner,
        # KPI strip
        KPI_TOTAL=total_calls,
        KPI_BOOKED=booked_count,
        KPI_RATE=booking_rate,
        KPI_CHS=_fmt_num(avg_chs, "—"),
        # Funnel
        BOOKED_COUNT=booked_count,
        BOOKING_RATE=booking_rate,
        # Economics
        AVG_LOADBOARD=_fmt_money(e.get("avg_loadboard_rate")),
        AVG_AGREED=_fmt_money(e.get("avg_agreed_rate")),
        AVG_DISCOUNT=_fmt_num(e.get("effective_delta_pct"), "0"),
        TOTAL_REVENUE=_fmt_money(e.get("total_revenue_booked")),
        # Operational (post-v15: duration + fmcsa decline + abandon rate)
        AVG_ROUNDS=_fmt_num(o.get("avg_duration_seconds"), "—"),
        PCT_NO_NEG=_fmt_num(o.get("fmcsa_decline_pct"), "—"),
        PCT_MAX_ROUNDS=_fmt_num(o.get("abandon_rate_pct"), "—"),
        # Quality
        AVG_HEALTH=_fmt_num(avg_chs, "—"),
        # FMCSA
        DECLINE_RATE=_fmt_num(fmcsa.get("decline_rate_pct", 0.0), "0"),
        # JSON blobs
        FILTERED_JSON=json.dumps(rows, default=str),
        FUNNEL_JSON=json.dumps(f, default=str),
        ECONOMICS_JSON=json.dumps(e, default=str),
        OPERATIONAL_JSON=json.dumps(o, default=str),
        QUALITY_JSON=json.dumps(q, default=str),
        OBSERVABILITY_JSON=json.dumps(observability, default=str),
        TREND_JSON=json.dumps(trend, default=str),
        HISTOGRAM_JSON=json.dumps(histogram, default=str),
        CHS_DIST_JSON=json.dumps(chs_dist, default=str),
        FMCSA_JSON=json.dumps(fmcsa, default=str),
        HEATMAP_JSON=json.dumps(heatmap, default=str),
        CARRIERS_JSON=json.dumps(carriers, default=str),
        VERSIONS_JSON=json.dumps(versions, default=str),
        TAGS_JSON=json.dumps(tags, default=str),
        RECENT_JSON=json.dumps(recent, default=str),
    )
    return HTMLResponse(content=html)
