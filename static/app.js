/* ═══════════════════════════════════════════════════════
   McEliece Cryptosystem UI — app.js
   All UI logic, API calls, and state management.
   ═══════════════════════════════════════════════════════ */

'use strict';

// ─── App State ───────────────────────────────────────────────────────────────
const appState = {
  initialized: false,
  keysGenerated: false,
  encrypted: false,
  cca2Done: false,
  niederreiterDone: false,
  isdDone: false,
  k: null,        // message length (set after init)
};

const STEP_FLAGS = ['initialized', 'keysGenerated', 'encrypted', 'cca2Done', 'niederreiterDone', 'isdDone'];
const STEP_NAV   = ['init', 'keygen', 'encdec', 'cca2', 'isd'];

// ─── Navigation ──────────────────────────────────────────────────────────────
function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const panel = document.getElementById('panel-' + name);
  const nav   = document.getElementById('nav-' + name);
  if (panel) panel.classList.add('active');
  if (nav)   nav.classList.add('active');
}

// ─── Progress bar + badges ────────────────────────────────────────────────────
function updateProgress() {
  const completed = STEP_FLAGS.filter(f => appState[f]).length;
  const pct = Math.round((completed / STEP_FLAGS.length) * 100);

  document.getElementById('workflow-progress-bar').style.width = pct + '%';
  document.getElementById('workflow-steps-text').textContent = `${completed} / ${STEP_FLAGS.length} steps completed`;

  // Nav badges
  STEP_FLAGS.forEach((flag, i) => {
    const nav   = document.getElementById('nav-' + STEP_NAV[i]);
    const badge = document.getElementById('badge-' + STEP_NAV[i]);
    if (!nav || !badge) return;
    if (appState[flag]) {
      nav.classList.add('done');
      badge.textContent = '✓';
    } else {
      nav.classList.remove('done');
      badge.textContent = String(i + 1);
    }
  });

  // Sidebar system status
  const dot  = document.getElementById('system-dot');
  const text = document.getElementById('system-status-text');
  const tb   = document.getElementById('topbar-state-badge');

  if (!appState.initialized) {
    dot.className  = 'status-dot';
    text.textContent = 'Not initialized';
    tb.innerHTML   = '<span>🔴</span> System Offline';
    tb.classList.remove('active-badge');
  } else if (!appState.keysGenerated) {
    dot.className  = 'status-dot partial';
    text.textContent = 'Awaiting key gen';
    tb.innerHTML   = '<span>🟡</span> Initialized';
    tb.classList.add('active-badge');
  } else {
    dot.className  = 'status-dot ready';
    text.textContent = 'Ready';
    tb.innerHTML   = '<span>🟢</span> Keys Active';
    tb.classList.add('active-badge');
  }
}

