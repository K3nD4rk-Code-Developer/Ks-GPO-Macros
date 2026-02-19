const CURRENT_VERSION = '2.0.1';
const GITHUB_REPO = 'K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing';
const CLIENT_ID = getClientId();

let BackendPort = 8765;

function BackendUrl(Path) {
    return `http://localhost:${BackendPort}${Path}`;
}

async function InitBackendPort() {
    if (typeof window.__BACKEND_PORT__ !== 'undefined') {
        BackendPort = window.__BACKEND_PORT__;
        return;
    }
    const Pid = window.__LAUNCHER_PID__;
    if (Pid) {
        for (let I = 0; I < 10; I++) {
            try {
                const Res = await fetch(`./port_${Pid}.json`);
                if (Res.ok) {
                    const Data = await Res.json();
                    BackendPort = Data.port;
                    return;
                }
            } catch (_) { }
            await new Promise(R => setTimeout(R, 500));
        }
    }
}

let activeCategoryIndex = 0;
let activeSlideIndex = 0;
let lastRenderedRecipes = null;
let lastRenderedSessionsJSON = null;
let lastSessionsUpdateTime = 0;
let pollInterval;
let activeElement = null;
let skipNextUpdate = new Set();

const SLIDESHOW_DATA = [
    {
        label: "Setup",
        slides: [
            { url: "https://i.postimg.cc/SK3FDVrW/Water-Point.png", title: "Step 1 – Launch & Configure", desc: "Open the macro and set your water target point first in the Locations tab." },
            { url: "https://i.postimg.cc/hvqFqjN2/Assign-Slots.png", title: "Step 2 – Assign Hotkey Slots", desc: "Make sure your fishing rod is in the correct inventory slot, and your alternative slot too." }
        ]
    },
    {
        label: "Auto Craft",
        slides: [
            { url: "https://i.postimg.cc/QtYB62PL/Auto-Craft-Position.png", title: "Position Setup", desc: "Position where the interact with Blacksmith Sen is available and you have a clear sight of the water." },
            { url: "https://i.postimg.cc/LXj9Prpq/Auto-Craft-Left-DIalog.png", title: "Configure Left Dialog", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/GtZxf8Nr/Middle-Dialog-Option.png", title: "Configure Middle Dialog", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/qvHGXKyz/Add-Ingredient.png", title: "Configure Add Ingredient", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/ZqTFXhf4/Top-Recipe-Slot.png", title: "Configure Top Recipe Slot", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/wB0cpbZd/Click-Craft-Confirm.png", title: "Configure Craft Button", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/MZ9X4fDD/Screenshot-2026-02-14-214908.png", title: "Configure Craft Selected", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/k4GNXvPb/Menu-Close.png", title: "Configure Menu Close", desc: "Go to Locations → Crafting Interface Points and configure." },
            { url: "https://i.postimg.cc/Xqyw9NJM/Add-and-Configure-Recipes.png", title: "Add and Configure Recipes", desc: "Go to Locations and click Add Recipe, then configure the recipe location." },
            { url: "https://i.postimg.cc/MGK3VRJ1/Add.png", title: "", desc: "" }
        ]
    },
    {
        label: "Auto Buy",
        slides: [
            { url: "https://i.postimg.cc/YqDzZP5R/Position.png", title: "Position Setup", desc: "Position where Common Fish Bait Purchase interaction is available." },
            { url: "https://i.postimg.cc/PrvjvgQP/Left-Dialog-Bait.png", title: "Configure Left Dialog", desc: "Go to Locations → Bait Shop Interaction Points and configure." },
            { url: "https://i.postimg.cc/NjLp0t6S/Middle-Dialog-Bait.png", title: "Configure Middle Dialog", desc: "Go to Locations → Bait Shop Interaction Points and configure." },
            { url: "https://i.postimg.cc/W1tX4VGY/Right-Dialog-Bait.png", title: "Configure Right Dialog", desc: "Go to Locations → Bait Shop Interaction Points and configure." }
        ]
    },
    {
        label: "Auto Store",
        slides: [
            { url: "https://i.postimg.cc/cHccJwWf/Item-Store.png", title: "Set up the store location", desc: "" }
        ]
    },
    {
        label: "Auto Select",
        slides: [
            { url: "https://i.postimg.cc/wjscmSH2/Select-Top-Bait.png", title: "Enable Auto Select", desc: "Toggle 'Auto Select Top Bait' in the Automation tab." }
        ]
    }
];

function getClientId() {
    let id = localStorage.getItem('macroClientId');
    if (!id) {
        id = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('macroClientId', id);
    }
    return id;
}

async function regenerateClientId() {
    if (!confirm('This will generate a new Client ID and may disconnect this device from sync. Continue?')) return;
    localStorage.removeItem('macroClientId');
    const newId = getClientId();
    document.getElementById('clientIdDisplay').textContent = newId;
    try {
        await sendToPython('set_client_id', newId);
        showToast('Client ID regenerated. Please restart the macro.', 'warn');
    } catch (e) {
        showToast('Failed to regenerate Client ID', 'err');
    }
}

function extractVersion(v) {
    const m = v.match(/(\d+)\.(\d+)\.(\d+)/);
    return m ? m[0] : v;
}

