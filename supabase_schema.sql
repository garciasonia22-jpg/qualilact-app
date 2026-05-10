-- ════════════════════════════════════════════════════════════════════════════
-- QualiLact — Esquema de base de datos para Supabase
-- ════════════════════════════════════════════════════════════════════════════
-- Pegar este archivo COMPLETO en: Supabase Dashboard → SQL Editor → New Query
-- y presionar "Run". Es idempotente: se puede ejecutar varias veces sin error.
-- ════════════════════════════════════════════════════════════════════════════
-- Notas de diseño:
--  * fecha y guardado_en se almacenan como TEXT (dd/mm/yyyy y dd/mm/yyyy HH:MM)
--    para coincidir EXACTAMENTE con lo que la app produce hoy en CSV. Esto evita
--    errores de parseo al migrar las funciones save_*_to_csv a Supabase.
--  * fotos_json es JSONB con el mismo nombre que ya lee historial.py.
--  * Las VIEWs v_rutas, v_acompanamientos, v_contramuestras reconstruyen los
--    campos estaciones_json / muestras_json (con jsonb_agg) para que el código
--    actual de historial.py funcione sin cambios cuando se haga el wire-up.
-- ════════════════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────────────────
-- 0) LIMPIEZA — recrea limpio el esquema de QualiLact
--    NO toca public.usuarios_app (ahí están los usuarios reales).
--    Todas las demás tablas listadas aquí son nuevas / aún sin datos en uso.
-- ────────────────────────────────────────────────────────────────────────────
DROP VIEW  IF EXISTS public.v_rutas                       CASCADE;
DROP VIEW  IF EXISTS public.v_acompanamientos             CASCADE;
DROP VIEW  IF EXISTS public.v_contramuestras              CASCADE;

DROP TABLE IF EXISTS public.rutas_estaciones              CASCADE;
DROP TABLE IF EXISTS public.rutas                         CASCADE;
DROP TABLE IF EXISTS public.transuiza                     CASCADE;
DROP TABLE IF EXISTS public.seguimientos_estaciones       CASCADE;
DROP TABLE IF EXISTS public.acompanamientos_muestras      CASCADE;
DROP TABLE IF EXISTS public.acompanamientos               CASCADE;
DROP TABLE IF EXISTS public.contramuestras_muestras       CASCADE;
DROP TABLE IF EXISTS public.contramuestras                CASCADE;
DROP TABLE IF EXISTS public.estaciones_catalogo           CASCADE;


-- ────────────────────────────────────────────────────────────────────────────
-- 1) CATÁLOGO DE ESTACIONES (gestionado en Registrar → Estaciones)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.estaciones_catalogo (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL,
    asesor      TEXT
);
CREATE INDEX IF NOT EXISTS ix_estaciones_catalogo_codigo ON public.estaciones_catalogo (codigo);


-- ────────────────────────────────────────────────────────────────────────────
-- 2) RUTAS  (header)  +  RUTAS_ESTACIONES  (detalle por estación)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.rutas (
    id                  BIGSERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha               TEXT,           -- dd/mm/yyyy
    ruta                TEXT,
    placa               TEXT,
    conductor           TEXT,
    volumen_declarado   INTEGER,
    vol_estaciones      INTEGER,
    diferencia          INTEGER,
    solidos_ruta        NUMERIC(6,2),
    crioscopia_ruta     NUMERIC(7,3),
    st_pond             NUMERIC(6,2),
    ic_pond             NUMERIC(7,3),
    num_estaciones      INTEGER,
    guardado_en         TEXT,           -- dd/mm/yyyy HH:MM
    fotos_json          JSONB NOT NULL DEFAULT '[]'::jsonb,  -- rutas dentro del bucket
    usuario_login       TEXT
);
CREATE INDEX IF NOT EXISTS ix_rutas_fecha ON public.rutas (fecha);
CREATE INDEX IF NOT EXISTS ix_rutas_placa ON public.rutas (placa);

