/**
 * Main Application Orchestrator
 * Connects UI interactions, sidebar directory, master allotment roster,
 * modal dialogs, and export triggers.
 */

document.addEventListener('DOMContentLoaded', function () {
    console.log('Initializing Rewari Road Cleaning Circle GIS System...');

    // 1. Initialize data and map
    window.CircleManager.init();
    window.MapController.initMap();
    if (window.SupabaseSync) {
        window.SupabaseSync.initClient();
    }

    // 2. Initial UI Renders
    renderCircleSidebarList();
    renderMasterRosterTable();
    updateStatisticsKPIs();

    // 3. Setup Event Listeners
    setupTabNavigation();
    setupSearchFilter();
    setupFileUploads();
    setupExports();
    setupModalHandlers();
    setupMapToolbar();

    // Re-render when data updates
    window.addEventListener('circlesChanged', () => {
        renderCircleSidebarList();
        renderMasterRosterTable();
        updateStatisticsKPIs();
    });

    console.log('✓ System ready.');
});

/**
 * Tab Navigation
 */
function setupTabNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.control-panel-tab').forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const target = tab.getAttribute('data-target');
            const panel = document.getElementById(target);
            if (panel) panel.classList.add('active');

            // Force map resize check
            setTimeout(() => {
                if (window.MapController && window.MapController.resetView) {
                    window.MapController.resetView();
                }
            }, 150);
        });
    });
}

/**
 * Render Sidebar Circles Directory List
 */
function renderCircleSidebarList(circlesToRender) {
    const container = document.getElementById('circle-list-container');
    if (!container) return;

    const circles = circlesToRender || window.CircleManager.getAll();
    container.innerHTML = '';

    if (circles.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4 small">No circles matching filter.</div>';
        return;
    }

    circles.forEach(c => {
        const col = window.MapController.getColor(c.circle_id);
        const card = document.createElement('div');
        card.className = 'circle-item';
        card.id = `circle-card-${c.circle_id}`;

        card.innerHTML = `
            <div class="circle-color-bar" style="background:${col};"></div>
            <div class="circle-header-row">
                <span class="circle-title">${c.full_title}</span>
                <span class="circle-km-badge">${c.road_length_km} km</span>
            </div>
            <div class="circle-landmarks-sub">
                🛣️ <b>Main:</b> ${c.arterials}<br>
                📍 <b>Landmarks:</b> ${c.landmarks}
            </div>
            <div class="circle-meta-row">
                <span>👮 <b>${c.daroga_name}</b></span>
                <span>🧹 <b>${c.sweepers_count}</b> sweepers</span>
                <button class="btn btn-sm btn-outline btn-zoom" data-cid="${c.circle_id}" style="padding:1px 6px; font-size:10px;">🔍 Zoom</button>
            </div>
        `;

        card.addEventListener('click', (e) => {
            if (!e.target.classList.contains('btn-zoom')) {
                window.MapController.zoomToCircle(c.circle_id);
            }
        });

        card.querySelector('.btn-zoom').addEventListener('click', (e) => {
            e.stopPropagation();
            window.MapController.zoomToCircle(c.circle_id);
        });

        container.appendChild(card);
    });
}

/**
 * Render Master Allotment Roster Table Below Map
 */
