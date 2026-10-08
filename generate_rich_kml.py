import json
import geopandas as gpd

def run():
    gdf = gpd.read_file('Rewari_30_Cleaning_Circles.geojson')

    colors = [
        '7f1f77b4', '7faec7e8', '7fff7f0e', '7ffffbb7', '7f2ca02c',
        '7f98df8a', '7fd62728', '7fff9896', '7f9467bd', '7fc5b0d5',
        '7f8c564b', '7fc49c94', '7fe377c2', '7ff7b6d2', '7f7f7f7f',
        '7fc7c7c7', '7fbcbd22', '7fdbdb8d', '7f17becf', '7f9edae5',
        '7fe41a1c', '7f377eb8', '7f4daf4a', '7f984ea3', '7ffff7f0',
        '7fa65628', '7ff781bf', '7f999999', '7fb3de69', '7ffccde5'
    ]

    header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Rewari Road Cleaning Circles (30 Circles) - Staff Allotment</name>
    <open>1</open>
    <description>Municipal Council Rewari SMP Road Cleaning Circles, Main Road Boundaries, and Sanitary Daroga Roster.</description>
"""
    styles = ""
    for idx in range(30):
        cid = idx + 1
        col = colors[idx % len(colors)]
        styles += f"""
    <Style id="circleStyle_{cid}">
      <LineStyle><color>ff000000</color><width>2.5</width></LineStyle>
      <PolyStyle><color>{col}</color><fill>1</fill><outline>1</outline></PolyStyle>
    </Style>"""

    placemarks = ""
    for _, row in gdf.iterrows():
        cid = int(row['circle_id'])
        title = row.get('full_title', f'Circle {cid}')
        arterials = row.get('arterials', 'Main Arterials')
        landmarks = row.get('landmarks', 'Key Landmarks')
        wards = row['wards_included']
        daroga = row.get('daroga_name', 'Unassigned')
        phone = row.get('daroga_phone', 'N/A')
        desig = row.get('daroga_desig', 'Sanitary Daroga')
        sweepers = row.get('sweepers_count', 12)
        target_m = row.get('target_m_per_sweeper', 1250)
        eq = row.get('equipment', '1 Tipper, 8 Hand-Carts')
        shift = row.get('shift', 'Morning (06:00 AM - 02:00 PM)')
        km = row['road_length_km']
        segs = row['road_segments']
        geom = row['geometry']

        desc = f"""<![CDATA[
          <div style="font-family:Arial,sans-serif; width:340px;">
            <h3 style="margin:0 0 6px 0; color:#1e3a8a;">{title}</h3>
            <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; width:100%; font-size:12px;">
              <tr><td style="background:#f3f4f6;"><b>Road Length</b></td><td><b>{km:.3f} km</b> ({segs} segments)</td></tr>
              <tr><td style="background:#f3f4f6;"><b>Main Roads</b></td><td><span style="color:#2563eb;font-weight:600;">{arterials}</span></td></tr>
              <tr><td style="background:#f3f4f6;"><b>Key Landmarks</b></td><td>{landmarks}</td></tr>
              <tr><td style="background:#f3f4f6;"><b>Wards Covered</b></td><td>{wards}</td></tr>
              <tr style="background:#e0f2fe;"><td colspan="2"><b>👮 Sanitary Staff Allotment</b></td></tr>
              <tr><td style="background:#f3f4f6;"><b>Daroga / Incharge</b></td><td><b>{daroga}</b> ({desig})</td></tr>
              <tr><td style="background:#f3f4f6;"><b>Mobile Number</b></td><td><a href="tel:{phone}">{phone}</a></td></tr>
              <tr><td style="background:#f3f4f6;"><b>Sweepers Deployed</b></td><td><b>{sweepers} workers</b></td></tr>
              <tr><td style="background:#f3f4f6;"><b>Daily Target</b></td><td>{target_m} meters / sweeper</td></tr>
              <tr><td style="background:#f3f4f6;"><b>Equipment / Vehicles</b></td><td>{eq}</td></tr>
              <tr><td style="background:#f3f4f6;"><b>Shift Timing</b></td><td>{shift}</td></tr>
            </table>
          </div>
        ]]>"""

        def geom_to_kml_poly(polygon):
            coords = " ".join([f"{c[0]},{c[1]},0" for c in polygon.exterior.coords])
            inner_str = ""
            for interior in polygon.interiors:
                in_coords = " ".join([f"{c[0]},{c[1]},0" for c in interior.coords])
                inner_str += f"""
            <innerBoundaryIs>
              <LinearRing><coordinates>{in_coords}</coordinates></LinearRing>
            </innerBoundaryIs>"""
            return f"""
          <Polygon>
            <outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs>{inner_str}
          </Polygon>"""

        poly_xml = ""
        if geom.geom_type == 'Polygon':
            poly_xml = geom_to_kml_poly(geom)
        elif geom.geom_type == 'MultiPolygon':
            poly_xml = "<MultiGeometry>" + "".join([geom_to_kml_poly(p) for p in geom.geoms]) + "</MultiGeometry>"

        placemarks += f"""
    <Placemark>
      <name>{title} ({km:.2f} km)</name>
      <description>{desc}</description>
      <styleUrl>#circleStyle_{cid}</styleUrl>
      {poly_xml}
    </Placemark>"""

    footer = """
  </Document>
</kml>"""

    with open('Rewari_30_Cleaning_Circles.kml', 'w', encoding='utf-8') as f:
        f.write(header + styles + placemarks + footer)
    print("Rewari_30_Cleaning_Circles.kml updated with full operational attributes!")

if __name__ == '__main__':
    run()
