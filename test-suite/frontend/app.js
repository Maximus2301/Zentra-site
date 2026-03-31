/* ── Config ──────────────────────────────────────────────────────────────── */
const API = 'http://localhost:8000';

/* ── State ───────────────────────────────────────────────────────────────── */
let currentRunId   = null;
let currentEvtSrc  = null;
let logCount       = 0;
let targetType     = 'url';

/* ── Init ────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadAgents();
  document.getElementById('target-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') startRun();
  });
});

/* ── Agents ──────────────────────────────────────────────────────────────── */
async function loadAgents() {
  try {
    const res  = await fetch(`${API}/api/agents`);
    const data = await res.json();
    renderAgents(data.agents);
  } catch (e) {
    document.getElementById('agent-list').innerHTML =
      `<div class="agents-loading" style="color:var(--error)">⚠ Cannot reach backend at ${API}</div>`;
  }
}

function renderAgents(agents) {
  const list = document.getElementById('agent-list');
  list.innerHTML = '';

  agents.forEach(agent => {
    const card = document.createElement('label');
    card.className = 'agent-card selected';
    card.dataset.key = agent.key;
    card.innerHTML = `
      <input type="checkbox" value="${agent.key}" checked />
      <div class="agent-card-body">
        <div class="agent-card-label">
          <span class="agent-dot" style="background:${agent.color}"></span>
          ${agent.label}
        </div>
        <div class="agent-card-desc">${agent.description}</div>
      </div>`;

    card.querySelector('input').addEventListener('change', () => {
      card.classList.toggle('selected', card.querySelector('input').checked);
    });

    list.appendChild(card);
  });
}

function selectAll()  {
  document.querySelectorAll('.agent-card input').forEach(cb => { cb.checked = true; cb.closest('.agent-card').classList.add('selected'); });
}
function selectNone() {
  document.querySelectorAll('.agent-card input').forEach(cb => { cb.checked = false; cb.closest('.agent-card').classList.remove('selected'); });
}

/* ── Target type ─────────────────────────────────────────────────────────── */
function setTargetType(type) {
  targetType = type;
  document.querySelectorAll('.toggle-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.type === type);
  });
  const input = document.getElementById('target-input');
  const hint  = document.getElementById('target-hint');
  if (type === 'url') {
    input.placeholder = 'https://example.com';
    hint.textContent  = 'Enter a web URL to test a live site.';
  } else {
    input.placeholder = '/mnt/c/Users/panka/Documents/sms_finance_tracker';
    hint.textContent  = 'Enter an absolute path to your local project folder.';
  }
}

