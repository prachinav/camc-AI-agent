WITH
-- 1) Define the single input point
input_pt AS (
    SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS geom
),

-- 2) ERA5 aggregation over all time
era5_agg AS (
    SELECT
        r.var_name,
        AVG(ST_Value(r.rast, input_pt.geom)) AS avg_value
    FROM input_pt
             JOIN era5_data r
                  ON ST_Intersects(r.rast, input_pt.geom)
    GROUP BY r.var_name
),

-- 3) TerraClimate aggregation
terraclim_agg AS (
    SELECT
        r.var_name,
        AVG(ST_Value(r.rast, input_pt.geom)) AS avg_value
    FROM input_pt
             JOIN terraclim_data r
                  ON ST_Intersects(r.rast, input_pt.geom)
    GROUP BY r.var_name
),

-- 4) ET & SPEI (no var_name column)
et_agg AS (
    SELECT
        AVG(ST_Value(r.rast, input_pt.geom)) AS avg_et
    FROM input_pt
             JOIN et_data r
                  ON ST_Intersects(r.rast, input_pt.geom)
),
spei_agg AS (
    SELECT
        AVG(ST_Value(r.rast, input_pt.geom)) AS avg_spei
    FROM input_pt
             JOIN spei_data r
                  ON ST_Intersects(r.rast, input_pt.geom)
),

-- 5) Static soil & elevation
soil_agg AS (
    SELECT
        s.var_name,
        ST_Value(s.rast, input_pt.geom) AS value
FROM input_pt
    JOIN soil_data s
ON ST_Intersects(s.rast, input_pt.geom)
    ),
    elev_agg AS (
SELECT
    e.var_name,
    ST_Value(e.rast, input_pt.geom) AS value
FROM input_pt
    JOIN elev_data e
ON ST_Intersects(e.rast, input_pt.geom)
    )

-- 6) Pivot into one row
SELECT
    -- ERA5 variables
    MAX(CASE WHEN e.var_name = 'evaptrans' THEN e.avg_value END) AS era5_evaptrans,
    MAX(CASE WHEN e.var_name = 'latheat'   THEN e.avg_value END) AS era5_latheat,
    MAX(CASE WHEN e.var_name = 'netsolrad' THEN e.avg_value END) AS era5_netsolrad,
    MAX(CASE WHEN e.var_name = 'press'     THEN e.avg_value END) AS era5_press,
    MAX(CASE WHEN e.var_name = 'sktemp'    THEN e.avg_value END) AS era5_sktemp,
    MAX(CASE WHEN e.var_name = 'temp'      THEN e.avg_value END) AS era5_temp,
    MAX(CASE WHEN e.var_name = 'totprec'   THEN e.avg_value END) AS era5_totprec,

    -- TerraClimate variables
    MAX(CASE WHEN t.var_name = 'aet'  THEN t.avg_value END) AS terraclim_aet,
    MAX(CASE WHEN t.var_name = 'def'  THEN t.avg_value END) AS terraclim_def,
    MAX(CASE WHEN t.var_name = 'pdsi' THEN t.avg_value END) AS terraclim_pdsi,
    MAX(CASE WHEN t.var_name = 'pet'  THEN t.avg_value END) AS terraclim_pet,
    MAX(CASE WHEN t.var_name = 'ppt'  THEN t.avg_value END) AS terraclim_ppt,

    -- ET & SPEI
    (SELECT avg_et   FROM et_agg)   AS avg_et,
    (SELECT avg_spei FROM spei_agg) AS avg_spei,

    -- Soil variables
    MAX(CASE WHEN s.var_name = 'phh2o' THEN s.value END) AS soil_ph,
    MAX(CASE WHEN s.var_name = 'sand'  THEN s.value END) AS soil_sand,
    MAX(CASE WHEN s.var_name = 'clay'  THEN s.value END) AS soil_clay,

    -- Elevation variables
    MAX(CASE WHEN el.var_name = 'elev' THEN el.value END) AS elevation,
    MAX(CASE WHEN el.var_name = 'slope' THEN el.value END) AS slope

FROM era5_agg e
         FULL  JOIN terraclim_agg t ON TRUE
         FULL  JOIN soil_agg       s ON TRUE
         FULL  JOIN elev_agg      el ON TRUE;