function compareVersions(v1, v2) {
    const a = extractVersion(v1).split('.').map(Number);
    const b = extractVersion(v2).split('.').map(Number);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
        if ((a[i] || 0) > (b[i] || 0)) return 1;
        if ((a[i] || 0) < (b[i] || 0)) return -1;
    }
    return 0;
}

async function checkForUpdates() {
    try {
        const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`);
        if (!res.ok) return;
        const data = await res.json();
        const latest = extractVersion(data.tag_name);
        if (compareVersions(latest, CURRENT_VERSION) > 0) {
            document.getElementById('newVersionText').textContent = `v${latest}`;
            document.getElementById('updateBanner').classList.remove('hidden');
            window.latestReleaseUrl = data.html_url;
        }
    } catch (e) { console.error('Update check failed:', e); }
}

async function downloadUpdate() {
    const url = window.latestReleaseUrl || `https://github.com/${GITHUB_REPO}/releases/latest`;
    try {
        await fetch(BackendUrl('/command'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'open_browser', payload: url, clientId: CLIENT_ID })
        });
    } catch (e) { window.location.href = url; }
}

function dismissBanner() {
    document.getElementById('updateBanner').classList.add('hidden');
}

function checkDisclaimer() {
    if (localStorage.getItem('hideDisclaimer') === 'true') {
        document.getElementById('disclaimerModal').classList.add('hidden');
    }
}

function closeDisclaimer() {
    if (document.getElementById('dontShowAgain').checked) {
        localStorage.setItem('hideDisclaimer', 'true');
    }
    document.getElementById('disclaimerModal').classList.add('hidden');
}