// ─── Toast ───────────────────────────────────────────────────────────────────
function toast(msg, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warn: '⚠️' };
  const container = document.getElementById('toast-container');

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${msg}</span>`;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('fadeout');
    el.addEventListener('animationend', () => el.remove());
  }, duration);
}

// ─── Loading helpers ──────────────────────────────────────────────────────────
function setLoading(btnId, loading, label, icon = '') {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? `<div class="spinner"></div> ${label}`
    : `${icon} ${label}`;
}

// ─── Info tiles builder ───────────────────────────────────────────────────────
function buildTiles(containerId, tiles) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = tiles.map(t => `
    <div class="info-tile">
      <div class="info-tile-label">${t.label}</div>
      <div class="info-tile-value">${t.value}</div>
      ${t.sub ? `<div class="info-tile-sub">${t.sub}</div>` : ''}
    </div>
  `).join('');
}

// ─── Terminal line builders ────────────────────────────────────────────────────
function termLine(label, value, cls = 'term-value') {
  return `<span class="term-label">${label}</span> <span class="${cls}">${value}</span>\n`;
}

function termSep(title) {
  return `<span class="term-dim">──────────────────────────────────\n${title}\n──────────────────────────────────</span>\n`;
}

function setTerminal(id, html) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('empty');
  el.innerHTML = html;
  el.scrollTop = el.scrollHeight;
}

// ─── Result badge ─────────────────────────────────────────────────────────────
function setResultBadge(containerId, success, successMsg, failMsg) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (success === null || success === undefined) { el.innerHTML = ''; return; }
  const cls  = success ? 'success' : 'failure';
  const icon = success ? '✅' : '❌';
  const msg  = success ? successMsg : failMsg;
  el.innerHTML = `<div class="result-badge ${cls}">${icon} ${msg}</div>`;
}

// ─── Short binary string for display (max 80 chars) ──────────────────────────
function shortBits(arr, max = 80) {
  if (!arr) return '—';
  const s = arr.join('');
  if (s.length <= max) return s;
  return s.slice(0, max) + `<span style="color:var(--text-muted)"> …+${s.length - max} bits</span>`;
}

// ─── API helper ──────────────────────────────────────────────────────────────
async function callAPI(endpoint, body = {}) {
  const res  = await fetch(endpoint, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  return res.json();
}

// ════════════════════════════════════════════════════════
//  INITIALIZATION
// ════════════════════════════════════════════════════════
async function runInit() {
  const m        = parseInt(document.getElementById('init-m').value) || 4;
  const primPoly = parseInt(document.getElementById('init-prim-poly').value) || 19;
  const t        = parseInt(document.getElementById('init-t').value) || 2;
  const n        = parseInt(document.getElementById('init-n').value) || 15;

  setLoading('btn-init', true, 'Initializing…');

  try {
    const data = await callAPI('/api/init', { m, prim_poly: primPoly, t, n });

    if (!data.success) {
      toast('Initialization failed: ' + data.error, 'error');
      setLoading('btn-init', false, 'Initialize System', '⚙️');
      return;
    }

    const d = data.details;
    appState.initialized   = true;
    appState.keysGenerated = false;
    appState.encrypted     = false;
    appState.k             = d.k;

    // Show result card
    document.getElementById('init-result').style.display = 'block';

    buildTiles('init-tiles', [
      { label: 'Field',       value: `GF(2<sup>${m}</sup>)`, sub: `${Math.pow(2,m)} elements` },
      { label: 'k (msg len)', value: d.k },
      { label: 'n (code)',    value: d.n },
      { label: 't (errors)',  value: d.t },
      { label: 'G shape',     value: `${d.generator_matrix_shape[0]}×${d.generator_matrix_shape[1]}` },
      { label: 'H shape',     value: `${d.parity_check_shape[0]}×${d.parity_check_shape[1]}` },
    ]);

    document.getElementById('enc-hint').textContent = `Message must be exactly k=${d.k} bits.`;

    const termHtml =
      termSep('GF(2^m) + Goppa Code Initialization') +
      termLine('Field:', `GF(2^${m})  (${Math.pow(2,m)} elements)`) +
      termLine('Primitive poly:', primPoly + ` (decimal)`) +
      termLine('t (correction):', t) +
      termLine('n (code len):', d.n) +
      termLine('k (msg len):', d.k) +
      termLine('Generator G shape:', `[${d.generator_matrix_shape.join(', ')}]`) +
      termLine('Parity-check H shape:', `[${d.parity_check_shape.join(', ')}]`) +
      termLine('Status:', '✓ Initialized successfully', 'term-success');

    setTerminal('init-terminal', termHtml);
    updateProgress();
    toast('System initialized successfully!', 'success');
  } catch (e) {
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-init', false, 'Initialize System', '⚙️');
  }
}

function resetDefaults() {
  document.getElementById('init-m').value = 4;
  document.getElementById('init-prim-poly').value = 19;
  document.getElementById('init-t').value = 2;
  document.getElementById('init-n').value = 15;
}

// ════════════════════════════════════════════════════════
//  KEY GENERATION
// ════════════════════════════════════════════════════════
async function runKeygen() {
  if (!appState.initialized) {
    toast('Initialize the system first (Step 1).', 'warn');
    return;
  }
  setLoading('btn-keygen', true, 'Generating keys…');

  try {
    const data = await callAPI('/api/generate-keys');

    if (!data.success) {
      toast('Key generation failed: ' + data.error, 'error');
      setLoading('btn-keygen', false, 'Generate Keys', '🗝️');
      return;
    }

    const d = data.details;
    appState.keysGenerated = true;
    appState.encrypted     = false;

    document.getElementById('keygen-result').style.display = 'block';

    buildTiles('keygen-tiles', [
      { label: 'G_pub rows',  value: d.public_key_shape[0], sub: 'k (message length)' },
      { label: 'G_pub cols',  value: d.public_key_shape[1], sub: 'n (code length)'    },
      { label: 't',           value: d.t,                   sub: 'error correction'   },
      { label: 'Private parts', value: '4',                 sub: 'S, G, P, goppa'     },
    ]);

    const termHtml =
      termSep('McEliece Key Generation') +
      termLine('Public Key G_pub shape:', `[${d.public_key_shape.join(' × ')}]`) +
      termLine('t:', d.t) +
      termLine('Private key components:', d.private_key_components.join(', ')) +
      termLine('Status:', '✓ Key pair generated', 'term-success');

    setTerminal('keygen-terminal', termHtml);
    updateProgress();
    toast('Key pair generated!', 'success');
  } catch (e) {
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-keygen', false, 'Generate Keys', '🗝️');
  }
}

// ════════════════════════════════════════════════════════
//  ENCRYPT
// ════════════════════════════════════════════════════════
async function runEncrypt() {
  if (!appState.keysGenerated) {
    toast('Generate keys first (Step 2).', 'warn');
    return;
  }
  const msg = document.getElementById('enc-message').value.trim();
  setLoading('btn-encrypt', true, 'Encrypting…');

  try {
    const data = await callAPI('/api/encrypt', { message: msg || null });

    if (!data.success) {
      toast('Encryption failed: ' + data.error, 'error');
      setLoading('btn-encrypt', false, 'Encrypt', '🔒');
      return;
    }

    const d = data.details;
    appState.encrypted = true;

    document.getElementById('enc-result').style.display = 'block';

    buildTiles('enc-tiles', [
      { label: 'Msg length',    value: d.original_message.length, sub: 'bits' },
      { label: 'Error weight',  value: d.error_weight },
      { label: 'Ciphertext len', value: d.ciphertext_length, sub: 'bits' },
      { label: 'Auto-gen?',    value: data.auto_generated ? 'Yes' : 'No' },
    ]);

    document.getElementById('enc-error-vec').innerHTML  = shortBits(d.error_vector);
    document.getElementById('enc-ciphertext').innerHTML = shortBits(d.ciphertext);

    if (data.auto_generated) {
      document.getElementById('enc-message').value = d.original_message_str;
    }

    // Pre-fill terminal with encrypt part — decrypt will append
    window._encTermHtml =
      termSep('McEliece Encryption') +
      termLine('Original message m:', d.original_message_str) +
      termLine('Error weight:', d.error_weight) +
      termLine('Error vector e:', shortBitsPlain(d.error_vector)) +
      termLine('Ciphertext c:', shortBitsPlain(d.ciphertext)) +
      termLine('Status:', '✓ Encryption successful', 'term-success');

    setTerminal('encdec-terminal', window._encTermHtml);
    updateProgress();
    toast('Encryption complete!', 'success');
  } catch (e) {
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-encrypt', false, 'Encrypt', '🔒');
  }
}

// ════════════════════════════════════════════════════════
//  DECRYPT
// ════════════════════════════════════════════════════════
async function runDecrypt() {
  if (!appState.encrypted) {
    toast('Encrypt a message first.', 'warn');
    return;
  }
  setLoading('btn-decrypt', true, 'Decrypting…');

  try {
    const data = await callAPI('/api/decrypt');

    if (!data.success) {
      toast('Decryption failed: ' + data.error, 'error');
      setLoading('btn-decrypt', false, 'Decrypt', '🔓');
      return;
    }

    const d = data.details;
    document.getElementById('dec-result').style.display = 'block';
    document.getElementById('dec-message').innerHTML = shortBits(d.decrypted_message);
    setResultBadge('dec-badge-wrap', d.decryption_match, 'Decryption matched original message', 'Decryption mismatch');

    const decHtml =
      termSep('McEliece Decryption') +
      termLine("Decrypted m':", d.decrypted_message_str) +
      (d.original_message ? termLine('Original m:', d.original_message.join('')) : '') +
      termLine('Match:', d.decryption_match ? '✓ SUCCESS' : '✗ FAILED',
               d.decryption_match ? 'term-success' : 'term-error');

    setTerminal('encdec-terminal', (window._encTermHtml || '') + '\n' + decHtml);
    updateProgress();
    toast(d.decryption_match ? 'Decryption verified ✓' : 'Decryption mismatch!',
          d.decryption_match ? 'success' : 'error');
  } catch (e) {
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-decrypt', false, 'Decrypt', '🔓');
  }
}

// ════════════════════════════════════════════════════════
//  CCA2
// ════════════════════════════════════════════════════════
async function runCCA2() {
  if (!appState.keysGenerated) {
    toast('Generate keys first (Step 2).', 'warn');
    return;
  }
  const msg    = document.getElementById('cca2-message').value.trim();
  const length = parseInt(document.getElementById('cca2-length').value) || 10;
  setLoading('btn-cca2', true, 'Running CCA2…');

  try {
    const data = await callAPI('/api/cca2', { message: msg || null, length });

    if (!data.success) {
      toast('CCA2 failed: ' + data.error, 'error');
      setLoading('btn-cca2', false, 'Run CCA2 Encrypt+Decrypt', '🛡️');
      return;
    }

    const d = data.details;
    appState.cca2Done = true;

    document.getElementById('cca2-result').style.display = 'block';

    buildTiles('cca2-tiles', [
      { label: 'Msg bits',   value: d.original_message.length },
      { label: 'c₁ length',  value: d.c1.length, sub: 'bits' },
      { label: 'c₂ length',  value: d.c2.length, sub: 'bits' },
      { label: 'Verification', value: d.verified ? '✓' : '✗', sub: d.verification },
    ]);

    document.getElementById('cca2-c1').innerHTML = shortBits(d.c1);
    document.getElementById('cca2-c2').innerHTML = shortBits(d.c2);
    setResultBadge('cca2-badge-wrap', d.verified, 'CCA2 integrity check PASSED', 'CCA2 integrity check FAILED');

    if (data.auto_generated) {
      document.getElementById('cca2-message').value = d.original_message_str;
    }

    const termHtml =
      termSep('CCA2 / IND-CCA2 Encryption+Decryption') +
      termLine('Original m:', d.original_message_str) +
      termLine('c₁ (McEliece enc of r):', shortBitsPlain(d.c1)) +
      termLine('c₂ (m XOR Hash(r)):', shortBitsPlain(d.c2)) +
      termLine('Decrypted m:', d.decrypted_message_str) +
      termLine('Verification:', d.verification, d.verified ? 'term-success' : 'term-error');

    setTerminal('cca2-terminal', termHtml);
    updateProgress();
    toast('CCA2 completed — ' + d.verification, d.verified ? 'success' : 'error');
  } catch (e) {
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-cca2', false, 'Run CCA2 Encrypt+Decrypt', '🛡️');
  }
}

// ════════════════════════════════════════════════════════
//  NIEDERREITER
// ════════════════════════════════════════════════════════
async function runNiederreiter() {
  if (!appState.initialized) {
    toast('Initialize the system first (Step 1).', 'warn');
    return;
  }
  setLoading('btn-niederreiter', true, 'Running Niederreiter…');

  try {
    const data = await callAPI('/api/niederreiter');

    if (!data.success) {
      toast('Niederreiter failed: ' + data.error, 'error');
      setLoading('btn-niederreiter', false, 'Run Niederreiter', '📡');
      return;
    }

    const d = data.details;
    appState.niederreiterDone = true;

    document.getElementById('niederreiter-result').style.display = 'block';

    buildTiles('nied-tiles', [
      { label: 'H_pub shape',    value: `${d.h_pub_shape[0]}×${d.h_pub_shape[1]}` },
      { label: 'Syndrome len',   value: d.syndrome_length, sub: 'bits (n−k)' },
      { label: 'Result',         value: d.decryption_match ? '✓' : '✗' },
    ]);

    document.getElementById('nied-syndrome').innerHTML    = shortBits(d.syndrome);
    document.getElementById('nied-error-orig').innerHTML  = shortBits(d.original_error_vector);
    document.getElementById('nied-error-dec').innerHTML   = shortBits(d.decrypted_error_vector);
    setResultBadge('nied-badge-wrap', d.decryption_match, 'Niederreiter decryption matched', 'Niederreiter decryption mismatch');

    const termHtml =
      termSep('Niederreiter Variant') +
      termLine('H_pub shape:', d.h_pub_shape.join(' × ')) +
      termLine('Syndrome (ciphertext):', shortBitsPlain(d.syndrome)) +
      termLine('Syndrome length:', d.syndrome_length + ' bits') +
      termLine('Original error e:', shortBitsPlain(d.original_error_vector)) +
      termLine("Decrypted error e':", shortBitsPlain(d.decrypted_error_vector)) +
      termLine('Match:', d.result, d.decryption_match ? 'term-success' : 'term-error');

    setTerminal('nied-terminal', termHtml);
    updateProgress();
    toast('Niederreiter — ' + d.result, d.decryption_match ? 'success' : 'error');
  } catch (e) {
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-niederreiter', false, 'Run Niederreiter', '📡');
  }
}

// ════════════════════════════════════════════════════════
//  ISD ATTACK
// ════════════════════════════════════════════════════════
async function runISD() {
  if (!appState.encrypted) {
    toast('Encrypt a message first (Step 3) to have a ciphertext to attack.', 'warn');
    return;
  }

  const maxIter = parseInt(document.getElementById('isd-max-iter').value) || 5000;

  setLoading('btn-isd', true, 'Running ISD Attack…');
  document.getElementById('isd-progress-wrap').classList.add('visible');
  document.getElementById('isd-result').style.display = 'none';

  try {
    const data = await callAPI('/api/isd', { max_iterations: maxIter });

    document.getElementById('isd-progress-wrap').classList.remove('visible');

    if (!data.success) {
      toast('ISD API error: ' + data.error, 'error');
      setLoading('btn-isd', false, 'Launch ISD Attack', '⚔️');
      return;
    }

    const d = data.details;
    appState.isdDone = true;

    document.getElementById('isd-result').style.display = 'block';
    const succeeded = d.status === 'SUCCESS';

    buildTiles('isd-tiles', [
      { label: 'Status',     value: succeeded ? '✓ Found' : '✗ Failed', sub: d.status },
      { label: 'Max iters',  value: maxIter },
      { label: 'Matches original', value: d.matches_original === null ? 'N/A' : (d.matches_original ? 'Yes ✓' : 'No ✗') },
    ]);

    if (succeeded && d.recovered_message) {
      document.getElementById('isd-recovered-wrap').style.display = 'block';
      document.getElementById('isd-recovered-msg').innerHTML = shortBits(d.recovered_message);
    } else {
      document.getElementById('isd-recovered-wrap').style.display = 'none';
    }

    const badgeMsg = succeeded
      ? (d.matches_original ? 'Attack succeeded — original message recovered!' : 'Attack found a valid message (no original to compare)')
      : `Attack failed after ${maxIter} iterations`;
    setResultBadge('isd-badge-wrap', succeeded, badgeMsg, badgeMsg);

    const termHtml =
      termSep("ISD Attack — Prange's Algorithm") +
      termLine('Max iterations:', maxIter) +
      termLine('Status:', d.status, succeeded ? 'term-success' : 'term-warn') +
      (succeeded ? (
        termLine('Recovered message:', shortBitsPlain(d.recovered_message)) +
        termLine('Matches original:', d.matches_original === null ? 'N/A' : String(d.matches_original),
                 d.matches_original ? 'term-success' : 'term-warn')
      ) : termLine('Result:', `No valid information set found in ${maxIter} iterations.`, 'term-warn'));

    setTerminal('isd-terminal', termHtml);
    updateProgress();
    toast(succeeded ? '⚔️ ISD Attack succeeded!' : '🛡️ ISD Attack failed — system is secure for these parameters.',
          succeeded ? 'warn' : 'success', 5000);
  } catch (e) {
    document.getElementById('isd-progress-wrap').classList.remove('visible');
    toast('Network error: ' + e.message, 'error');
  } finally {
    setLoading('btn-isd', false, 'Launch ISD Attack', '⚔️');
  }
}

// ─── Auto-fill helpers ────────────────────────────────────────────────────────
function autoFillMessage() {
  const k = appState.k;
  if (!k) { toast('Initialize system first to know message length k.', 'warn'); return; }
  const bits = Array.from({ length: k }, () => Math.random() < 0.5 ? '0' : '1').join('');
  document.getElementById('enc-message').value = bits;
}

function autoFillCCA2() {
  const len = parseInt(document.getElementById('cca2-length').value) || 10;
  const bits = Array.from({ length: len }, () => Math.random() < 0.5 ? '0' : '1').join('');
  document.getElementById('cca2-message').value = bits;
}

// ─── Plain-text bit string (for terminal — no HTML) ──────────────────────────
function shortBitsPlain(arr, max = 60) {
  if (!arr) return '—';
  const s = arr.join('');
  if (s.length <= max) return s;
  return s.slice(0, max) + `…(+${s.length - max} bits)`;
}

// ─── Init ─────────────────────────────────────────────────────────────────────
updateProgress();
