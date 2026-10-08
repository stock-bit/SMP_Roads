import os
import zipfile
import pandas as pd
import numpy as np
import geopandas as gpd
import pyogrio
from shapely.ops import voronoi_diagram, unary_union
from shapely.geometry import MultiPoint, Polygon, MultiPolygon
from shapely.validation import make_valid

def build_cleaning_circles():
    print("=== STEP 1: Loading Datasets ===")
    # 1. Load Wards
    layers = pyogrio.list_layers('extracted_kmz/doc.kml')
    ward_gdfs = []
    for layer in layers:
        gdf = gpd.read_file('extracted_kmz/doc.kml', layer=layer[0])
        gdf['ward_id'] = int(gdf['Name'].iloc[0])
        ward_gdfs.append(gdf[['ward_id', 'geometry']])

    wards = gpd.GeoDataFrame(pd.concat(ward_gdfs, ignore_index=True), crs=ward_gdfs[0].crs).to_crs(epsg=32643)
    wards['geometry'] = wards['geometry'].apply(make_valid)
    wards = wards.sort_values('ward_id').reset_index(drop=True)
    muni_boundary = unary_union(wards.geometry)

    # 2. Load Roads
    roads = gpd.read_file('SMP_Roads_Inside_32_Wards.geojson').to_crs(epsg=32643)
    roads['road_len_km'] = roads.geometry.length / 1000.0
    midpoints = roads.geometry.interpolate(0.5, normalized=True)
    roads['mid_x'] = midpoints.x
    roads['mid_y'] = midpoints.y

    # Spatial join roads to wards
    roads_pts = gpd.GeoDataFrame(roads[['OBJECTID', 'road_len_km', 'mid_x', 'mid_y']], geometry=midpoints, crs=roads.crs)
    joined = gpd.sjoin(roads_pts, wards[['ward_id', 'geometry']], how='left', predicate='within')
    joined = joined[~joined.index.duplicated(keep='first')]

    if joined['ward_id'].isna().sum() > 0:
        for idx in joined[joined['ward_id'].isna()].index:
            pt = midpoints.loc[idx]
            dists = wards.geometry.distance(pt)
            joined.loc[idx, 'ward_id'] = wards.iloc[dists.argmin()]['ward_id']

    roads['ward_id'] = joined['ward_id'].astype(int)
    roads['circle_id'] = 0

    total_roads_km = roads['road_len_km'].sum()
    target_km = total_roads_km / 30.0
    print(f"Total Roads: {len(roads)} segments | Total Length: {total_roads_km:.3f} km")
    print(f"Target per Circle: {target_km:.3f} km")

    # Helper function for axis-based sequential split
    def assign_roads_split(sub_indices, circle_ids, axis='mid_y', targets=None):
        sub_roads = roads.loc[sub_indices].sort_values(axis)
        k = len(circle_ids)
        if targets is None:
            t = sub_roads['road_len_km'].sum() / k
            targets = [t] * k
        curr_c = 0
        curr_len = 0.0
        for idx, row in sub_roads.iterrows():
            if curr_len >= targets[curr_c] and curr_c < k - 1:
                curr_c += 1
                curr_len = 0.0
            roads.loc[idx, 'circle_id'] = circle_ids[curr_c]
            curr_len += row['road_len_km']

    print("=== STEP 2: Partitioning Roads into 30 Circles ===")

    # Sector 1: Ward 13 (Circles 1, 2)
    assign_roads_split(roads[roads.ward_id == 13].index, [1, 2], axis='mid_y')

    # Sector 2: Ward 12 (Circles 3, 4, 5)
    assign_roads_split(roads[roads.ward_id == 12].index, [3, 4, 5], axis='mid_y')

    # Sector 3: Ward 11 (Circles 6, 7, 8)
    # Ward 11 transfers ~2.86 km from West to Ward 20/South Central
    w11 = roads[roads.ward_id == 11].sort_values('mid_x')
    curr_len = 0.0
    w11_trans_idx = []
    w11_rem_idx = []
    for idx, row in w11.iterrows():
        if curr_len < 2.86:
            w11_trans_idx.append(idx)
            curr_len += row['road_len_km']
        else:
            w11_rem_idx.append(idx)
    assign_roads_split(w11_rem_idx, [6, 7, 8], axis='mid_y')

    # Sector 4: Natural Single Wards (Ward 6, 19, 31)
    # Ward 6 transfers ~1.11 km south to Ward 20
    w6 = roads[roads.ward_id == 6].sort_values('mid_y')
    curr_len = 0.0
    w6_trans_idx = []
    for idx, row in w6.iterrows():
        if curr_len < 1.11:
            w6_trans_idx.append(idx)
            curr_len += row['road_len_km']
        else:
            roads.loc[idx, 'circle_id'] = 9

    # Ward 19 transfers ~1.47 km east to Ward 20
    w19 = roads[roads.ward_id == 19].sort_values('mid_x', ascending=False)
    curr_len = 0.0
    w19_trans_idx = []
    for idx, row in w19.iterrows():
        if curr_len < 1.47:
            w19_trans_idx.append(idx)
            curr_len += row['road_len_km']
        else:
            roads.loc[idx, 'circle_id'] = 10

    # Ward 31 (Whole -> Circle 11)
    roads.loc[roads.ward_id == 31, 'circle_id'] = 11

    # Sector 5: West Cluster (Wards 29, 30, 32 -> Circles 12, 13, 14)
    assign_roads_split(roads[roads.ward_id == 30].index, [12, 13], axis='mid_x', targets=[target_km, 9.72])
    w32 = roads[roads.ward_id == 32].sort_values('mid_x')
    target_13_needed = target_km - roads[roads.circle_id == 13]['road_len_km'].sum()
    curr_len = 0.0
    for idx, row in w32.iterrows():
        if curr_len < target_13_needed:
            roads.loc[idx, 'circle_id'] = 13
            curr_len += row['road_len_km']
        else:
            roads.loc[idx, 'circle_id'] = 14
    roads.loc[roads.ward_id == 29, 'circle_id'] = 14

    # Sector 6: South-West Cluster (Wards 21, 22 -> Circles 15, 16, 17)
    roads.loc[roads.ward_id == 22, 'circle_id'] = 15
    w21 = roads[roads.ward_id == 21].sort_values('mid_x')
    target_15_needed = target_km - roads[roads.ward_id == 22]['road_len_km'].sum()
    curr_len = 0.0
    w21_rem_idx = []
    for idx, row in w21.iterrows():
        if curr_len < target_15_needed:
            roads.loc[idx, 'circle_id'] = 15
            curr_len += row['road_len_km']
        else:
            w21_rem_idx.append(idx)
    assign_roads_split(w21_rem_idx, [16, 17], axis='mid_x')

    # Sector 7: North Cluster (Wards 1, 2, 24, 25, 26, 27, 28 -> Circles 18..22)
    assign_roads_split(roads[roads.ward_id == 28].index, [18, 19], axis='mid_y', targets=[target_km, 4.08])
    roads.loc[roads.ward_id == 2, 'circle_id'] = 19
    roads.loc[roads.ward_id.isin([1, 24]), 'circle_id'] = 22
    w26 = roads[roads.ward_id == 26].sort_values('mid_y', ascending=False)
    roads.loc[roads.ward_id == 27, 'circle_id'] = 20
    target_20_needed = target_km - roads[roads.ward_id == 27]['road_len_km'].sum()
    curr_len = 0.0
    w26_rem_idx = []
    for idx, row in w26.iterrows():
        if curr_len < target_20_needed:
            roads.loc[idx, 'circle_id'] = 20
            curr_len += row['road_len_km']
        else:
            w26_rem_idx.append(idx)
    roads.loc[roads.ward_id == 25, 'circle_id'] = 21
    roads.loc[w26_rem_idx, 'circle_id'] = 21

    # Sector 8: Central Core & South Transition (Circles 23..30)
    # Circle 23: Ward 14 (Whole) + Ward 15 (Whole)
    roads.loc[roads.ward_id.isin([14, 15]), 'circle_id'] = 23

    # Circle 24: Ward 16, 17, 18 (Whole) + portion from Ward 23
    roads.loc[roads.ward_id.isin([16, 17, 18]), 'circle_id'] = 24
    w23 = roads[roads.ward_id == 23].sort_values('mid_y', ascending=False)
    target_24_needed = target_km - roads[roads.circle_id == 24]['road_len_km'].sum()
    curr_len = 0.0
    w23_rem_idx = []
    for idx, row in w23.iterrows():
        if curr_len < target_24_needed:
            roads.loc[idx, 'circle_id'] = 24
            curr_len += row['road_len_km']
        else:
            w23_rem_idx.append(idx)

    # Circle 25: Ward 3, 8, 9, 10 (Whole) + small portion of Ward 4
    roads.loc[roads.ward_id.isin([3, 8, 9, 10]), 'circle_id'] = 25
    w4 = roads[roads.ward_id == 4].sort_values('mid_x')
    target_25_needed = target_km - roads[roads.circle_id == 25]['road_len_km'].sum()
    curr_len = 0.0
    w4_rem_idx = []
    for idx, row in w4.iterrows():
        if curr_len < target_25_needed:
            roads.loc[idx, 'circle_id'] = 25
            curr_len += row['road_len_km']
        else:
            w4_rem_idx.append(idx)

    # Circle 26: Ward 4 remainder + Ward 5 North
    roads.loc[w4_rem_idx, 'circle_id'] = 26
    w5 = roads[roads.ward_id == 5].sort_values('mid_y', ascending=False)
    target_26_needed = target_km - roads[roads.circle_id == 26]['road_len_km'].sum()
    curr_len = 0.0
    w5_rem_idx = []
    for idx, row in w5.iterrows():
        if curr_len < target_26_needed:
            roads.loc[idx, 'circle_id'] = 26
            curr_len += row['road_len_km']
        else:
            w5_rem_idx.append(idx)

    # Circle 27: Ward 5 remainder + Ward 7 North
    roads.loc[w5_rem_idx, 'circle_id'] = 27
    w7 = roads[roads.ward_id == 7].sort_values('mid_y', ascending=False)
    target_27_needed = target_km - roads[roads.circle_id == 27]['road_len_km'].sum()
    curr_len = 0.0
    w7_rem_idx = []
    for idx, row in w7.iterrows():
        if curr_len < target_27_needed:
            roads.loc[idx, 'circle_id'] = 27
            curr_len += row['road_len_km']
        else:
            w7_rem_idx.append(idx)

    # Remaining roads to divide equally across Circles 28, 29, 30:
    # Contains: Ward 7 remainder + Ward 20 + Ward 23 remainder + transfers from Ward 11, Ward 6, Ward 19
    rem_pool_idx = w7_rem_idx + list(roads[roads.ward_id == 20].index) + w23_rem_idx + w11_trans_idx + w6_trans_idx + w19_trans_idx
    assign_roads_split(rem_pool_idx, [28, 29, 30], axis='mid_y')

    # Verification: Ensure no road segment left unassigned
    assert (roads['circle_id'] == 0).sum() == 0, "Unassigned roads exist!"

    print("=== STEP 3: Compiling Circle Statistics ===")
    summary_list = []
    for cid in range(1, 31):
        c_roads = roads[roads['circle_id'] == cid]
        c_km = c_roads['road_len_km'].sum()
        c_count = len(c_roads)
        c_wards = sorted(list(set(c_roads['ward_id'])))
        
        split_wards = []
        for w in c_wards:
            total_ward_roads = len(roads[roads['ward_id'] == w])
            in_circle_roads = len(c_roads[c_roads['ward_id'] == w])
            if in_circle_roads < total_ward_roads:
                split_wards.append(w)
        
        is_split = "Yes" if len(split_wards) > 0 else "No"
        wards_str = ", ".join([f"Ward {w}" for w in c_wards])
        split_details_str = f"Split ({', '.join([f'Ward {w}' for w in split_wards])})" if len(split_wards) > 0 else "Whole"

        summary_list.append({
            'circle_id': cid,
            'circle_name': f"Circle {cid}",
            'wards_included': wards_str,
            'is_ward_split': is_split,
            'split_details': split_details_str,
            'road_length_km': round(c_km, 3),
            'road_segments': c_count,
            'diff_target_km': round(c_km - target_km, 3)
        })

    df_summary = pd.DataFrame(summary_list)
    print(df_summary.to_string(index=False))
    print(f"\nTotal Network Length: {df_summary['road_length_km'].sum():.3f} km")
    print(f"Circle Road Length Range: Min = {df_summary['road_length_km'].min():.3f} km | Max = {df_summary['road_length_km'].max():.3f} km")
    print(f"Mean = {df_summary['road_length_km'].mean():.3f} km | Std Dev = {df_summary['road_length_km'].std():.3f} km")

    # Save CSV
    df_summary.to_csv('Rewari_Cleaning_Circles_Summary.csv', index=False)
    print("Saved: Rewari_Cleaning_Circles_Summary.csv")

    print("\n=== STEP 4: Generating Geometric Boundary Polygons ===")
    # Generate Voronoi diagram on all road midpoints
    mp = MultiPoint(list(roads.geometry.interpolate(0.5, normalized=True)))
    vd = voronoi_diagram(mp, envelope=muni_boundary.buffer(500))
    vor_gdf = gpd.GeoDataFrame(geometry=list(vd.geoms), crs=wards.crs)
    
    # Associate each Voronoi polygon with its corresponding road's circle_id
    road_pts_gdf = gpd.GeoDataFrame(roads[['circle_id']], geometry=roads.geometry.interpolate(0.5, normalized=True), crs=roads.crs)
    joined_vor = gpd.sjoin(vor_gdf, road_pts_gdf, how='inner', predicate='contains')
    joined_vor = joined_vor[~joined_vor.index.duplicated(keep='first')]

    # Dissolve Voronoi cells by circle_id to form contiguous circle boundary polygons
    dissolved = joined_vor.dissolve(by='circle_id').reset_index()
    # Intersect with municipal boundary so outer bounds exactly match the council boundary
    dissolved['geometry'] = dissolved.geometry.apply(lambda g: make_valid(g).intersection(muni_boundary))

    # Merge metadata with geometry
    gdf_circles = df_summary.merge(dissolved[['circle_id', 'geometry']], on='circle_id', how='left')
    gdf_circles = gpd.GeoDataFrame(gdf_circles, geometry='geometry', crs=wards.crs)
    
    # Validate area and topology
    print(f"Total Circles Polygon Area: {gdf_circles.geometry.area.sum() / 1e6:.3f} sq km")
    print(f"Municipal Council Area:     {muni_boundary.area / 1e6:.3f} sq km")
    
    # Convert to WGS84 (EPSG:4326) for GeoJSON and KML
    gdf_circles_wgs84 = gdf_circles.to_crs(epsg=4326)
    gdf_circles_wgs84.to_file('Rewari_30_Cleaning_Circles.geojson', driver='GeoJSON')
    print("Saved: Rewari_30_Cleaning_Circles.geojson")

    # Generate Styled KML
    kml_content = generate_styled_kml(gdf_circles_wgs84)
    with open('Rewari_30_Cleaning_Circles.kml', 'w', encoding='utf-8') as f:
        f.write(kml_content)
    print("Saved: Rewari_30_Cleaning_Circles.kml")

    # Save roads GeoJSON with assigned circles
    roads_wgs84 = roads[['OBJECTID', 'circle_id', 'ward_id', 'road_len_km', 'geometry']].to_crs(epsg=4326)
    roads_wgs84.to_file('Rewari_Roads_Assigned_Circles.geojson', driver='GeoJSON')
    print("Saved: Rewari_Roads_Assigned_Circles.geojson")

    print("\nAll division files successfully created!")