function showToast(msg, type = 'warn') {
    const el = document.createElement('div');
    el.className = `notif-toast ${type}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 5000);
}

function showWarningNotification(msg) { showToast(msg, 'warn'); }
function showErrorNotification(msg) { showToast(msg, 'err'); }

function updateStatus(isRunning) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    dot.classList.toggle('active', isRunning);
    text.textContent = isRunning ? 'Active' : 'Inactive';
}

function updateHotkey(key, value) {
    const el = document.getElementById(`hotkey-${key}`);
    if (el) el.textContent = value.toUpperCase();
}

function updateRdpIndicator(isRdp, sessionState) {
    const pill = document.getElementById('rdpIndicator');
    const text = document.getElementById('rdpText');
    const stEl = document.getElementById('sessionTypeText');
    pill.classList.toggle('active', isRdp);
    text.textContent = isRdp ? (sessionState === 'connected' ? 'RDP' : 'RDP?') : 'Local';
    if (stEl) stEl.textContent = isRdp ? 'Remote Desktop' : 'Local Desktop';
}

function updatePointStatus(name, x, y) {
    const el = document.getElementById(`${name}Status`);
    if (!el) return;
    if (x != null && y != null) {
        el.textContent = `${x}, ${y}`;
        el.className = 'point-badge set';
    } else {
        el.textContent = 'Not Set';
        el.className = 'point-badge unset';
    }
}

function buildSlideshow() {
    const tabsEl = document.getElementById('slideshowTabs');
    const viewEl = document.getElementById('slideshowViewport');

    tabsEl.innerHTML = '';
    SLIDESHOW_DATA.forEach((cat, ci) => {
        const btn = document.createElement('button');
        btn.className = 'ss-tab' + (ci === 0 ? ' active' : '');
        btn.textContent = cat.label;
        btn.onclick = () => switchCategory(ci);
        tabsEl.appendChild(btn);
    });

    const prev = viewEl.querySelector('.slide-arrow.prev');
    const next = viewEl.querySelector('.slide-arrow.next');
    viewEl.querySelectorAll('.slide').forEach(s => s.remove());

    SLIDESHOW_DATA.forEach((cat, ci) => {
        cat.slides.forEach((slide, si) => {
            const div = document.createElement('div');
            div.className = 'slide';
            div.id = `slide-${ci}-${si}`;
            if (ci === 0 && si === 0) div.classList.add('visible');
            div.innerHTML = `<img src="${slide.url}" alt="${slide.title || ''}">
            <div class="slide-overlay">
              ${slide.title ? `<div class="slide-overlay-title">${slide.title}</div>` : ''}
              ${slide.desc ? `<div class="slide-overlay-desc">${slide.desc}</div>` : ''}
            </div>`;
            viewEl.insertBefore(div, prev);
        });
    });

    rebuildDots();
    prev.onclick = () => goToSlide(activeSlideIndex - 1);
    next.onclick = () => goToSlide(activeSlideIndex + 1);
}

function rebuildDots() {
    const dotsEl = document.getElementById('slideDots');
    dotsEl.innerHTML = '';
    const count = SLIDESHOW_DATA[activeCategoryIndex].slides.length;
    for (let i = 0; i < count; i++) {
        const dot = document.createElement('div');
        dot.className = 'slide-dot' + (i === activeSlideIndex ? ' active' : '');
        dot.onclick = () => goToSlide(i);
        dotsEl.appendChild(dot);
    }
}

function switchCategory(ci) {
    document.querySelectorAll('.ss-tab').forEach((t, i) => t.classList.toggle('active', i === ci));
    activeCategoryIndex = ci;
    activeSlideIndex = 0;
    showCurrentSlide();
    rebuildDots();
}

function goToSlide(idx) {
    const len = SLIDESHOW_DATA[activeCategoryIndex].slides.length;
    if (idx < 0) idx = len - 1;
    if (idx >= len) idx = 0;
    activeSlideIndex = idx;
    showCurrentSlide();
    rebuildDots();
}

function showCurrentSlide() {
    SLIDESHOW_DATA.forEach((cat, ci) =>
        cat.slides.forEach((_, si) => {
            const el = document.getElementById(`slide-${ci}-${si}`);
            if (el) el.classList.remove('visible');
        })
    );
    const target = document.getElementById(`slide-${activeCategoryIndex}-${activeSlideIndex}`);
    if (target) target.classList.add('visible');
}

function renderDevilFruitSlotSelector(selectedSlots) {
    const container = document.getElementById('devilFruitSlotSelector');
    if (!container) { setTimeout(() => renderDevilFruitSlotSelector(selectedSlots), 100); return; }
    if (!Array.isArray(selectedSlots)) selectedSlots = ['3'];
    container.innerHTML = '';
    for (let i = 0; i <= 9; i++) {
        const btn = document.createElement('button');
        btn.className = 'slot-btn' + (selectedSlots.includes(i.toString()) ? ' slot-selected' : '');
        btn.textContent = i;
        btn.onclick = () => toggleDevilFruitSlot(i.toString());
        container.appendChild(btn);
    }
}

function toggleDevilFruitSlot(slot) {
    const rodSlot = document.getElementById('rodHotkey').value;
    const secSlot = document.getElementById('anythingElseHotkey').value;
    if (slot === rodSlot) { showToast(`Slot ${slot} is used by the Fishing Rod!`, 'warn'); return; }
    if (slot === secSlot) { showToast(`Slot ${slot} is used by the Secondary Item!`, 'warn'); return; }
    let slots = window.currentDevilFruitSlots || ['3'];
    slots = slots.includes(slot) ? slots.filter(s => s !== slot) : [...slots, slot];
    if (slots.length === 0) slots = ['3'];
    window.currentDevilFruitSlots = slots;
    renderDevilFruitSlotSelector(slots);
    sendToPython('set_devil_fruit_hotkeys', slots.join(','));
}

function validateAndSetRodSlot(value) {
    const sec = document.getElementById('anythingElseHotkey').value;
    const df = window.currentDevilFruitSlots || ['3'];
    if (value === sec || df.includes(value)) {
        showToast(`Slot ${value} is already in use!`, 'warn');
        document.getElementById('rodHotkey').value = window.lastValidRodSlot || '1';
        return;
    }
    window.lastValidRodSlot = value;
    sendToPython('set_rod_hotkey', value);
}

function validateAndSetSecondarySlot(value) {
    const rod = document.getElementById('rodHotkey').value;
    const df = window.currentDevilFruitSlots || ['3'];
    if (value === rod || df.includes(value)) {
        showToast(`Slot ${value} is already in use!`, 'warn');
        document.getElementById('anythingElseHotkey').value = window.lastValidSecondarySlot || '2';
        return;
    }
    window.lastValidSecondarySlot = value;
    sendToPython('set_anything_else_hotkey', value);
}

function renderRecipes(recipes) {
    const container = document.getElementById('RecipesContainer');
    if (!container) return;
    if (JSON.stringify(recipes) === JSON.stringify(lastRenderedRecipes)) return;
    lastRenderedRecipes = JSON.parse(JSON.stringify(recipes));
    container.innerHTML = '';
    if (!recipes.length) {
        container.innerHTML = '<div class="empty-msg">No recipes configured. Click "+ Add Recipe" to get started.</div>';
        return;
    }
    recipes.forEach((r, i) => {
        const div = document.createElement('div');
        div.className = 'recipe-card';
        div.innerHTML = `
          <div class="recipe-header-row">
            <span class="recipe-title">Recipe ${i + 1}</span>
            <button class="btn-sm" onclick="removeRecipe(${i})">Remove</button>
          </div>
          <div class="row-item">
            <span class="row-label">Bait Recipe Selection</span>
            <div class="row-ctrl">
              <span class="point-badge ${r.BaitRecipePoint ? 'set' : 'unset'}">${r.BaitRecipePoint ? `${r.BaitRecipePoint.x}, ${r.BaitRecipePoint.y}` : 'Not Set'}</span>
              <button class="btn-sm" onclick="setRecipePoint(${i},'BaitRecipePoint')">Set</button>
            </div>
          </div>
          <div class="row-item">
            <span class="row-label">Select Max Button</span>
            <div class="row-ctrl">
              <span class="point-badge ${r.SelectMaxPoint ? 'set' : 'unset'}">${r.SelectMaxPoint ? `${r.SelectMaxPoint.x}, ${r.SelectMaxPoint.y}` : 'Not Set'}</span>
              <button class="btn-sm" onclick="setRecipePoint(${i},'SelectMaxPoint')">Set</button>
            </div>
          </div>
          <div class="row-item">
            <span class="row-label">Switch Fish Cycle</span>
            <div class="row-ctrl">
              <input type="number" class="inp" value="${r.SwitchFishCycle || 5}" step="1" onchange="updateRecipeValue(${i},'SwitchFishCycle',this.value)">
            </div>
          </div>`;
        container.appendChild(div);
    });
}

async function addNewRecipe() {
    try {
        const res = await fetch(BackendUrl('/add_recipe'), { method: 'POST', headers: { 'Content-Type': 'application/json' } });
        const result = await res.json();
        if (result.status === 'success') { lastRenderedRecipes = null; await pollPythonState(); }
    } catch (e) { console.error('Failed to add recipe:', e); }
}

async function removeRecipe(idx) {
    try {
        await fetch(BackendUrl('/remove_recipe'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ index: idx }) });
        await pollPythonState();
    } catch (e) { console.error('Failed to remove recipe:', e); }
}

async function setRecipePoint(idx, type) {
    try {
        await fetch(BackendUrl('/set_recipe_point'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipeIndex: idx, pointType: type }) });
    } catch (e) { console.error('Failed to set recipe point:', e); }
}

async function updateRecipeValue(idx, field, value) {
    try {
        await fetch(BackendUrl('/update_recipe_value'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipeIndex: idx, fieldName: field, value: parseInt(value) }) });
    } catch (e) { console.error('Failed to update recipe value:', e); }
}

async function checkAndToggleMegalodon() {
    const toggle = document.getElementById('megalodonSoundToggle');
    const warning = document.getElementById('megalodonAudioWarning');
    if (toggle.classList.contains('active')) {
        activeElement = toggle; skipNextUpdate.add('megalodonSoundToggle');
        toggle.classList.remove('active');
        warning.classList.add('hidden');
        sendToPython('toggle_megalodon_sound', 'false');
        setTimeout(() => { activeElement = null; skipNextUpdate.delete('megalodonSoundToggle'); }, 1000);
        return;
    }
    try {
        const res = await fetch(BackendUrl('/check_audio_device'));
        const result = await res.json();
        if (!result.found) { warning.classList.remove('hidden'); return; }
        warning.classList.add('hidden');
        activeElement = toggle; skipNextUpdate.add('megalodonSoundToggle');
        toggle.classList.add('active');
        sendToPython('toggle_megalodon_sound', 'true');
        setTimeout(() => { activeElement = null; skipNextUpdate.delete('megalodonSoundToggle'); }, 1000);
    } catch (e) {
        warning.classList.remove('hidden');
        showErrorNotification('Could not check audio device: ' + e.message);
    }
}

function toggleLoggingExpandable(toggleId, expandId) {
    const toggle = document.getElementById(toggleId);
    const section = document.getElementById(expandId);
    activeElement = toggle; skipNextUpdate.add(toggleId);
    toggle.classList.toggle('active');
    const isActive = toggle.classList.contains('active');
    section.classList.toggle('expanded', isActive);
    const nameMap = {
        'logDevilFruitToggle': 'log_devil_fruit',
        'logRecastTimeoutsToggle': 'log_recast_timeouts',
        'logPeriodicStatsToggle': 'log_periodic_stats',
        'logGeneralUpdatesToggle': 'log_general_updates',
        'logMacroStateToggle': 'log_macro_state',
        'logErrorsToggle': 'log_errors',
        'logSpawnsToggle': 'log_spawns'
    };
    const name = nameMap[toggleId];
    if (name) sendToPython(`toggle_${name}`, isActive.toString());
    setTimeout(() => { activeElement = null; skipNextUpdate.delete(toggleId); }, 1000);
}

function toggleExpandable(settingName, expandId) {
    const toggle = document.getElementById(`${settingName}Toggle`);
    const section = document.getElementById(expandId);
    activeElement = toggle; skipNextUpdate.add(`${settingName}Toggle`);
    toggle.classList.toggle('active');
    const isActive = toggle.classList.contains('active');
    section.classList.toggle('expanded', isActive);
    sendToPython(`toggle_${settingName.replace(/([A-Z])/g, '_$1').toLowerCase()}`, isActive.toString());
    setTimeout(() => { activeElement = null; skipNextUpdate.delete(`${settingName}Toggle`); }, 1000);
}

function toggleSetting(settingName) {
    const toggle = document.getElementById(`${settingName}Toggle`);
    activeElement = toggle; skipNextUpdate.add(`${settingName}Toggle`);
    toggle.classList.toggle('active');
    const isActive = toggle.classList.contains('active');
    sendToPython(`toggle_${settingName.replace(/([A-Z])/g, '_$1').toLowerCase()}`, isActive.toString());
    setTimeout(() => { activeElement = null; skipNextUpdate.delete(`${settingName}Toggle`); }, 1000);
}

function setExpandableSection(toggleId, expandId, isActive) {
    const toggle = document.getElementById(toggleId);
    const section = document.getElementById(expandId);
    if (!toggle || !section) return;
    if (activeElement === toggle || skipNextUpdate.has(toggleId)) return;
    toggle.classList.toggle('active', isActive);
    section.classList.toggle('expanded', isActive);
}

function setToggleState(id, isActive) {
    const el = document.getElementById(id);
    if (!el) return;
    if (activeElement === el || skipNextUpdate.has(id)) return;
    el.classList.toggle('active', isActive);
}

function checkRequirements(name) {
    const warn = document.getElementById(`${name}Warning`);
    const toggle = document.getElementById(`${name}Toggle`);
    if (!warn) return;
    const on = toggle && toggle.classList.contains('active');
    let missing = false;
    if (name === 'autoStoreFruit') {
        if (document.getElementById('storeFruitPointStatus')?.classList.contains('unset')) missing = true;
    }
    if (name === 'autoBuyBait') {
        ['leftPointStatus', 'middlePointStatus', 'rightPointStatus'].forEach(id => {
            if (document.getElementById(id)?.classList.contains('unset')) missing = true;
        });
    }
    if (name === 'autoCraftBait') {
        ['craftLeftPointStatus', 'craftMiddlePointStatus', 'craftButtonPointStatus', 'craftConfirmPointStatus', 'closeMenuPointStatus', 'addRecipePointStatus', 'topRecipePointStatus'].forEach(id => {
            if (document.getElementById(id)?.classList.contains('unset')) missing = true;
        });
    }
    if (name === 'autoSelectBait') {
        if (document.getElementById('baitPointStatus')?.classList.contains('unset')) missing = true;
    }
    warn.classList.toggle('hidden', !(on && missing));
}

function navigateToLocations() {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelector('[data-view="locations"]').classList.add('active');
    document.getElementById('locations').classList.add('active');
}

async function testWebhook() {
    const url = document.getElementById('webhookUrl').value;
    if (!url?.trim()) { showErrorNotification('Enter a Webhook URL first.'); return; }
    try {
        const res = await fetch(BackendUrl('/command'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'test_webhook', payload: '', clientId: CLIENT_ID })
        });
        const result = await res.json();
        if (result.status !== 'success') showErrorNotification(`Webhook test failed: ${result.message}`);
    } catch (e) { showErrorNotification('Failed to send test webhook.'); }
}

async function sendToPython(action, payload) {
    try {
        const res = await fetch(BackendUrl('/command'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, payload, clientId: CLIENT_ID })
        });
        const result = await res.json();
        if (result.status === 'error') showErrorNotification(`Error: ${result.message}`);
        return result;
    } catch (e) {
        console.error('Failed to send to Python:', e);
    }
}

function confirmResetSettings() {
    if (confirm('This will reset ALL settings to defaults. This cannot be undone. Continue?')) {
        if (confirm('Really reset everything?')) {
            sendToPython('reset_settings', 'confirm').then(async () => {
                try {
                    const res = await fetch(BackendUrl('/state'));
                    const state = await res.json();
                    loadAllSettings(state);
                    lastRenderedRecipes = null;
                    renderRecipes(state.baitRecipes || []);
                    window.currentDevilFruitSlots = state.devilFruitHotkeys || ['3'];
                    renderDevilFruitSlotSelector(window.currentDevilFruitSlots);
                    window.lastValidRodSlot = state.rodHotkey || '1';
                    window.lastValidSecondarySlot = state.anythingElseHotkey || '2';
                } catch (e) {
                    console.error('Failed to reload state after reset:', e);
                }
            });
        }
    }
}

function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (!el || document.activeElement === el) return;
    el.value = value;
}

async function loadAudioDevices() {
    try {
        const res = await fetch(BackendUrl('/get_audio_devices'));
        const data = await res.json();
        const sel = document.getElementById('audioDeviceSelect');
        if (!sel) return;
        while (sel.options.length > 2) sel.remove(2);
        if (data.devices?.length) {
            data.devices.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.name} (${d.sampleRate}Hz)`;
                opt.dataset.deviceName = d.name;
                sel.appendChild(opt);
            });
            document.getElementById('megalodonAudioWarning')?.classList.add('hidden');
        } else {
            document.getElementById('megalodonAudioWarning')?.classList.remove('hidden');
        }
    } catch (e) { console.error('Failed to load audio devices:', e); }
}

