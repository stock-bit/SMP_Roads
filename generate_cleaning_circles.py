import os
import zipfile
import pandas as pd
import numpy as np
import geopandas as gpd
import pyogrio
from shapely.geometry import box, Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union, split
from shapely.validation import make_valid

def main():
    print("=== Rewari 30 Cleaning Circles Division Pipeline ===")

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
    print(f"Total Roads: {len(roads)} segments, {total_roads_km:.3f} km")
    print(f"Target length per circle: {target_km:.3f} km")

    # Helper function to split a set of roads by axis
    def assign_roads(sub_indices, circle_ids, axis='mid_y', targets=None):
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

    # --- Sector 1: Ward 13 (Circles 1, 2) ---
    assign_roads(roads[roads.ward_id == 13].index, [1, 2], axis='mid_y')

    # --- Sector 2: Ward 12 (Circles 3, 4, 5) ---
    assign_roads(roads[roads.ward_id == 12].index, [3, 4, 5], axis='mid_y')

    # --- Sector 3: Ward 11 (Circles 6, 7, 8) ---
    assign_roads(roads[roads.ward_id == 11].index, [6, 7, 8], axis='mid_y')

    # --- Sector 4: Natural Single Wards (Circles 9, 10, 11) ---
    roads.loc[roads.ward_id == 6, 'circle_id'] = 9
    roads.loc[roads.ward_id == 19, 'circle_id'] = 10
    roads.loc[roads.ward_id == 31, 'circle_id'] = 11

    # --- Sector 5: West Cluster (Wards 29, 30, 32 -> Circles 12, 13, 14) ---
    assign_roads(roads[roads.ward_id.isin([29, 30, 32])].index, [12, 13, 14], axis='mid_x')

    # --- Sector 6: South-West Cluster (Wards 21, 22 -> Circles 15, 16, 17) ---
    assign_roads(roads[roads.ward_id.isin([21, 22])].index, [15, 16, 17], axis='mid_x')

    # --- Sector 7: North Cluster (Wards 1, 2, 24, 25, 26, 27, 28 -> Circles 18, 19, 20, 21, 22) ---
    assign_roads(roads[roads.ward_id.isin([1, 2, 24, 25, 26, 27, 28])].index, [18, 19, 20, 21, 22], axis='mid_y')

    # --- Sector 8: Central Core / Transition Cluster (Wards 3, 4, 5, 7, 8, 9, 10, 14, 15, 16, 17, 18, 20, 23 -> Circles 23..30) ---
    assign_roads(roads[roads.ward_id.isin([3, 4, 5, 7, 8, 9, 10, 14, 15, 16, 17, 18, 20, 23])].index, [23, 24, 25, 26, 27, 28, 29, 30], axis='mid_y')

    # Verification: Check every road is assigned
    unassigned = (roads['circle_id'] == 0).sum()
    assert unassigned == 0, f"Error: {unassigned} roads unassigned!"

    # Calculate summary per circle
    circle_records = []
    for cid in range(1, 31):
        c_roads = roads[roads['circle_id'] == cid]
        c_km = c_roads['road_len_km'].sum()
        c_count = len(c_roads)
        c_wards = sorted(list(set(c_roads['ward_id'])))
        
        # Determine split wards
        split_details = []
        for w in c_wards:
            total_ward_roads = len(roads[roads['ward_id'] == w])
            in_circle_roads = len(c_roads[c_roads['ward_id'] == w])
            if in_circle_roads < total_ward_roads:
                split_details.append(w)
        
        is_split = "Yes" if len(split_details) > 0 else "No"
        wards_str = ", ".join([f"Ward {w}" for w in c_wards])
        split_str = f"Yes ({', '.join([f'Ward {w}' for w in split_details])})" if len(split_details) > 0 else "No"

        circle_records.append({
            'circle_id': cid,
            'circle_name': f"Circle {cid}",
            'wards_included': wards_str,
            'is_ward_split': is_split,
            'split_details': split_str,
            'road_length_km': round(c_km, 3),
            'road_segments': c_count,
            'diff_target_km': round(c_km - target_km, 3)
        })

    df_summary = pd.DataFrame(circle_records)
    print("\n=== SUMMARY OF 30 CLEANING CIRCLES ===")
    print(df_summary.to_string(index=False))

    # Construct Polygon Boundaries for each Circle
    # For each circle, we create a polygon boundary by Voronoi / spatial alpha shape or road buffer clipped to wards
    print("\nGenerating Circle Boundary Polygons...")
    
    # Create road buffers and dissolve by circle, then clip/snap to ward bounds
    # A 50m buffer around road segments dissolved per circle, or Voronoi partitioning around road midpoints
    # PostGIS standard: Voronoi tessellation of road midpoints constrained within the municipal ward boundary!
    from scipy.spatial import Voronoi
    from shapely.ops import voronoi_diagram
    
    # Combine municipal boundary
    muni_boundary = unary_union(wards.geometry)
    
    # We can also generate polygons by clustering road geometries with buffer and convex hull / concave hull
    # or Voronoi on road midpoints
    circle_polys = []
    
    # Clean Voronoi partitioning:
    points_geom = unary_union(roads.geometry.interpolate(0.5, normalized=True))
    vor_regions = voronoi_diagram(points_geom, envelope=muni_boundary.buffer(100))
    vor_gdf = gpd.GeoDataFrame(geometry=list(vor_regions.geoms), crs=wards.crs)
    
    # Join Voronoi cells to road points
    joined_vor = gpd.sjoin(vor_gdf, roads[['circle_id', 'geometry']].copy().set_geometry(roads.geometry.interpolate(0.5, normalized=True)), how='inner', predicate='contains')
    joined_vor = joined_vor[~joined_vor.index.duplicated(keep='first')]
    
    # Dissolve by circle_id
    dissolved = joined_vor.dissolve(by='circle_id').reset_index()
    # Clip to municipal boundary
    dissolved['geometry'] = dissolved.geometry.apply(lambda g: make_valid(g).intersection(muni_boundary))
    
    # Merge summary metadata
    gdf_circles = df_summary.merge(dissolved[['circle_id', 'geometry']], on='circle_id', how='left')
    gdf_circles = gpd.GeoDataFrame(gdf_circles, geometry='geometry', crs=wards.crs)
    gdf_circles_wgs84 = gdf_circles.to_crs(epsg=4326)
    
    # Export files
    print("\nExporting files...")
    # 1. Summary CSV
    df_summary.to_csv('Rewari_Cleaning_Circles_Summary.csv', index=False)
    print("Saved: Rewari_Cleaning_Circles_Summary.csv")

    # 2. GeoJSON Circles Polygons
    gdf_circles_wgs84.to_file('Rewari_30_Cleaning_Circles.geojson', driver='GeoJSON')
    print("Saved: Rewari_30_Cleaning_Circles.geojson")

    # 3. KML Circles Polygons
    gdf_circles_wgs84.to_file('Rewari_30_Cleaning_Circles.kml', driver='KML')
    print("Saved: Rewari_30_Cleaning_Circles.kml")

    # 4. Roads with circle_id assigned
    roads_wgs84 = roads[['OBJECTID', 'circle_id', 'ward_id', 'road_len_km', 'geometry']].to_crs(epsg=4326)
    roads_wgs84.to_file('Rewari_Roads_Assigned_Circles.geojson', driver='GeoJSON')
    print("Saved: Rewari_Roads_Assigned_Circles.geojson")

    print("\nPipeline completed successfully!")

if __name__ == '__main__':
    main()
