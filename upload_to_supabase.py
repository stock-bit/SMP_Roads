"""
Rewari Road Cleaning Circles - Supabase Upload & Synchronization Script
------------------------------------------------------------------------
Allows uploading updated offline KML or GeoJSON circle polygons to Supabase.
Supabase PostGIS automatically recalculates road lengths per circle via database triggers!
"""

import os
import argparse
import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon

# To use with psycopg2 or sqlalchemy:
# pip install psycopg2-binary sqlalchemy geoalchemy2

def upload_circles_to_supabase(file_path, db_connection_url=None):
    """
    Reads offline KML or GeoJSON circles, normalizes geometries to EPSG:4326 MultiPolygon,
    and upserts into Supabase 'cleaning_circles' table.
    """
    print(f"Loading offline file: {file_path}")
    gdf = gpd.read_file(file_path)

    # Ensure WGS84 CRS
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Normalize geometries to MultiPolygon for standard DB storage
    gdf['geometry'] = gdf['geometry'].apply(
        lambda g: MultiPolygon([g]) if isinstance(g, Polygon) else g
    )

    print(f"Loaded {len(gdf)} circles.")

    if not db_connection_url:
        db_connection_url = os.getenv("SUPABASE_DB_URL")

    import re
    # If circle_id is not already a column (e.g., reading from KML), parse from Name
    if 'circle_id' not in gdf.columns:
        if 'Name' in gdf.columns:
            gdf['circle_id'] = gdf['Name'].apply(lambda n: int(re.search(r'Circle\s*(\d+)', str(n)).group(1)) if re.search(r'Circle\s*(\d+)', str(n)) else None)
            gdf['circle_name'] = gdf['Name'].apply(lambda n: f"Circle {re.search(r'Circle\s*(\d+)', str(n)).group(1)}" if re.search(r'Circle\s*(\d+)', str(n)) else str(n))
        else:
            gdf['circle_id'] = range(1, len(gdf) + 1)
            gdf['circle_name'] = [f"Circle {i}" for i in gdf['circle_id']]

    for col in ['wards_included', 'is_ward_split', 'split_details']:
        if col not in gdf.columns:
            gdf[col] = ''

    if not db_connection_url:
        print("\n[NOTE] No database connection URL provided.")
        print("To push directly to your Supabase instance, set SUPABASE_DB_URL or pass --db-url:")
        print("Example: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        print("\nValidated Circles in file:")
        print(gdf[['circle_id', 'circle_name']].head())
        return

    from sqlalchemy import create_engine
    engine = create_engine(db_connection_url)

    print("Uploading to Supabase PostGIS...")
    # Upload to a staging table or directly upsert
    gdf.to_postgis('cleaning_circles_staging', engine, if_exists='replace', index=False)

    with engine.connect() as conn:
        conn.execute("""
            INSERT INTO public.cleaning_circles (circle_id, circle_name, wards_included, is_ward_split, split_details, geom)
            SELECT 
                circle_id::int, 
                circle_name, 
                wards_included, 
                is_ward_split, 
                split_details, 
                geometry 
            FROM public.cleaning_circles_staging
            ON CONFLICT (circle_id) DO UPDATE SET
                circle_name = EXCLUDED.circle_name,
                wards_included = EXCLUDED.wards_included,
                is_ward_split = EXCLUDED.is_ward_split,
                split_details = EXCLUDED.split_details,
                geom = EXCLUDED.geom;
            DROP TABLE IF EXISTS public.cleaning_circles_staging;
        """)
        conn.commit()

    print("Successfully synchronized with Supabase! Database triggers have recomputed all road lengths.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload offline Circle KML/GeoJSON to Supabase PostGIS")
    parser.add_argument("--file", default="Rewari_30_Cleaning_Circles.kml", help="Path to KML or GeoJSON file")
    parser.add_argument("--db-url", default=None, help="Supabase PostgreSQL connection string")
    args = parser.parse_args()

    upload_circles_to_supabase(args.file, args.db_url)
