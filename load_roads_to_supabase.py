"""
Rewari Road Network - Initial Supabase Loader
---------------------------------------------
Loads all base SMP road features into Supabase 'smp_roads' table once.
These roads serve as the static reference against which circle road lengths are computed.
"""

import os
import argparse
import geopandas as gpd

def load_roads(geojson_path="SMP_Roads_Inside_32_Wards.geojson", db_url=None):
    if not db_url:
        db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url:
        print("[NOTE] Set SUPABASE_DB_URL or provide --db-url to push roads to Supabase.")
        print("Example: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        return

    from sqlalchemy import create_engine
    engine = create_engine(db_url)

    print(f"Loading roads from: {geojson_path}")
    roads = gpd.read_file(geojson_path)
    if roads.crs is None or roads.crs.to_epsg() != 4326:
        roads = roads.to_crs(epsg=4326)

    roads_df = roads[['OBJECTID', 'FULL_STREET_NAME', 'geometry']].copy()
    roads_df.columns = ['objectid', 'street_name', 'geometry']

    # Compute road length in km on projected coordinates
    roads_proj = roads.to_crs(epsg=32643)
    roads_df['road_length_km'] = (roads_proj.geometry.length / 1000.0).round(4)

    print(f"Uploading {len(roads_df)} road segments to Supabase...")
    roads_df.to_postgis('smp_roads', engine, if_exists='append', index=False)
    print("Base road network successfully populated in Supabase!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load base SMP road network into Supabase PostGIS")
    parser.add_argument("--file", default="SMP_Roads_Inside_32_Wards.geojson", help="Path to roads GeoJSON")
    parser.add_argument("--db-url", default=None, help="Supabase database URL")
    args = parser.parse_args()

    load_roads(args.file, args.db_url)