async function refreshAudioDevices() {
    await loadAudioDevices();
}

async function selectAudioDevice(value) {
    const sel = document.getElementById('audioDeviceSelect');
    const opt = sel.options[sel.selectedIndex];
    try {
        await fetch(BackendUrl('/command'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'set_audio_device',
                payload: JSON.stringify({ index: value !== 'auto' ? parseInt(value) : null, name: opt.dataset.deviceName || '' }),
                clientId: CLIENT_ID
            })
        });
    } catch (e) { showErrorNotification('Failed to set audio device'); }
}

function loadAllSettings(state) {
    if (state.hotkeys) {
        updateHotkey('start', state.hotkeys.StartStop || state.hotkeys.start_stop || 'f1');
        updateHotkey('exit', state.hotkeys.Exit || state.hotkeys.exit || 'f3');
    }
    setInputValue('rodHotkey', state.rodHotkey || '1');
    setInputValue('anythingElseHotkey', state.anythingElseHotkey || '2');
    let dfSlots = state.devilFruitHotkeys || state.devilFruitHotkey || ['3'];
    if (!Array.isArray(dfSlots)) dfSlots = [dfSlots];
    window.currentDevilFruitSlots = dfSlots;
    window.lastValidRodSlot = state.rodHotkey || '1';
    window.lastValidSecondarySlot = state.anythingElseHotkey || '2';
    renderDevilFruitSlotSelector(dfSlots);

    setToggleState('alwaysOnTopToggle', state.alwaysOnTop);
    setToggleState('debugOverlayToggle', state.showDebugOverlay);
    setToggleState('megalodonSoundToggle', state.megalodonSoundEnabled);

    setExpandableSection('enableSpawnDetectionToggle', 'spawnDetectionExpand', state.enableSpawnDetection || false);
    setExpandableSection('autoBuyBaitToggle', 'autoBuyExpand', state.autoBuyCommonBait);
    setExpandableSection('autoCraftBaitToggle', 'autoCraftExpand', state.autoCraftBait);
    setExpandableSection('autoStoreFruitToggle', 'autoStoreExpand', state.autoStoreDevilFruit);
    setToggleState('autoSelectBaitToggle', state.autoSelectTopBait);
    setToggleState('storeToBackpackToggle', state.storeToBackpack);

    setInputValue('kp', state.kp);
    setInputValue('kd', state.kd);
    setInputValue('pdClamp', state.pdClamp);
    setInputValue('pdApproaching', state.pdApproachingDamping);
    setInputValue('pdChasing', state.pdChasingDamping);
    setInputValue('gapTolerance', state.gapToleranceMultiplier);
    setInputValue('castHold', state.castHoldDuration);
    setInputValue('recastTimeout', state.recastTimeout);
    setInputValue('fishEndDelay', state.fishEndDelay);
    setInputValue('stateResend', state.stateResendInterval);
    setInputValue('loopsPerPurchase', state.loopsPerPurchase);
    setInputValue('loopsPerStore', state.loopsPerStore);
    setInputValue('moveDuration', state.moveDuration);
    setInputValue('fishCountPerCraft', state.fishCountPerCraft);
    setInputValue('focusDelay', state.robloxFocusDelay);
    setInputValue('postFocusDelay', state.robloxPostFocusDelay);
    setInputValue('preCastE', state.preCastEDelay);
    setInputValue('preCastClick', state.preCastClickDelay);
    setInputValue('preCastType', state.preCastTypeDelay);
    setInputValue('antiDetect', state.preCastAntiDetectDelay);
    setInputValue('fruitHotkey', state.storeFruitHotkeyDelay);
    setInputValue('fruitClick', state.storeFruitClickDelay);
    setInputValue('fruitShift', state.storeFruitShiftDelay);
    setInputValue('fruitBackspace', state.storeFruitBackspaceDelay);
    setInputValue('rodDelay', state.rodSelectDelay);
    setInputValue('baitDelay', state.autoSelectBaitDelay);
    setInputValue('cursorDelay', state.cursorAntiDetectDelay);
    setInputValue('scanDelay', state.scanLoopDelay);
    setInputValue('blackThreshold', state.blackScreenThreshold);
    setInputValue('spamDelay', state.antiMacroSpamDelay);
    setInputValue('craftMenuDelay', state.craftMenuOpenDelay);
    setInputValue('craftClickDelay', state.craftClickDelay);
    setInputValue('craftRecipeDelay', state.craftRecipeSelectDelay);
    setInputValue('webhookUrl', state.webhookUrl || '');
    setInputValue('discordUserId', state.discordUserId || '');
    setInputValue('soundSensitivity', state.soundSensitivity || 0.1);
    setInputValue('spawnScanInterval', state.spawnScanInterval || 5.0);

    setExpandableSection('logDevilFruitToggle', 'logDevilFruitExpand', state.logDevilFruit || false);
    setToggleState('pingDevilFruitToggle', state.pingDevilFruit || false);
    setExpandableSection('logSpawnsToggle', 'logSpawnsExpand', state.logSpawns || false);
    setToggleState('pingSpawnsToggle', state.pingSpawns || false);
    setExpandableSection('logRecastTimeoutsToggle', 'logRecastTimeoutsExpand', state.logRecastTimeouts || false);
    setToggleState('pingRecastTimeoutsToggle', state.pingRecastTimeouts || false);
    setExpandableSection('logPeriodicStatsToggle', 'logPeriodicStatsExpand', state.logPeriodicStats || false);
    setToggleState('pingPeriodicStatsToggle', state.pingPeriodicStats || false);
    setExpandableSection('logGeneralUpdatesToggle', 'logGeneralUpdatesExpand', state.logGeneralUpdates || false);
    setToggleState('pingGeneralUpdatesToggle', state.pingGeneralUpdates || false);
    setExpandableSection('logMacroStateToggle', 'logMacroStateExpand', state.logMacroState || false);
    setToggleState('pingMacroStateToggle', state.pingMacroState || false);
    setExpandableSection('logErrorsToggle', 'logErrorsExpand', state.logErrors !== false);
    setToggleState('pingErrorsToggle', state.pingErrors || false);
    setInputValue('periodicStatsInterval', state.periodicStatsInterval || 5);

    updatePointStatus('waterPoint', state.waterPoint?.x, state.waterPoint?.y);
    updatePointStatus('leftPoint', state.leftPoint?.x, state.leftPoint?.y);
    updatePointStatus('middlePoint', state.middlePoint?.x, state.middlePoint?.y);
    updatePointStatus('rightPoint', state.rightPoint?.x, state.rightPoint?.y);
    updatePointStatus('storeFruitPoint', state.storeFruitPoint?.x, state.storeFruitPoint?.y);
    updatePointStatus('baitPoint', state.baitPoint?.x, state.baitPoint?.y);
    updatePointStatus('craftLeftPoint', state.craftLeftPoint?.x, state.craftLeftPoint?.y);
    updatePointStatus('craftMiddlePoint', state.craftMiddlePoint?.x, state.craftMiddlePoint?.y);
    updatePointStatus('addRecipePoint', state.addRecipePoint?.x, state.addRecipePoint?.y);
    updatePointStatus('topRecipePoint', state.topRecipePoint?.x, state.topRecipePoint?.y);
    updatePointStatus('craftButtonPoint', state.craftButtonPoint?.x, state.craftButtonPoint?.y);
    updatePointStatus('craftConfirmPoint', state.craftConfirmPoint?.x, state.craftConfirmPoint?.y);
    updatePointStatus('closeMenuPoint', state.closeMenuPoint?.x, state.closeMenuPoint?.y);
    updatePointStatus('devilFruitLocationPoint', state.devilFruitLocationPoint?.x, state.devilFruitLocationPoint?.y);

    if (state.baitRecipes !== undefined) renderRecipes(state.baitRecipes);
}

