const CURRENT_VERSION = '1.2.8';
const GITHUB_REPO = 'K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing';
const CLIENT_ID = getClientId();

let activeCategoryIndex = 0;
let activeSlideIndex = 0;
let lastRenderedRecipes = null;
let lastRenderedSessions = null;
let pollInterval;
let activeElement = null;
let skipNextUpdate = new Set();

const SLIDESHOW_DATA = [
    {
        label: "Setup",
        slides: [
            {
                url: "https://i.postimg.cc/SK3FDVrW/Water-Point.png",
                title: "Step 1 – Launch & Configure",
                desc: "Open the macro and set your water target point first in the Locations tab."
            },
            {
                url: "https://i.postimg.cc/hvqFqjN2/Assign-Slots.png",
                title: "Step 2 – Assign Hotkey Slots",
                desc: "Make sure your fishing rod is in the correct inventory slot, and your alternative slot too."
            },
        ]
    },
    {
        label: "Auto Craft",
        slides: [
            {
                url: "https://i.postimg.cc/QtYB62PL/Auto-Craft-Position.png",
                title: "Position Setup",
                desc: "Good in a good position where the interact with Blacksmith Sen is available, and you are close and have a clear sight of the water."
            },
            {
                url: "https://i.postimg.cc/LXj9Prpq/Auto-Craft-Left-DIalog.png",
                title: "Configure Left Dialog",
                desc: "Go to Locations tab, to Crafting Interface Points and configure."
            },
            {
                url: "https://i.postimg.cc/GtZxf8Nr/Middle-Dialog-Option.png",
                title: "Configure Middle Dialog",
                desc: "Go to Locations tab, to Crafting Interface Points and configure."
            },
            {
                url: "https://i.postimg.cc/qvHGXKyz/Add-Ingredient.png",
                title: "Configure Add Ingredient",
                desc: "Go to Locations tab, to Crafting Interface Points and configure."
            },
            {
                url: "https://i.postimg.cc/ZqTFXhf4/Top-Recipe-Slot.png",
                title: "Configure Top Recipe Slot",
                desc: "Go to Locations tab, to Crafting Interface Points and configure."
            },
            {
                url: "https://i.postimg.cc/wB0cpbZd/Click-Craft-Confirm.png",
                title: "Configure Click Craft Confirm",
                desc: "Go to Locations tab, to Crafting Interface Points and configure."
            },
            {
                url: "https://i.postimg.cc/k4GNXvPb/Menu-Close.png",
                title: "Configure Menu Close",
                desc: "Go to Locations tab, to Crafting Interface Points and configure."
            },
            {
                url: "https://i.postimg.cc/Xqyw9NJM/Add-and-Configure-Recipes.png",
                title: "Add and Configure Recipes",
                desc: "Go to Locations tab and click add recipe. Once you've done that, you may configure the location to be the location of the recipe on the craft menu."
            },
            {
                url: "https://i.postimg.cc/MGK3VRJ1/Add.png",
                title: "",
                desc: ""
            }
        ]
    },
    {
        label: "Auto Buy",
        slides: [
            {
                url: "https://i.postimg.cc/YqDzZP5R/Position.png",
                title: "Position Setup",
                desc: "Good in a good position where the interaction with Common Fish Bait Purchase is available."
            },
            {
                url: "https://i.postimg.cc/PrvjvgQP/Left-Dialog-Bait.png",
                title: "Configure Left Dialog",
                desc: "Go to Locations tab, to Bait Shop Interaction Points and configure."
            },
            {
                url: "https://i.postimg.cc/NjLp0t6S/Middle-Dialog-Bait.png",
                title: "Configure Middle Dialog",
                desc: "Go to Locations tab, to Bait Shop Interaction Points and configure."
            },
            {
                url: "https://i.postimg.cc/W1tX4VGY/Right-Dialog-Bait.png",
                title: "Configure Right Dialog",
                desc: "Go to Locations tab, to Bait Shop Interaction Points and configure."
            },
        ]
    },
    {
        label: "Auto Store",
        slides: [
            {
                url: "https://i.postimg.cc/cHccJwWf/Item-Store.png",
                title: "Set up the location for store",
                desc: ""
            },
        ]
    },
    {
        label: "Auto Select",
        slides: [
            {
                url: "https://i.postimg.cc/wjscmSH2/Select-Top-Bait.png",
                title: "Enable Auto Select",
                desc: "Toggle 'Auto Select Top Bait' in the Automation tab."
            }
        ]
    }
];

function getClientId() {
    let clientId = localStorage.getItem('macroClientId');
    if (!clientId) {
        clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('macroClientId', clientId);
    }
    return clientId;
}

async function regenerateClientId() {
    if (!confirm('This will generate a new Client ID and may disconnect this device from sync. Continue?')) {
        return;
    }

    localStorage.removeItem('macroClientId');
    const newClientId = getClientId();
    document.getElementById('clientIdDisplay').textContent = newClientId;

    try {
        await sendToPython('set_client_id', newClientId);
        showWarningNotification('Client ID regenerated. Please restart the macro.');
    } catch (error) {
        showErrorNotification('Failed to regenerate Client ID');
    }
}

function extractVersion(versionString) {
    const match = versionString.match(/(\d+)\.(\d+)\.(\d+)/);
    if (match) {
        return match[0];
    }
    return versionString;
}

