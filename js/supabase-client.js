/**
 * Supabase Cloud Synchronization Client
 * Connects Rewari Cleaning Circles web application to Supabase PostGIS cloud.
 */

window.SupabaseSync = (function () {
    // Current project credentials (Updated for Municipal Council Rewari)
    const SUPABASE_URL = 'https://ocejvxjctwnbksqztyya.supabase.co';
    const SUPABASE_KEY = 'sb_publishable_iEkCuYa1sBQJMScoU23-sg_R8dckwU8';

    let client = null;
    let isConnected = false;

    // Clear any obsolete cached URL from older projects
    try {
        const cachedUrl = localStorage.getItem('rewari_supabase_url');
        if (cachedUrl && cachedUrl !== SUPABASE_URL) {
            localStorage.removeItem('rewari_supabase_url');
            localStorage.removeItem('rewari_supabase_key');
            console.log('✓ Cleared old Supabase project cache, using updated project.');
        }
    } catch (e) {}

    function initClient() {
        if (client) return client;
        try {
            if (typeof window.supabase !== 'undefined' && window.supabase.createClient) {
                client = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY, {
                    auth: { persistSession: false }
                });
                isConnected = true;
                console.log('✓ Connected to Supabase Cloud Database:', SUPABASE_URL);
                updateBadge(true);
            } else {
                console.warn('Supabase JS library not loaded. Working in offline local storage mode.');
                updateBadge(false);
            }
        } catch (e) {
            console.error('Failed to initialize Supabase client:', e);
            isConnected = false;
            updateBadge(false);
        }
        return client;
    }

    function updateBadge(connected) {
        const badge = document.getElementById('cloud-sync-badge');
        if (!badge) return;
        if (connected) {
            badge.className = 'badge badge-live';
            badge.innerHTML = '<span class="status-dot"></span> ☁️ Supabase Connected';
            badge.title = `Connected to ${SUPABASE_URL}`;
        } else {
            badge.className = 'badge';
            badge.style.background = 'rgba(107, 114, 128, 0.2)';
            badge.style.borderColor = '#4b5563';
            badge.style.color = '#9ca3af';
            badge.innerHTML = '💾 Local Storage Mode';
            badge.title = 'Working locally in browser';
        }
    }

    async function fetchCircles() {
        const sb = initClient();
        if (!sb) return null;
        try {
            const { data, error } = await sb
                .from('cleaning_circles')
                .select('*')
                .order('circle_id', { ascending: true });

            if (error) {
                console.warn('Supabase fetch notice (table may need initial SQL migration):', error.message);
                return null;
            }
            return data;
        } catch (e) {
            console.warn('Supabase network error:', e);
            return null;
        }
    }

    async function saveCircleAllotment(circleData) {
        const sb = initClient();
        if (!sb) return false;
        try {
            const payload = {
                circle_id: circleData.circle_id,
                circle_name: circleData.circle_name,
                full_title: circleData.full_title,
                arterials: circleData.arterials,
                landmarks: circleData.landmarks,
                wards_included: circleData.wards_included,
                is_ward_split: circleData.is_ward_split,
                road_length_km: circleData.road_length_km,
                daroga_name: circleData.daroga_name,
                daroga_phone: circleData.daroga_phone,
                daroga_desig: circleData.daroga_desig,
                sweepers_count: circleData.sweepers_count,
                target_m_per_sweeper: circleData.target_m_per_sweeper,
                equipment: circleData.equipment,
                shift: circleData.shift,
                updated_at: new Date().toISOString()
            };

            const { error } = await sb
                .from('cleaning_circles')
                .upsert(payload, { onConflict: 'circle_id' });

            if (error) {
                console.warn('Supabase update failed:', error.message);
                return false;
            }
            console.log(`✓ Synced Circle ${circleData.circle_id} to Supabase`);
            return true;
        } catch (e) {
            console.warn('Error saving to Supabase:', e);
            return false;
        }
    }

    return {
        initClient,
        fetchCircles,
        saveCircleAllotment,
        isConnected: () => isConnected,
        getUrl: () => SUPABASE_URL
    };
})();
