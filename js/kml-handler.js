/**
 * KML / GeoJSON Handler Module
 * Handles offline KML/GeoJSON upload, instant spatial road-length calculation via Turf.js,
 * and comprehensive KML / GeoJSON / CSV exports.
 */

window.KMLHandler = (function () {

    /**
     * Process an uploaded file (KML, KMZ, or GeoJSON)
     */
    async function processUploadedFile(file) {
        const name = file.name.toLowerCase();
        let geoJSON = null;

        if (name.endsWith('.kml')) {
            const text = await file.text();
            geoJSON = parseKMLText(text);
        } else if (name.endsWith('.kmz')) {
            geoJSON = await parseKMZFile(file);
        } else if (name.endsWith('.geojson') || name.endsWith('.json')) {
            const text = await file.text();
            geoJSON = JSON.parse(text);
        } else {
            throw new Error('Unsupported format. Please upload .kml, .kmz, or .geojson');
        }

        if (!geoJSON || !geoJSON.features || geoJSON.features.length === 0) {
            throw new Error('No valid polygon features found in file.');
        }

        // Filter and normalize to Polygon / MultiPolygon features only
        const polygonFeatures = geoJSON.features.filter(f => 
            f.geometry && (f.geometry.type === 'Polygon' || f.geometry.type === 'MultiPolygon')
        );

        if (polygonFeatures.length === 0) {
            throw new Error('File does not contain any polygon boundaries.');
        }

        console.log(`Found ${polygonFeatures.length} polygon features in uploaded file.`);

        // Perform instant spatial road length recalculation
        return recalculateCircleRoadLengths(polygonFeatures);
    }

    /**
     * Parse KML XML string to GeoJSON using DOMParser
     */
    function parseKMLText(kmlString) {
        if (typeof toGeoJSON !== 'undefined' && toGeoJSON.kml) {
            const parser = new DOMParser();
            const xml = parser.parseFromString(kmlString, 'text/xml');
            return toGeoJSON.kml(xml);
        }
        throw new Error('toGeoJSON parser library not loaded.');
    }

    /**
     * Parse KMZ (ZIP archive)
     */
    async function parseKMZFile(file) {
        if (typeof JSZip === 'undefined') {
            throw new Error('JSZip library required to unpack KMZ.');
        }
        const zip = await JSZip.loadAsync(file);
        let kmlFile = zip.file(/.*\.kml$/i)[0];
        if (!kmlFile) throw new Error('No KML file found inside KMZ archive.');
        const kmlText = await kmlFile.async('text');
        return parseKMLText(kmlText);
    }

    /**
     * Recalculate road lengths for uploaded circle polygons using Turf.js
     */
    function recalculateCircleRoadLengths(polygonFeatures) {
        if (!window.REWARI_SMP_ROADS || !window.REWARI_SMP_ROADS.features) {
            throw new Error('SMP Road Network dataset is not available for intersection.');
        }

        const roads = window.REWARI_SMP_ROADS.features;
        console.log(`Recalculating lengths against ${roads.length} SMP road segments...`);

        // Prepare road midpoints for fast point-in-polygon assignment (avoids double counting)
        const roadMidpoints = roads.map(r => {
            const coords = r.geometry.coordinates;
            const midCoord = coords[Math.floor(coords.length / 2)];
            return {
                pt: turf.point(midCoord),
                length_km: Number(r.properties.road_len_km || 0),
                ward_id: r.properties.ward_id,
                orig: r
            };
        });

        const target_km = 15.220;
        const newCircles = [];

        polygonFeatures.forEach((feat, idx) => {
            const cid = idx + 1;
            let circleKm = 0;
            let segCount = 0;
            const wardsSet = new Set();
            const poly = feat.geometry;

            // Compute length by summing midpoints inside polygon
            roadMidpoints.forEach(rm => {
                if (turf.booleanPointInPolygon(rm.pt, poly)) {
                    circleKm += rm.length_km;
                    segCount += 1;
                    if (rm.ward_id) wardsSet.add(rm.ward_id);
                }
            });

            // Preserve existing Daroga / metadata if matching circle_id exists
            const existing = window.CircleManager.getById(cid) || {};
            const wardsStr = Array.from(wardsSet).sort((a,b)=>a-b).map(w => `Ward ${w}`).join(', ') || existing.wards_included || 'N/A';

            newCircles.push({
                circle_id: cid,
                circle_name: feat.properties.name || existing.circle_name || `Circle ${cid}`,
                full_title: existing.full_title || `Circle ${String(cid).padStart(2, '0')} - Custom Boundary`,
                arterials: existing.arterials || 'Uploaded Boundary Sector',
                landmarks: existing.landmarks || 'Custom offline polygon',
                road_length_km: Number(circleKm.toFixed(3)),
                road_segments: segCount,
                wards_included: wardsStr,
                is_ward_split: wardsSet.size > 1 ? 'Yes' : 'No',
                split_details: wardsSet.size > 1 ? `Split (${wardsStr})` : 'Whole',
                diff_target_km: Number((circleKm - target_km).toFixed(3)),
                daroga_name: existing.daroga_name || 'Unassigned',
                daroga_phone: existing.daroga_phone || '',
                daroga_desig: existing.daroga_desig || 'Sanitary Daroga',
                sweepers_count: existing.sweepers_count || 12,
                target_m_per_sweeper: circleKm > 0 ? Math.round((circleKm * 1000) / (existing.sweepers_count || 12)) : 1250,
                equipment: existing.equipment || '1 Tipper, 8 Hand-Carts',
                shift: existing.shift || 'Morning (06:00 AM - 02:00 PM)',
                geometry: feat.geometry
            });
        });

        return newCircles;
    }

    /**
     * Generate Styled KML for Google Earth
     */
    function generateKMLString(circles) {
        const colors = [
            "7f1f77b4", "7faec7e8", "7fff7f0e", "7ffffbb7", "7f2ca02c",
            "7f98df8a", "7fd62728", "7fff9896", "7f9467bd", "7fc5b0d5",
            "7f8c564b", "7fc49c94", "7fe377c2", "7ff7b6d2", "7f7f7f7f",
            "7fc7c7c7", "7fbcbd22", "7fdbdb8d", "7f17becf", "7f9edae5",
            "7fe41a1c", "7f377eb8", "7f4daf4a", "7f984ea3", "7ffff7f0",
            "7fa65628", "7ff781bf", "7f999999", "7fb3de69", "7ffccde5"
        ];

        let xml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Rewari Road Cleaning Circles (30 Circles)</name>
    <description>Municipal Council Rewari SMP Road Cleaning Circles &amp; Sanitary Staff Allotment</description>
`;

        circles.forEach((c, i) => {
            const col = colors[i % colors.length];
            xml += `    <Style id="circle_style_${c.circle_id}">
      <LineStyle><color>ff000000</color><width>2.5</width></LineStyle>
      <PolyStyle><color>${col}</color><fill>1</fill><outline>1</outline></PolyStyle>
    </Style>\n`;
        });

        circles.forEach(c => {
            const desc = `<![CDATA[
              <h3>${c.full_title}</h3>
              <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;font-family:sans-serif;font-size:12px;">
                <tr><td style="background:#f0f0f0;"><b>Road Length:</b></td><td><b>${c.road_length_km} km</b></td></tr>
                <tr><td style="background:#f0f0f0;"><b>Main Roads:</b></td><td>${c.arterials}</td></tr>
                <tr><td style="background:#f0f0f0;"><b>Key Landmarks:</b></td><td>${c.landmarks}</td></tr>
                <tr><td style="background:#f0f0f0;"><b>Wards Covered:</b></td><td>${c.wards_included}</td></tr>
                <tr><td style="background:#f0f0f0;"><b>Sanitary Daroga:</b></td><td>${c.daroga_name} (${c.daroga_phone || 'N/A'})</td></tr>
                <tr><td style="background:#f0f0f0;"><b>Sweepers Deployed:</b></td><td>${c.sweepers_count} workers</td></tr>
                <tr><td style="background:#f0f0f0;"><b>Daily Target:</b></td><td>${c.target_m_per_sweeper} m/worker</td></tr>
                <tr><td style="background:#f0f0f0;"><b>Equipment:</b></td><td>${c.equipment}</td></tr>
              </table>
            ]]>`;

            xml += `    <Placemark>
      <name>${c.circle_name} (${c.road_length_km} km)</name>
      <description>${desc}</description>
      <styleUrl>#circle_style_${c.circle_id}</styleUrl>
      ${geometryToKML(c.geometry)}
    </Placemark>\n`;
        });

        xml += `  </Document>\n</kml>`;
        return xml;
    }

    function geometryToKML(geom) {
        if (!geom) return '';
        if (geom.type === 'Polygon') {
            return polygonToKML(geom.coordinates);
        } else if (geom.type === 'MultiPolygon') {
            return `<MultiGeometry>${geom.coordinates.map(p => polygonToKML(p)).join('')}</MultiGeometry>`;
        }
        return '';
    }

    function polygonToKML(coords) {
        const outer = coords[0].map(pt => `${pt[0]},${pt[1]},0`).join(' ');
        let inners = '';
        for (let i = 1; i < coords.length; i++) {
            const innerCoords = coords[i].map(pt => `${pt[0]},${pt[1]},0`).join(' ');
            inners += `<innerBoundaryIs><LinearRing><coordinates>${innerCoords}</coordinates></LinearRing></innerBoundaryIs>`;
        }
        return `<Polygon><outerBoundaryIs><LinearRing><coordinates>${outer}</coordinates></LinearRing></outerBoundaryIs>${inners}</Polygon>`;
    }

    /**
     * Generate CSV content for Excel export
     */
    function generateCSVString(circles) {
        const headers = [
            'Circle_No', 'Circle_Title', 'Main_Road_Boundaries', 'Key_Landmarks',
            'Road_Length_KM', 'Road_Segments', 'Wards_Included', 'Split_Status',
            'Daroga_Incharge', 'Designation', 'Mobile_Number', 'Sweepers_Deployed',
            'Daily_Target_Meters_Per_Sweeper', 'Equipment_Vehicles', 'Shift'
        ];

        const escapeCSV = (val) => {
            const str = String(val == null ? '' : val);
            return `"${str.replace(/"/g, '""')}"`;
        };

        const rows = circles.map(c => [
            escapeCSV(`Circle ${String(c.circle_id).padStart(2, '0')}`),
            escapeCSV(c.full_title),
            escapeCSV(c.arterials),
            escapeCSV(c.landmarks),
            c.road_length_km,
            c.road_segments,
            escapeCSV(c.wards_included),
            escapeCSV(c.is_ward_split),
            escapeCSV(c.daroga_name),
            escapeCSV(c.daroga_desig),
            escapeCSV(c.daroga_phone),
            c.sweepers_count,
            c.target_m_per_sweeper,
            escapeCSV(c.equipment),
            escapeCSV(c.shift)
        ].join(','));

        return [headers.join(','), ...rows].join('\r\n');
    }

    /**
     * Browser File Download Trigger
     */
    function downloadBlob(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    return {
        processUploadedFile,
        generateKMLString,
        generateCSVString,
        downloadBlob
    };
})();