function compareVersions(v1, v2) {
    const version1 = extractVersion(v1);
    const version2 = extractVersion(v2);

    const parts1 = version1.split('.').map(Number);
    const parts2 = version2.split('.').map(Number);

    for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        const part1 = parts1[i] || 0;
        const part2 = parts2[i] || 0;

        if (part1 > part2) return 1;
        if (part1 < part2) return -1;
    }

    return 0;
}

async function checkForUpdates() {
    try {
        const response = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`);

        if (!response.ok) {
            return;
        }

        const data = await response.json();
        const latestVersionRaw = data.tag_name;
        const latestVersion = extractVersion(latestVersionRaw);

        if (compareVersions(latestVersion, CURRENT_VERSION) > 0) {
            showUpdateBanner(latestVersion, data.html_url);
        }

    } catch (error) {
        console.error('Error checking for updates:', error);
    }
}

function showUpdateBanner(newVersion, downloadUrl) {
    const banner = document.getElementById('updateBanner');
    const versionText = document.getElementById('newVersionText');

    if (banner && versionText) {
        versionText.textContent = `v${newVersion}`;
        banner.style.display = 'block';
        window.latestReleaseUrl = downloadUrl;
    }
}

async function downloadUpdate() {
    const url = window.latestReleaseUrl || `https://github.com/${GITHUB_REPO}/releases/latest`;

    try {
        await fetch('http://localhost:8765/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'open_browser',
                payload: url,
                clientId: CLIENT_ID
            })
        });
    } catch (error) {
        console.error('Failed to open browser:', error);
        window.location.href = url;
    }
}

function dismissBanner() {
    const banner = document.getElementById('updateBanner');
    if (banner) {
        banner.style.animation = 'slideUp 0.3s ease-out';
        setTimeout(() => {
            banner.style.display = 'none';
        }, 300);
    }
}

function checkDisclaimer() {
    const hideDisclaimer = localStorage.getItem('hideDisclaimer');
    const modal = document.getElementById('disclaimerModal');
    if (hideDisclaimer === 'true') {
        modal.style.display = 'none';
    } else {
        modal.style.display = 'flex';
    }
}

function closeDisclaimer() {
    const dontShowAgain = document.getElementById('dontShowAgain').checked;
    if (dontShowAgain) {
        localStorage.setItem('hideDisclaimer', 'true');
    }
    document.getElementById('disclaimerModal').style.display = 'none';
}

function showWarningNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = 'position:fixed;top:80px;right:20px;background:linear-gradient(135deg,rgba(255,170,0,0.95),rgba(245,158,11,0.95));color:#111;padding:16px 24px;border-radius:12px;font-weight:600;font-size:14px;box-shadow:0 8px 32px rgba(255,170,0,0.4);z-index:10000;animation:slideInRight 0.3s ease-out;border:1px solid rgba(255,255,255,0.2);max-width:400px;word-wrap:break-word;';
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function showErrorNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = 'position:fixed;top:80px;right:20px;background:linear-gradient(135deg,rgba(255,68,102,0.95),rgba(220,38,38,0.95));color:white;padding:16px 24px;border-radius:12px;font-weight:600;font-size:14px;box-shadow:0 8px 32px rgba(255,68,102,0.4);z-index:10000;animation:slideInRight 0.3s ease-out;border:1px solid rgba(255,255,255,0.2);max-width:400px;word-wrap:break-word;';
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function updateRdpIndicator(isRdp, sessionState) {
    const indicator = document.getElementById('rdpIndicator');
    const text = document.getElementById('rdpText');
    const sessionTypeIndicator = document.getElementById('sessionTypeIndicator');
    const sessionTypeText = document.getElementById('sessionTypeText');

    if (isRdp) {
        indicator.classList.add('active');
        text.textContent = sessionState === 'connected' ? 'RDP Active' : 'RDP Disconnected';

        if (sessionTypeIndicator) {
            sessionTypeIndicator.classList.add('active');
            sessionTypeText.textContent = 'Remote Desktop Protocol';
        }
    } else {
        indicator.classList.remove('active');
        text.textContent = 'Local Session';

        if (sessionTypeText) {
            sessionTypeText.textContent = 'Local Desktop';
        }
    }
}

function updateStatus(isRunning) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (isRunning) {
        dot.classList.add('active');
        text.textContent = 'Active';
    } else {
        dot.classList.remove('active');
        text.textContent = 'Inactive';
    }
}

function updateHotkey(key, value) {
    const element = document.getElementById(`hotkey-${key}`);
    if (element) element.textContent = value.toUpperCase();
}

function updatePointStatus(pointName, x, y) {
    const status = document.getElementById(`${pointName}Status`);
    if (!status) {
        console.warn(`Point status element not found: ${pointName}Status`);
        return;
    }
    if (x !== null && y !== null && x !== undefined && y !== undefined) {
        status.textContent = `X: ${x}, Y: ${y}`;
        status.classList.remove('unset');
        status.classList.add('set');
    } else {
        status.textContent = 'Not Configured';
        status.classList.remove('set');
        status.classList.add('unset');
    }
}

function formatUptime(seconds) {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
}