CREATE TABLE IF NOT EXISTS public.rutas_estaciones (
    id              BIGSERIAL PRIMARY KEY,
    ruta_id         BIGINT NOT NULL REFERENCES public.rutas(id) ON DELETE CASCADE,
    orden           INTEGER,
    codigo          TEXT,
    grasa           NUMERIC(6,2),
    solidos         NUMERIC(6,2),
    proteina        NUMERIC(6,2),
    crioscopia      NUMERIC(7,3),
    volumen         INTEGER,
    alcohol         TEXT,
    cloruros        TEXT,
    neutralizantes  TEXT,
    agua_pct        NUMERIC(6,2),
    obs             TEXT
);
CREATE INDEX IF NOT EXISTS ix_rutas_estaciones_ruta ON public.rutas_estaciones (ruta_id);


-- ────────────────────────────────────────────────────────────────────────────
-- 3) TRANSUIZA  (registro independiente — un único carrotanque, sin estaciones)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transuiza (
    id                  BIGSERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha               TEXT,           -- dd/mm/yyyy
    ruta                TEXT,           -- siempre 'ENTRERIOS' por convención
    placa               TEXT,
    st_carrotanque      NUMERIC(6,2),
    solidos_ruta        NUMERIC(6,2),   -- ST de la muestra
    grasa_muestra       NUMERIC(6,2),
    proteina_muestra    NUMERIC(6,2),
    diferencia_solidos  NUMERIC(6,2),
    guardado_en         TEXT,           -- dd/mm/yyyy HH:MM
    fotos_json          JSONB NOT NULL DEFAULT '[]'::jsonb,
    usuario_login       TEXT
);
CREATE INDEX IF NOT EXISTS ix_transuiza_fecha ON public.transuiza (fecha);


-- ────────────────────────────────────────────────────────────────────────────
-- 4) SEGUIMIENTOS — ESTACIONES  (sub_tipo "ESTACIONES": una sola muestra)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.seguimientos_estaciones (
    id                  BIGSERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha               TEXT,           -- dd/mm/yyyy
    seg_codigo          TEXT,
    seg_quien_trajo     TEXT,
    ruta                TEXT,
    seg_responsable     TEXT,
    seg_id_muestra      TEXT,
    seg_grasa           NUMERIC(6,2),
    seg_st              NUMERIC(6,2),
    seg_proteina        NUMERIC(6,2),
    seg_ic              NUMERIC(7,3),
    seg_agua            NUMERIC(6,2),
    seg_alcohol         TEXT,
    seg_cloruros        TEXT,
    seg_neutralizantes  TEXT,
    seg_observaciones   TEXT,
    guardado_en         TEXT,           -- dd/mm/yyyy HH:MM
    fotos_json          JSONB NOT NULL DEFAULT '[]'::jsonb,
    usuario_login       TEXT
);
CREATE INDEX IF NOT EXISTS ix_seg_est_fecha  ON public.seguimientos_estaciones (fecha);
CREATE INDEX IF NOT EXISTS ix_seg_est_codigo ON public.seguimientos_estaciones (seg_codigo);


-- ────────────────────────────────────────────────────────────────────────────
-- 5) ACOMPAÑAMIENTOS  (header)  +  ACOMPAÑAMIENTOS_MUESTRAS  (detalle)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.acompanamientos (
    id                  BIGSERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha               TEXT,           -- dd/mm/yyyy
    seg_codigo          TEXT,
    seg_quien_trajo     TEXT,
    ruta                TEXT,
    seg_responsable     TEXT,
    vol_declarado       INTEGER,
    vol_muestras        INTEGER,
    diferencia_vol      INTEGER,
    solidos_ruta        NUMERIC(6,2),
    crioscopia_ruta     NUMERIC(7,3),
    st_pond             NUMERIC(6,2),
    ic_pond             NUMERIC(7,3),
    guardado_en         TEXT,           -- dd/mm/yyyy HH:MM
    fotos_json          JSONB NOT NULL DEFAULT '[]'::jsonb,
    usuario_login       TEXT
);
CREATE INDEX IF NOT EXISTS ix_acomp_fecha ON public.acompanamientos (fecha);

