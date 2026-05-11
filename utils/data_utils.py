"""Capa de acceso a datos de QualiLact.

API pública conservada para no romper los componentes:
    load_historial, save_ruta_to_csv,
    load_seguimientos, save_seguimiento_to_csv,
    load_catalogo, save_catalogo,
    delete_row_from_csv, delete_rows_from_csv, update_row_in_csv,
    delete_seg_row, delete_seg_rows, update_seg_row_in_csv

Ahora delegan a Supabase (db.supabase_repo). El nombre legacy "*_to_csv" se
conserva intencionalmente para minimizar cambios en los componentes.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from db import supabase_repo as repo


# ───────────────────────────────────────────────────────────────────────────
# RUTAS / TRANSUIZA
# ───────────────────────────────────────────────────────────────────────────
def load_historial() -> pd.DataFrame:
    df = repo.historial_load()
    if df.empty:
        return df
    df["tipo_seguimiento"] = df["tipo_seguimiento"].fillna("RUTAS").replace("", "RUTAS")
    for col in ["volumen_declarado", "vol_estaciones", "diferencia", "num_estaciones"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
                "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "fecha" in df.columns:
        df["_fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
    return df.reset_index(drop=True)


def save_ruta_to_csv(row: dict):
    repo.ruta_save(row)


def _resolve_target(orig_idx: int, loader) -> tuple[str | None, int | None]:
    """Mapea un índice posicional del DataFrame a (tabla, db_id) en Supabase."""
    df = loader()
    if orig_idx not in df.index:
        return None, None
    r = df.loc[orig_idx]
    return r.get("_db_table"), r.get("_db_id")


def delete_row_from_csv(orig_idx: int):
    table, db_id = _resolve_target(orig_idx, load_historial)
    if table and db_id is not None:
        repo.historial_delete(table, int(db_id))


def delete_rows_from_csv(orig_indices: list):
    df = load_historial()
    for i in orig_indices:
        if i in df.index:
            r = df.loc[i]
            t, did = r.get("_db_table"), r.get("_db_id")
            if t and did is not None:
                repo.historial_delete(t, int(did))


def update_row_in_csv(orig_idx: int, new_vals: dict):
    table, db_id = _resolve_target(orig_idx, load_historial)
    if table and db_id is not None:
        repo.historial_update(table, int(db_id), new_vals)


# ───────────────────────────────────────────────────────────────────────────
# SEGUIMIENTOS
# ───────────────────────────────────────────────────────────────────────────
def load_seguimientos() -> pd.DataFrame:
    df = repo.seguimientos_load()
    if df.empty:
        return df
    if "sub_tipo_seguimiento" in df.columns:
        df["sub_tipo_seguimiento"] = df["sub_tipo_seguimiento"].replace("TERCEROS", "ESTACIONES")
    for col in ["seg_grasa", "seg_st", "seg_ic", "seg_agua",
                "seg_vol_declarado", "seg_vol_muestras", "seg_diferencia_vol",
                "seg_solidos_ruta", "seg_crioscopia_ruta", "seg_st_pond", "seg_ic_pond"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "fecha" in df.columns:
        df["_fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
    return df.reset_index(drop=True)


def save_seguimiento_to_csv(row: dict):
    repo.seguimiento_save(row)


def delete_seg_row(orig_idx: int):
    table, db_id = _resolve_target(orig_idx, load_seguimientos)
    if table and db_id is not None:
        repo.seguimiento_delete(table, int(db_id))


def delete_seg_rows(orig_indices: list):
    df = load_seguimientos()
    for i in orig_indices:
        if i in df.index:
            r = df.loc[i]
            t, did = r.get("_db_table"), r.get("_db_id")
            if t and did is not None:
                repo.seguimiento_delete(t, int(did))


def update_seg_row_in_csv(orig_idx: int, new_vals: dict):
    table, db_id = _resolve_target(orig_idx, load_seguimientos)
    if table and db_id is not None:
        repo.seguimiento_update(table, int(db_id), new_vals)


# ───────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE ESTACIONES
# ───────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_catalogo() -> pd.DataFrame:
    try:
        return repo.cat_load()
    except Exception:
        return pd.DataFrame(columns=["codigo", "nombre", "asesor"])


def save_catalogo(df: pd.DataFrame):
    repo.cat_save_full(df)
    load_catalogo.clear()