function renderMasterRosterTable(circlesToRender) {
    const tbody = document.getElementById('master-roster-tbody');
    if (!tbody) return;

    const circles = circlesToRender || window.CircleManager.getAll();
    tbody.innerHTML = '';

    circles.forEach(c => {
        const col = window.MapController.getColor(c.circle_id);
        const tr = document.createElement('tr');

        const splitBadge = c.is_ward_split === 'Yes' 
            ? `<span class="tag-split-yes" title="${c.split_details}">Split Ward</span>` 
            : `<span class="tag-split-no">Whole Ward</span>`;

        tr.innerHTML = `
            <td>
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${col};margin-right:6px;"></span>
                <b>C-${String(c.circle_id).padStart(2, '0')}</b>
            </td>
            <td>
                <strong style="color:var(--text-primary);">${c.full_title}</strong>
            </td>
            <td>
                <span style="color:#60a5fa; font-weight:500;">${c.arterials}</span>
                <div class="small text-muted" style="font-size:0.72rem;">📍 ${c.landmarks}</div>
            </td>
            <td>
                <b style="color:#34d399;">${c.road_length_km} km</b>
                <div class="small text-muted">${c.road_segments} segs</div>
            </td>
            <td>
                <span>${c.wards_included}</span>
                <div>${splitBadge}</div>
            </td>
            <td>
                <b>${c.daroga_name}</b>
                <div class="small text-muted">${c.daroga_desig || 'Daroga'}</div>
            </td>
            <td>
                <a href="tel:${c.daroga_phone}" style="color:#93c5fd;text-decoration:none;">${c.daroga_phone || 'N/A'}</a>
            </td>
            <td style="text-align:center;">
                <b style="color:#f59e0b;font-size:0.95rem;">${c.sweepers_count}</b>
            </td>
            <td>
                <span>${c.target_m_per_sweeper} m/day</span>
            </td>
            <td>
                <span class="small text-muted">${c.equipment}</span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline btn-edit-allotment" data-cid="${c.circle_id}" title="Edit supervisor, workers and landmarks">✏️ Edit</button>
                <button class="btn btn-sm btn-outline btn-view-map" data-cid="${c.circle_id}" title="Zoom to circle on map">📍 View</button>
            </td>
        `;

        tr.querySelector('.btn-edit-allotment').addEventListener('click', () => {
            openEditModal(c.circle_id);
        });

        tr.querySelector('.btn-view-map').addEventListener('click', () => {
            window.MapController.zoomToCircle(c.circle_id);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        tbody.appendChild(tr);
    });
}

/**
 * Update KPI Statistics on Sidebar and Roster Header
 */
function updateStatisticsKPIs() {
    const stats = window.CircleManager.getStatistics();

    // Sidebar KPIs
    const elTotalKm = document.getElementById('stat-total-km');
    const elAvgKm = document.getElementById('stat-avg-km');
    const elTotalSweepers = document.getElementById('stat-total-sweepers');
    const elTotalDarogas = document.getElementById('stat-total-darogas');

    if (elTotalKm) elTotalKm.textContent = `${stats.totalRoadLengthKm} km`;
    if (elAvgKm) elAvgKm.textContent = `${stats.avgKm} km`;
    if (elTotalSweepers) elTotalSweepers.textContent = stats.totalSweepers;
    if (elTotalDarogas) elTotalDarogas.textContent = stats.totalDarogas;

    // Roster summary pills
    const pillKm = document.getElementById('pill-total-roads');
    const pillSweepers = document.getElementById('pill-total-workforce');
    const pillDarogas = document.getElementById('pill-total-darogas');

    if (pillKm) pillKm.textContent = `${stats.totalRoadLengthKm} km`;
    if (pillSweepers) pillSweepers.textContent = `${stats.totalSweepers} Workers`;
    if (pillDarogas) pillDarogas.textContent = `${stats.totalDarogas} Darogas`;
}

/**
 * Live Search Filter for Circles & Staff
 */
function setupSearchFilter() {
    const searchInput = document.getElementById('search-circles-input');
    const rosterSearch = document.getElementById('master-roster-search');

    function handleFilter(query) {
        const filtered = window.CircleManager.filterCircles(query);
        renderCircleSidebarList(filtered);
        renderMasterRosterTable(filtered);
    }

    if (searchInput) {
        searchInput.addEventListener('input', (e) => handleFilter(e.target.value));
    }
    if (rosterSearch) {
        rosterSearch.addEventListener('input', (e) => handleFilter(e.target.value));
    }
}

/**
 * Upload Offline KML / GeoJSON Circle Polygons
 */
function setupFileUploads() {
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('kml-file-input');
    const headerInput = document.getElementById('header-file-input');

    async function handleFile(file) {
        if (!file) return;
        try {
            showNotification(`Processing ${file.name}... Calculating road lengths...`, 'info');
            const newCircles = await window.KMLHandler.processUploadedFile(file);
            window.CircleManager.replaceAllCircles(newCircles);
            showNotification(`✓ Successfully updated ${newCircles.length} circles! Road lengths recalculated.`, 'success');
        } catch (err) {
            console.error(err);
            alert(`Upload Error: ${err.message}`);
        }
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
    }
    if (headerInput) {
        headerInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
    }

    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleFile(e.dataTransfer.files[0]);
            }
        });
        dropzone.addEventListener('click', () => fileInput && fileInput.click());
    }

    const btnReset = document.getElementById('btn-reset-defaults');
    if (btnReset) {
        btnReset.addEventListener('click', () => {
            if (confirm('Reset circles and Daroga records to the default 30-circle master plan?')) {
                window.CircleManager.resetDefaults();
                showNotification('Reset to default 30 circles plan.', 'info');
            }
        });
    }
}

/**
 * Exports Handling
 */
function setupExports() {
    // Export KML
    const exportKmlBtns = [document.getElementById('btn-export-kml'), document.getElementById('btn-header-export-kml')];
    exportKmlBtns.forEach(btn => {
        if (!btn) return;
        btn.addEventListener('click', () => {
            const circles = window.CircleManager.getAll();
            const kmlStr = window.KMLHandler.generateKMLString(circles);
            window.KMLHandler.downloadBlob(kmlStr, 'Rewari_30_Cleaning_Circles.kml', 'application/vnd.google-earth.kml+xml');
            showNotification('Downloaded Rewari_30_Cleaning_Circles.kml', 'success');
        });
    });

    // Export GeoJSON
    const btnGeoJSON = document.getElementById('btn-export-geojson');
    if (btnGeoJSON) {
        btnGeoJSON.addEventListener('click', () => {
            const geojson = window.CircleManager.toGeoJSON();
            window.KMLHandler.downloadBlob(JSON.stringify(geojson, null, 2), 'Rewari_30_Cleaning_Circles.geojson', 'application/json');
            showNotification('Downloaded Rewari_30_Cleaning_Circles.geojson', 'success');
        });
    }

    // Export CSV / Excel
    const exportCsvBtns = [document.getElementById('btn-export-csv'), document.getElementById('btn-header-export-csv')];
    exportCsvBtns.forEach(btn => {
        if (!btn) return;
        btn.addEventListener('click', () => {
            const circles = window.CircleManager.getAll();
            const csvStr = window.KMLHandler.generateCSVString(circles);
            window.KMLHandler.downloadBlob(csvStr, 'Rewari_30_Cleaning_Circles_Roster.csv', 'text/csv;charset=utf-8;');
            showNotification('Downloaded Rewari_30_Cleaning_Circles_Roster.csv', 'success');
        });
    });
}

