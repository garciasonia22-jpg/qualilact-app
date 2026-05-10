"""Repositorio Supabase para QualiLact.

Encapsula todas las operaciones contra Supabase (tablas, vistas y Storage).
Las funciones públicas devuelven y aceptan exactamente los mismos formatos que
las antiguas helpers basadas en CSV / disco, de modo que utils/data_utils.py
pueda mantener su API sin filtrarse hacia los componentes.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pandas as pd
import streamlit as st

from db.supabase_client import init_connection

BUCKET = "qualilact-imagenes"

# ─── Tipos de seguimiento / tablas ─────────────────────────────────────────
T_RUTAS                   = "rutas"
T_TRANSUIZA               = "transuiza"
T_SEG_ESTACIONES          = "seguimientos_estaciones"
T_ACOMP                   = "acompanamientos"
T_ACOMP_DET               = "acompanamientos_muestras"
T_CONTRA                  = "contramuestras"
T_CONTRA_DET              = "contramuestras_muestras"
T_RUTAS_DET               = "rutas_estaciones"
T_CATALOGO                = "estaciones_catalogo"

V_RUTAS                   = "v_rutas"
V_ACOMP                   = "v_acompanamientos"
V_CONTRA                  = "v_contramuestras"


# ───────────────────────────────────────────────────────────────────────────
# Utilidades internas
# ───────────────────────────────────────────────────────────────────────────
def _client():
    return init_connection()


def _to_json_str(v: Any) -> str:
    """Convierte un valor JSONB devuelto por PostgREST (lista/dict) a string."""
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _clean_row(row: dict, allowed: set[str]) -> dict:
    """Filtra el dict a solo columnas permitidas, normaliza vacíos a None.
    Hace trim de strings para evitar persistir espacios sobrantes."""
    out = {}
    for k, v in row.items():
        if k not in allowed:
            continue
        if isinstance(v, str):
            v = v.strip()
        if v == "" or v is None:
            out[k] = None
        else:
            out[k] = v
    return out


# Coerciones por columna para builders de UPDATE (solo se aplican si la clave
# está presente en `vals`; así no se inyecta NULL accidentalmente).
_NUM_INT  = {"volumen_declarado", "vol_estaciones", "diferencia", "num_estaciones",
             "vol_declarado", "vol_muestras", "diferencia_vol"}
_NUM_FLOAT = {"solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
              "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos",
              "seg_grasa", "seg_st", "seg_proteina", "seg_ic", "seg_agua",
              "grasa", "st", "proteina", "ic", "agua", "agua_pct"}


def _coerce(key: str, v):
    if key in _NUM_INT:
        return _safe_int(v)
    if key in _NUM_FLOAT:
        return _safe_float(v)
    return v


def _build_update_payload(vals: dict, allowed: set[str], translate: dict | None = None) -> dict:
    """Construye el payload de UPDATE usando solo las claves presentes en `vals`.
    Si `translate` se da, mapea nombres antes de filtrar. Aplica coerción y trim.
    Excluye `fotos_json` y otros JSONB (se manejan aparte por el caller)."""
    out = {}
    for raw_k, v in vals.items():
        k = (translate.get(raw_k, raw_k) if translate else raw_k)
        if k not in allowed or k in ("fotos_json",):
            continue
        v = _coerce(k, v)
        if isinstance(v, str):
            v = v.strip()
        if v == "":
            v = None
        out[k] = v
    return out


def _safe_int(v):
    try:
        if v is None or v == "":
            return None
        f = float(str(v).replace(",", "."))
        if f != f:  # NaN
            return None
        return int(round(f))
    except Exception:
        return None


def _safe_float(v):
    try:
        if v is None or v == "":
            return None
        f = float(str(v).replace(",", "."))
        if f != f:  # NaN
            return None
        return f
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────────────────
# Storage (imágenes)
# ───────────────────────────────────────────────────────────────────────────
def upload_imagen(path: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Sube bytes al bucket y devuelve el path interno."""
    cli = _client()
    cli.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return path


