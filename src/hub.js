const invoke = window.__TAURI__?.core?.invoke ?? (async (cmd, args) => {
    console.log('[invoke]', cmd, args);
    if (cmd === 'keyauth_verify') return { success: true };
    if (cmd === 'open_macro_window') return true;
    if (cmd === 'get_saved_key') return null;
    if (cmd === 'launch_macro') return { port: window.__BACKEND_PORT__ || 8765 };
    return null;
});

const MACROS = [
    {
        id: 'fishing',
        name: 'Fishing Macro',
        desc: 'Auto-fishes with detection, cast timing, and item collection.',
        tag: 'FISHING',
        free: true,
        visible: true,
        color: '#00d4ff',
        icon: `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 16.5a2 2 0 1 1-4 0c0-1.1 2-4 2-4s2 2.9 2 4z"/><path d="M4 18h2M6 14c0 0 2-2 4-2s4 2 4 2"/><line x1="6" y1="18" x2="6" y2="10"/><line x1="6" y1="10" x2="18" y2="4"/></svg>`,
        modalIcon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 16.5a2 2 0 1 1-4 0c0-1.1 2-4 2-4s2 2.9 2 4z"/><path d="M4 18h2M6 14c0 0 2-2 4-2s4 2 4 2"/><line x1="6" y1="18" x2="6" y2="10"/><line x1="6" y1="10" x2="18" y2="4"/></svg>`,
    },
    {
        id: 'juzo',
        name: 'Juzo Macro',
        comingSoon: true,
        desc: 'Automated Juzo combat with skill rotation and targeting.',
        tag: 'JUZO',
        free: false,
        visible: true,
        color: '#a855f7',
        icon: `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`,
        modalIcon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`,
    },
    {
        id: 'mihawk',
        name: 'Mihawk Macro',
        comingSoon: true,
        desc: 'Precision Mihawk boss automation with dodge and DPS logic.',
        tag: 'MIHAWK',
        free: false,
        visible: true,
        color: '#f0c040',
        icon: `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><polyline points="8 6 18 6 18 16"/></svg>`,
        modalIcon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><polyline points="8 6 18 6 18 16"/></svg>`,
    },
    {
        id: 'roger',
        name: 'Roger Macro',
        comingSoon: true,
        desc: 'Full Roger raid loop with phase detection and auto-heal.',
        tag: 'ROGER',
        free: false,
        visible: true,
        color: '#ef4444',
        icon: `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>`,
        modalIcon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>`,
    },
];

let activeMacro = null;
let verifying = false;
let backendReady = false;

function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r},${g},${b}`;
}

function buildGrid() {
    const grid = document.getElementById('macroGrid');
    grid.innerHTML = '';

    const visible = MACROS.filter(m => m.visible);

    visible.forEach(m => {
        const rgb = hexToRgb(m.color);
        const card = document.createElement('div');
        card.className = 'macro-card';
        card.dataset.macro = m.id;
        if (m.comingSoon) {
            card.classList.add('coming-soon');
        } else {
            card.onclick = () => handleCardClick(card, m.id, m.name);
        }
        card.innerHTML = `
            <div class="card-thumb">
                <div class="card-thumb-bg" style="background:linear-gradient(135deg,#0a0c10 0%,rgba(${rgb},0.08) 100%)"></div>
                <div class="card-thumb-overlay"></div>
                <div class="card-thumb-placeholder" style="color:${m.color};opacity:0.3">${m.icon}</div>
                <div class="card-label-chip" style="background:rgba(${rgb},0.15);border-color:rgba(${rgb},0.3);color:${m.color}">${m.comingSoon ? 'COMING SOON' : m.tag + (m.free ? ' <span style=\"font-size:9px;opacity:0.7\">FREE</span>' : '')}</div>
                ${m.comingSoon ? '<div class="card-soon-overlay"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg><span>Coming Soon</span></div>' : ''}
            </div>
            <div class="card-body">
                <div class="card-title">${m.name}</div>
                <div class="card-desc">${m.comingSoon ? 'This macro is currently in development. Stay tuned.' : m.desc}</div>
            </div>
            <div class="card-footer">
                <span class="card-status-dot" style="background:${m.comingSoon ? 'var(--muted)' : m.color};box-shadow:${m.comingSoon ? 'none' : '0 0 5px ' + m.color}"></span>
                <span class="card-footer-hint">${m.comingSoon ? 'In development' : 'Click to launch'}</span>
                ${m.comingSoon ? '' : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>'}
            </div>`;
        grid.appendChild(card);
    });

    grid.style.gridTemplateColumns = `repeat(${Math.min(visible.length, 4)}, 1fr)`;
}

function setToast(text, visible) {
    const toast = document.getElementById('backendToast');
    const toastText = document.getElementById('backendToastText');
    toastText.textContent = text;
    if (visible) {
        toast.classList.add('show');
    } else {
        toast.classList.remove('show');
    }
}

async function handleCardClick(cardEl, macro_id, displayName) {
    if (cardEl.classList.contains('card-loading')) return;

    const macro = MACROS.find(m => m.id === macro_id);

    if (!macro?.free) {
        cardEl.classList.add('card-loading');
        setToast(`Loading ${displayName}…`, true);
        await new Promise(r => setTimeout(r, 700));
        setToast('', false);
        cardEl.classList.remove('card-loading');
        openKeyModal(macro_id, displayName);
        return;
    }

    cardEl.classList.add('card-loading');
    setToast('Starting backend…', true);

    try {
        await invoke('launch_macro', { macroName: macro_id });
        document.getElementById('rippleRing').classList.add('go');
        await new Promise(r => setTimeout(r, 400));
        setToast('', false);
    } catch (e) {
        console.error('launch_macro failed:', e);
        setToast(`Error: ${e?.toString().replace('Error: ', '') || 'Failed to start'}`, true);
        setTimeout(() => setToast('', false), 3000);
    } finally {
        cardEl.classList.remove('card-loading');
    }
}

async function openKeyModal(macro_id, displayName) {
    activeMacro = macro_id;
    const macro = MACROS.find(m => m.id === macro_id);

    if (macro?.free) {
        await invoke('launch_macro', { macroName: macro_id });
        document.getElementById('rippleRing').classList.add('go');
        return;
    }

    try {
        const saved = await invoke('get_saved_key', { macroName: macro_id });
        if (saved) {
            await autoLogin(macro_id, displayName, saved);
            return;
        }
    } catch (_) { }

    showModal(macro_id, displayName);
}

function applyModalColors(macro_id) {
    const macro = MACROS.find(m => m.id === macro_id);
    if (!macro) return;
    const rgb = hexToRgb(macro.color);
    const iconEl = document.getElementById('modalIcon');
    iconEl.style.background = `rgba(${rgb},0.1)`;
    iconEl.style.borderColor = `rgba(${rgb},0.25)`;
    iconEl.style.color = macro.color;
    iconEl.innerHTML = macro.modalIcon ?? '';
}

async function autoLogin(macro_id, displayName, key) {
    activeMacro = macro_id;
    applyModalColors(macro_id);

    document.getElementById('modalTitle').textContent = displayName;
    document.getElementById('modalSub').textContent = 'Verifying saved key…';
    document.getElementById('keyInputWrap').className = 'key-input-wrap';
    const inputEl = document.getElementById('keyInput');
    inputEl.value = key;
    inputEl.classList.add('masked');
    document.getElementById('keyClear').style.display = 'none';
    setFeedback('Verifying saved key…', '');
    setVerifyLoading(true);

    document.getElementById('modalBackdrop').classList.add('visible');
    document.getElementById('keyModal').classList.add('visible');

    try {
        const result = await invoke('keyauth_verify', { key, macroName: macro_id });

        if (result?.success) {
            document.getElementById('keyInputWrap').className = 'key-input-wrap success';
            setFeedback('Verified — launching…', 'success');
            await new Promise(r => setTimeout(r, 500));
            setToast('Starting backend…', true);
            await invoke('launch_macro', { macroName: macro_id });
            setToast('', false);
            document.getElementById('rippleRing').classList.add('go');
        } else {
            document.getElementById('modalSub').textContent = 'Saved key rejected — enter a new one';
            document.getElementById('keyInput').value = '';
            document.getElementById('keyInputWrap').className = 'key-input-wrap error';
            setFeedback('Saved key is invalid or expired.', 'error');
            setVerifyLoading(false);
        }
    } catch (e) {
        document.getElementById('modalSub').textContent = 'Saved key rejected — enter a new one';
        document.getElementById('keyInput').value = '';
        document.getElementById('keyInputWrap').className = 'key-input-wrap error';
        setFeedback(e?.toString().replace('Error: ', '') || 'Verification failed.', 'error');
        setVerifyLoading(false);
    }
}

function showModal(macro_id, displayName) {
    applyModalColors(macro_id);
    document.getElementById('modalTitle').textContent = displayName;
    document.getElementById('modalSub').textContent = 'Enter your license key to continue';
    document.getElementById('keyInputWrap').className = 'key-input-wrap';
    document.getElementById('keyInput').value = '';
    document.getElementById('keyClear').style.display = 'none';
    setFeedback('', '');
    setVerifyLoading(false);

    document.getElementById('modalBackdrop').classList.add('visible');
    document.getElementById('keyModal').classList.add('visible');

    setTimeout(() => document.getElementById('keyInput').focus(), 220);
}

function closeKeyModal() {
    if (verifying) return;
    document.getElementById('keyModal').classList.remove('visible');
    document.getElementById('modalBackdrop').classList.remove('visible');
    activeMacro = null;
}

function clearKey() {
    const input = document.getElementById('keyInput');
    input.value = '';
    input.classList.remove('masked');
    input.focus();
    document.getElementById('keyClear').style.display = 'none';
    document.getElementById('keyInputWrap').className = 'key-input-wrap';
    setFeedback('', '');
}

function handleKeyDown(e) {
    if (e.key === 'Enter') verifyKey();
    if (e.key === 'Escape') closeKeyModal();
    setTimeout(() => {
        const input = document.getElementById('keyInput');
        input.classList.remove('masked');
        document.getElementById('keyClear').style.display = input.value.length > 0 ? 'flex' : 'none';
    }, 0);
}

function setFeedback(msg, type) {
    const el = document.getElementById('keyFeedback');
    el.className = 'key-feedback' + (type ? ` ${type}` : '');
    el.textContent = msg;
}

function setVerifyLoading(loading) {
    verifying = loading;
    const btn = document.getElementById('btnVerify');
    const label = document.getElementById('verifyLabel');
    const spinner = document.getElementById('verifySpinner');
    btn.disabled = loading;
    label.style.display = loading ? 'none' : 'inline';
    spinner.style.display = loading ? 'block' : 'none';
}

async function verifyKey() {
    if (verifying) return;

    const key = document.getElementById('keyInput').value.trim();
    if (!key) {
        document.getElementById('keyInputWrap').className = 'key-input-wrap error';
        setFeedback('Please enter a license key.', 'error');
        return;
    }

    setVerifyLoading(true);
    setFeedback('Contacting KeyAuth…', '');
    document.getElementById('keyInputWrap').className = 'key-input-wrap';

    try {
        const result = await invoke('keyauth_verify', { key, macroName: activeMacro });

        if (result?.success) {
            document.getElementById('keyInputWrap').className = 'key-input-wrap success';
            setFeedback('Key verified — launching…', 'success');
            await new Promise(r => setTimeout(r, 600));
            setToast('Starting backend…', true);
            await invoke('launch_macro', { macroName: activeMacro });
            setToast('', false);
            document.getElementById('rippleRing').classList.add('go');
        } else {
            document.getElementById('keyInputWrap').className = 'key-input-wrap error';
            setFeedback('Invalid or expired key.', 'error');
            setVerifyLoading(false);
        }
    } catch (e) {
        document.getElementById('keyInputWrap').className = 'key-input-wrap error';
        setFeedback(e?.toString().replace('Error: ', '') || 'Verification failed.', 'error');
        setVerifyLoading(false);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    buildGrid();
    fetch('./version.json')
        .then(r => r.json())
        .then(d => { document.getElementById('hubVer').textContent = `v${d.version}`; })
        .catch(() => { });
});