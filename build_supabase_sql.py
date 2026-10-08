"""
Builds the complete supabase_schema_and_triggers.sql file.
Includes:
- PostGIS extension
- smp_roads table schema and spatial indices
- cleaning_circles table schema with full staff & arterial attributes
- Row Level Security (RLS) policies allowing anon and authenticated access
- Real-time road length recalculation trigger and procedure
- Analytical view vw_circle_summary
- INSERT statements for all 30 Cleaning Circles with PostGIS ST_GeomFromGeoJSON
"""

import json
import os

def generate_sql():
    geojson_path = "Rewari_30_Cleaning_Circles.geojson"
    out_sql_path = "supabase_schema_and_triggers.sql"

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data["features"]

    sql_parts = []

    sql_parts.append("""-- ======================================================================================
-- SUPABASE POSTGIS ARCHITECTURE FOR MUNICIPAL COUNCIL REWARI
-- 30 ROAD CLEANING CIRCLES & SANITARY ROSTER MANAGEMENT
-- Project URL: https://ocejvxjctwnbksqztyya.supabase.co
-- ======================================================================================

-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Create Table for SMP Road Network
-- Stores base road segments (456.60 km across 7,674 segments).
-- Circle geometries can intersect against this table to auto-calculate road length.
DROP TABLE IF EXISTS public.smp_roads CASCADE;
CREATE TABLE public.smp_roads (
    id BIGSERIAL PRIMARY KEY,
    objectid INT,
    ward_id INT,
    circle_id INT,
    street_name TEXT,
    road_length_km NUMERIC(10, 4),
    geom GEOMETRY(LineString, 4326) NOT NULL,
    midpoint_geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_LineInterpolatePoint(geom, 0.5)) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_smp_roads_geom ON public.smp_roads USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_smp_roads_midpoint ON public.smp_roads USING GIST (midpoint_geom);

-- 3. Create Table for Cleaning Circles
-- Stores the 30 cleaning circle polygon boundaries, arterial descriptors,
-- Sanitary Daroga allotments, mobile numbers, sweeper workforce counts, and shifts.
DROP TABLE IF EXISTS public.cleaning_circles CASCADE;
CREATE TABLE public.cleaning_circles (
    circle_id INT PRIMARY KEY,
    circle_name TEXT NOT NULL,
    full_title TEXT,
    arterials TEXT,
    landmarks TEXT,
    wards_included TEXT,
    is_ward_split TEXT DEFAULT 'No',
    split_details TEXT DEFAULT 'Whole',
    target_km NUMERIC(10, 3) DEFAULT 15.220,
    road_length_km NUMERIC(10, 3) DEFAULT 0,
    road_segments_count INT DEFAULT 0,
    diff_target_km NUMERIC(10, 3) DEFAULT 0,
    daroga_name TEXT DEFAULT 'Unassigned',
    daroga_phone TEXT,
    daroga_desig TEXT DEFAULT 'Sanitary Daroga',
    sweepers_count INT DEFAULT 12,
    target_m_per_sweeper INT DEFAULT 1250,
    equipment TEXT DEFAULT '1 Tipper, 8 Hand-Carts',
    shift TEXT DEFAULT 'Morning (06:00 AM - 02:00 PM)',
    notes TEXT,
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cleaning_circles_geom ON public.cleaning_circles USING GIST (geom);

-- 4. Enable Row Level Security (RLS) & Grant Public Anon Access
ALTER TABLE public.cleaning_circles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public select on cleaning_circles" ON public.cleaning_circles;
CREATE POLICY "Public select on cleaning_circles" ON public.cleaning_circles FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Public insert on cleaning_circles" ON public.cleaning_circles;
CREATE POLICY "Public insert on cleaning_circles" ON public.cleaning_circles FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "Public update on cleaning_circles" ON public.cleaning_circles;
CREATE POLICY "Public update on cleaning_circles" ON public.cleaning_circles FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "Public delete on cleaning_circles" ON public.cleaning_circles;
CREATE POLICY "Public delete on cleaning_circles" ON public.cleaning_circles FOR DELETE TO anon, authenticated USING (true);

ALTER TABLE public.smp_roads ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public select on smp_roads" ON public.smp_roads;
CREATE POLICY "Public select on smp_roads" ON public.smp_roads FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Public insert on smp_roads" ON public.smp_roads;
CREATE POLICY "Public insert on smp_roads" ON public.smp_roads FOR INSERT TO anon, authenticated WITH CHECK (true);

GRANT ALL ON TABLE public.cleaning_circles TO anon, authenticated, service_role;
GRANT ALL ON TABLE public.smp_roads TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- 5. Trigger: Automatically Recompute Road Length when Circle Geometry is Updated
CREATE OR REPLACE FUNCTION public.recompute_single_circle_road_length()
RETURNS TRIGGER AS $$
DECLARE
    v_total_km NUMERIC(10, 3);
    v_count INT;
    v_has_roads BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM public.smp_roads LIMIT 1) INTO v_has_roads;

    IF v_has_roads THEN
        SELECT 
            COALESCE(ROUND(SUM(ST_Length(ST_Intersection(r.geom::geography, NEW.geom::geography)) / 1000.0)::numeric, 3), 0),
            COUNT(r.id)
        INTO 
            v_total_km,
            v_count
        FROM public.smp_roads r
        WHERE ST_Intersects(r.geom, NEW.geom);

        IF v_count > 0 THEN
            NEW.road_length_km := v_total_km;
            NEW.road_segments_count := v_count;
        END IF;
    END IF;

    IF NEW.target_km IS NULL OR NEW.target_km = 0 THEN
        NEW.target_km := 15.220;
    END IF;

    NEW.diff_target_km := ROUND((NEW.road_length_km - NEW.target_km)::numeric, 3);
    NEW.updated_at := NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recompute_circle_road_length ON public.cleaning_circles;
CREATE TRIGGER trg_recompute_circle_road_length
BEFORE INSERT OR UPDATE OF geom ON public.cleaning_circles
FOR EACH ROW
EXECUTE FUNCTION public.recompute_single_circle_road_length();

-- 6. Batch Recomputation Procedure
CREATE OR REPLACE PROCEDURE public.recompute_all_circles()
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE public.cleaning_circles c
    SET 
        road_length_km = COALESCE(calc.total_km, 0),
        road_segments_count = COALESCE(calc.seg_count, 0),
        diff_target_km = ROUND((COALESCE(calc.total_km, 0) - c.target_km)::numeric, 3),
        updated_at = NOW()
    FROM (
        SELECT 
            c2.circle_id,
            ROUND(SUM(ST_Length(ST_Intersection(r.geom::geography, c2.geom::geography)) / 1000.0)::numeric, 3) AS total_km,
            COUNT(r.id) AS seg_count
        FROM public.cleaning_circles c2
        JOIN public.smp_roads r ON ST_Intersects(r.geom, c2.geom)
        GROUP BY c2.circle_id
    ) calc
    WHERE c.circle_id = calc.circle_id;
END;
$$;

-- 7. Analytics View
CREATE OR REPLACE VIEW public.vw_circle_summary AS
SELECT 
    circle_id,
    circle_name,
    full_title,
    arterials,
    daroga_name,
    daroga_phone,
    sweepers_count,
    road_length_km,
    target_km,
    diff_target_km,
    road_segments_count,
    ROUND((road_length_km / NULLIF(target_km, 0) * 100)::numeric, 1) AS pct_of_target,
    updated_at
FROM public.cleaning_circles
ORDER BY circle_id;

-- 8. Seed Initial 30 Cleaning Circles Data & Geometry
""")

    def escape_sql(val):
        if val is None:
            return "NULL"
        s = str(val).replace("'", "''")
        return f"'{s}'"

    for f in features:
        p = f["properties"]
        geom_json = json.dumps(f["geometry"])
        cid = p.get("circle_id")
        cname = escape_sql(p.get("circle_name", f"Circle {cid}"))
        ftitle = escape_sql(p.get("full_title", f"Circle {cid:02d}"))
        arterials = escape_sql(p.get("arterials", "Main Road Sector"))
        landmarks = escape_sql(p.get("landmarks", "Key Ground Landmarks"))
        wards = escape_sql(p.get("wards_included", ""))
        is_split = escape_sql(p.get("is_ward_split", "No"))
        split_details = escape_sql(p.get("split_details", "Whole"))
        target_km = 15.220
        road_km = float(p.get("road_length_km", 0.0))
        segs = int(p.get("road_segments", 0))
        diff_km = float(p.get("diff_target_km", 0.0))
        daroga = escape_sql(p.get("daroga_name", "Unassigned"))
        phone = escape_sql(p.get("daroga_phone", ""))
        desig = escape_sql(p.get("daroga_desig", "Sanitary Daroga"))
        sweepers = int(p.get("sweepers_count", 12))
        target_sweeper = int(p.get("target_m_per_sweeper", 1250))
        equip = escape_sql(p.get("equipment", "1 Tipper, 8 Hand-Carts"))
        shift = escape_sql(p.get("shift", "Morning (06:00 AM - 02:00 PM)"))

        stmt = f"""INSERT INTO public.cleaning_circles (
    circle_id, circle_name, full_title, arterials, landmarks,
    wards_included, is_ward_split, split_details, target_km,
    road_length_km, road_segments_count, diff_target_km,
    daroga_name, daroga_phone, daroga_desig, sweepers_count,
    target_m_per_sweeper, equipment, shift, geom
) VALUES (
    {cid}, {cname}, {ftitle}, {arterials}, {landmarks},
    {wards}, {is_split}, {split_details}, {target_km},
    {road_km}, {segs}, {diff_km},
    {daroga}, {phone}, {desig}, {sweepers},
    {target_sweeper}, {equip}, {shift},
    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON('{geom_json}'), 4326))
) ON CONFLICT (circle_id) DO UPDATE SET
    circle_name = EXCLUDED.circle_name,
    full_title = EXCLUDED.full_title,
    arterials = EXCLUDED.arterials,
    landmarks = EXCLUDED.landmarks,
    wards_included = EXCLUDED.wards_included,
    is_ward_split = EXCLUDED.is_ward_split,
    split_details = EXCLUDED.split_details,
    road_length_km = EXCLUDED.road_length_km,
    road_segments_count = EXCLUDED.road_segments_count,
    diff_target_km = EXCLUDED.diff_target_km,
    daroga_name = EXCLUDED.daroga_name,
    daroga_phone = EXCLUDED.daroga_phone,
    daroga_desig = EXCLUDED.daroga_desig,
    sweepers_count = EXCLUDED.sweepers_count,
    target_m_per_sweeper = EXCLUDED.target_m_per_sweeper,
    equipment = EXCLUDED.equipment,
    shift = EXCLUDED.shift,
    geom = EXCLUDED.geom,
    updated_at = NOW();
"""
        sql_parts.append(stmt)

    with open(out_sql_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_parts))

    print(f"Generated {out_sql_path} with {len(features)} circles seeded successfully!")

if __name__ == "__main__":
    generate_sql()