@st.cache_data(ttl=1800, show_spinner=False)
def get_imagen_url(path: str) -> str | None:
    """Devuelve URL firmada (1h) para un objeto en el bucket. None si no existe."""
    if not path:
        return None
    try:
        cli = _client()
        res = cli.storage.from_(BUCKET).create_signed_url(path, 3600)
        # supabase-py 2.x devuelve {'signedURL': '...'} o {'signed_url': '...'}
        return res.get("signedURL") or res.get("signed_url")
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────────────────
# Catálogo de estaciones
# ───────────────────────────────────────────────────────────────────────────
def cat_load() -> pd.DataFrame:
    cli = _client()
    res = cli.table(T_CATALOGO).select("codigo,nombre,asesor").order("codigo").execute()
    rows = res.data or []
    if not rows:
        return pd.DataFrame(columns=["codigo", "nombre", "asesor"])
    df = pd.DataFrame(rows)
    for c in ["codigo", "nombre", "asesor"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str).str.strip()
    df["nombre"] = df["nombre"].str.upper()
    return df[["codigo", "nombre", "asesor"]]


def cat_save_full(df: pd.DataFrame) -> None:
    """Sincroniza la tabla con el DataFrame completo (delete-missing + upsert)."""
    cli = _client()
    df = df.copy()
    for c in ["codigo", "nombre", "asesor"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str).str.strip()
    df = df[df["codigo"] != ""]
    nuevos_codigos = df["codigo"].tolist()

    # Borrar los que ya no estén
    actuales = cli.table(T_CATALOGO).select("codigo").execute().data or []
    for r in actuales:
        if r["codigo"] not in nuevos_codigos:
            cli.table(T_CATALOGO).delete().eq("codigo", r["codigo"]).execute()

    # Upsert por código
    if not df.empty:
        payload = df[["codigo", "nombre", "asesor"]].to_dict(orient="records")
        cli.table(T_CATALOGO).upsert(payload, on_conflict="codigo").execute()


# ───────────────────────────────────────────────────────────────────────────
# RUTAS / TRANSUIZA  →  load_historial
# ───────────────────────────────────────────────────────────────────────────
_RUTAS_HEADER_COLS = {
    "fecha", "ruta", "placa", "conductor",
    "volumen_declarado", "vol_estaciones", "diferencia",
    "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
    "num_estaciones", "guardado_en", "fotos_json", "usuario_login",
}
_TRANSUIZA_COLS = {
    "fecha", "ruta", "placa",
    "st_carrotanque", "solidos_ruta", "grasa_muestra",
    "proteina_muestra", "diferencia_solidos",
    "guardado_en", "fotos_json", "usuario_login",
}
_RUTAS_ESTACION_COLS_MAP = {  # claves del dict de la app → columnas tabla
    "codigo": "codigo",
    "grasa": "grasa",
    "solidos": "solidos",
    "proteina": "proteina",
    "crioscopia": "crioscopia",
    "volumen": "volumen",
    "alcohol": "alcohol",
    "cloruros": "cloruros",
    "neutralizantes": "neutralizantes",
    "agua_pct": "agua_pct",
    "obs": "obs",
}


def _serialize_estaciones_json(estaciones_str: str) -> list[dict]:
    if not estaciones_str:
        return []
    try:
        data = json.loads(estaciones_str)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _insert_rutas_estaciones(ruta_id: int, estaciones: list[dict]) -> None:
    cli = _client()
    if not estaciones:
        return
    payload = []
    for orden, e in enumerate(estaciones, start=1):
        row = {"ruta_id": ruta_id, "orden": orden}
        for src, dst in _RUTAS_ESTACION_COLS_MAP.items():
            v = e.get(src)
            if dst in ("grasa", "solidos", "proteina", "crioscopia", "agua_pct"):
                row[dst] = _safe_float(v)
            elif dst == "volumen":
                row[dst] = _safe_int(v)
            else:
                row[dst] = v if v not in ("", None) else None
        payload.append(row)
    cli.table(T_RUTAS_DET).insert(payload).execute()


