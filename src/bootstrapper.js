let CURRENT_VERSION = '0.0.0';
const GITHUB_REPO = 'K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing';
const TOTAL_STEPS = 2;

let latestReleaseUrl = null;

const invoke = window.__TAURI__?.core?.invoke ?? (async (cmd, args) => {
    console.log('[invoke]', cmd, args);
    if (cmd === 'kill_conflicting_processes') return { killed: 0 };
    if (cmd === 'open_main_window') return true;
    return null;
});

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

const ICONS = {
    search: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    trash: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
    check: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    warn: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    'fast-forward': `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg>`,
};

function setStep(id, state, detail, icon) {
    const el = document.getElementById(`step-${id}`);
    const detEl = document.getElementById(`detail-${id}`);
    const iconEl = document.getElementById(`icon-${id}`);

    el.className = `step ${state}`;
    if (detail !== undefined) detEl.textContent = detail;
    if (icon !== undefined) iconEl.innerHTML = ICONS[icon] ?? icon;

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

async function checkForUpdates() {
    setStep('update', 'active', 'Contacting GitHub…');
    setStatus('Checking for updates…');

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
        } else {
            setStep('update', 'done', `v${CURRENT_VERSION} is up to date`, 'check');
        }
    } catch (e) {
        setStep('update', 'done', 'Could not reach update server — skipping', 'warn');
    }

    setProgress(1);
}

async function killConflictingProcesses() {
    setStep('kill', 'active', 'Scanning for running instances…');
    setStatus('Cleaning up processes…');

    try {
        const result = await invoke('kill_conflicting_processes');
        const killed = result?.killed ?? 0;
        setStep('kill', 'done',
            killed > 0 ? `Terminated ${killed} process(es)` : 'No conflicting processes found',
            killed > 0 ? 'trash' : 'check'
        );
    } catch (e) {
        setStep('kill', 'done', 'Process cleanup skipped', 'warn');
    }

    setProgress(2);
    await sleep(200);
}

async function launchApp() {
    setLaunchBtn('Launching…', false);
    setStatus('Launching…');

    const ring = document.getElementById('rippleRing');
    ring.classList.add('go');

    await sleep(200);

    try {
        await invoke('open_main_window');
    } catch (_) {
        window.location.href = 'hub.html';
    }

    setStatus('Ready', 'active');
}

async function boot() {
    CURRENT_VERSION = (await fetch('./version.json').then(r => r.json())).version;
    document.getElementById('footerVer').textContent = `v${CURRENT_VERSION}`;

    setProgress(0);
    setLaunchBtn('Preparing…', false);

    await checkForUpdates();

    if (window.__TAURI__) {
        try {
            const { check } = await import('@tauri-apps/plugin-updater');
            const update = await check();
            if (update) {
                const yes = confirm(`Update ${update.version} available. Install now?`);
                if (yes) {
                    setStatus('Downloading update…');
                    await update.downloadAndInstall();
                    return;
                }
            }
        } catch (e) {
            console.log('Update check failed:', e);
        }
    }

    await killConflictingProcesses();

    setLaunchBtn('Launch', true, true);
    setStatus('Ready to launch', 'active');
}

window.addEventListener('DOMContentLoaded', boot);