def generate_styled_kml(gdf):
    """Generates an attractive, well-formatted KML file with polygon styles and metadata balloons."""
    # Color palette for 30 distinct circles (ABGR format for KML)
    colors = [
        "7f1f77b4", "7faec7e8", "7fff7f0e", "7ffffbb7", "7f2ca02c",
        "7f98df8a", "7fd62728", "7fff9896", "7f9467bd", "7fc5b0d5",
        "7f8c564b", "7fc49c94", "7fe377c2", "7ff7b6d2", "7f7f7f7f",
        "7fc7c7c7", "7fbcbd22", "7fdbdb8d", "7f17becf", "7f9edae5",
        "7fe41a1c", "7f377eb8", "7f4daf4a", "7f984ea3", "7ffff7f0",
        "7fa65628", "7ff781bf", "7f999999", "7fb3de69", "7ffccde5"
    ]

    header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Rewari Road Cleaning Circles (30 Circles)</name>
    <open>1</open>
    <description>Division of Rewari Municipal Council SMP Road Network into 30 Balanced Cleaning Circles.</description>
"""

    styles = ""
    for idx in range(30):
        cid = idx + 1
        col = colors[idx % len(colors)]
        styles += f"""
    <Style id="circleStyle_{cid}">
      <LineStyle>
        <color>ff000000</color>
        <width>2</width>
      </LineStyle>
      <PolyStyle>
        <color>{col}</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
    </Style>"""

    placemarks = ""
    for _, row in gdf.iterrows():
        cid = row['circle_id']
        name = row['circle_name']
        wards = row['wards_included']
        is_split = row['is_ward_split']
        split_det = row['split_details']
        km = row['road_length_km']
        segs = row['road_segments']
        diff = row['diff_target_km']
        geom = row['geometry']

        desc = f"""<![CDATA[
          <h3>{name}</h3>
          <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;font-family:sans-serif;font-size:12px;">
            <tr><th style="background:#f2f2f2;">Attribute</th><th style="background:#f2f2f2;">Value</th></tr>
            <tr><td><b>Total Road Length</b></td><td><b>{km:.3f} km</b></td></tr>
            <tr><td><b>Target Difference</b></td><td>{'+' if diff >= 0 else ''}{diff:.3f} km</td></tr>
            <tr><td><b>Road Segments</b></td><td>{segs}</td></tr>
            <tr><td><b>Wards Included</b></td><td>{wards}</td></tr>
            <tr><td><b>Ward Split Status</b></td><td>{split_det}</td></tr>
          </table>
        ]]>"""

        def geom_to_kml_poly(polygon):
            coords = " ".join([f"{c[0]},{c[1]},0" for c in polygon.exterior.coords])
            inner_str = ""
            for interior in polygon.interiors:
                in_coords = " ".join([f"{c[0]},{c[1]},0" for c in interior.coords])
                inner_str += f"""
            <innerBoundaryIs>
              <LinearRing>
                <coordinates>{in_coords}</coordinates>
              </LinearRing>
            </innerBoundaryIs>"""
            return f"""
          <Polygon>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>{coords}</coordinates>
              </LinearRing>
            </outerBoundaryIs>{inner_str}
          </Polygon>"""

        poly_xml = ""
        if geom.geom_type == 'Polygon':
            poly_xml = geom_to_kml_poly(geom)
        elif geom.geom_type == 'MultiPolygon':
            poly_xml = "<MultiGeometry>" + "".join([geom_to_kml_poly(p) for p in geom.geoms]) + "</MultiGeometry>"

        placemarks += f"""
    <Placemark>
      <name>{name} ({km:.2f} km)</name>
      <description>{desc}</description>
      <styleUrl>#circleStyle_{cid}</styleUrl>
      {poly_xml}
    </Placemark>"""

    footer = """
  </Document>
</kml>
"""
    return header + styles + placemarks + footer

if __name__ == '__main__':
    build_cleaning_circles()