def ruta_save(row: dict) -> int:
    """Inserta una RUTA o TRANSUIZA. Devuelve el id insertado."""
    cli = _client()
    tipo = (row.get("tipo_seguimiento") or "RUTAS").upper()
    if tipo == "TRANSUIZA":
        payload = _clean_row({
            **row,
            "st_carrotanque":     _safe_float(row.get("st_carrotanque")),
            "solidos_ruta":       _safe_float(row.get("solidos_ruta")),
            "grasa_muestra":      _safe_float(row.get("grasa_muestra")),
            "proteina_muestra":   _safe_float(row.get("proteina_muestra")),
            "diferencia_solidos": _safe_float(row.get("diferencia_solidos")),
        }, _TRANSUIZA_COLS)
        # fotos_json viene como string JSON desde la app → pasar como lista
        if "fotos_json" in payload and isinstance(payload["fotos_json"], str):
            try:    payload["fotos_json"] = json.loads(payload["fotos_json"])
            except: payload["fotos_json"] = []
        res = cli.table(T_TRANSUIZA).insert(payload).execute()
        return (res.data or [{}])[0].get("id")

    # RUTAS
    payload = _clean_row({
        **row,
        "volumen_declarado": _safe_int(row.get("volumen_declarado")),
        "vol_estaciones":    _safe_int(row.get("vol_estaciones")),
        "diferencia":        _safe_int(row.get("diferencia")),
        "solidos_ruta":      _safe_float(row.get("solidos_ruta")),
        "crioscopia_ruta":   _safe_float(row.get("crioscopia_ruta")),
        "st_pond":           _safe_float(row.get("st_pond")),
        "ic_pond":           _safe_float(row.get("ic_pond")),
        "num_estaciones":    _safe_int(row.get("num_estaciones")),
    }, _RUTAS_HEADER_COLS)
    if "fotos_json" in payload and isinstance(payload["fotos_json"], str):
        try:    payload["fotos_json"] = json.loads(payload["fotos_json"])
        except: payload["fotos_json"] = []
    res = cli.table(T_RUTAS).insert(payload).execute()
    ruta_id = (res.data or [{}])[0].get("id")
    estaciones = _serialize_estaciones_json(row.get("estaciones_json", ""))
    if ruta_id and estaciones:
        _insert_rutas_estaciones(ruta_id, estaciones)
    return ruta_id


def historial_load() -> pd.DataFrame:
    """Devuelve un DataFrame compatible con la antigua load_historial.
    Columnas extra: _db_id, _db_table.
    """
    cli = _client()
    rutas  = cli.table(V_RUTAS).select("*").order("id").execute().data or []
    trans  = cli.table(T_TRANSUIZA).select("*").order("id").execute().data or []
    rows = []
    for r in rutas:
        rows.append({
            "_db_id":            r.get("id"),
            "_db_table":         T_RUTAS,
            "tipo_seguimiento":  "RUTAS",
            "fecha":             r.get("fecha") or "",
            "ruta":              r.get("ruta") or "",
            "placa":             r.get("placa") or "",
            "conductor":         r.get("conductor") or "",
            "volumen_declarado": r.get("volumen_declarado"),
            "vol_estaciones":    r.get("vol_estaciones"),
            "diferencia":        r.get("diferencia"),
            "solidos_ruta":      r.get("solidos_ruta"),
            "crioscopia_ruta":   r.get("crioscopia_ruta"),
            "st_pond":           r.get("st_pond"),
            "ic_pond":           r.get("ic_pond"),
            "num_estaciones":    r.get("num_estaciones"),
            "guardado_en":       r.get("guardado_en") or "",
            "st_carrotanque":    None,
            "grasa_muestra":     None,
            "proteina_muestra":  None,
            "diferencia_solidos":None,
            "estaciones_json":   _to_json_str(r.get("estaciones_json")),
            "fotos_json":        _to_json_str(r.get("fotos_json")),
        })
    for r in trans:
        rows.append({
            "_db_id":            r.get("id"),
            "_db_table":         T_TRANSUIZA,
            "tipo_seguimiento":  "TRANSUIZA",
            "fecha":             r.get("fecha") or "",
            "ruta":              r.get("ruta") or "",
            "placa":             r.get("placa") or "",
            "conductor":         "",
            "volumen_declarado": None,
            "vol_estaciones":    None,
            "diferencia":        None,
            "solidos_ruta":      r.get("solidos_ruta"),
            "crioscopia_ruta":   None,
            "st_pond":           None,
            "ic_pond":           None,
            "num_estaciones":    None,
            "guardado_en":       r.get("guardado_en") or "",
            "st_carrotanque":    r.get("st_carrotanque"),
            "grasa_muestra":     r.get("grasa_muestra"),
            "proteina_muestra":  r.get("proteina_muestra"),
            "diferencia_solidos":r.get("diferencia_solidos"),
            "estaciones_json":   "",
            "fotos_json":        _to_json_str(r.get("fotos_json")),
        })
    return pd.DataFrame(rows)


