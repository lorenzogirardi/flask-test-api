/* DebugKnife — Real-time dashboard logic */
(function () {
  'use strict';

  const BASE = document.head.querySelector('meta[name="base-path"]')?.content || '';
  const POLL_MS = 5000;
  let pollTimer = null;

  /* ── Theme toggle ── */
  function initTheme() {
    const saved = localStorage.getItem('dk-theme');
    const pref = saved || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    document.documentElement.setAttribute('data-theme', pref);
    updateThemeIcon(pref);
  }
  function toggleTheme() {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('dk-theme', next);
    updateThemeIcon(next);
  }
  function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = theme === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
  }

  /* ── Fetch helpers ── */
  async function fetchJSON(path) {
    try {
      const r = await fetch(BASE + path, { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      return await r.json();
    } catch { return null; }
  }

  /* ── Status color ── */
  function statusColor(s) {
    if (!s) return 'gray';
    s = s.toUpperCase();
    if (s === 'UP' || s === 'READY' || s === 'CONNECTED') return 'green';
    if (s === 'DEGRADED' || s === 'NOT_CONFIGURED') return 'yellow';
    return 'red';
  }

  /* ── Update health panel ── */
  async function refreshHealth() {
    const data = await fetchJSON('/mgmt/health');
    if (!data) return;

    // overall dot
    const dot = document.getElementById('overall-dot');
    if (dot) {
      dot.className = 'dot ' + (data.status === 'UP' ? '' : 'degraded');
    }

    // per-check status
    (data.checks || []).forEach(c => {
      const el = document.getElementById('status-' + c.name);
      if (!el) return;
      const dotEl = el.querySelector('.status-dot');
      const detailEl = el.querySelector('.status-detail');
      if (dotEl) {
        dotEl.className = 'status-dot pulse ' + statusColor(c.status);
      }
      if (detailEl) {
        detailEl.textContent = c.status + (c.error ? ' — ' + c.error : '');
      }
    });
  }

  /* ── Update info ── */
  async function refreshInfo() {
    const data = await fetchJSON('/mgmt/info');
    if (!data?.app) return;
    const el = document.getElementById('app-version');
    if (el) el.textContent = 'v' + data.app.version + ' · ' + data.app.environment;
  }

  /* ── Update mappings count ── */
  async function refreshMappings() {
    const data = await fetchJSON('/mgmt/mappings');
    if (!data?.mappings) return;
    const el = document.getElementById('kpi-endpoints');
    if (el) el.textContent = data.mappings.length;

    // build endpoints table
    const tbody = document.getElementById('endpoints-tbody');
    if (!tbody) return;
    const routes = data.mappings
      .filter(m => m.name && !['openapi','swagger_ui_html','swagger_ui_redirect','redoc_html'].includes(m.name))
      .sort((a, b) => a.path.localeCompare(b.path));

    tbody.innerHTML = routes.map(r => {
      const methods = (r.methods || []).map(m =>
        '<span class="method-badge ' + m.toLowerCase() + '">' + m + '</span>'
      ).join(' ');
      const authTag = (r.path.startsWith('/debug/') || r.path === '/mgmt/threaddump')
        ? ' <span class="tag-auth">auth</span>' : '';
      return '<tr>' +
        '<td>' + methods + '</td>' +
        '<td><span class="path-text">' + r.path + '</span>' + authTag + '</td>' +
        '<td>' + (r.name || '') + '</td>' +
        '<td><button class="copy-btn" data-path="' + r.path + '" title="Copy URL">&#128203;</button></td>' +
        '</tr>';
    }).join('');
  }

  /* ── Copy to clipboard ── */
  function handleCopy(e) {
    const btn = e.target.closest('.copy-btn');
    if (!btn) return;
    const path = btn.dataset.path;
    const url = location.origin + BASE + path;
    navigator.clipboard.writeText(url).then(() => {
      btn.classList.add('copied');
      btn.textContent = '\u2713';
      showToast('Copied: ' + url);
      setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = '&#128203;'; }, 1500);
    });
  }

  /* ── Toast ── */
  function showToast(msg) {
    let t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      t.className = 'toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2000);
  }

  /* ── Uptime counter ── */
  let startTime = Date.now();
  function updateUptime() {
    const el = document.getElementById('kpi-uptime');
    if (!el) return;
    const diff = Math.floor((Date.now() - startTime) / 1000);
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const s = diff % 60;
    el.textContent = (h > 0 ? h + 'h ' : '') + m + 'm ' + s + 's';
  }

  /* ── Poll cycle ── */
  async function poll() {
    await Promise.all([refreshHealth(), refreshInfo(), refreshMappings()]);
    updateUptime();
  }

  /* ── Init ── */
  function init() {
    initTheme();
    document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
    document.addEventListener('click', handleCopy);
    poll();
    pollTimer = setInterval(poll, POLL_MS);
    setInterval(updateUptime, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