function renderConnectedDevices(devices) {
    const container = document.getElementById('devicesContainer');
    if (!container) return;

    if (!devices || devices.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">No devices connected. Enable device synchronization to see connected devices.</div>';
        return;
    }

    container.innerHTML = '';
    devices.forEach((device, index) => {
        const isOnline = device.last_seen && (Date.now() - device.last_seen * 1000) < 30000;
        const deviceCard = document.createElement('div');
        deviceCard.className = 'device-card';
        deviceCard.innerHTML = `
      <div class="device-header">
        <div class="device-name">
          <i class="fas fa-desktop"></i> ${device.name || `Device ${index + 1}`}
        </div>
        <div class="device-status ${isOnline ? '' : 'offline'}">
          <div style="width: 6px; height: 6px; border-radius: 50%; background: currentColor;"></div>
          ${isOnline ? 'Online' : 'Offline'}
        </div>
      </div>
      <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 8px;">
        ID: ${device.client_id}
      </div>
      <div class="device-stats">
        <div class="device-stat">
          <div class="device-stat-label">Fish Caught</div>
          <div class="device-stat-value">${device.fish_caught || 0}</div>
        </div>
        <div class="device-stat">
          <div class="device-stat-label">Uptime</div>
          <div class="device-stat-value">${formatUptime(device.uptime || 0)}</div>
        </div>
        <div class="device-stat">
          <div class="device-stat-label">Status</div>
          <div class="device-stat-value" style="font-size: 12px;">${device.is_running ? 'Active' : 'Idle'}</div>
        </div>
      </div>
    `;
        container.appendChild(deviceCard);
    });
}

function renderActiveSessions(sessions) {
    const container = document.getElementById('activeSessionsContainer');
    if (!container) return;

    const validSessions = sessions.filter(session =>
        session.client_id &&
        session.client_id !== 'unknown' &&
        session.client_id.trim() !== ''
    );

    const sessionKey = validSessions ? validSessions.map(s =>
        `${s.client_id}-${s.is_running}`
    ).join('|') : 'empty';

    if (sessionKey === window.lastSessionKey) return;
    window.lastSessionKey = sessionKey;

    if (!validSessions || validSessions.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">No active sessions detected</div>';
        return;
    }

    container.innerHTML = '';

    validSessions.sort((a, b) => {
        if (a.client_id === CLIENT_ID) return -1;
        if (b.client_id === CLIENT_ID) return 1;
        return a.client_id.localeCompare(b.client_id);
    });

    validSessions.forEach(session => {
        const isCurrentClient = session.client_id === CLIENT_ID;
        const sessionCard = document.createElement('div');
        sessionCard.className = 'device-card';
        sessionCard.style.borderColor = isCurrentClient ? 'var(--border-accent)' : 'var(--border-subtle)';

        const displayId = session.client_id.substring(0, 16) + '...';

        sessionCard.innerHTML = `
            <div class="device-header">
                <div class="device-name">
                    ${isCurrentClient ? '<strong>This Device</strong>' : `Client ${displayId}`}
                </div>
                <div class="device-status ${session.is_running ? '' : 'offline'}">
                    <div style="width: 6px; height: 6px; border-radius: 50%; background: currentColor;"></div>
                    ${session.is_running ? 'Running' : 'Idle'}
                </div>
            </div>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 8px;">
                Client ID: ${displayId}
            </div>
            ${session.rdp_detected ? `
                <div style="margin-top: 8px;">
                    <div class="rdp-indicator active">
                        <div class="rdp-dot"></div>
                        <span>RDP ${session.rdp_state}</span>
                    </div>
                </div>
            ` : ''}
        `;
        container.appendChild(sessionCard);
    });
}

function debugSessions() {
    console.log('=== SESSION DEBUG INFO ===');
    console.log('My Client ID:', CLIENT_ID);
    console.log('Stored in localStorage:', localStorage.getItem('macroClientId'));

    fetch(`http://localhost:8765/state?clientId=${CLIENT_ID}`)
        .then(r => r.json())
        .then(state => {
            console.log('Current Active Client ID:', state.currentActiveClientId);
            console.log('Is Running:', state.isRunning);
            console.log('Active Sessions:', state.activeSessions);
            console.log('=========================');
        });
}


function buildSlideshow() {
    const tabsEl = document.getElementById('slideshowTabs');
    const viewEl = document.getElementById('slideshowViewport');
    const dotsEl = document.getElementById('slideDots');

    tabsEl.innerHTML = '';
    SLIDESHOW_DATA.forEach((cat, ci) => {
        const btn = document.createElement('button');
        btn.className = 'slideshow-tab' + (ci === 0 ? ' active' : '');
        btn.textContent = cat.label;
        btn.onclick = () => switchCategory(ci);
        tabsEl.appendChild(btn);
    });

    const prevBtn = viewEl.querySelector('.slide-nav.prev');
    const nextBtn = viewEl.querySelector('.slide-nav.next');

    viewEl.querySelectorAll('.slide').forEach(s => s.remove());

    SLIDESHOW_DATA.forEach((cat, ci) => {
        cat.slides.forEach((slide, si) => {
            const div = document.createElement('div');
            div.className = 'slide';
            div.id = `slide-${ci}-${si}`;
            if (ci === 0 && si === 0) div.classList.add('visible');

            div.innerHTML = `
          <img src="${slide.url}" alt="${slide.title || 'Guide image'}">
          <div class="slide-overlay">
            <div class="slide-overlay-inner">
              ${slide.title ? `<div class="slide-overlay-title">${slide.title}</div>` : ''}
              ${slide.desc ? `<div class="slide-overlay-desc">${slide.desc}</div>` : ''}
            </div>
          </div>`;

            viewEl.insertBefore(div, prevBtn);
        });
    });

    rebuildDots();

    prevBtn.onclick = () => goToSlide(activeSlideIndex - 1);
    nextBtn.onclick = () => goToSlide(activeSlideIndex + 1);
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
    document.querySelectorAll('.slideshow-tab').forEach((t, i) => {
        t.classList.toggle('active', i === ci);
    });
    activeCategoryIndex = ci;
    activeSlideIndex = 0;
    showCurrentSlide();
    rebuildDots();
}