CREATE TABLE IF NOT EXISTS public.acompanamientos_muestras (
    id                  BIGSERIAL PRIMARY KEY,
    acompanamiento_id   BIGINT NOT NULL REFERENCES public.acompanamientos(id) ON DELETE CASCADE,
    orden               INTEGER,
    id_muestra          TEXT,
    volumen             INTEGER,
    grasa               NUMERIC(6,2),
    st                  NUMERIC(6,2),
    proteina            NUMERIC(6,2),
    ic                  NUMERIC(7,3),
    agua                NUMERIC(6,2),
    alcohol             TEXT,
    cloruros            TEXT,
    neutralizantes      TEXT,
    obs                 TEXT
);
CREATE INDEX IF NOT EXISTS ix_acomp_m_acomp ON public.acompanamientos_muestras (acompanamiento_id);


-- ────────────────────────────────────────────────────────────────────────────
-- 6) CONTRAMUESTRAS SOLICITADAS  (header + detalle por muestra)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.contramuestras (
    id                  BIGSERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha               TEXT,           -- dd/mm/yyyy
    seg_codigo          TEXT,
    seg_quien_trajo     TEXT,
    ruta                TEXT,
    seg_responsable     TEXT,
    guardado_en         TEXT,           -- dd/mm/yyyy HH:MM
    fotos_json          JSONB NOT NULL DEFAULT '[]'::jsonb,
    usuario_login       TEXT
);
CREATE INDEX IF NOT EXISTS ix_contra_fecha ON public.contramuestras (fecha);

CREATE TABLE IF NOT EXISTS public.contramuestras_muestras (
    id                  BIGSERIAL PRIMARY KEY,
    contramuestra_id    BIGINT NOT NULL REFERENCES public.contramuestras(id) ON DELETE CASCADE,
    orden               INTEGER,
    id_muestra          TEXT,
    proveedor           TEXT,
    grasa               NUMERIC(6,2),
    st                  NUMERIC(6,2),
    proteina            NUMERIC(6,2),
    ic                  NUMERIC(7,3),
    agua                NUMERIC(6,2),
    alcohol             TEXT,
    cloruros            TEXT,
    neutralizantes      TEXT,
    obs                 TEXT
);
CREATE INDEX IF NOT EXISTS ix_contra_m_contra ON public.contramuestras_muestras (contramuestra_id);


-- ════════════════════════════════════════════════════════════════════════════
-- VIEWS DE COMPATIBILIDAD CON historial.py
-- ────────────────────────────────────────────────────────────────────────────
-- historial.py espera leer registros "planos" con columnas estaciones_json y
-- muestras_json (campos JSONB). Estas vistas reconstruyen ese formato a partir
-- de las tablas detalle, para no tener que modificar historial.py durante el
-- wire-up.
-- ════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW public.v_rutas AS
SELECT
    r.*,
    'RUTAS'::text AS tipo_seguimiento,
    COALESCE(
        (SELECT jsonb_agg(
            jsonb_build_object(
                'codigo',         e.codigo,
                'grasa',          e.grasa,
                'solidos',        e.solidos,
                'proteina',       e.proteina,
                'crioscopia',     e.crioscopia,
                'volumen',        e.volumen,
                'alcohol',        e.alcohol,
                'cloruros',       e.cloruros,
                'neutralizantes', e.neutralizantes,
                'agua_pct',       e.agua_pct,
                'obs',            e.obs
            ) ORDER BY e.orden NULLS LAST, e.id)
         FROM public.rutas_estaciones e WHERE e.ruta_id = r.id),
        '[]'::jsonb
    ) AS estaciones_json
FROM public.rutas r;