async function loadInitialSettings() {
    const MAX_ATTEMPTS = 30;
    const RETRY_DELAY = 2000;

    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        try {
            const res = await fetch(BackendUrl('/state'));
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const state = await res.json();
            loadAllSettings(state);
            console.log(`Settings loaded on attempt ${attempt}`);
            return;
        } catch (e) {
            console.log(`Backend not ready (attempt ${attempt}/${MAX_ATTEMPTS}), retrying in ${RETRY_DELAY}ms...`);
            if (attempt < MAX_ATTEMPTS) {
                await new Promise(r => setTimeout(r, RETRY_DELAY));
            }
        }
    }
    console.error('Failed to load settings after max attempts — backend may be down.');
}

async function pollPythonState() {
    try {
        const res = await fetch(BackendUrl(`/state?clientId=${CLIENT_ID}`));
        const state = await res.json();
        updateStatus(state.isRunning);

        if (state.hotkeys) {
            updateHotkey('start', state.hotkeys.StartStop || state.hotkeys.start_stop || 'f1');
            updateHotkey('exit', state.hotkeys.Exit || state.hotkeys.exit || 'f3');
        }

        if (state.is_admin !== undefined) {
            const ind = document.getElementById('adminIndicator');
            const text = document.getElementById('adminText');
            ind.classList.toggle('active', state.is_admin);
            text.textContent = state.is_admin ? 'Running as Admin' : 'Not Admin';
        }

        const portEl = document.getElementById('backendPortDisplay');
        if (portEl) portEl.textContent = `:${BackendPort}`;

        if (state.activeSessions) renderActiveSessions(state.activeSessions);
        if (state.rdp_detected !== undefined) updateRdpIndicator(state.rdp_detected, state.rdp_session_state);
        if (state.megalodonSoundEnabled !== undefined) setToggleState('megalodonSoundToggle', state.megalodonSoundEnabled);
        if (state.soundSensitivity !== undefined) setInputValue('soundSensitivity', state.soundSensitivity);

        const clientIdEl = document.getElementById('clientIdDisplay');
        if (clientIdEl) clientIdEl.textContent = CLIENT_ID;

        setToggleState('autoDetectRdpToggle', state.auto_detect_rdp !== false);
        setExpandableSection('enableDeviceSyncToggle', 'deviceSyncExpand', state.enable_device_sync || false);
        setToggleState('syncSettingsToggle', state.sync_settings !== false);
        setToggleState('syncStatsToggle', state.sync_stats !== false);
        setToggleState('sharesFishCountToggle', state.share_fish_count || false);

        if (state.sync_interval) setInputValue('syncInterval', state.sync_interval);
        if (state.device_name) setInputValue('deviceName', state.device_name);
        if (state.enableSpawnDetection !== undefined) setExpandableSection('enableSpawnDetectionToggle', 'spawnDetectionExpand', state.enableSpawnDetection);

        updatePointStatus('waterPoint', state.waterPoint?.x, state.waterPoint?.y);
        updatePointStatus('leftPoint', state.leftPoint?.x, state.leftPoint?.y);
        updatePointStatus('middlePoint', state.middlePoint?.x, state.middlePoint?.y);
        updatePointStatus('rightPoint', state.rightPoint?.x, state.rightPoint?.y);
        updatePointStatus('storeFruitPoint', state.storeFruitPoint?.x, state.storeFruitPoint?.y);
        updatePointStatus('baitPoint', state.baitPoint?.x, state.baitPoint?.y);
        updatePointStatus('craftLeftPoint', state.craftLeftPoint?.x, state.craftLeftPoint?.y);
        updatePointStatus('craftMiddlePoint', state.craftMiddlePoint?.x, state.craftMiddlePoint?.y);
        updatePointStatus('craftConfirmPoint', state.craftConfirmPoint?.x, state.craftConfirmPoint?.y);
        updatePointStatus('closeMenuPoint', state.closeMenuPoint?.x, state.closeMenuPoint?.y);
        updatePointStatus('craftButtonPoint', state.craftButtonPoint?.x, state.craftButtonPoint?.y);
        updatePointStatus('addRecipePoint', state.addRecipePoint?.x, state.addRecipePoint?.y);
        updatePointStatus('topRecipePoint', state.topRecipePoint?.x, state.topRecipePoint?.y);
        updatePointStatus('devilFruitLocationPoint', state.devilFruitLocationPoint?.x, state.devilFruitLocationPoint?.y);

        if (state.discordUserId !== undefined) setInputValue('discordUserId', state.discordUserId);
        setInputValue('periodicStatsInterval', state.periodicStatsInterval || 5);

        ['logDevilFruit', 'logSpawns', 'logRecastTimeouts', 'logPeriodicStats', 'logGeneralUpdates', 'logMacroState', 'logErrors'].forEach(k => {
            const toggleId = `${k}Toggle`;
            const expandId = `${k}Expand`;
            if (state[k] !== undefined) setExpandableSection(toggleId, expandId, state[k]);
        });
        
        ['pingDevilFruit', 'pingSpawns', 'pingRecastTimeouts', 'pingPeriodicStats', 'pingGeneralUpdates', 'pingMacroState', 'pingErrors'].forEach(k => {
            if (state[k] !== undefined) setToggleState(`${k}Toggle`, state[k]);
        });

        if (state.baitRecipes !== undefined) renderRecipes(state.baitRecipes);
        checkRequirements('autoStoreFruit');
        checkRequirements('autoBuyBait');
        checkRequirements('autoCraftBait');
        checkRequirements('autoSelectBait');
    } catch (e) { }
}

