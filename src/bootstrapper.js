const CURRENT_VERSION = '2.0.1';
const GITHUB_REPO = 'K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing';

let latestReleaseUrl = null;
let backendPort = null;
let readyToLaunch = false;

    const invoke = window.__TAURI__?.core?.invoke ?? (async (cmd, args) => {
    console.log('[invoke]', cmd, args);
if (cmd === 'kill_conflicting_processes') return {killed: 0 };
if (cmd === 'start_backend') return {port: 8765 };
if (cmd === 'open_main_window') return true;
return null;
    });

function extractVersion(v) {
        const m = v.match(/(\d+\.\d+\.\d+)/);
return m ? m[1] : v;
    }

function compareVersions(v1, v2) {
        const a = extractVersion(v1).split('.').map(Number);
const b = extractVersion(v2).split('.').map(Number);
for (let i = 0; i < 3; i++) {
            if ((a[i] || 0) > (b[i] || 0)) return 1;
if ((a[i] || 0) < (b[i] || 0)) return -1;
        }
return 0;
    }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

const TOTAL_STEPS = 4;

function setStep(id, state, detail, icon) {
        const el = document.getElementById(`step-${id}`);
const detEl = document.getElementById(`detail-${id}`);
const iconEl = document.getElementById(`icon-${id}`);

el.className = `step ${state}`;
if (detail !== undefined) detEl.textContent = detail;
if (icon !== undefined) iconEl.textContent = icon;

const oldSpinner = el.querySelector('.spinner');
if (oldSpinner) oldSpinner.remove();

if (state === 'active') {
            const spinner = document.createElement('div');
spinner.className = 'spinner';
el.appendChild(spinner);
        }
    }

function setProgress(numerator) {
    document.getElementById('progressBar').style.width =
    `${Math.round((numerator / TOTAL_STEPS) * 100)}%`;
    }

function setStatus(text, dotState = 'pulse') {
    document.getElementById('statusLabel').textContent = text;
document.getElementById('statusDot').className = `sdot ${dotState}`;
    }

function setLaunchBtn(text, enabled, glowing = false) {
        const btn = document.getElementById('btnLaunch');
btn.textContent = text;
btn.disabled = !enabled;
btn.classList.toggle('ready', glowing);
    }

async function checkForUpdates() {
    setStep('update', 'active', 'Contacting GitHub…');
setStatus('Checking for updates…');

try {
            const res = await fetch(
`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`,
{signal: AbortSignal.timeout(8000) }
);
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const data = await res.json();
const latest = extractVersion(data.tag_name);
latestReleaseUrl = data.html_url;

            if (compareVersions(latest, CURRENT_VERSION) > 0) {
    document.getElementById('newVer').textContent = `v${latest}`;
document.getElementById('curVer').textContent = `v${CURRENT_VERSION}`;
document.getElementById('updateBadge').classList.add('visible');
document.getElementById('updateRow').classList.add('visible');
setStep('update', 'done', `New version v${latest} available`, '⚡');
            } else {
    setStep('update', 'done', `v${CURRENT_VERSION} is up to date`, '✅');
            }
        } catch (e) {
    setStep('update', 'done', 'Could not reach update server — skipping', '⚠️');
        }

setProgress(1);
    }

function downloadUpdate() {
        const url = latestReleaseUrl || `https://github.com/${GITHUB_REPO}/releases/latest`;
if (window.__TAURI__) {
    invoke('open_browser', { url });
        } else {
    window.open(url, '_blank');
        }
    }

function dismissUpdate() {
    document.getElementById('updateBadge').classList.remove('visible');
document.getElementById('updateRow').classList.remove('visible');
    }

async function killConflictingProcesses() {
    setStep('kill', 'active', 'Scanning for running instances…');
setStatus('Cleaning up processes…');

try {
            const result = await invoke('kill_conflicting_processes');
const killed = result?.killed ?? 0;
setStep('kill', 'done',
                killed > 0 ? `Terminated ${killed} process(es)` : 'No conflicting processes found',
                killed > 0 ? '🧹' : '✅'
);
        } catch (e) {
    setStep('kill', 'done', 'Process cleanup skipped', '⚠️');
        }

setProgress(2);
await sleep(200);
    }

async function startBackend() {
    setStep('backend', 'active', 'Spawning Python backend…');
setStatus('Starting backend…');

try {
            const result = await invoke('start_backend');
backendPort = result?.port ?? 8765;
setStep('backend', 'done', `Backend running on port ${backendPort}`, '✅');
        } catch (e) {
    backendPort = window.__BACKEND_PORT__ ?? 8765;
setStep('backend', 'done', `Using existing backend (port ${backendPort})`, '✅');
        }

setProgress(3);
await sleep(150);
    }

async function loadSettings() {
    setStep('settings', 'active', 'Waiting for backend health…');
setStatus('Loading settings…');

const MAX = 30;
let ready = false;

for (let i = 0; i < MAX; i++) {
            try {
                const res = await fetch(`http://localhost:${backendPort}/health`,
{signal: AbortSignal.timeout(1500) });
if (res.ok) {ready = true; break; }
            } catch (_) { }
setStep('settings', 'active', `Waiting for backend… (${i + 1}/${MAX})`);
await sleep(500);
        }

if (!ready) {
    setStep('settings', 'error', 'Backend did not respond in time', '❌');
setStatus('Error — backend failed', 'pulse');
setLaunchBtn('Backend Failed', false);
return false;
        }

try {
    await fetch(`http://localhost:${backendPort}/state`,
        { signal: AbortSignal.timeout(3000) });
setStep('settings', 'done', 'Settings loaded and cached', '✅');
        } catch (_) {
    setStep('settings', 'done', 'Backend ready (settings will load in app)', '✅');
        }

setProgress(4);
await sleep(150);
return true;
    }

async function launchApp() {
        if (!readyToLaunch) return;

setLaunchBtn('Launching…', false);
setStatus('Launching…');

const ring = document.getElementById('rippleRing');
ring.classList.add('go');

await sleep(200);

try {
    await invoke('open_main_window');
        } catch (_) {
    window.location.href = 'main.html';
        }

setStatus('Ready', 'active');
    }

async function boot() {
    document.getElementById('footerVer').textContent = `v${CURRENT_VERSION}`;
setProgress(0);
setLaunchBtn('Preparing…', false);

await checkForUpdates();
await killConflictingProcesses();
await startBackend();

const ok = await loadSettings();
if (!ok) return;

readyToLaunch = true;
setLaunchBtn('Launch', true, true);
setStatus('Ready to launch', 'active');
    }

window.addEventListener('DOMContentLoaded', boot);
