WITH
target AS (
  SELECT
    ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS geom,
    '2020-01-01'::date AS start_date,
    '2023-12-31'::date AS end_date
),

-- ERA5 Aggregation
era5_agg AS (
  SELECT
    r.var_name,
    AVG(ST_Value(r.rast, t.geom)) AS avg_value
  FROM era5_data r
  CROSS JOIN target t
  WHERE r.date_id BETWEEN t.start_date AND t.end_date
    AND ST_Intersects(r.rast, t.geom)
  GROUP BY r.var_name
),

-- TerraClimate Aggregation
terraclim_agg AS (
  SELECT
    r.var_name,
    AVG(ST_Value(r.rast, t.geom)) AS avg_value
  FROM terraclim_data r
  CROSS JOIN target t
  WHERE r.date_id BETWEEN t.start_date AND t.end_date
    AND ST_Intersects(r.rast, t.geom)
  GROUP BY r.var_name
),

-- SPEI Aggregation
spei_agg AS (
  SELECT
    AVG(ST_Value(r.rast, t.geom)) AS avg_spei
  FROM spei_data r
  CROSS JOIN target t
  WHERE r.date_id BETWEEN t.start_date AND t.end_date
    AND ST_Intersects(r.rast, t.geom)
),

-- -- Static Soil Data
-- soil_agg AS (
--   SELECT
--     s.var_name,
--     ST_Value(s.rast, t.geom) AS value
--   FROM soil_data s
--   CROSS JOIN target t
--   WHERE ST_Intersects(s.rast, t.geom)
-- ),

-- Static Elevation Data
elev_agg AS (
  SELECT
    s.var_name,
    ST_Value(s.rast, t.geom) AS value
  FROM elev_data s
  CROSS JOIN target t
  WHERE ST_Intersects(s.rast, t.geom)
)

-- Final SELECT with Pivoting
SELECT
  -- ERA5 variables
  MAX(CASE WHEN e.var_name = 'evaptrans'   THEN e.avg_value END) AS era5_evaptrans,
  MAX(CASE WHEN e.var_name = 'latheat'     THEN e.avg_value END) AS era5_latheat,
  MAX(CASE WHEN e.var_name = 'netsolrad'   THEN e.avg_value END) AS era5_netsolrad,
  MAX(CASE WHEN e.var_name = 'press'       THEN e.avg_value END) AS era5_press,
  MAX(CASE WHEN e.var_name = 'sktemp'      THEN e.avg_value END) AS era5_sktemp,
  MAX(CASE WHEN e.var_name = 'sotemp1'     THEN e.avg_value END) AS era5_sotemp1,
  MAX(CASE WHEN e.var_name = 'sotemp2'     THEN e.avg_value END) AS era5_sotemp2,
  MAX(CASE WHEN e.var_name = 'sotemp3'     THEN e.avg_value END) AS era5_sotemp3,
  MAX(CASE WHEN e.var_name = 'temp'        THEN e.avg_value END) AS era5_temp,
  MAX(CASE WHEN e.var_name = 'totprec'     THEN e.avg_value END) AS era5_totprec,
  MAX(CASE WHEN e.var_name = 'uwind'       THEN e.avg_value END) AS era5_uwind,
  MAX(CASE WHEN e.var_name = 'vwind'       THEN e.avg_value END) AS era5_vwind,
  MAX(CASE WHEN e.var_name = 'volsowat1'   THEN e.avg_value END) AS era5_volsowat1,
  MAX(CASE WHEN e.var_name = 'volsowat12'  THEN e.avg_value END) AS era5_volsowat12,
  MAX(CASE WHEN e.var_name = 'volsowat13'  THEN e.avg_value END) AS era5_volsowat13,

  -- TerraClimate variables
  MAX(CASE WHEN t.var_name = 'aet'   THEN t.avg_value END) AS terraclim_aet,
  MAX(CASE WHEN t.var_name = 'def'   THEN t.avg_value END) AS terraclim_def,
  MAX(CASE WHEN t.var_name = 'pdsi'  THEN t.avg_value END) AS terraclim_pdsi,
  MAX(CASE WHEN t.var_name = 'pet'   THEN t.avg_value END) AS terraclim_pet,
  MAX(CASE WHEN t.var_name = 'ppt'   THEN t.avg_value END) AS terraclim_ppt,
  MAX(CASE WHEN t.var_name = 'q'     THEN t.avg_value END) AS terraclim_q,
  MAX(CASE WHEN t.var_name = 'soil'  THEN t.avg_value END) AS terraclim_soil,
  MAX(CASE WHEN t.var_name = 'srad'  THEN t.avg_value END) AS terraclim_srad,
  MAX(CASE WHEN t.var_name = 'tmin'  THEN t.avg_value END) AS terraclim_tmin,
  MAX(CASE WHEN t.var_name = 'tmax'  THEN t.avg_value END) AS terraclim_tmax,
  MAX(CASE WHEN t.var_name = 'vap'   THEN t.avg_value END) AS terraclim_vap,
  MAX(CASE WHEN t.var_name = 'vpd'   THEN t.avg_value END) AS terraclim_vpd,
  MAX(CASE WHEN t.var_name = 'ws'    THEN t.avg_value END) AS terraclim_ws,

  -- SPEI
  (SELECT avg_spei FROM spei_agg) AS avg_spei,

  -- Static SOIL