function goToSlide(idx) {
    const slides = SLIDESHOW_DATA[activeCategoryIndex].slides;
    if (idx < 0) idx = slides.length - 1;
    if (idx >= slides.length) idx = 0;
    activeSlideIndex = idx;
    showCurrentSlide();
    rebuildDots();
}

function showCurrentSlide() {
    SLIDESHOW_DATA.forEach((cat, ci) => {
        cat.slides.forEach((slide, si) => {
            const slideEl = document.getElementById(`slide-${ci}-${si}`);
            if (slideEl) {
                slideEl.classList.remove('visible');
            }
        });
    });

    const target = document.getElementById(`slide-${activeCategoryIndex}-${activeSlideIndex}`);
    if (target) {
        target.classList.add('visible');
    }
}

function renderDevilFruitSlotSelector(selectedSlots) {
    const container = document.getElementById('devilFruitSlotSelector');
    if (!container) {
        setTimeout(() => renderDevilFruitSlotSelector(selectedSlots), 100);
        return;
    }
    if (!selectedSlots || !Array.isArray(selectedSlots)) selectedSlots = ['3'];
    container.innerHTML = '';
    for (let i = 0; i <= 9; i++) {
        const button = document.createElement('button');
        button.className = 'btn btn-sm slot-button';
        button.textContent = i.toString();
        const isSelected = selectedSlots.includes(i.toString());
        if (isSelected) {
            button.style.cssText = 'min-width:40px;padding:8px 12px;background:linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));border-color:var(--accent-primary);box-shadow:0 4px 15px rgba(0, 217, 255, 0.4);';
        } else {
            button.style.cssText = 'min-width:40px;padding:8px 12px;background:rgba(22, 27, 38, 0.8);box-shadow:none;border:1px solid var(--border-subtle);';
        }
        button.onclick = () => toggleDevilFruitSlot(i.toString());
        container.appendChild(button);
    }
}

function toggleDevilFruitSlot(slot) {
    const rodSlot = document.getElementById('rodHotkey').value;
    const secondarySlot = document.getElementById('anythingElseHotkey').value;

    if (slot === rodSlot) {
        showWarningNotification(`Slot ${slot} is already used by the Fishing Rod!`);
        return;
    }

    if (slot === secondarySlot) {
        showWarningNotification(`Slot ${slot} is already used by the Secondary Item!`);
        return;
    }

    let currentSlots = window.currentDevilFruitSlots || ['3'];
    if (currentSlots.includes(slot)) {
        currentSlots = currentSlots.filter(s => s !== slot);
    } else {
        currentSlots.push(slot);
    }
    if (currentSlots.length === 0) currentSlots = ['3'];
    window.currentDevilFruitSlots = currentSlots;
    renderDevilFruitSlotSelector(currentSlots);
    sendToPython('set_devil_fruit_hotkeys', currentSlots.join(','));
}

function validateAndSetRodSlot(value) {
    const secondarySlot = document.getElementById('anythingElseHotkey').value;
    const devilFruitSlots = window.currentDevilFruitSlots || ['3'];

    if (value === secondarySlot) {
        showWarningNotification(`Slot ${value} is already used by the Secondary Item!`);
        document.getElementById('rodHotkey').value = window.lastValidRodSlot || '1';
        return;
    }

    if (devilFruitSlots.includes(value)) {
        showWarningNotification(`Slot ${value} is already used by Devil Fruit slots!`);
        document.getElementById('rodHotkey').value = window.lastValidRodSlot || '1';
        return;
    }

    window.lastValidRodSlot = value;
    sendToPython('set_rod_hotkey', value);
}

