# Rewari Municipal Council – 30 SMP Road Cleaning Circles & Staff Allotment GIS

A specialized local Web GIS and Operations Management application developed for **Municipal Council Rewari, Haryana** to manage the **30 Sanitation Cleaning Circles** covering the official **456.60 km SMP road network** across all 32 municipal wards.

---

## 🚀 Quick Start (Local Use)

### Option 1: One-Click Local Launcher (Recommended)
Double-click **`start_server.bat`**.
- Starts the local Python web server on port `8000`.
- Automatically opens your default web browser at `http://localhost:8000`.
- Enables real-time local file persistence (updates save directly to KML/GeoJSON on disk).

### Option 2: Direct Double-Click
Double-click **`index.html`** in Chrome, Edge, or Firefox.
- Works 100% offline via embedded data (`js/rewari-smp-data.js`).

---

## 🌟 Key Features & Differences from Previous Project

| Feature | Previous Project (`safai circle`) | New Project (`smp roads`) |
| :--- | :--- | :--- |
| **Road Dataset** | Multi-agency raw roads requiring algorithmic deduplication | **Official SMP Road Network** clipped to 32 wards (**456.60 km, 7,674 segments**) |
| **Deduplication Engine** | Complex 2m distance tolerance & overlap filtering | **Not needed** — Clean, verified municipal dataset used directly |
| **Offline KML Upload** | Basic import | **Live Spatial Road Length Recalculation**: Uploading a revised KML instantly recalculates road length per circle via Turf.js / PostGIS |
| **Boundary Division** | Free-form arbitrary polygons | **Divided along Major Arterial Roads & Ground Landmarks** (Circular Rd, Delhi Rd, Bawal Rd, Railway Line, etc.) for field identification |
| **Staff Allotment Records** | Basic sweeper counts | **Master 30-Circle Allotment Roster**: Sanitary Daroga/Supervisor incharge, mobile numbers, sweeper teams, daily targets (m/day), equipment |
| **Persistence** | Local storage / Basic file save | **Multi-tier Persistence**: LocalStorage + Local Server (`server.py`) + Supabase PostGIS Cloud |

---

## 🗺️ 30 Cleaning Circles & Main Road Arterial Division

Each circle is bounded along **prominent ground landmarks and arterial roads** so supervisors and field workers can easily identify their operational area:

1. **Circle 01**: Delhi Road Corridor & Sector 4 Outer Ring (`14.925 km`) – Sunil Kumar (98120-41001)
2. **Circle 02**: Dharuhera Road Radial & Northern Outskirts (`14.864 km`) – Rajesh Sharma (98120-41002)
3. **Circle 03**: NH-919 Highway Corridor & Eastern Peripheral (`14.065 km`) – Vikram Singh (98120-41003)
4. **Circle 04**: Housing Board Colony & Sector 1 Main Road (`14.119 km`) – Satish Yadav (98120-41004)
5. **Circle 05**: Subhash Basti & New Anaj Mandi North (`13.898 km`) – Rameshwar Dayal (98120-41005)
6. **Circle 06**: Bawal Road Industrial Corridor & Sector 3 (`15.261 km`) – Sanjay Kumar (98120-41006)
7. **Circle 07**: Model Town South & Central Park Corridor (`15.219 km`) – Ashok Kumar (98120-41007)
8. **Circle 08**: Model Town Core Block A/B & Shopping Center (`15.165 km`) – Rakesh Kumar (98120-41008)
9. **Circle 09**: Brass Market & Commercial Plaza Hub (`15.119 km`) – Manoj Kumar (98120-41009)
10. **Circle 10**: Konsiwas Road & Southern Municipal Border (`15.164 km`) – Naresh Kumar (98120-41010)
11. **Circle 11**: Jhajjar Road North & Outer Octroi Zone (`15.512 km`) – Dinesh Yadav (98120-41011)
12. **Circle 12**: Western Bypass Corridor & Rampura Link (`15.234 km`) – Surender Singh (98120-41012)
13. **Circle 13**: Mahendragarh Road & Rampura Gate (`15.237 km`) – Mukesh Kumar (98120-41013)
14. **Circle 14**: Kaluwas Approach & North-West Agricultural Ring (`14.796 km`) – Ajay Sharma (98120-41014)
15. **Circle 15**: Garhi Bolni Road & South-West Peripheral (`15.285 km`) – Praveen Yadav (98120-41015)
16. **Circle 16**: Narnaul Road Corridor & Southern Spine (`15.766 km`) – Amit Kumar (98120-41016)
17. **Circle 17**: Railway Station West & Rewari Jn Goods Yard (`15.696 km`) – Deepak Saini (98120-41017)
18. **Circle 18**: Rewari Bypass North & Anand Nagar (`15.274 km`) – Ravinder Kumar (98120-41018)
19. **Circle 19**: Old Court Road & Naiwali Sub-Sector (`14.259 km`) – Pawan Kumar (98120-41019)
20. **Circle 20**: Circular Road North Outer & Grain Market (`15.230 km`) – Vijay Kumar (98120-41020)
21. **Circle 21**: Jhajjar Gate & Bada Bazaar North (`14.940 km`) – Sohan Lal (98120-41021)
22. **Circle 22**: Gokal Gate & Nai Sarak Corridor (`14.951 km`) – Joginder Singh (98120-41022)
23. **Circle 23**: Ghanta Ghar & Dharuhera Gate Core (`15.182 km`) – Satyanarayan (98120-41023)
24. **Circle 24**: Qutabpur & Balwal Gate Core (`15.233 km`) – Kailash Chand (98120-41024)
25. **Circle 25**: Sarafa Bazaar & Old Mandi Central Hub (`16.918 km`) – Mahesh Kumar (98120-41025)
26. **Circle 26**: Old Tehsil & Civil Hospital Zone (`15.223 km`) – Subhash Chand (98120-41026)
27. **Circle 27**: Circular Road West Inner & Bara Hazari (`15.386 km`) – Anil Kumar (98120-41027)
28. **Circle 28**: Circular Road South-East & Kutubpur Outer (`16.264 km`) – Krishan Lal (98120-41028)
29. **Circle 29**: South-Central Railway Colony & Loco Shed (`16.232 km`) – Baljeet Singh (98120-41029)
30. **Circle 30**: South-East Radial & Industrial Bypass Link (`16.184 km`) – Rajender Prasad (98120-41030)

---

## 📁 Directory & File Structure

```text
smp roads/
├── start_server.bat                    # One-click Windows server launcher
├── server.py                           # Python HTTP server & /api/save-circles handler
├── index.html                          # Main GIS Dashboard & Allotment Roster
├── css/
│   └── style.css                       # Modern dark-theme GIS stylesheet
├── js/
│   ├── app.js                          # UI orchestrator, event bus, modals
│   ├── map.js                          # Leaflet map controller & multi-layer visualizer
│   ├── circle-manager.js               # 30-Circle state, Daroga roster, metrics
│   ├── kml-handler.js                  # KML/KMZ upload parser, Turf.js calculator, exports
│   ├── supabase-client.js              # Supabase Cloud synchronization
│   └── rewari-smp-data.js              # Pre-bundled offline dataset (circles, roads, wards)
├── Rewari_30_Cleaning_Circles.kml      # Styled KML for Google Earth (colors, popups)
├── Rewari_30_Cleaning_Circles.geojson  # GeoJSON boundaries of 30 circles
├── Rewari_30_Cleaning_Circles_Roster.csv # Excel-ready operational roster table
├── Rewari_32_Wards.geojson             # 32 Municipal ward boundaries
├── Rewari_SMP_Roads_Web.geojson        # 7,674 SMP road segments
├── supabase_schema_and_triggers.sql    # PostGIS database schema, triggers & views
├── upload_to_supabase.py               # CLI tool to upload KML to Supabase
└── load_roads_to_supabase.py           # CLI tool to load static roads into Supabase
```

---

## ☁️ Supabase Cloud Integration

Connected to project: `https://ocejvxjctwnbksqztyya.supabase.co`

To configure:
1. Open your Supabase Dashboard: `https://supabase.com/dashboard/project/ocejvxjctwnbksqztyya`
2. Go to **SQL Editor** -> **New query**.
3. Copy & paste the contents of `supabase_schema_and_triggers.sql` and click **Run**.
   - This creates tables `cleaning_circles` and `smp_roads`, enables PostGIS, configures public RLS policies, triggers, and seeds all 30 Cleaning Circles with polygons and supervisor allotments.
4. The web dashboard will automatically synchronize with your Supabase cloud database!