/**
 * Edit Allotment Modal Logic
 */
let currentEditCid = null;

function openEditModal(cid) {
    const c = window.CircleManager.getById(cid);
    if (!c) return;
    currentEditCid = cid;

    document.getElementById('modal-circle-title').textContent = `Edit Circle ${String(c.circle_id).padStart(2, '0')} Allotment`;
    document.getElementById('edit-circle-name').value = c.full_title;
    document.getElementById('edit-arterials').value = c.arterials;
    document.getElementById('edit-landmarks').value = c.landmarks;
    document.getElementById('edit-daroga-name').value = c.daroga_name;
    document.getElementById('edit-daroga-phone').value = c.daroga_phone;
    document.getElementById('edit-daroga-desig').value = c.daroga_desig || 'Sanitary Daroga';
    document.getElementById('edit-sweepers').value = c.sweepers_count;
    document.getElementById('edit-equipment').value = c.equipment;
    document.getElementById('edit-shift').value = c.shift;
    document.getElementById('edit-notes').value = c.notes || '';

    document.getElementById('edit-modal').classList.add('open');
}

function setupModalHandlers() {
    const modal = document.getElementById('edit-modal');
    const btnClose = document.getElementById('btn-close-modal');
    const btnCancel = document.getElementById('btn-cancel-modal');
    const form = document.getElementById('form-edit-allotment');

    function closeModal() {
        if (modal) modal.classList.remove('open');
        currentEditCid = null;
    }

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (!currentEditCid) return;

            const updates = {
                full_title: document.getElementById('edit-circle-name').value,
                arterials: document.getElementById('edit-arterials').value,
                landmarks: document.getElementById('edit-landmarks').value,
                daroga_name: document.getElementById('edit-daroga-name').value,
                daroga_phone: document.getElementById('edit-daroga-phone').value,
                daroga_desig: document.getElementById('edit-daroga-desig').value,
                sweepers_count: Number(document.getElementById('edit-sweepers').value) || 12,
                equipment: document.getElementById('edit-equipment').value,
                shift: document.getElementById('edit-shift').value,
                notes: document.getElementById('edit-notes').value
            };

            window.CircleManager.updateCircle(currentEditCid, updates);
            closeModal();
            showNotification(`✓ Updated allotment record for Circle ${currentEditCid}`, 'success');
        });
    }
}

/**
 * Map Toolbar Toggle Buttons
 */
function setupMapToolbar() {
    const btnToggleRoads = document.getElementById('map-toggle-roads');
    const btnToggleWards = document.getElementById('map-toggle-wards');
    const btnToggleCircles = document.getElementById('map-toggle-circles');
    const btnToggleLabels = document.getElementById('map-toggle-labels');
    const btnResetView = document.getElementById('map-reset-view');

    let roadsOn = true;
    let wardsOn = true;
    let circlesOn = true;

    if (btnToggleRoads) {
        btnToggleRoads.addEventListener('click', () => {
            roadsOn = !roadsOn;
            window.MapController.toggleRoads(roadsOn);
            btnToggleRoads.classList.toggle('active', roadsOn);
        });
    }

    if (btnToggleWards) {
        btnToggleWards.addEventListener('click', () => {
            wardsOn = !wardsOn;
            window.MapController.toggleWards(wardsOn);
            btnToggleWards.classList.toggle('active', wardsOn);
        });
    }

    if (btnToggleCircles) {
        btnToggleCircles.addEventListener('click', () => {
            circlesOn = !circlesOn;
            window.MapController.toggleCircles(circlesOn);
            btnToggleCircles.classList.toggle('active', circlesOn);
        });
    }

    if (btnToggleLabels) {
        btnToggleLabels.addEventListener('click', () => {
            const active = window.MapController.toggleLabels();
            btnToggleLabels.classList.toggle('active', active);
        });
    }

    if (btnResetView) {
        btnResetView.addEventListener('click', () => {
            window.MapController.resetView();
        });
    }

    // Scroll to roster button
    const btnRosterJump = document.getElementById('btn-jump-roster');
    if (btnRosterJump) {
        btnRosterJump.addEventListener('click', () => {
            const section = document.getElementById('section-master-roster');
            if (section) section.scrollIntoView({ behavior: 'smooth' });
        });
    }
}

/**
 * Toast Notifications
 */
function showNotification(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#3b82f6';
    toast.style.cssText = `background:${bg};color:#fff;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,0.4);opacity:0;transition:opacity 0.2s;`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => toast.style.opacity = '1', 10);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 250);
    }, 3500);
}