function validateAndSetSecondarySlot(value) {
    const rodSlot = document.getElementById('rodHotkey').value;
    const devilFruitSlots = window.currentDevilFruitSlots || ['3'];

    if (value === rodSlot) {
        showWarningNotification(`Slot ${value} is already used by the Fishing Rod!`);
        document.getElementById('anythingElseHotkey').value = window.lastValidSecondarySlot || '2';
        return;
    }

    if (devilFruitSlots.includes(value)) {
        showWarningNotification(`Slot ${value} is already used by Devil Fruit slots!`);
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
    if (recipes.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">No recipes configured. Click "+ Add Recipe" to get started.</div>';
        return;
    }
    recipes.forEach((recipe, index) => {
        const recipeDiv = document.createElement('div');
        recipeDiv.className = 'recipe-item';
        recipeDiv.style.cssText = 'border:1px solid var(--border-subtle);border-radius:12px;padding:18px;margin-bottom:14px;background:linear-gradient(135deg, rgba(26, 32, 48, 0.5), rgba(22, 27, 38, 0.5));transition:all 0.3s ease;backdrop-filter:blur(10px);';
        recipeDiv.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <strong style="background:linear-gradient(135deg, var(--accent-primary), var(--accent-tertiary));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;font-size:14px;">Recipe ${index + 1}</strong>
        <button class="btn btn-sm btn-secondary" onclick="removeRecipe(${index})">Remove</button>
      </div>
      <div class="control-group">
        <span class="control-label">Bait Recipe Selection</span>
        <div class="control-input">
          <span class="point-indicator ${recipe.BaitRecipePoint ? 'set' : 'unset'}">
            ${recipe.BaitRecipePoint ? `X: ${recipe.BaitRecipePoint.x}, Y: ${recipe.BaitRecipePoint.y}` : 'Not Configured'}
          </span>
          <button class="btn btn-sm" onclick="setRecipePoint(${index}, 'BaitRecipePoint')">Configure</button>
        </div>
      </div>
      <div class="control-group">
        <span class="control-label">Amount of Crafts</span>
        <div class="control-input">
          <input type="number" class="input" value="${recipe.CraftsPerCycle || 40}" step="1" onchange="updateRecipeValue(${index}, 'CraftsPerCycle', this.value)">
        </div>
      </div>
      <div class="control-group">
        <span class="control-label">Switch Fish Cycle</span>
        <div class="control-input">
          <input type="number" class="input" value="${recipe.SwitchFishCycle || 5}" step="1" onchange="updateRecipeValue(${index}, 'SwitchFishCycle', this.value)">
        </div>
      </div>`;
        container.appendChild(recipeDiv);
    });
}

async function addNewRecipe() {
    try {
        const response = await fetch('http://localhost:8765/add_recipe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await response.json();
        if (result.status === 'success') {
            lastRenderedRecipes = null;
            await pollPythonState();
        }
    } catch (error) {
        console.error('Failed to add recipe:', error);
    }
}

async function removeRecipe(recipeIndex) {
    try {
        await fetch('http://localhost:8765/remove_recipe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: recipeIndex })
        });
        await pollPythonState();
    } catch (error) {
        console.error('Failed to remove recipe:', error);
    }
}

async function setRecipePoint(recipeIndex, pointType) {
    try {
        await fetch('http://localhost:8765/set_recipe_point', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipeIndex: recipeIndex, pointType: pointType })
        });
    } catch (error) {
        console.error('Failed to set recipe point:', error);
    }
}

async function updateRecipeValue(recipeIndex, fieldName, value) {
    try {
        await fetch('http://localhost:8765/update_recipe_value', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                recipeIndex: recipeIndex,
                fieldName: fieldName,
                value: parseInt(value)
            })
        });
    } catch (error) {
        console.error('Failed to update recipe value:', error);
    }
}

async function checkAndToggleMegalodon() {
    const toggle = document.getElementById('megalodonSoundToggle');
    const warning = document.getElementById('megalodonAudioWarning');

    if (toggle.classList.contains('active')) {
        activeElement = toggle;
        skipNextUpdate.add('megalodonSoundToggle');
        toggle.classList.remove('active');
        if (warning) warning.classList.remove('show');
        sendToPython('toggle_megalodon_sound', 'false');
        setTimeout(() => {
            activeElement = null;
            skipNextUpdate.delete('megalodonSoundToggle');
        }, 1000);
        return;
    }

    try {
        const response = await fetch('http://localhost:8765/check_audio_device');
        const result = await response.json();

        if (!result.found) {
            if (warning) warning.classList.add('show');
            return;
        }

        if (warning) warning.classList.remove('show');
        activeElement = toggle;
        skipNextUpdate.add('megalodonSoundToggle');
        toggle.classList.add('active');
        sendToPython('toggle_megalodon_sound', 'true');
        setTimeout(() => {
            activeElement = null;
            skipNextUpdate.delete('megalodonSoundToggle');
        }, 1000);

    } catch (error) {
        if (warning) warning.classList.add('show');
        showErrorNotification('Could not check audio device: ' + error.message);
    }
}

function toggleLoggingExpandable(toggleId, expandId) {
    const toggle = document.getElementById(toggleId);
    const section = document.getElementById(expandId);

    activeElement = toggle;
    skipNextUpdate.add(toggleId);

    toggle.classList.toggle('active');
    const isActive = toggle.classList.contains('active');

    if (isActive) {
        section.classList.add('expanded');
    } else {
        section.classList.remove('expanded');
    }

    const settingNameMap = {
        'logDevilFruitToggle': 'log_devil_fruit',
        'logRecastTimeoutsToggle': 'log_recast_timeouts',
        'logPeriodicStatsToggle': 'log_periodic_stats',
        'logGeneralUpdatesToggle': 'log_general_updates',
        'logMacroStateToggle': 'log_macro_state',
        'logErrorsToggle': 'log_errors',
        'logSpawnsToggle': 'log_spawns'
    };

    const settingName = settingNameMap[toggleId];
    if (settingName) {
        sendToPython(`toggle_${settingName}`, isActive.toString());
    }

    setTimeout(() => {
        activeElement = null;
        skipNextUpdate.delete(toggleId);
    }, 1000);
}

function toggleExpandable(settingName, expandId) {
    const toggle = document.getElementById(`${settingName}Toggle`);
    const section = document.getElementById(expandId);

    activeElement = toggle;
    skipNextUpdate.add(`${settingName}Toggle`);

    toggle.classList.toggle('active');
    const isActive = toggle.classList.contains('active');

    if (isActive) {
        section.classList.add('expanded');
    } else {
        section.classList.remove('expanded');
    }

    sendToPython(`toggle_${settingName.replace(/([A-Z])/g, '_$1').toLowerCase()}`, isActive.toString());

    setTimeout(() => {
        activeElement = null;
        skipNextUpdate.delete(`${settingName}Toggle`);
    }, 1000);
}

function toggleSetting(settingName) {
    const toggle = document.getElementById(`${settingName}Toggle`);

    activeElement = toggle;
    skipNextUpdate.add(`${settingName}Toggle`);

    toggle.classList.toggle('active');
    const isActive = toggle.classList.contains('active');

    sendToPython(`toggle_${settingName.replace(/([A-Z])/g, '_$1').toLowerCase()}`, isActive.toString());

    setTimeout(() => {
        activeElement = null;
        skipNextUpdate.delete(`${settingName}Toggle`);
    }, 1000);
}

function setExpandableSection(toggleId, expandId, isActive) {
    const toggle = document.getElementById(toggleId);
    const section = document.getElementById(expandId);
    if (!toggle || !section) {
        return;
    }

    if (activeElement === toggle || skipNextUpdate.has(toggleId)) {
        return;
    }

    if (isActive) {
        toggle.classList.add('active');
        section.classList.add('expanded');
    } else {
        toggle.classList.remove('active');
        section.classList.remove('expanded');
    }
}

function checkRequirements(settingName) {
    const warningId = `${settingName}Warning`;
    const warningEl = document.getElementById(warningId);
    const toggleEl = document.getElementById(`${settingName}Toggle`);

    if (!warningEl) return true;

    const isToggled = toggleEl && toggleEl.classList.contains('active');

    let missingRequirements = false;
    let message = '<strong>⚠️ Missing Requirements:</strong><br>';

    if (settingName === 'autoStoreFruit') {
        const storeFruitStatus = document.getElementById('storeFruitPointStatus');
        if (storeFruitStatus && storeFruitStatus.classList.contains('unset')) {
            missingRequirements = true;
            message += 'Configure Devil Fruit Store location in <a onclick="navigateToLocations()">Locations → Devil Fruit Locations</a>';
        }
    }

    if (settingName === 'autoBuyBait') {
        const leftStatus = document.getElementById('leftPointStatus');
        const middleStatus = document.getElementById('middlePointStatus');
        const rightStatus = document.getElementById('rightPointStatus');

        const missing = [];
        if (leftStatus && leftStatus.classList.contains('unset')) missing.push('Left Dialog');
        if (middleStatus && middleStatus.classList.contains('unset')) missing.push('Middle Dialog');
        if (rightStatus && rightStatus.classList.contains('unset')) missing.push('Right Dialog');

        if (missing.length > 0) {
            missingRequirements = true;
            message += `Configure ${missing.join(', ')} in <a onclick="navigateToLocations()">Locations → Bait Shop Interaction Points</a>`;
        }
    }

    if (settingName === 'autoCraftBait') {
        const points = {
            'craftLeftPointStatus': 'Left Dialog',
            'craftMiddlePointStatus': 'Middle Dialog',
            'craftButtonPointStatus': 'Craft Confirm',
            'closeMenuPointStatus': 'Menu Close',
            'addRecipePointStatus': 'Add Recipe',
            'topRecipePointStatus': 'Top Recipe Slot'
        };

        const missing = [];
        for (const [id, name] of Object.entries(points)) {
            const status = document.getElementById(id);
            if (status && status.classList.contains('unset')) missing.push(name);
        }

        if (missing.length > 0) {
            missingRequirements = true;
            message += `Configure ${missing.join(', ')} in <a onclick="navigateToLocations()">Locations → Crafting Interface Points</a>`;
        }

        const recipesContainer = document.getElementById('RecipesContainer');
        if (!recipesContainer || recipesContainer.children.length === 0 ||
            recipesContainer.textContent.includes('No recipes configured')) {
            if (!missingRequirements) {
                missingRequirements = true;
                message += 'Add at least one bait recipe in <a onclick="navigateToLocations()">Locations → Crafting Recipes</a>';
            } else {
                message += '<br>Also add at least one bait recipe in <a onclick="navigateToLocations()">Locations → Crafting Recipes</a>';
            }
        }
    }

    if (settingName === 'autoSelectBait') {
        const baitStatus = document.getElementById('baitPointStatus');
        if (baitStatus && baitStatus.classList.contains('unset')) {
            missingRequirements = true;
            message += 'Configure Top Bait Point in <a onclick="navigateToLocations()">Locations → Bait Locations</a>';
        }
    }

    if (settingName === 'enableSpawnDetection') {
        const ocrRegion = document.getElementById('enableSpawnDetectionWarning');
        if (ocrRegion && ocrRegion.dataset.ocrConfigured !== 'true') {
            missingRequirements = true;
            message += 'Configure the OCR Detection Area in <a onclick="navigateToLocations()">Locations → OCR Configuration</a>';
        }
    }

    if (isToggled && missingRequirements) {
        warningEl.innerHTML = message;
        warningEl.classList.add('show');
    } else {
        warningEl.classList.remove('show');
    }

    return !missingRequirements;
}

function navigateToLocations() {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelector('[data-view="locations"]').classList.add('active');
    document.getElementById('locations').classList.add('active');
}

async function testWebhook() {
    const webhookUrl = document.getElementById('webhookUrl').value;
    if (!webhookUrl || !webhookUrl.trim()) {
        showErrorNotification('Please enter a Webhook URL First.');
        return;
    }

    try {
        const response = await fetch('http://localhost:8765/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'test_webhook',
                payload: '',
                clientId: CLIENT_ID
            })
        });

        const result = await response.json();
        if (result.status != "success") {
            showErrorNotification(`Webhook test failed: ${result.message}`);
        }
    } catch (error) {
        showErrorNotification('Failed to send test webhook.');
    }
}

async function sendToPython(action, payload) {
    try {
        console.log('Sending to Python:', action, payload);
        const response = await fetch('http://localhost:8765/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, payload }),
            clientId: CLIENT_ID
        });
        const result = await response.json();
        if (result.status === 'error') {
            showErrorNotification(`Error: ${result.message}`);
        }
    } catch (error) {
        console.error('Failed to send to Python:', error);
        showErrorNotification(`Connection failed: ${error.message}`);
    }
}

function confirmResetSettings() {
    if (confirm('⚠️ WARNING: This will reset ALL settings to their default values.\n\nThis action cannot be undone. Are you sure you want to continue?')) {
        if (confirm('Really reset everything? Click OK to confirm.')) {
            sendToPython('reset_settings', 'confirm');
        }
    }
}

function setInputValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn(`Element not found: ${elementId}`);
        return;
    }

    if (document.activeElement === element) {
        return;
    }

    if (element.type === 'number' || element.tagName === 'INPUT') {
        element.value = value;
    } else if (element.tagName === 'SELECT') {
        element.value = value;
    }
}

function setToggleState(elementId, isActive) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn(`Toggle element not found: ${elementId}`);
        return;
    }

    if (activeElement === element || skipNextUpdate.has(elementId)) {
        return;
    }

    if (isActive) {
        element.classList.add('active');
    } else {
        element.classList.remove('active');
    }
}

function loadAllSettings(state) {
    console.log('Loading all settings from state:', state);

    if (state.hotkeys) {
        updateHotkey('start', state.hotkeys.start_stop || 'f1');
        updateHotkey('exit', state.hotkeys.exit || 'f3');
    }

    setInputValue('rodHotkey', state.rodHotkey || '1');
    setInputValue('anythingElseHotkey', state.anythingElseHotkey || '2');

    let dfSlots = state.devilFruitHotkeys || state.devilFruitHotkey || ['3'];
    if (!Array.isArray(dfSlots)) dfSlots = [dfSlots];
    window.currentDevilFruitSlots = dfSlots;
    setTimeout(() => renderDevilFruitSlotSelector(dfSlots), 100);

    setToggleState('alwaysOnTopToggle', state.alwaysOnTop);
    setToggleState('debugOverlayToggle', state.showDebugOverlay);
    setToggleState('megalodonSoundToggle', state.megalodonSoundEnabled);

    // FIX: use setExpandableSection so the panel opens when the setting is saved as true
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
    setInputValue('craftsPerCycle', state.craftsPerCycle);
    setInputValue('loopsPerCraft', state.loopsPerCraft);
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
    setInputValue('soundSensitivity', state.soundSensitivity || 0.7);
    setInputValue('spawnScanInterval', state.spawnScanInterval || 2.0);

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
    updatePointStatus('baitRecipePoint', state.baitRecipePoint?.x, state.baitRecipePoint?.y);
    updatePointStatus('topRecipePoint', state.topRecipePoint?.x, state.topRecipePoint?.y);
    updatePointStatus('craftButtonPoint', state.craftButtonPoint?.x, state.craftButtonPoint?.y);
    updatePointStatus('closeMenuPoint', state.closeMenuPoint?.x, state.closeMenuPoint?.y);
    updatePointStatus('addRecipePoint', state.addRecipePoint?.x, state.addRecipePoint?.y);
    updatePointStatus('devilFruitLocationPoint', state.devilFruitLocationPoint?.x, state.devilFruitLocationPoint?.y);

    if (state.baitRecipes !== undefined) renderRecipes(state.baitRecipes);

    console.log('All settings loaded successfully');
}

async function loadInitialSettings() {
    try {
        const response = await fetch('http://localhost:8765/state');
        const state = await response.json();
        console.log('Loaded initial state:', state);
        loadAllSettings(state);
    } catch (error) {
        console.error('Failed to load initial settings:', error);
    }
}

async function pollPythonState() {
    try {
        const response = await fetch(`http://localhost:8765/state?clientId=${CLIENT_ID}`);
        const state = await response.json();

        const isThisClientActive = state.currentActiveClientId === CLIENT_ID && state.isRunning;
        updateStatus(isThisClientActive);

        if (state.hotkeys) {
            updateHotkey('start', state.hotkeys.StartStop || state.hotkeys.start_stop || 'f1');
            updateHotkey('exit', state.hotkeys.Exit || state.hotkeys.exit || 'f3');
        }

        if (state.activeSessions) {
            renderActiveSessions(state.activeSessions);
        }

        if (state.rdp_detected !== undefined) {
            updateRdpIndicator(state.rdp_detected, state.rdp_session_state);
        }

        if (state.connected_devices) {
            renderConnectedDevices(state.connected_devices);
        }

        if (state.enableSpawnDetection !== undefined) {
            setExpandableSection('enableSpawnDetectionToggle', 'spawnDetectionExpand', state.enableSpawnDetection);
        }

        if (state.logSpawns !== undefined) {
            setExpandableSection('logSpawnsToggle', 'logSpawnsExpand', state.logSpawns);
        }
        if (state.pingSpawns !== undefined) {
            setToggleState('pingSpawnsToggle', state.pingSpawns);
        }

        if (state.is_syncing) {
            const syncStatus = document.getElementById('syncStatus');
            if (syncStatus) syncStatus.style.display = 'flex';
        } else {
            const syncStatus = document.getElementById('syncStatus');
            if (syncStatus) syncStatus.style.display = 'none';
        }

        if (state.device_name && document.getElementById('deviceName')) {
            document.getElementById('deviceName').value = state.device_name;
        }

        if (state.megalodonSoundEnabled !== undefined) {
            setToggleState('megalodonSoundToggle', state.megalodonSoundEnabled);
            if (!state.megalodonSoundEnabled) {
                const megWarning = document.getElementById('megalodonAudioWarning');
                if (megWarning) megWarning.classList.remove('show');
            }
        }

        if (state.soundSensitivity !== undefined) {
            setInputValue('soundSensitivity', state.soundSensitivity);
        }

        const clientIdDisplay = document.getElementById('clientIdDisplay');
        if (clientIdDisplay) {
            clientIdDisplay.textContent = CLIENT_ID;
        }

        setToggleState('autoDetectRdpToggle', state.auto_detect_rdp !== false);

        setToggleState('enableDeviceSyncToggle', state.enable_device_sync || false);
        setExpandableSection('enableDeviceSyncToggle', 'deviceSyncExpand', state.enable_device_sync || false);
        setToggleState('syncSettingsToggle', state.sync_settings !== false);
        setToggleState('syncStatsToggle', state.sync_stats !== false);
        setToggleState('sharesFishCountToggle', state.share_fish_count || false);

        if (state.sync_interval && document.getElementById('syncInterval')) {
            document.getElementById('syncInterval').value = state.sync_interval;
        }

        if (state.baitRecipes !== undefined) renderRecipes(state.baitRecipes);

        updatePointStatus('waterPoint', state.waterPoint?.x, state.waterPoint?.y);
        updatePointStatus('leftPoint', state.leftPoint?.x, state.leftPoint?.y);
        updatePointStatus('middlePoint', state.middlePoint?.x, state.middlePoint?.y);
        updatePointStatus('rightPoint', state.rightPoint?.x, state.rightPoint?.y);
        updatePointStatus('storeFruitPoint', state.storeFruitPoint?.x, state.storeFruitPoint?.y);
        updatePointStatus('baitPoint', state.baitPoint?.x, state.baitPoint?.y);
        updatePointStatus('craftLeftPoint', state.craftLeftPoint?.x, state.craftLeftPoint?.y);
        updatePointStatus('craftMiddlePoint', state.craftMiddlePoint?.x, state.craftMiddlePoint?.y);
        updatePointStatus('closeMenuPoint', state.closeMenuPoint?.x, state.closeMenuPoint?.y);
        updatePointStatus('devilFruitLocationPoint', state.devilFruitLocationPoint?.x, state.devilFruitLocationPoint?.y);
        updatePointStatus('craftButtonPoint', state.craftButtonPoint?.x, state.craftButtonPoint?.y);
        updatePointStatus('addRecipePoint', state.addRecipePoint?.x, state.addRecipePoint?.y);
        updatePointStatus('topRecipePoint', state.topRecipePoint?.x, state.topRecipePoint?.y);

        if (state.discordUserId !== undefined && document.getElementById('discordUserId')) {
            setInputValue('discordUserId', state.discordUserId);
        }

        if (state.logDevilFruit !== undefined) {
            setExpandableSection('logDevilFruitToggle', 'logDevilFruitExpand', state.logDevilFruit);
        }
        if (state.pingDevilFruit !== undefined) {
            setToggleState('pingDevilFruitToggle', state.pingDevilFruit);
        }

        if (state.logRecastTimeouts !== undefined) {
            setExpandableSection('logRecastTimeoutsToggle', 'logRecastTimeoutsExpand', state.logRecastTimeouts);
        }
        if (state.pingRecastTimeouts !== undefined) {
            setToggleState('pingRecastTimeoutsToggle', state.pingRecastTimeouts);
        }

        if (state.logPeriodicStats !== undefined) {
            setExpandableSection('logPeriodicStatsToggle', 'logPeriodicStatsExpand', state.logPeriodicStats);
        }
        if (state.pingPeriodicStats !== undefined) {
            setToggleState('pingPeriodicStatsToggle', state.pingPeriodicStats);
        }

        if (state.logGeneralUpdates !== undefined) {
            setExpandableSection('logGeneralUpdatesToggle', 'logGeneralUpdatesExpand', state.logGeneralUpdates);
        }
        if (state.pingGeneralUpdates !== undefined) {
            setToggleState('pingGeneralUpdatesToggle', state.pingGeneralUpdates);
        }

        if (state.logMacroState !== undefined) {
            setExpandableSection('logMacroStateToggle', 'logMacroStateExpand', state.logMacroState);
        }
        if (state.pingMacroState !== undefined) {
            setToggleState('pingMacroStateToggle', state.pingMacroState);
        }

        if (state.logErrors !== undefined) {
            setExpandableSection('logErrorsToggle', 'logErrorsExpand', state.logErrors);
        }
        if (state.pingErrors !== undefined) {
            setToggleState('pingErrorsToggle', state.pingErrors);
        }

        setInputValue('periodicStatsInterval', state.periodicStatsInterval || 5);

        checkRequirements('autoStoreFruit');
        checkRequirements('autoBuyBait');
        checkRequirements('autoCraftBait');
        checkRequirements('autoSelectBait');

    } catch (error) {
        console.error('Failed to poll state:', error);
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollPythonState, 500);
}

window.addEventListener('DOMContentLoaded', () => {
    checkForUpdates();
    checkDisclaimer();
    buildSlideshow();
    loadInitialSettings();

    setTimeout(() => {
        const container = document.getElementById('devilFruitSlotSelector');
        if (container && container.children.length === 0) {
            renderDevilFruitSlotSelector(window.currentDevilFruitSlots || ['3']);
        }
    }, 500);

    startPolling();

    document.querySelectorAll('.nav-item').forEach(nav => {
        nav.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            nav.classList.add('active');
            document.getElementById(nav.dataset.view).classList.add('active');
            setTimeout(() => lucide.createIcons(), 100);
        });
    });

    lucide.createIcons();
});

window.updateStatus = updateStatus;
window.updateHotkey = updateHotkey;
window.updatePointStatus = updatePointStatus;