def historial_delete(table: str, db_id: int) -> None:
    _client().table(table).delete().eq("id", db_id).execute()


def historial_update(table: str, db_id: int, vals: dict) -> None:
    """Actualiza una fila de rutas/transuiza. Si vals trae estaciones_json (RUTAS),
    reemplaza las estaciones detalle."""
    cli = _client()
    if table == T_RUTAS:
        head = _build_update_payload(vals, _RUTAS_HEADER_COLS)
        if "fotos_json" in vals:
            v = vals["fotos_json"]
            head["fotos_json"] = json.loads(v) if isinstance(v, str) else v
        if head:
            cli.table(T_RUTAS).update(head).eq("id", db_id).execute()
        if "estaciones_json" in vals:
            cli.table(T_RUTAS_DET).delete().eq("ruta_id", db_id).execute()
            ests = _serialize_estaciones_json(vals.get("estaciones_json", ""))
            if ests:
                _insert_rutas_estaciones(db_id, ests)
    elif table == T_TRANSUIZA:
        body = _build_update_payload(vals, _TRANSUIZA_COLS)
        if "fotos_json" in vals:
            v = vals["fotos_json"]
            body["fotos_json"] = json.loads(v) if isinstance(v, str) else v
        if body:
            cli.table(T_TRANSUIZA).update(body).eq("id", db_id).execute()


# ───────────────────────────────────────────────────────────────────────────
# SEGUIMIENTOS
# ───────────────────────────────────────────────────────────────────────────
_SEG_EST_COLS = {
    "fecha", "seg_codigo", "seg_quien_trajo", "ruta", "seg_responsable",
    "seg_id_muestra", "seg_grasa", "seg_st", "seg_proteina", "seg_ic",
    "seg_agua", "seg_alcohol", "seg_cloruros", "seg_neutralizantes",
    "seg_observaciones", "guardado_en", "fotos_json", "usuario_login",
}
_ACOMP_HEADER_COLS = {
    "fecha", "seg_codigo", "seg_quien_trajo", "ruta", "seg_responsable",
    "vol_declarado", "vol_muestras", "diferencia_vol",
    "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
    "guardado_en", "fotos_json", "usuario_login",
}
_CONTRA_HEADER_COLS = {
    "fecha", "seg_codigo", "seg_quien_trajo", "ruta", "seg_responsable",
    "guardado_en", "fotos_json", "usuario_login",
}

_ACOMP_FIELD_MAP = {  # seg_* (alias en vista) → real en tabla
    "seg_vol_declarado":   "vol_declarado",
    "seg_vol_muestras":    "vol_muestras",
    "seg_diferencia_vol":  "diferencia_vol",
    "seg_solidos_ruta":    "solidos_ruta",
    "seg_crioscopia_ruta": "crioscopia_ruta",
    "seg_st_pond":         "st_pond",
    "seg_ic_pond":         "ic_pond",
}


