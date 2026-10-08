/**
 * Circle Manager Module
 * Manages the state, Daroga allotments, sweeper deployments, and metrics for all 30 cleaning circles.
 */

window.CircleManager = (function () {
    let circles = [];
    const STORAGE_KEY = 'rewari_smp_30_circles_v1';

    function init() {
        // 1. Try loading from localStorage
        const saved = loadFromStorage();
        if (saved && saved.length === 30) {
            circles = saved;
            console.log('✓ Loaded 30 circles from LocalStorage.');
        } else if (window.REWARI_DEFAULT_CIRCLES && window.REWARI_DEFAULT_CIRCLES.features) {
            // 2. Fallback to default embedded dataset
            circles = window.REWARI_DEFAULT_CIRCLES.features.map(f => {
                const p = f.properties;
                return {
                    circle_id: Number(p.circle_id),
                    circle_name: p.circle_name || `Circle ${p.circle_id}`,
                    full_title: p.full_title || `Circle ${String(p.circle_id).padStart(2, '0')} - ${p.arterials || ''}`,
                    arterials: p.arterials || 'Main Road Sector',
                    landmarks: p.landmarks || 'Boundary along major corridors',
                    road_length_km: Number(p.road_length_km || 0),
                    road_segments: Number(p.road_segments || 0),
                    wards_included: p.wards_included || 'N/A',
                    is_ward_split: p.is_ward_split || 'No',
                    split_details: p.split_details || 'Whole',
                    diff_target_km: Number(p.diff_target_km || 0),
                    daroga_name: p.daroga_name || 'Unassigned',
                    daroga_phone: p.daroga_phone || '',
                    daroga_desig: p.daroga_desig || 'Sanitary Daroga',
                    sweepers_count: Number(p.sweepers_count || 12),
                    target_m_per_sweeper: Number(p.target_m_per_sweeper || 1250),
                    equipment: p.equipment || '1 Tipper, 8 Hand-Carts',
                    shift: p.shift || 'Morning (06:00 AM - 02:00 PM)',
                    notes: p.notes || '',
                    geometry: f.geometry
                };
            });
            saveToStorage();
            console.log('✓ Initialized 30 default circles with Daroga rosters.');
        }

        // Try syncing from Supabase if connected
        if (window.SupabaseSync) {
            window.SupabaseSync.fetchCircles().then(remoteData => {
                if (remoteData && remoteData.length === 30) {
                    mergeRemoteData(remoteData);
                }
            }).catch(e => console.warn('Could not sync remote circles:', e));
        }
    }

    function saveToStorage() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(circles));
        } catch (e) {
            console.warn('Storage quota exceeded or disabled:', e);
        }
    }

    function loadFromStorage() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) {
            console.warn('Could not read from storage:', e);
        }
        return null;
    }

    function mergeRemoteData(remoteRows) {
        let changed = false;
        remoteRows.forEach(row => {
            const c = circles.find(x => x.circle_id === Number(row.circle_id));
            if (c) {
                if (row.daroga_name && row.daroga_name !== c.daroga_name) {
                    c.daroga_name = row.daroga_name;
                    changed = true;
                }
                if (row.daroga_phone && row.daroga_phone !== c.daroga_phone) {
                    c.daroga_phone = row.daroga_phone;
                    changed = true;
                }
                if (row.sweepers_count && row.sweepers_count !== c.sweepers_count) {
                    c.sweepers_count = Number(row.sweepers_count);
                    changed = true;
                }
            }
        });
        if (changed) {
            saveToStorage();
            dispatchChangeEvent();
        }
    }

    function getAll() {
        return circles;
    }

    function getById(id) {
        return circles.find(c => c.circle_id === Number(id));
    }

    function updateCircle(id, updates) {
        const c = getById(id);
        if (!c) return false;

        Object.assign(c, updates);
        
        // Recalculate daily target if sweepers or length changed
        if (c.sweepers_count > 0 && c.road_length_km > 0) {
            c.target_m_per_sweeper = Math.round((c.road_length_km * 1000) / c.sweepers_count);
        }

        saveToStorage();
        dispatchChangeEvent();

        // Sync to Supabase in background
        if (window.SupabaseSync) {
            window.SupabaseSync.saveCircleAllotment(c);
        }

        // Notify local server if running
        trySaveToServer();
        return true;
    }

    function replaceAllCircles(newCircleList) {
        circles = newCircleList;
        saveToStorage();
        dispatchChangeEvent();
        trySaveToServer();
    }

    function resetDefaults() {
        localStorage.removeItem(STORAGE_KEY);
        init();
        dispatchChangeEvent();
        trySaveToServer();
    }

    function getStatistics() {
        const totalKm = circles.reduce((sum, c) => sum + (c.road_length_km || 0), 0);
        const totalSweepers = circles.reduce((sum, c) => sum + (c.sweepers_count || 0), 0);
        const totalDarogas = circles.filter(c => c.daroga_name && c.daroga_name !== 'Unassigned').length;
        const totalSegments = circles.reduce((sum, c) => sum + (c.road_segments || 0), 0);

        const lengths = circles.map(c => c.road_length_km || 0);
        const minKm = lengths.length > 0 ? Math.min(...lengths) : 0;
        const maxKm = lengths.length > 0 ? Math.max(...lengths) : 0;
        const avgKm = circles.length > 0 ? totalKm / circles.length : 0;

        return {
            totalCircles: circles.length,
            totalRoadLengthKm: totalKm.toFixed(3),
            totalSweepers,
            totalDarogas,
            totalSegments,
            avgKm: avgKm.toFixed(3),
            minKm: minKm.toFixed(3),
            maxKm: maxKm.toFixed(3)
        };
    }

    function filterCircles(query) {
        if (!query || query.trim() === '') return circles;
        const q = query.toLowerCase().trim();
        return circles.filter(c => {
            return (
                c.circle_name.toLowerCase().includes(q) ||
                c.full_title.toLowerCase().includes(q) ||
                c.arterials.toLowerCase().includes(q) ||
                c.landmarks.toLowerCase().includes(q) ||
                c.wards_included.toLowerCase().includes(q) ||
                (c.daroga_name && c.daroga_name.toLowerCase().includes(q)) ||
                (c.daroga_phone && c.daroga_phone.includes(q))
            );
        });
    }

    function toGeoJSON() {
        return {
            type: 'FeatureCollection',
            features: circles.map(c => ({
                type: 'Feature',
                properties: {
                    circle_id: c.circle_id,
                    circle_name: c.circle_name,
                    full_title: c.full_title,
                    arterials: c.arterials,
                    landmarks: c.landmarks,
                    road_length_km: c.road_length_km,
                    road_segments: c.road_segments,
                    wards_included: c.wards_included,
                    is_ward_split: c.is_ward_split,
                    split_details: c.split_details,
                    diff_target_km: c.diff_target_km,
                    daroga_name: c.daroga_name,
                    daroga_phone: c.daroga_phone,
                    daroga_desig: c.daroga_desig,
                    sweepers_count: c.sweepers_count,
                    target_m_per_sweeper: c.target_m_per_sweeper,
                    equipment: c.equipment,
                    shift: c.shift
                },
                geometry: c.geometry
            }))
        };
    }

    function trySaveToServer() {
        if (window.location.protocol.startsWith('http')) {
            fetch('/api/save-circles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ geojson: toGeoJSON() })
            }).catch(() => {});
        }
    }

    function dispatchChangeEvent() {
        window.dispatchEvent(new CustomEvent('circlesChanged', { detail: { circles } }));
    }

    return {
        init,
        getAll,
        getById,
        updateCircle,
        replaceAllCircles,
        resetDefaults,
        getStatistics,
        filterCircles,
        toGeoJSON
    };
})();