function renderActiveSessions(sessions) {
    const container = document.getElementById('activeSessionsContainer');
    if (!container) return;
    const now = Date.now();
    if (now - lastSessionsUpdateTime < 5000) return;
    const json = JSON.stringify(sessions);
    if (json === lastRenderedSessionsJSON) { lastSessionsUpdateTime = now; return; }
    lastSessionsUpdateTime = now;
    lastRenderedSessionsJSON = json;
    const valid = sessions.filter(s => s.client_id && s.client_id !== 'unknown' && s.client_id.trim());
    if (!valid.length) { container.innerHTML = '<div class="empty-msg">No active sessions detected</div>'; return; }
    container.innerHTML = '';
    valid.sort((a, b) => (a.client_id === CLIENT_ID ? -1 : b.client_id === CLIENT_ID ? 1 : 0));
    valid.forEach(s => {
        const isSelf = s.client_id === CLIENT_ID;
        const card = document.createElement('div');
        card.className = 'device-card' + (isSelf ? ' current-client' : '');
        card.innerHTML = `
          <div class="device-row">
            <div class="device-name">${isSelf ? '★ This Device' : `Client ${s.client_id.substring(0, 12)}...`}</div>
            ${s.rdp_detected ? `<span class="device-status">RDP ${s.rdp_state}</span>` : ''}
          </div>
          <div class="device-id">ID: ${s.client_id}</div>`;
        container.appendChild(card);
    });
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollPythonState, 500);
}