def _muestras_payload_acomp(parent_id: int, muestras: list[dict]) -> list[dict]:
    out = []
    for orden, m in enumerate(muestras, start=1):
        out.append({
            "acompanamiento_id": parent_id,
            "orden":             orden,
            "id_muestra":        m.get("ID") or m.get("_id_muestra"),
            "volumen":           _safe_int(m.get("_volumen")),
            "grasa":             _safe_float(m.get("_grasa")),
            "st":                _safe_float(m.get("_st")),
            "proteina":          _safe_float(m.get("_proteina")),
            "ic":                _safe_float(m.get("_ic")),
            "agua":              _safe_float(m.get("_agua")),
            "alcohol":           m.get("_alcohol") or "N/A",
            "cloruros":          m.get("_cloruros") or "N/A",
            "neutralizantes":    m.get("_neutralizantes") or "N/A",
            "obs":               str(m.get("_obs") or ""),
        })
    return out


def _muestras_payload_contra(parent_id: int, muestras: list[dict]) -> list[dict]:
    out = []
    for orden, m in enumerate(muestras, start=1):
        out.append({
            "contramuestra_id": parent_id,
            "orden":            orden,
            "id_muestra":       m.get("ID") or m.get("_id_muestra"),
            "proveedor":        m.get("_proveedor") or m.get("PROVEEDOR"),
            "grasa":            _safe_float(m.get("_grasa")),
            "st":               _safe_float(m.get("_st")),
            "proteina":         _safe_float(m.get("_proteina")),
            "ic":               _safe_float(m.get("_ic")),
            "agua":             _safe_float(m.get("_agua")),
            "alcohol":          m.get("_alcohol") or "N/A",
            "cloruros":         m.get("_cloruros") or "N/A",
            "neutralizantes":   m.get("_neutralizantes") or "N/A",
            "obs":              str(m.get("_obs") or ""),
        })
    return out


def seguimiento_save(row: dict) -> tuple[str, int]:
    """Guarda un seguimiento. Devuelve (tabla, id) del header."""
    cli = _client()
    sub = (row.get("sub_tipo_seguimiento") or "ESTACIONES").upper()

    if sub == "ACOMPAÑAMIENTOS":
        head = _clean_row({
            **row,
            "vol_declarado":     _safe_int(row.get("seg_vol_declarado")),
            "vol_muestras":      _safe_int(row.get("seg_vol_muestras")),
            "diferencia_vol":    _safe_int(row.get("seg_diferencia_vol")),
            "solidos_ruta":      _safe_float(row.get("seg_solidos_ruta")),
            "crioscopia_ruta":   _safe_float(row.get("seg_crioscopia_ruta")),
            "st_pond":           _safe_float(row.get("seg_st_pond")),
            "ic_pond":           _safe_float(row.get("seg_ic_pond")),
        }, _ACOMP_HEADER_COLS)
        if "fotos_json" in head and isinstance(head["fotos_json"], str):
            try:    head["fotos_json"] = json.loads(head["fotos_json"])
            except: head["fotos_json"] = []
        res = cli.table(T_ACOMP).insert(head).execute()
        parent_id = (res.data or [{}])[0].get("id")
        muestras = _serialize_estaciones_json(row.get("muestras_json", ""))
        if parent_id and muestras:
            cli.table(T_ACOMP_DET).insert(_muestras_payload_acomp(parent_id, muestras)).execute()
        return (T_ACOMP, parent_id)

    if sub == "CONTRAMUESTRAS SOLICITADAS":
        head = _clean_row(row, _CONTRA_HEADER_COLS)
        if "fotos_json" in head and isinstance(head["fotos_json"], str):
            try:    head["fotos_json"] = json.loads(head["fotos_json"])
            except: head["fotos_json"] = []
        res = cli.table(T_CONTRA).insert(head).execute()
        parent_id = (res.data or [{}])[0].get("id")
        muestras = _serialize_estaciones_json(row.get("muestras_json", ""))
        if parent_id and muestras:
            cli.table(T_CONTRA_DET).insert(_muestras_payload_contra(parent_id, muestras)).execute()
        return (T_CONTRA, parent_id)

    # ESTACIONES (sub_tipo por defecto, una sola muestra)
    body = _clean_row({
        **row,
        "seg_grasa":   _safe_float(row.get("seg_grasa")),
        "seg_st":      _safe_float(row.get("seg_st")),
        "seg_proteina":_safe_float(row.get("seg_proteina")),
        "seg_ic":      _safe_float(row.get("seg_ic")),
        "seg_agua":    _safe_float(row.get("seg_agua")),
    }, _SEG_EST_COLS)
    if "fotos_json" in body and isinstance(body["fotos_json"], str):
        try:    body["fotos_json"] = json.loads(body["fotos_json"])
        except: body["fotos_json"] = []
    res = cli.table(T_SEG_ESTACIONES).insert(body).execute()
    return (T_SEG_ESTACIONES, (res.data or [{}])[0].get("id"))