/* ── Run ─────────────────────────────────────────────────────────────────── */
async function startRun() {
  const target = document.getElementById('target-input').value.trim().replace(/^["']|["']$/g, '');
  if (!target) { flashInput(); return; }

  const agents = Array.from(document.querySelectorAll('.agent-card input:checked')).map(cb => cb.value);
  if (!agents.length) { alert('Select at least one test agent.'); return; }

  // Close any existing stream
  if (currentEvtSrc) { currentEvtSrc.close(); currentEvtSrc = null; }

  resetUI();
  setStatus('running', 'Starting…');
  setRunBtn(false);

  let runId;
  try {
    const res  = await fetch(`${API}/api/run`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ target, target_type: targetType, agents }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    runId = data.run_id;
    currentRunId = runId;
  } catch (e) {
    setStatus('error', `Error: ${e.message}`);
    setRunBtn(true);
    appendLog({ type: 'fatal_error', error: e.message });
    return;
  }

  openStream(runId);
}

/* ── SSE stream ──────────────────────────────────────────────────────────── */
function openStream(runId) {
  const es = new EventSource(`${API}/api/run/${runId}/stream`);
  currentEvtSrc = es;

  es.onmessage = e => {
    let event;
    try { event = JSON.parse(e.data); } catch { return; }
    handleEvent(event, runId);
  };

  es.onerror = () => {
    if (es.readyState === EventSource.CLOSED) return;
    setStatus('error', 'Connection lost.');
    setRunBtn(true);
    es.close();
  };
}

/* ── Event handler ───────────────────────────────────────────────────────── */
function handleEvent(ev, runId) {
  appendLog(ev);

  switch (ev.type) {
    case 'suite_start':
      setStatus('running', `Running ${ev.agents.length} agent${ev.agents.length > 1 ? 's' : ''}…`);
      break;

    case 'agent_start':
      setStatus('running', `${ev.label}…`);
      break;

    case 'stream_end':
      currentEvtSrc && currentEvtSrc.close();
      setStatus('done', 'All agents complete');
      setRunBtn(true);
      enableExport(true);
      if (ev.consolidated_report) renderReport(ev.consolidated_report);
      switchTab('report');
      showReportBadge();
      break;

    case 'fatal_error':
      setStatus('error', ev.error);
      setRunBtn(true);
      break;

    case 'agent_error':
      // keep running other agents
      break;
  }
}

/* ── Log ─────────────────────────────────────────────────────────────────── */
const TYPE_META = {
  suite_start:   { badge: 'SUITE',   cls: 'suite-start'  },
  agent_start:   { badge: 'START',   cls: 'agent-start'  },
  tool_call:     { badge: 'TOOL →',  cls: 'tool-call'    },
  tool_result:   { badge: '← RESULT',cls: 'tool-result'  },
  progress:      { badge: 'INFO',    cls: 'progress'     },
  agent_done:    { badge: 'DONE ✓',  cls: 'agent-done'   },
  agent_error:   { badge: 'ERROR ✗', cls: 'agent-error'  },
  stream_end:    { badge: '⚡ COMPLETE', cls: 'stream-end'},
  fatal_error:   { badge: 'FATAL',   cls: 'fatal-error'  },
};

function appendLog(ev) {
  const container = document.getElementById('log-container');

  // Remove empty state placeholder on first entry
  const empty = container.querySelector('.log-empty');
  if (empty) empty.remove();

  const meta = TYPE_META[ev.type] || { badge: ev.type.toUpperCase(), cls: 'progress' };
  const ts   = new Date().toTimeString().slice(0, 8);

  const msg  = buildLogMessage(ev);
  if (!msg) return;

  const div = document.createElement('div');
  div.className = `log-entry ${meta.cls}`;
  div.innerHTML = `
    <span class="log-ts">${ts}</span>
    <span class="log-badge">${meta.badge}</span>
    <span class="log-msg">${escHtml(msg)}</span>`;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;

  // Update count badge
  logCount++;
  document.getElementById('log-count').textContent = logCount;
}

function buildLogMessage(ev) {
  switch (ev.type) {
    case 'suite_start':   return `Target: ${ev.target} | Agents: ${(ev.agents || []).join(', ')}`;
    case 'agent_start':   return `[${ev.label}] Starting analysis…`;
    case 'tool_call':     return `  [${ev.label}] ${ev.tool}(${ev.input_preview || ''})`;
    case 'tool_result':   return `  [${ev.label}] ← ${ev.tool}: ${ev.result_preview || ''}`;
    case 'progress':      return `  [${ev.label}] ${ev.message || ''}`;
    case 'agent_done':    return `[${ev.label}] Report generated.`;
    case 'agent_error':   return `[${ev.label || ev.agent}] ERROR: ${ev.error}`;
    case 'stream_end':    return 'All agents finished. Consolidated report ready.';
    case 'fatal_error':   return `FATAL: ${ev.error}`;
    default:              return JSON.stringify(ev).slice(0, 200);
  }
}

/* ── Report ──────────────────────────────────────────────────────────────── */
function renderReport(markdown) {
  const container = document.getElementById('report-container');
  container.innerHTML = marked.parse(markdown);
}

function showReportBadge() {
  const badge = document.getElementById('report-badge');
  badge.classList.remove('hidden');
}

/* ── Export ──────────────────────────────────────────────────────────────── */
function enableExport(on) {
  document.getElementById('btn-dl-md').disabled  = !on;
  document.getElementById('btn-dl-pdf').disabled = !on;
}

async function downloadMarkdown() {
  if (!currentRunId) return;
  try {
    const res  = await fetch(`${API}/api/run/${currentRunId}/report`);
    if (!res.ok) throw new Error(await res.text());
    const text = await res.text();
    const blob = new Blob([text], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `test-report-${currentRunId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('Download failed: ' + e.message);
  }
}

function exportPDF() {
  const el = document.getElementById('report-container');
  if (!el || el.querySelector('.report-empty')) {
    alert('No report to export yet.'); return;
  }
  const opt = {
    margin:     [10, 10, 10, 10],
    filename:   `test-report-${currentRunId || 'export'}.pdf`,
    image:      { type: 'jpeg', quality: 0.95 },
    html2canvas:{ scale: 2, useCORS: true },
    jsPDF:      { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak:  { mode: ['avoid-all', 'css', 'legacy'] },
  };
  html2pdf().set(opt).from(el).save();
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
function switchTab(name) {
  ['log', 'report'].forEach(t => {
    document.getElementById(`panel-${t}`).classList.toggle('hidden', t !== name);
    document.getElementById(`tab-${t}-btn`).classList.toggle('active', t === name);
  });
}

/* ── UI helpers ──────────────────────────────────────────────────────────── */
function setStatus(state, text) {
  const dot  = document.getElementById('status-dot');
  const span = document.getElementById('status-text');
  dot.className  = `status-dot ${state}`;
  span.textContent = text;
}

function setRunBtn(enabled) {
  const btn = document.getElementById('run-btn');
  btn.disabled = !enabled;
  btn.querySelector('.run-icon').textContent = enabled ? '▶' : '⏳';
}

function resetUI() {
  logCount = 0;
  document.getElementById('log-count').textContent = '0';
  document.getElementById('log-container').innerHTML =
    '<div class="log-empty"><div class="log-empty-icon">📋</div><div>Initialising…</div></div>';
  document.getElementById('report-container').innerHTML =
    '<div class="report-empty"><div class="report-empty-icon">📄</div><div>Report will appear here when all agents complete.</div></div>';
  document.getElementById('report-badge').classList.add('hidden');
  enableExport(false);
  switchTab('log');
}

function flashInput() {
  const input = document.getElementById('target-input');
  input.style.borderColor = 'var(--error)';
  input.focus();
  setTimeout(() => { input.style.borderColor = ''; }, 1500);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