function changeTheme(name) {
    document.documentElement.setAttribute('data-theme', name === 'default' ? '' : name);
    document.querySelectorAll('.theme-opt').forEach(o => o.classList.toggle('active', o.dataset.theme === name));
    localStorage.setItem('selectedTheme', name);
}

function loadSavedTheme() {
    changeTheme(localStorage.getItem('selectedTheme') || 'default');
}

async function toggleFastMode(enabled) {
    document.documentElement.setAttribute('data-perf', enabled ? 'fast' : 'normal');
    localStorage.setItem('fastMode', enabled ? 'true' : 'false');
    try {
        await fetch(BackendUrl('/set_fast_mode'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
    } catch (e) { }
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollPythonState, enabled ? 1000 : 500);
}

function loadFastMode() {
    const saved = localStorage.getItem('fastMode') === 'true';
    const toggle = document.getElementById('fastModeToggle');
    if (toggle) toggle.classList.toggle('active', saved);
    if (saved) document.documentElement.setAttribute('data-perf', 'fast');
}

window.addEventListener('DOMContentLoaded', async () => {
    await InitBackendPort();
    loadFastMode();
    loadSavedTheme();
    checkForUpdates();
    checkDisclaimer();
    buildSlideshow();
    loadAudioDevices();
    loadInitialSettings();

    setTimeout(() => {
        const c = document.getElementById('devilFruitSlotSelector');
        if (c && !c.children.length) renderDevilFruitSlotSelector(window.currentDevilFruitSlots || ['3']);
    }, 500);

    startPolling();
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.view).classList.add('active');
        });
    });
});

window.updateStatus = updateStatus;
window.updateHotkey = updateHotkey;
window.updatePointStatus = updatePointStatus;