def seguimientos_load() -> pd.DataFrame:
    """DataFrame compatible con load_seguimientos. _db_id, _db_table extra."""
    cli = _client()
    est    = cli.table(T_SEG_ESTACIONES).select("*").order("id").execute().data or []
    acomp  = cli.table(V_ACOMP).select("*").order("id").execute().data or []
    contra = cli.table(V_CONTRA).select("*").order("id").execute().data or []

    rows = []
    for r in est:
        rows.append({
            "_db_id":               r.get("id"),
            "_db_table":            T_SEG_ESTACIONES,
            "tipo_seguimiento":     "SEGUIMIENTOS",
            "sub_tipo_seguimiento": "ESTACIONES",
            "fecha":                r.get("fecha") or "",
            "seg_codigo":           r.get("seg_codigo") or "",
            "seg_quien_trajo":      r.get("seg_quien_trajo") or "",
            "ruta":                 r.get("ruta") or "",
            "seg_responsable":      r.get("seg_responsable") or "",
            "seg_id_muestra":       r.get("seg_id_muestra") or "",
            "seg_volumen":          "",
            "seg_grasa":            r.get("seg_grasa"),
            "seg_st":               r.get("seg_st"),
            "seg_ic":               r.get("seg_ic"),
            "seg_agua":             r.get("seg_agua"),
            "seg_alcohol":          r.get("seg_alcohol") or "",
            "seg_cloruros":         r.get("seg_cloruros") or "",
            "seg_neutralizantes":   r.get("seg_neutralizantes") or "",
            "seg_observaciones":    r.get("seg_observaciones") or "",
            "seg_vol_declarado":    None,
            "seg_vol_muestras":     None,
            "seg_diferencia_vol":   None,
            "seg_solidos_ruta":     None,
            "seg_crioscopia_ruta":  None,
            "seg_st_pond":          None,
            "seg_ic_pond":          None,
            "muestras_json":        "",
            "guardado_en":          r.get("guardado_en") or "",
            "fotos_json":           _to_json_str(r.get("fotos_json")),
        })
    for r in acomp:
        rows.append({
            "_db_id":               r.get("id"),
            "_db_table":            T_ACOMP,
            "tipo_seguimiento":     "SEGUIMIENTOS",
            "sub_tipo_seguimiento": "ACOMPAÑAMIENTOS",
            "fecha":                r.get("fecha") or "",
            "seg_codigo":           r.get("seg_codigo") or "",
            "seg_quien_trajo":      r.get("seg_quien_trajo") or "",
            "ruta":                 r.get("ruta") or "",
            "seg_responsable":      r.get("seg_responsable") or "",
            "seg_id_muestra":       "",
            "seg_volumen":          "",
            "seg_grasa":            None, "seg_st": None, "seg_ic": None, "seg_agua": None,
            "seg_alcohol":          "", "seg_cloruros": "", "seg_neutralizantes": "",
            "seg_observaciones":    "",
            "seg_vol_declarado":    r.get("seg_vol_declarado"),
            "seg_vol_muestras":     r.get("seg_vol_muestras"),
            "seg_diferencia_vol":   r.get("seg_diferencia_vol"),
            "seg_solidos_ruta":     r.get("seg_solidos_ruta"),
            "seg_crioscopia_ruta":  r.get("seg_crioscopia_ruta"),
            "seg_st_pond":          r.get("seg_st_pond"),
            "seg_ic_pond":          r.get("seg_ic_pond"),
            "muestras_json":        _to_json_str(r.get("muestras_json")),
            "guardado_en":          r.get("guardado_en") or "",
            "fotos_json":           _to_json_str(r.get("fotos_json")),
        })
    for r in contra:
        rows.append({
            "_db_id":               r.get("id"),
            "_db_table":            T_CONTRA,
            "tipo_seguimiento":     "SEGUIMIENTOS",
            "sub_tipo_seguimiento": "CONTRAMUESTRAS SOLICITADAS",
            "fecha":                r.get("fecha") or "",
            "seg_codigo":           r.get("seg_codigo") or "",
            "seg_quien_trajo":      r.get("seg_quien_trajo") or "",
            "ruta":                 r.get("ruta") or "",
            "seg_responsable":      r.get("seg_responsable") or "",
            "seg_id_muestra":       "",
            "seg_volumen":          "",
            "seg_grasa":            None, "seg_st": None, "seg_ic": None, "seg_agua": None,
            "seg_alcohol":          "", "seg_cloruros": "", "seg_neutralizantes": "",
            "seg_observaciones":    "",
            "seg_vol_declarado":    None, "seg_vol_muestras": None, "seg_diferencia_vol": None,
            "seg_solidos_ruta":     None, "seg_crioscopia_ruta": None,
            "seg_st_pond":          None, "seg_ic_pond": None,
            "muestras_json":        _to_json_str(r.get("muestras_json")),
            "guardado_en":          r.get("guardado_en") or "",
            "fotos_json":           _to_json_str(r.get("fotos_json")),
        })
    return pd.DataFrame(rows)


