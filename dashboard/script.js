// ==========================================
// 1. UI RENDER LOGIC (Flicker-Free)
// ==========================================
async function fetchApps() {
    try {
        const response = await fetch('/api/apps');
        const apps = await response.json();
        const container = document.getElementById('app-list');

        // Clear loading text on first successful fetch
        if (container.querySelector('.loading-text')) {
            container.innerHTML = '';
        }

        const activeAppNames = new Set(apps.map(a => a.name));

        for (const app of apps) {
            // -- Fetch RAM Telemetry --
            let statsHtml = 'Waiting for telemetry...';
            if (app.status === 'running' && app.name !== 'paas-proxy') {
                const statRes = await fetch(`/api/apps/${app.name}/stats`);
                const stats = await statRes.json();
                
                if (!stats.error) {
                    const percentage = Math.min((stats.usage_mb / stats.limit_mb) * 100, 100).toFixed(1);
                    statsHtml = `
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <strong>RAM Usage</strong>
                            <span>${stats.usage_mb} MB / ${stats.limit_mb} MB</span>
                        </div>
                        <div class="ram-bar-bg">
                            <div class="ram-bar-fill" style="width: ${percentage}%;"></div>
                        </div>
                    `;
                }
            } else if (app.name === 'paas-proxy') {
                statsHtml = '<div style="display: flex; align-items: center; height: 100%;">Infrastructure Router (Stats Hidden)</div>';
            } else {
                statsHtml = '<div style="display: flex; align-items: center; height: 100%; color: #ef4444;">Container is currently offline.</div>';
            }

            // -- Build Control Buttons --
            let powerBtn = app.status === 'running' 
                ? `<button class="btn-pause" onclick="toggleApp('${app.name}', 'stop')">Pause</button>`
                : `<button class="btn-start" onclick="toggleApp('${app.name}', 'start')">Start</button>`;

            let extraTools = '';
            if (app.name !== 'paas-proxy') {
                extraTools = `
                    <button class="btn-secret" onclick="saveSecret('${app.name}')">🔑 Add Secret</button>
                    <button class="btn-delete" onclick="nukeApp('${app.name}')">Delete</button>
                `;
            } else {
                extraTools = `<div style="flex: 1; text-align: right; font-size: 12px; color: var(--text-muted); align-self: center;">Core Infrastructure</div>`;
            }

            // -- Construct Card HTML --
            const cardInnerHtml = `
                <div class="card-header">
                    <div>
                        <div class="app-title">${app.name}</div>
                        <div class="app-image">${app.image}</div>
                    </div>
                    <div class="status-badge ${app.status === 'running' ? 'running' : 'exited'}">
                        ${app.status}
                    </div>
                </div>
                <div class="stats-container">
                    ${statsHtml}
                </div>
                <div class="actions">
                    ${powerBtn}
                    ${extraTools}
                </div>
            `;

            // -- Smart DOM Update --
            let existingCard = document.getElementById(`card-${app.name}`);
            if (existingCard) {
                // Update existing card silently
                existingCard.innerHTML = cardInnerHtml;
                existingCard.style.borderColor = app.status === 'running' ? 'var(--border-color)' : 'rgba(239, 68, 68, 0.4)';
            } else {
                // Create brand new card
                let newCard = document.createElement('div');
                newCard.id = `card-${app.name}`;
                newCard.className = "app-card";
                newCard.style.borderColor = app.status === 'running' ? 'var(--border-color)' : 'rgba(239, 68, 68, 0.4)';
                newCard.innerHTML = cardInnerHtml;
                container.appendChild(newCard);
            }
        }

        // -- Cleanup Old/Deleted Apps --
        Array.from(container.children).forEach(childElement => {
            if (childElement.id && childElement.id.startsWith('card-')) {
                const appName = childElement.id.replace('card-', '');
                if (!activeAppNames.has(appName)) {
                    childElement.remove();
                }
            }
        });

    } catch (error) {
        // Silently wait if the FastAPI backend is momentarily rebooting
    }
}

// ==========================================
// 2. API ACTION LOGIC
// ==========================================
async function toggleApp(appName, action) {
    await fetch(`/api/apps/${appName}/${action}`, { method: 'POST' });
    fetchApps(); // Immediate refresh for instant UI feedback
}

async function saveSecret(appName) {
    const key = prompt("Enter Variable Name (e.g., DATABASE_URL):");
    if (!key) return;
    const value = prompt(`Enter value for ${key}:`);
    if (key && value) {
        const payload = { variables: {} };
        payload.variables[key] = value;
        
        await fetch(`/api/apps/${appName}/env`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        alert("Secret saved! It will be securely injected on your next git push.");
    }
}

async function nukeApp(appName) {
    if(confirm(`DANGER: Are you sure you want to permanently delete ${appName} and its routing data?`)) {
        await fetch(`/api/apps/${appName}`, { method: 'DELETE' });
        fetchApps();
    }
}

// Start polling every 4 seconds
setInterval(fetchApps, 4000); 
fetchApps();

// ==========================================
// 3. LIVE RELOAD WATCHER
// ==========================================
(function() {
    const CONTROL_PLANE_URL = "/api/apps";
    let currentContainerId = null;

    setInterval(async () => {
        try {
            const response = await fetch(CONTROL_PLANE_URL);
            const apps = await response.json();
            
            const myApp = apps.find(a => 
                (a.name.startsWith('app-') || a.name === 'app') && a.name !== 'paas-proxy'
            );
            
            if (myApp && myApp.status === 'running') {
                if (!currentContainerId) {
                    currentContainerId = myApp.id;
                } else if (currentContainerId !== myApp.id) {
                    console.log("🚀 Zero-Downtime swap detected! Reloading page...");
                    window.location.reload();
                }
            }
        } catch (error) {}
    }, 1500); 
})();