/**
 * Leaflet Map Controller Module
 * Handles base maps, 30-circle polygons, SMP road network rendering,
 * ward boundary overlays, tooltips, and interactive spatial inspection.
 */

window.MapController = (function () {
    let map = null;
    let circlesLayer = null;
    let roadsLayer = null;
    let wardsLayer = null;
    let labelsLayer = null;
    let showLabels = true;
    let canvasRenderer = null;

    // Distinct palette for 30 circles
    // Distinct high-contrast palette for 30 circles (curated to avoid pure yellow or cyan)
    const circleColors = [
        '#e11d48', // C-01 Rose Red
        '#7c3aed', // C-02 Purple
        '#059669', // C-03 Emerald
        '#f97316', // C-04 Orange
        '#2563eb', // C-05 Royal Blue
        '#d946ef', // C-06 Fuchsia
        '#10b981', // C-07 Mint Green
        '#ea580c', // C-08 Deep Orange
        '#4f46e5', // C-09 Indigo
        '#ec4899', // C-10 Pink
        '#047857', // C-11 Forest Green
        '#9333ea', // C-12 Deep Violet
        '#c026d3', // C-13 Magenta
        '#b91c1c', // C-14 Crimson
        '#6366f1', // C-15 Periwinkle
        '#15803d', // C-16 Green
        '#be185d', // C-17 Deep Pink
        '#6d28d9', // C-18 Grape
        '#c2410c', // C-19 Rust Orange
        '#1d4ed8', // C-20 Cobalt Blue
        '#a21caf', // C-21 Plum
        '#0f766e', // C-22 Deep Teal
        '#dc2626', // C-23 Scarlet
        '#7e22ce', // C-24 Violet
        '#4338ca', // C-25 Midnight Blue
        '#be123c', // C-26 Carmine
        '#065f46', // C-27 Pine Green
        '#86198f', // C-28 Deep Plum
        '#3730a3', // C-29 Navy Blue
        '#991b1b'  // C-30 Ruby Red
    ];

    function initMap() {
        if (map) return map;

        console.log('Initializing Leaflet Map with Clear Satellite Imagery...');
        const mapElement = document.getElementById('map');
        if (!mapElement) {
            console.error('#map element not found in DOM');
            return null;
        }

        // Dedicated Canvas renderer for high-speed rendering of 7,674 roads
        canvasRenderer = L.canvas({ padding: 0.5 });

        // Initialize Leaflet map centered over Rewari, Haryana
        map = L.map('map', {
            center: [28.196, 76.618],
            zoom: 13,
            zoomControl: false,
            preferCanvas: true
        });

        // Add custom zoom control in top-right
        L.control.zoom({ position: 'topright' }).addTo(map);

        // 1. Google Clear Satellite Hybrid (High-Resolution Satellite + Road/Landmark Labels) - ALWAYS DEFAULT ON STARTUP
        const googleHybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
            attribution: '&copy; Google Maps Satellite',
            maxZoom: 20,
            subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
        }).addTo(map);

        // 2. Esri World Imagery (Clean Pure Satellite)
        const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; Esri &copy; DigitalGlobe',
            maxZoom: 19
        });

        // 3. OpenStreetMap (Standard Street Map)
        const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        });

        // 4. CartoDB Dark Matter
        const cartoDark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; CartoDB &copy; OpenStreetMap',
            maxZoom: 19
        });

        L.control.layers({
            '🛰️ Clear Satellite (Google Hybrid)': googleHybrid,
            '🛰️ Esri Satellite (Clean)': esriSat,
            '🗺️ Street Map (OpenStreetMap)': osm,
            '🌙 Dark Matter': cartoDark
        }, null, { position: 'topright' }).addTo(map);

        labelsLayer = L.layerGroup().addTo(map);

        // Force Leaflet to recalculate container size
        setTimeout(() => { if (map) map.invalidateSize(); }, 100);
        setTimeout(() => { if (map) map.invalidateSize(); }, 500);
        window.addEventListener('resize', () => { if (map) map.invalidateSize(); });

        // Load layers in optimal visual z-order:
        // 1. Circles (bottom translucent polygons)
        // 2. Wards (middle thick dashed yellow borders)
        // 3. Roads (top electric cyan lines)
        try { renderCircles(); } catch (e) { console.warn('Circles layer error:', e); }
        try { loadWards(); } catch (e) { console.warn('Wards layer error:', e); }
        try { loadRoads(); } catch (e) { console.warn('Roads layer error:', e); }

        // Listen for data updates
        window.addEventListener('circlesChanged', () => {
            renderCircles();
        });

        console.log('✓ Leaflet Map successfully loaded & centered.');
        return map;
    }

    function getColor(cid) {
        return circleColors[(Number(cid) - 1) % circleColors.length] || '#3b82f6';
    }

    /**
     * Safe Center Point Calculator (works even if Turf.js CDN is blocked/delayed)
     */
    function getFeatureCenter(feat) {
        if (typeof turf !== 'undefined' && turf.centerOfMass) {
            try {
                const c = turf.centerOfMass(feat);
                return [c.geometry.coordinates[1], c.geometry.coordinates[0]]; // [lat, lng]
            } catch (e) {}
        }
        // Fallback: Leaflet polygon bounds center
        try {
            const tempLayer = L.geoJSON(feat);
            const center = tempLayer.getBounds().getCenter();
            return [center.lat, center.lng];
        } catch (e) {
            return [28.196, 76.618];
        }
    }

    /**
     * Render the 30 Cleaning Circles
     */
    function renderCircles() {
        if (!map) return;
        if (circlesLayer) {
            map.removeLayer(circlesLayer);
        }
        labelsLayer.clearLayers();

        const circles = window.CircleManager.getAll();
        if (!circles || circles.length === 0) return;

        const geoJSONData = window.CircleManager.toGeoJSON();

        circlesLayer = L.geoJSON(geoJSONData, {
            style: function (feat) {
                const cid = feat.properties.circle_id;
                const col = getColor(cid);
                return {
                    color: col,
                    weight: 2.8,
                    opacity: 0.95,
                    fillColor: col,
                    fillOpacity: 0.18 // Translucent so satellite imagery & buildings remain sharp underneath
                };
            },
            onEachFeature: function (feat, layer) {
                const p = feat.properties;
                const cid = p.circle_id;
                const col = getColor(cid);

                // Floating Center Label
                if (feat.geometry) {
                    const centerLatLng = getFeatureCenter(feat);
                    const labelIcon = L.divIcon({
                        className: 'circle-map-label',
                        html: `<div style="background:rgba(15,23,42,0.92); color:#fff; border:1.5px solid ${col}; border-radius:4px; padding:2px 6px; font-size:10px; font-weight:700; white-space:nowrap; box-shadow:0 2px 6px rgba(0,0,0,0.6); text-align:center; pointer-events:none;">C-${String(cid).padStart(2,'0')}<br><span style="color:#34d399;font-weight:700;">${p.road_length_km}k</span></div>`,
                        iconSize: [48, 30],
                        iconAnchor: [24, 15]
                    });
                    const marker = L.marker(centerLatLng, { icon: labelIcon, interactive: false });
                    labelsLayer.addLayer(marker);
                }

                // Rich Popup balloon
                const popupContent = `
                    <div style="font-family:'Inter',sans-serif; min-width:260px; font-size:12px; color:#111827;">
                        <div style="background:${col}; color:#fff; padding:6px 10px; border-radius:4px 4px 0 0; margin:-1px -1px 8px -1px;">
                            <div style="font-weight:700; font-size:13px;">${p.full_title}</div>
                            <div style="font-size:10px; opacity:0.9;">Road Length: <b>${p.road_length_km} km</b> (${p.road_segments} segs)</div>
                        </div>
                        <div style="padding:0 4px 6px 4px;">
                            <div style="margin-bottom:4px;"><b>🛣️ Main Roads:</b> ${p.arterials}</div>
                            <div style="margin-bottom:4px;"><b>📍 Key Landmarks:</b> ${p.landmarks}</div>
                            <div style="margin-bottom:4px;"><b>🏛️ Wards:</b> ${p.wards_included}</div>
                            <hr style="border:0; border-top:1px solid #e5e7eb; margin:6px 0;">
                            <div style="margin-bottom:3px;"><b>👮 Daroga:</b> ${p.daroga_name} (${p.daroga_desig || 'Daroga'})</div>
                            <div style="margin-bottom:3px;"><b>📞 Phone:</b> <a href="tel:${p.daroga_phone}">${p.daroga_phone || 'N/A'}</a></div>
                            <div style="margin-bottom:3px;"><b>🧹 Sweepers:</b> ${p.sweepers_count} workers (${p.target_m_per_sweeper} m/day)</div>
                            <div><b>🚜 Equipment:</b> ${p.equipment}</div>
                        </div>
                    </div>
                `;
                layer.bindPopup(popupContent, { maxWidth: 320 });

                layer.on('mouseover', function () {
                    this.setStyle({ fillOpacity: 0.40, weight: 3.8 });
                });
                layer.on('mouseout', function () {
                    circlesLayer.resetStyle(this);
                });
                layer.on('click', function () {
                    highlightSidebarItem(cid);
                });
            }
        }).addTo(map);

        // Fit map to bounds of all 30 circles
        try {
            map.fitBounds(circlesLayer.getBounds(), { padding: [15, 15] });
        } catch (e) {}
    }

    /**
     * Load SMP Road Network (Rendered via Hardware Canvas in Electric Cyan)
     */
    function loadRoads() {
        if (!window.REWARI_SMP_ROADS) return;
        console.log(`Loading SMP Roads (${window.REWARI_SMP_ROADS.features ? window.REWARI_SMP_ROADS.features.length : 0} segments)...`);

        roadsLayer = L.geoJSON(window.REWARI_SMP_ROADS, {
            renderer: canvasRenderer,
            style: function (feat) {
                return {
                    color: '#00f5ff', // Bright Electric Cyan - High contrast against satellite
                    weight: 2.2,
                    opacity: 0.95
                };
            },
            onEachFeature: function (feat, layer) {
                const p = feat.properties || {};
                const lenM = p.road_len_km ? Math.round(Number(p.road_len_km) * 1000) : 0;
                layer.bindTooltip(`🛣️ Road: ${p.FULL_STREET_NAME || 'SMP Segment'}<br>Length: ${lenM}m | Circle: C-${p.circle_id || 'N/A'}`, {
                    sticky: true,
                    className: 'road-map-tooltip'
                });
            }
        });
        roadsLayer.addTo(map);
    }

    /**
     * Load Ward Boundaries (Rendered in Neon Yellow Thick Dashed)
     */
    function loadWards() {
        if (!window.REWARI_WARDS) return;
        wardsLayer = L.geoJSON(window.REWARI_WARDS, {
            style: {
                color: '#ffea00', // Bright High-Vis Neon Yellow
                weight: 3.2,
                dashArray: '8, 6', // Thick dashed pattern to distinctly separate from roads
                fillColor: '#ffea00',
                fillOpacity: 0.02,
                opacity: 1.0
            },
            onEachFeature: function (feat, layer) {
                const wId = feat.properties.ward_id || feat.properties.Name || 'N/A';
                layer.bindTooltip(`🏛️ Ward Boundary: ${wId}`, { sticky: true });
            }
        });
        wardsLayer.addTo(map);
    }

    function toggleRoads(show) {
        if (!map || !roadsLayer) return;
        if (show) map.addLayer(roadsLayer);
        else map.removeLayer(roadsLayer);
    }

    function toggleWards(show) {
        if (!map || !wardsLayer) return;
        if (show) map.addLayer(wardsLayer);
        else map.removeLayer(wardsLayer);
    }

    function toggleCircles(show) {
        if (!map || !circlesLayer) return;
        if (show) map.addLayer(circlesLayer);
        else map.removeLayer(circlesLayer);
    }

    function toggleLabels() {
        showLabels = !showLabels;
        if (!map || !labelsLayer) return showLabels;
        if (showLabels) map.addLayer(labelsLayer);
        else map.removeLayer(labelsLayer);
        return showLabels;
    }

    function zoomToCircle(cid) {
        if (!circlesLayer || !map) return;
        circlesLayer.eachLayer(layer => {
            if (layer.feature && layer.feature.properties.circle_id === Number(cid)) {
                map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 15 });
                layer.openPopup();
                layer.setStyle({ fillOpacity: 0.45, weight: 4 });
                setTimeout(() => circlesLayer.resetStyle(layer), 2500);
            }
        });
    }

    function resetView() {
        if (circlesLayer && map) {
            map.fitBounds(circlesLayer.getBounds(), { padding: [20, 20] });
        } else if (map) {
            map.setView([28.196, 76.618], 13);
        }
    }

    function highlightSidebarItem(cid) {
        const item = document.getElementById(`circle-card-${cid}`);
        if (item) {
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            item.classList.add('active');
            setTimeout(() => item.classList.remove('active'), 2000);
        }
    }

    return {
        initMap,
        renderCircles,
        toggleRoads,
        toggleWards,
        toggleCircles,
        toggleLabels,
        zoomToCircle,
        resetView,
        getColor
    };
})();
