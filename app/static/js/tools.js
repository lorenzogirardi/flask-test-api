/* DebugKnife — Chaos & Tools panel */
(function () {
  'use strict';

  const root = document.getElementById('tools-root');
  const out = document.getElementById('tool-result');
  if (!root || !out) return;
  const BASE = root.dataset.base || '/api';

  function qs(obj) {
    const p = new URLSearchParams();
    Object.entries(obj).forEach(([k, v]) => { if (v !== '' && v != null) p.append(k, v); });
    const s = p.toString();
    return s ? '?' + s : '';
  }

  function authHeader() {
    const u = document.getElementById('dbg-user');
    const p = document.getElementById('dbg-pass');
    if (!u || !p) return {};
    return { Authorization: 'Basic ' + btoa(unescape(encodeURIComponent(u.value + ':' + p.value))) };
  }

  /* tool -> request builder (receives the form's field values) */
  const TOOLS = {
    chaos: v => ({ url: v.path + qs({ inject_error: v.inject_error, delay_ms: v.delay_ms }) }),
    fib: v => ({ url: '/fib/' + encodeURIComponent(v.n) }),
    sleep: v => ({ url: '/sleep/' + encodeURIComponent(v.seconds) }),
    cpu: v => ({
      url: '/debug/cpu/spike', auth: true, method: 'POST',
      body: { duration: Number(v.duration), cores: Number(v.cores) },
    }),
    scan: v => ({ url: '/debug/network/scan' + qs({ target: v.target }), auth: true }),
    ping: v => ({ url: '/debug/ping' + qs({ host: v.host, count: v.count }), auth: true }),
    dns: v => ({ url: '/debug/dns' + qs({ name: v.name }), auth: true }),
    tcp: v => ({ url: '/debug/tcp-check' + qs({ host: v.host, port: v.port }), auth: true }),
    curl: v => ({ url: '/debug/curl' + qs({ url: v.url }), auth: true }),
    rnderr: () => ({ url: '/debug/random-error', auth: true }),
  };

  async function run(tool, values, btn) {
    const spec = TOOLS[tool](values);
    const headers = {};
    if (spec.auth) Object.assign(headers, authHeader());
    if (spec.body) headers['Content-Type'] = 'application/json';

    const method = spec.method || 'GET';
    out.textContent = method + ' ' + BASE + spec.url + ' ...';
    if (btn) btn.disabled = true;
    const t0 = performance.now();
    try {
      const r = await fetch(BASE + spec.url, {
        method, headers, cache: 'no-store',
        body: spec.body ? JSON.stringify(spec.body) : undefined,
      });
      const ms = Math.round(performance.now() - t0);
      const text = await r.text();
      let body = text;
      try { body = JSON.stringify(JSON.parse(text), null, 2); } catch { /* not JSON */ }
      out.textContent = method + ' ' + BASE + spec.url + '\n' + r.status + ' ' + r.statusText + ' · ' + ms + ' ms\n\n' + body;
      out.className = 'tool-result ' + (r.ok ? 'ok' : 'err');
    } catch (e) {
      out.textContent = 'Request failed: ' + e.message;
      out.className = 'tool-result err';
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  root.addEventListener('submit', e => {
    const form = e.target.closest('form[data-tool]');
    if (!form) return;
    e.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    if (TOOLS[form.dataset.tool]) run(form.dataset.tool, values, form.querySelector('button[type=submit]'));
  });
})();