CREATE OR REPLACE VIEW public.v_acompanamientos AS
SELECT
    a.*,
    'SEGUIMIENTOS'::text         AS tipo_seguimiento,
    'ACOMPAÑAMIENTOS'::text      AS sub_tipo_seguimiento,
    a.vol_declarado              AS seg_vol_declarado,
    a.vol_muestras               AS seg_vol_muestras,
    a.diferencia_vol             AS seg_diferencia_vol,
    a.solidos_ruta               AS seg_solidos_ruta,
    a.crioscopia_ruta            AS seg_crioscopia_ruta,
    a.st_pond                    AS seg_st_pond,
    a.ic_pond                    AS seg_ic_pond,
    COALESCE(
        (SELECT jsonb_agg(
            jsonb_build_object(
                'ID',              m.id_muestra,
                '_volumen',        m.volumen,
                '_grasa',          m.grasa,
                '_st',             m.st,
                '_proteina',       m.proteina,
                '_ic',             m.ic,
                '_agua',           m.agua,
                '_alcohol',        m.alcohol,
                '_cloruros',       m.cloruros,
                '_neutralizantes', m.neutralizantes,
                '_obs',            m.obs
            ) ORDER BY m.orden NULLS LAST, m.id)
         FROM public.acompanamientos_muestras m WHERE m.acompanamiento_id = a.id),
        '[]'::jsonb
    ) AS muestras_json
FROM public.acompanamientos a;

CREATE OR REPLACE VIEW public.v_contramuestras AS
SELECT
    c.*,
    'SEGUIMIENTOS'::text                    AS tipo_seguimiento,
    'CONTRAMUESTRAS SOLICITADAS'::text      AS sub_tipo_seguimiento,
    COALESCE(
        (SELECT jsonb_agg(
            jsonb_build_object(
                'ID',              m.id_muestra,
                '_proveedor',      m.proveedor,
                '_grasa',          m.grasa,
                '_st',             m.st,
                '_proteina',       m.proteina,
                '_ic',             m.ic,
                '_agua',           m.agua,
                '_alcohol',        m.alcohol,
                '_cloruros',       m.cloruros,
                '_neutralizantes', m.neutralizantes,
                '_obs',            m.obs
            ) ORDER BY m.orden NULLS LAST, m.id)
         FROM public.contramuestras_muestras m WHERE m.contramuestra_id = c.id),
        '[]'::jsonb
    ) AS muestras_json
FROM public.contramuestras c;


-- ════════════════════════════════════════════════════════════════════════════
-- BUCKET DE IMÁGENES (storage)
-- ────────────────────────────────────────────────────────────────────────────
-- La app guarda fotos de muestras / rutas / transuiza. El bucket se llama
-- "qualilact-imagenes" y la columna fotos_json (JSONB) en cada tabla almacena
-- las rutas dentro del bucket, p. ej.:
--   ["rutas/2026/05/SXX-1234_1.jpg", "rutas/2026/05/SXX-1234_2.jpg"]
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO storage.buckets (id, name, public)
VALUES ('qualilact-imagenes', 'qualilact-imagenes', false)
ON CONFLICT (id) DO NOTHING;

-- Política mínima: lectura/escritura abierta sobre el bucket (la app usa anon
-- key + tabla usuarios_app propia). Ajusta cuando agregues Supabase Auth.
DROP POLICY IF EXISTS "qualilact_imgs_anon_all" ON storage.objects;
CREATE POLICY "qualilact_imgs_anon_all" ON storage.objects
    FOR ALL
    USING  (bucket_id = 'qualilact-imagenes')
    WITH CHECK (bucket_id = 'qualilact-imagenes');


-- ════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN
-- ════════════════════════════════════════════════════════════════════════════
-- Tablas:
--   SELECT table_name FROM information_schema.tables
--   WHERE table_schema='public' ORDER BY table_name;
-- Vistas:
--   SELECT table_name FROM information_schema.views
--   WHERE table_schema='public' ORDER BY table_name;
-- Bucket:
--   SELECT id, name, public FROM storage.buckets WHERE id='qualilact-imagenes';