def seguimiento_delete(table: str, db_id: int) -> None:
    _client().table(table).delete().eq("id", db_id).execute()


def seguimiento_update(table: str, db_id: int, vals: dict) -> None:
    cli = _client()
    if table == T_SEG_ESTACIONES:
        body = _build_update_payload(vals, _SEG_EST_COLS)
        if "fotos_json" in vals:
            v = vals["fotos_json"]
            body["fotos_json"] = json.loads(v) if isinstance(v, str) else v
        if body:
            cli.table(T_SEG_ESTACIONES).update(body).eq("id", db_id).execute()
        return

    if table == T_ACOMP:
        head = _build_update_payload(vals, _ACOMP_HEADER_COLS, translate=_ACOMP_FIELD_MAP)
        if "fotos_json" in vals:
            v = vals["fotos_json"]
            head["fotos_json"] = json.loads(v) if isinstance(v, str) else v
        if head:
            cli.table(T_ACOMP).update(head).eq("id", db_id).execute()
        if "muestras_json" in vals:
            cli.table(T_ACOMP_DET).delete().eq("acompanamiento_id", db_id).execute()
            ms = _serialize_estaciones_json(vals.get("muestras_json", ""))
            if ms:
                cli.table(T_ACOMP_DET).insert(_muestras_payload_acomp(db_id, ms)).execute()
        return

    if table == T_CONTRA:
        head = _build_update_payload(vals, _CONTRA_HEADER_COLS)
        if "fotos_json" in vals:
            v = vals["fotos_json"]
            head["fotos_json"] = json.loads(v) if isinstance(v, str) else v
        if head:
            cli.table(T_CONTRA).update(head).eq("id", db_id).execute()
        if "muestras_json" in vals:
            cli.table(T_CONTRA_DET).delete().eq("contramuestra_id", db_id).execute()
            ms = _serialize_estaciones_json(vals.get("muestras_json", ""))
            if ms:
                cli.table(T_CONTRA_DET).insert(_muestras_payload_contra(db_id, ms)).execute()
