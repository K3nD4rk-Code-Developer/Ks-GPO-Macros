let CURRENT_VERSION = '0.0.0';
const GITHUB_REPO = 'K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing';
const TOTAL_STEPS = 2;

let latestReleaseUrl = null;
const invoke = window.__TAURI__.core.invoke;

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

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

function ts() {
    const d = new Date();
    return [d.getHours(), d.getMinutes(), d.getSeconds()]
        .map(n => String(n).padStart(2, '0')).join(':');
}

function appendLog(msg, type = '') {
    const body = document.getElementById('logBody');
    const line = document.createElement('div');
    line.className = 'log-line ' + type;
    line.innerHTML = `<span class="log-time">${ts()}</span><span class="log-msg">${msg}</span>`;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}

async function loadAndIncrementLaunches() {
    const { load } = window.__TAURI__.store;
    const store = await load('stats.json', { autoSave: true });
    const count = (await store.get('launch_count') ?? 0) + 1;
    await store.set('launch_count', count);
    document.getElementById('sysLaunches').textContent = count;
    appendLog('Launch count: ' + count, 'info');
}

function setSysinfo({ ram, ramSub, status, statusSub } = {}) {
    if (ram) document.getElementById('sysRam').textContent = ram;
    if (ramSub) document.getElementById('sysRamSub').textContent = ramSub;
    if (status) document.getElementById('sysStatus').textContent = status;
    if (statusSub) document.getElementById('sysStatusSub').textContent = statusSub;
}

async function loadMemory() {
    const result = await invoke('get_system_info');
    setSysinfo({
        ram: result.ram_available_gb.toFixed(1) + ' GB',
        ramSub: 'available'
    });
    appendLog('Memory: ' + result.ram_available_gb.toFixed(1) + ' GB available', 'info');
}

const ICONS = {
    search: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    trash: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
    check: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    warn: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    'fast-forward': `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg>`,
    x: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
};

function setStep(id, state, detail, icon) {
    const el = document.getElementById(`step-${id}`);
    const detEl = document.getElementById(`detail-${id}`);
    const iconEl = document.getElementById(`icon-${id}`);
    const tsEl = document.getElementById(`ts-${id}`);

    el.className = `step ${state}`;
    if (detail !== undefined) detEl.textContent = detail;
    if (tsEl) tsEl.textContent = ts();

    if (state === 'active') {
        iconEl.innerHTML = '<div class="spinner"></div>';
    } else if (icon !== undefined) {
        iconEl.innerHTML = ICONS[icon] ?? icon;
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

async function launchApp() {
    setLaunchBtn('Launching…', false);
    setStatus('Launching…');
    appendLog('Handing off to application…', 'info');

    const overlay = document.getElementById('flashOverlay');
    overlay.classList.add('go');

    await sleep(200);

    try {
        await invoke('open_main_window');
    } catch (_) {
        window.location.href = 'hub.html';
    }

    setTimeout(() => overlay.classList.remove('go'), 400);
    setStatus('Ready', 'active');
}

async function checkForUpdates() {
    setStep('update', 'active', 'Contacting GitHub…');
    setStatus('Checking for updates…');
    appendLog('Querying GitHub releases API…');

    try {
        const res = await fetch(
            `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`,
            { signal: AbortSignal.timeout(8000) }
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
            setStep('update', 'done', `New version v${latest} available`, 'fast-forward');
            appendLog(`Update available: v${latest}`, 'warn');
        } else {
            setStep('update', 'done', `v${CURRENT_VERSION} is up to date`, 'check');
            appendLog(`Already on latest: v${CURRENT_VERSION}`, 'ok');
            setSysinfo({ status: 'OK', statusSub: 'up to date' });
        }
    } catch (e) {
        setStep('update', 'done', 'Could not reach update server — skipping', 'warn');
        appendLog('Could not reach update server — skipping', 'warn');
    }

    setProgress(1);
}

async function killConflictingProcesses() {
    setStep('kill', 'active', 'Scanning for running instances…');
    setStatus('Cleaning up processes…');
    appendLog('Checking for stale backend processes…');

    try {
        const result = await invoke('kill_conflicting_processes');
        const killed = result?.killed ?? 0;

        setStep('kill', 'done',
            killed > 0 ? `Terminated ${killed} process(es)` : 'No conflicting processes found',
            killed > 0 ? 'trash' : 'check'
        );

        if (killed > 0) {
            appendLog(`Terminated ${killed} conflicting process(es)`, 'warn');
        } else {
            appendLog('Environment is clean', 'ok');
        }
    } catch (e) {
        setStep('kill', 'done', 'Process cleanup skipped', 'warn');
        appendLog('Process cleanup skipped', 'warn');
    }

    setProgress(2);
    await sleep(200);
}

async function boot() {
    try {
        const versionData = await fetch('./version.json').then(r => r.json());
        CURRENT_VERSION = versionData.version;
    } catch (_) { }

    document.getElementById('footerVer').textContent = `v${CURRENT_VERSION}`;
    document.getElementById('footerVerBottom').textContent = `K's Macros v${CURRENT_VERSION}`;

    setSysinfo({ ram: '—', ramSub: 'loading…', status: '—', statusSub: 'checking' });

    setProgress(0);
    setLaunchBtn('Preparing…', false);
    appendLog('Launcher started', 'info');

    await Promise.all([loadMemory(), loadAndIncrementLaunches()]);

    await checkForUpdates();

    if (window.__TAURI__) {
        try {
            const { check } = await import('@tauri-apps/plugin-updater');
            const update = await check();
            if (update) {
                const yes = confirm(`Update ${update.version} available. Install now?`);
                if (yes) {
                    setStatus('Downloading update…');
                    appendLog(`Downloading update ${update.version}…`, 'info');
                    await update.downloadAndInstall();
                    return;
                }
            }
        } catch (_) { }
    }

    await killConflictingProcesses();

    setSysinfo({ status: 'Ready', statusSub: 'all checks passed' });
    setLaunchBtn('Launch', true, true);
    setStatus('Ready to launch', 'active');
    appendLog('All checks passed — ready to launch', 'ok');
}

window.addEventListener('DOMContentLoaded', boot);