--   MAX(CASE WHEN s.var_name = 'phh2o'     THEN s.value END) AS soil_ph,
--   MAX(CASE WHEN s.var_name = 'sand'   THEN s.value END) AS soil_sand,
--   MAX(CASE WHEN s.var_name = 'clay'   THEN s.value END) AS soil_clay,
--   MAX(CASE WHEN s.var_name = 'silt'   THEN s.value END) AS soil_silt,
--   MAX(CASE WHEN s.var_name = 'bdod'     THEN s.value END) AS soil_bdod,
--   MAX(CASE WHEN s.var_name = 'cec'     THEN s.value END) AS soil_cec,
--   MAX(CASE WHEN s.var_name = 'cfvo'     THEN s.value END) AS soil_cfvo,
--   MAX(CASE WHEN s.var_name = 'nitrogen'     THEN s.value END) AS soil_nitrogen,
--   MAX(CASE WHEN s.var_name = 'ocd'     THEN s.value END) AS soil_ocd,
--   MAX(CASE WHEN s.var_name = 'ocs'     THEN s.value END) AS soil_ocs,
--   MAX(CASE WHEN s.var_name = 'soc'     THEN s.value END) AS soil_soc,
--   MAX(CASE WHEN s.var_name = 'wv0010'     THEN s.value END) AS soil_wv0010,
--   MAX(CASE WHEN s.var_name = 'wv0030'     THEN s.value END) AS soil_wv0030,
--   MAX(CASE WHEN s.var_name = 'wv1500'     THEN s.value END) AS soil_wv1500,

  -- Static ELEVATION
  MAX(CASE WHEN el.var_name = 'elev' THEN el.value END) AS elevation,
  MAX(CASE WHEN el.var_name = 'aspect' THEN el.value END) AS aspect,
  MAX(CASE WHEN el.var_name = 'flowdir' THEN el.value END) AS flowdir,
  MAX(CASE WHEN el.var_name = 'hillshade' THEN el.value END) AS hillshade,
  MAX(CASE WHEN el.var_name = 'roughness' THEN el.value END) AS roughness,
  MAX(CASE WHEN el.var_name = 'tpi' THEN el.value END) AS tpi,
  MAX(CASE WHEN el.var_name = 'tri' THEN el.value END) AS tri,
  MAX(CASE WHEN el.var_name = 'slope' THEN el.value END) AS slope

FROM
  era5_agg e
  FULL OUTER JOIN terraclim_agg t ON TRUE
--   FULL OUTER JOIN soil_agg s ON TRUE
  FULL OUTER JOIN elev_agg el ON TRUE;
