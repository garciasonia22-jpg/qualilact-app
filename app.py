from datetime import datetime, date
import base64
import csv
import io
import os
import re
import json

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as XLImage
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image as RLImage, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ── Persistencia CSV ─────────────────────────────────────────────────────────
CSV_PATH = "rutas_historial.csv"
CSV_COLS = [
    "tipo_seguimiento",
    "fecha", "ruta", "placa", "conductor",
    "volumen_declarado", "vol_estaciones", "diferencia",
    "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
    "num_estaciones", "guardado_en",
    "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos",
    "estaciones_json",
]

# ── CSV separado para SEGUIMIENTOS ───────────────────────────────────────────
SEG_CSV_PATH = "seguimientos_historial.csv"
SEG_COLS = [
    "sub_tipo_seguimiento", "fecha",
    "seg_codigo", "seg_quien_trajo", "ruta", "seg_responsable",
    "seg_id_muestra", "seg_grasa", "seg_st", "seg_ic", "seg_agua",
    "seg_alcohol", "seg_cloruros", "seg_neutralizantes", "seg_observaciones",
    "guardado_en",
]

DRAFT_PATH = "borrador_autoguardado.json"
DRAFT_EXACT_KEYS = [
    "continuar", "_tipo_servicio_guardado", "_sub_tipo_seg_guardado",
    "tipo_servicio_select", "sub_tipo_seg_select",
    "fecha_ruta", "nombre_ruta", "placa_vehiculo", "conductor",
    "volumen_ruta", "solidos_totales", "crioscopia",
    "imagenes_confirmadas", "imagenes_nombres_guardados",
    "estaciones_guardadas", "form_ver",
    "trans_fecha", "trans_placa", "trans_st_carrotanque",
    "trans_grasa", "trans_st_muestra", "trans_proteina",
    "seg_fecha", "seg_codigo", "seg_quien_trajo", "seg_ruta_acomp",
    "seg_responsable", "seg_quality_key_counter",
    "acomp_muestras", "contra_muestras",
]
DRAFT_PREFIXES = (
    "nue_",
    "seg_id_muestra_", "seg_grasa_", "seg_st_", "seg_ic_raw_", "seg_agua_",
    "seg_alcohol_", "seg_cloruros_", "seg_neutralizantes_", "seg_observaciones_",
)


def _draft_encode(value):
    if isinstance(value, datetime):
        return {"__draft_type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__draft_type": "date", "value": value.isoformat()}
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _draft_decode(value):
    if isinstance(value, dict) and value.get("__draft_type") in ("date", "datetime"):
        raw = value.get("value", "")
        try:
            return datetime.fromisoformat(raw).date()
        except Exception:
            return date.today()
    return value


def restore_draft_state():
    if st.session_state.get("_draft_restored"):
        return
    st.session_state["_draft_restored"] = True
    if not os.path.exists(DRAFT_PATH):
        return
    try:
        with open(DRAFT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    if "tipo_servicio_select" not in data and "_tipo_servicio_guardado" in data:
        data["tipo_servicio_select"] = data.get("_tipo_servicio_guardado")
    if "sub_tipo_seg_select" not in data and "_sub_tipo_seg_guardado" in data:
        data["sub_tipo_seg_select"] = data.get("_sub_tipo_seg_guardado")
    for key, value in data.items():
        if key not in st.session_state:
            st.session_state[key] = _draft_decode(value)


def save_draft_state():
    if st.session_state.pop("_skip_draft_save_once", False):
        return
    data = {}
    for key in DRAFT_EXACT_KEYS:
        if key in st.session_state:
            data[key] = _draft_encode(st.session_state[key])
    for key, value in st.session_state.items():
        if key.startswith(DRAFT_PREFIXES):
            data[key] = _draft_encode(value)
    try:
        with open(DRAFT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_draft_state():
    st.session_state["_skip_draft_save_once"] = True
    try:
        if os.path.exists(DRAFT_PATH):
            os.remove(DRAFT_PATH)
    except Exception:
        pass


def load_historial() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=CSV_COLS)
    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
        # Columnas nuevas que pueden no existir en CSVs anteriores
        for col in CSV_COLS:
            if col not in df.columns:
                df[col] = ""
        # Tipo de seguimiento: filas vacías → RUTAS (compatibilidad)
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
        return df
    except Exception:
        return pd.DataFrame(columns=CSV_COLS)


def save_ruta_to_csv(row: dict):
    if os.path.exists(CSV_PATH):
        df = load_historial()
        if "_fecha_dt" in df.columns:
            df = df.drop(columns=["_fecha_dt"])
    else:
        df = pd.DataFrame(columns=CSV_COLS)
    # Asegurar que todas las columnas existen en df
    for col in CSV_COLS:
        if col not in df.columns:
            df[col] = ""
    new_row = pd.DataFrame([{k: row.get(k, "") for k in CSV_COLS}])
    df = pd.concat([df[CSV_COLS], new_row], ignore_index=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")


def load_seguimientos() -> pd.DataFrame:
    if not os.path.exists(SEG_CSV_PATH):
        return pd.DataFrame(columns=SEG_COLS)
    try:
        df = pd.read_csv(SEG_CSV_PATH, dtype=str)
        for col in SEG_COLS:
            if col not in df.columns:
                df[col] = ""
        for col in ["seg_grasa", "seg_st", "seg_ic", "seg_agua"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "fecha" in df.columns:
            df["_fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=SEG_COLS)


def save_seguimiento_to_csv(row: dict):
    if os.path.exists(SEG_CSV_PATH):
        df = load_seguimientos()
        if "_fecha_dt" in df.columns:
            df = df.drop(columns=["_fecha_dt"])
    else:
        df = pd.DataFrame(columns=SEG_COLS)
    for col in SEG_COLS:
        if col not in df.columns:
            df[col] = ""
    new_row = pd.DataFrame([{k: row.get(k, "") for k in SEG_COLS}])
    df = pd.concat([df[SEG_COLS], new_row], ignore_index=True)
    df.to_csv(SEG_CSV_PATH, index=False, encoding="utf-8")


def delete_seg_row(orig_idx: int):
    df = load_seguimientos()
    df = df.drop(index=orig_idx)
    if "_fecha_dt" in df.columns:
        df = df.drop(columns=["_fecha_dt"])
    df[SEG_COLS].to_csv(SEG_CSV_PATH, index=False, encoding="utf-8")


ADMIN_PIN = "1234"


def delete_row_from_csv(orig_idx: int):
    df = load_historial()
    df = df.drop(index=orig_idx)
    if "_fecha_dt" in df.columns:
        df = df.drop(columns=["_fecha_dt"])
    df[CSV_COLS].to_csv(CSV_PATH, index=False, encoding="utf-8")


def update_row_in_csv(orig_idx: int, new_vals: dict):
    df = load_historial()
    for k, v in new_vals.items():
        if k in df.columns:
            df.at[orig_idx, k] = v
    if "_fecha_dt" in df.columns:
        df = df.drop(columns=["_fecha_dt"])
    df[CSV_COLS].to_csv(CSV_PATH, index=False, encoding="utf-8")


def calcular_estado_calidad(row: dict) -> str:
    """Retorna 'CONFORME' o 'DESVIACIÓN' según los parámetros de la ruta.
    Solo aplica a registros de tipo RUTAS."""
    if str(row.get("tipo_seguimiento", "RUTAS")).strip() != "RUTAS":
        return "CONFORME"
    try:
        st_val = float(str(row.get("solidos_ruta", "")).replace(",", "."))
        if 0 < st_val < 12.60:
            return "DESVIACIÓN"
    except (ValueError, TypeError):
        pass
    try:
        ic_val = float(str(row.get("crioscopia_ruta", "")).replace(",", "."))
        if ic_val > -0.535 or ic_val < -0.550:
            return "DESVIACIÓN"
    except (ValueError, TypeError):
        pass
    return "CONFORME"


def historial_to_excel(df: pd.DataFrame) -> bytes:
    wb = openpyxl.Workbook()

    fill_hdr  = PatternFill("solid", fgColor="BDD7EE")
    fill_bad  = PatternFill("solid", fgColor="FFC7CE")
    font_bad  = Font(bold=True, size=10, color="9C0006")
    bold      = Font(bold=True, size=10)
    normal    = Font(size=10)
    center    = Alignment(horizontal="center", vertical="center")
    bd = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    def _write_headers(ws, cols, widths):
        for ci, hdr in enumerate(cols, 1):
            cell = ws.cell(row=1, column=ci, value=hdr)
            cell.fill = fill_hdr; cell.font = bold
            cell.alignment = center; cell.border = bd
        for ci, w in enumerate(widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w

    def _write_cell(ws, ri, ci, val, fmt=None, bad=False):
        v = val if (val is not None and not (isinstance(val, float) and pd.isna(val))) else ""
        cell = ws.cell(row=ri, column=ci, value=v)
        cell.alignment = center; cell.border = bd
        cell.font = font_bad if bad else normal
        if bad: cell.fill = fill_bad
        if fmt: cell.number_format = fmt
        return cell

    # ── Hoja 1: Rutas y Seguimientos ───────────────────────────────────
    ws1 = wb.active
    ws1.title = "Rutas y Seguimientos"
    df_rutas = df[df["tipo_seguimiento"].isin(["RUTAS"])].copy() \
        if "tipo_seguimiento" in df.columns else df.copy()

    cols1 = [
        ("TIPO", "tipo_seguimiento"), ("FECHA", "fecha"), ("RUTA", "ruta"),
        ("PLACA", "placa"), ("CONDUCTOR", "conductor"),
        ("VOL. DECLARADO (L)", "volumen_declarado"), ("VOL. ESTACIONES (L)", "vol_estaciones"),
        ("DIFERENCIA (L)", "diferencia"), ("SÓLIDOS RUTA (%)", "solidos_ruta"),
        ("CRIOSCOPIA RUTA (°C)", "crioscopia_ruta"), ("ST POND", "st_pond"),
        ("IC POND", "ic_pond"), ("Nº ESTACIONES", "num_estaciones"),
        ("GUARDADO EN", "guardado_en"),
    ]
    _write_headers(ws1, [h for h, _ in cols1], [10, 12, 18, 10, 18, 16, 18, 14, 16, 18, 10, 10, 12, 18])

    for ri, row in enumerate(df_rutas.itertuples(index=False), start=2):
        rd = row._asdict()
        desv_st = desv_ic = False
        try:
            v = float(str(rd.get("solidos_ruta", "")).replace(",", "."))
            if 0 < v < 12.60: desv_st = True
        except Exception: pass
        try:
            v = float(str(rd.get("crioscopia_ruta", "")).replace(",", "."))
            if v > -0.535 or v < -0.550: desv_ic = True
        except Exception: pass
        hay_desv = desv_st or desv_ic

        for ci, (_, col) in enumerate(cols1, 1):
            val = rd.get(col, "")
            fmt = "0.00" if col in ("solidos_ruta", "st_pond") else \
                  "0.000" if col in ("crioscopia_ruta", "ic_pond") else None
            bad = (hay_desv and col == "ruta") or \
                  (desv_st and col == "solidos_ruta") or \
                  (desv_ic and col == "crioscopia_ruta")
            _write_cell(ws1, ri, ci, val, fmt=fmt, bad=bad)

    # ── Hoja 2: Transuiza ───────────────────────────────────────────────
    ws2 = wb.create_sheet("Transuiza")
    df_trans = df[df.get("tipo_seguimiento", pd.Series(["RUTAS"]*len(df))) == "TRANSUIZA"].copy() \
        if "tipo_seguimiento" in df.columns else pd.DataFrame()

    cols2 = [
        ("FECHA", "fecha"), ("PLACA", "placa"),
        ("ST CARROTANQUE (%)", "st_carrotanque"),
        ("GRASA (%)", "grasa_muestra"),
        ("ST MUESTRA (%)", "solidos_ruta"),
        ("PROTEÍNA (%)", "proteina_muestra"),
        ("DIFERENCIA SÓLIDOS", "diferencia_solidos"),
        ("GUARDADO EN", "guardado_en"),
    ]
    _write_headers(ws2, [h for h, _ in cols2], [12, 10, 18, 10, 16, 12, 18, 18])

    for ri, row in enumerate(df_trans.itertuples(index=False), start=2):
        rd = row._asdict()
        for ci, (_, col) in enumerate(cols2, 1):
            val = rd.get(col, "")
            fmt = "0.00" if col in ("st_carrotanque","grasa_muestra","solidos_ruta",
                                    "proteina_muestra","diferencia_solidos") else None
            _write_cell(ws2, ri, ci, val, fmt=fmt)

    # ── Hoja 3: Seguimientos ────────────────────────────────────────
    ws3 = wb.create_sheet("Seguimientos")
    df_seg = load_seguimientos().drop(columns=["_fecha_dt"], errors="ignore")

    cols3 = [
        ("SUB-TIPO", "sub_tipo_seguimiento"),
        ("FECHA", "fecha"),
        ("CÓDIGO", "seg_codigo"),
        ("ENTREGADO POR", "seg_quien_trajo"),
        ("RUTA", "ruta"),
        ("RESPONSABLE", "seg_responsable"),
        ("ID MUESTRA", "seg_id_muestra"),
        ("GRASA (%)", "seg_grasa"),
        ("ST (%)", "seg_st"),
        ("IC (°C)", "seg_ic"),
        ("AGUA (%)", "seg_agua"),
        ("ALCOHOL", "seg_alcohol"),
        ("CLORUROS", "seg_cloruros"),
        ("NEUTRALIZANTES", "seg_neutralizantes"),
        ("OBSERVACIONES", "seg_observaciones"),
        ("GUARDADO EN", "guardado_en"),
    ]
    _write_headers(ws3, [h for h, _ in cols3],
                   [18, 12, 12, 18, 16, 18, 14, 10, 10, 10, 10, 12, 12, 16, 30, 18])

    for ri, row in enumerate(df_seg.itertuples(index=False), start=2):
        rd = row._asdict()
        for ci, (_, col) in enumerate(cols3, 1):
            val = rd.get(col, "")
            fmt = "0.00"  if col in ("seg_grasa", "seg_st", "seg_agua") else \
                  "0.000" if col == "seg_ic" else None
            _write_cell(ws3, ri, ci, val, fmt=fmt)

    # ── Hoja 4: Estaciones (una fila por estación, unida a datos de ruta) ──
    ws4 = wb.create_sheet("Estaciones")
    cols4 = [
        ("FECHA",           None), ("RUTA",          None), ("PLACA",        None),
        ("CONDUCTOR",       None), ("VOL. DECLARADO", None),
        ("# ESTACIÓN",      None), ("CÓDIGO",         None),
        ("GRASA (%)",       None), ("SÓL.TOT. (%)",   None), ("PROTEÍNA (%)", None),
        ("CRIOSCOPIA (°C)", None), ("VOLUMEN (L)",     None),
        ("ALCOHOL",         None), ("CLORUROS",        None), ("NEUTRALIZANTES", None),
        ("% AGUA",          None), ("OBSERVACIONES",  None),
        ("ST RUTA (%)",     None), ("IC RUTA (°C)",    None),
        ("ESTADO CALIDAD",  None),
    ]
    _write_headers(ws4, [h for h, _ in cols4],
                   [12, 18, 10, 18, 14, 10, 14,
                    10, 10, 10, 14, 12,
                    10, 10, 14,
                    8, 26,
                    12, 12, 14])

    est_ri = 2
    for _, ruta_row in df_rutas.iterrows():
        raw_json = str(ruta_row.get("estaciones_json", "") or "")
        try:
            estaciones_list = json.loads(raw_json) if raw_json.strip() else []
        except Exception:
            estaciones_list = []
        if not estaciones_list:
            continue
        try:
            st_rv = float(str(ruta_row.get("solidos_ruta", "")).replace(",", "."))
        except Exception:
            st_rv = None
        try:
            ic_rv = float(str(ruta_row.get("crioscopia_ruta", "")).replace(",", "."))
        except Exception:
            ic_rv = None
        desv_st_r = st_rv is not None and 0 < st_rv < 12.60
        desv_ic_r = ic_rv is not None and (ic_rv > -0.535 or ic_rv < -0.550)
        estado_r = "DESVIACIÓN" if (desv_st_r or desv_ic_r) else "CONFORME"

        for idx_e, est in enumerate(estaciones_list, 1):
            try:
                ic_e = float(str(est.get("crioscopia", "")).replace(",", "."))
            except Exception:
                ic_e = None
            desv_ic_e = ic_e is not None and (ic_e > -0.535 or ic_e < -0.550)
            try:
                st_e = float(str(est.get("solidos", "")).replace(",", "."))
            except Exception:
                st_e = None
            desv_st_e = st_e is not None and 0 < st_e < 12.60
            hay_desv_e = desv_ic_e or desv_st_e

            row_vals = [
                ruta_row.get("fecha", ""),
                ruta_row.get("ruta", ""),
                ruta_row.get("placa", ""),
                ruta_row.get("conductor", ""),
                ruta_row.get("volumen_declarado", ""),
                idx_e,
                est.get("codigo", ""),
                est.get("grasa"),
                est.get("solidos"),
                est.get("proteina"),
                est.get("crioscopia"),
                est.get("volumen"),
                est.get("alcohol", ""),
                est.get("cloruros", ""),
                est.get("neutralizantes", ""),
                est.get("agua_pct"),
                est.get("obs", ""),
                st_rv,
                ic_rv,
                estado_r,
            ]
            fmts = [None, None, None, None, "0",
                    "0", None,
                    "0.00", "0.00", "0.00", "0.000", "0",
                    None, None, None,
                    "0.0", None,
                    "0.00", "0.000", None]
            for ci_e, (val_e, fmt_e) in enumerate(zip(row_vals, fmts), 1):
                bad_e = hay_desv_e and ci_e in (8, 9, 11)
                _write_cell(ws4, est_ri, ci_e, val_e, fmt=fmt_e, bad=bad_e)
            est_ri += 1

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


st.set_page_config(page_title="QualiLact", page_icon="🧪", layout="wide")
restore_draft_state()

st.markdown(
    """
    <style>
    /* ── Indicador de carga: ciclo de iconos ───────────────────── */
    @keyframes _ql_icono {
        0%,  30%  { content: "🐄  Cargando..."; }
        33%, 63%  { content: "🥛  Cargando..."; }
        66%, 96%  { content: "🧪  Cargando..."; }
        100%      { content: "🐄  Cargando..."; }
    }
    /* Ocultar spinner original */
    [data-testid="stStatusWidget"] > div > div { display: none !important; }
    /* Mostrar icono ciclico fijo en parte superior derecha */
    [data-testid="stStatusWidget"]::after {
        content: "🐄  Cargando...";
        position: fixed;
        top: 10px;
        right: 24px;
        font-size: 1rem;
        font-weight: 600;
        color: #0056A3;
        background: #EAF1FA;
        border: 1.5px solid #BDD7EE;
        border-radius: 20px;
        padding: 4px 14px;
        display: block;
        animation: _ql_icono 2.4s linear infinite;
        line-height: 1.6;
        z-index: 9999;
        pointer-events: none;
        white-space: nowrap;
    }


    /* ── Fondo azul claro QualiLact ────────────────────────────── */
    .stApp { background-color: #F0F5F9 !important; }
    section[data-testid="stSidebar"] { background-color: #E8EFF5 !important; }
    /* ── Tarjetas blancas redondeadas ──────────────────────────── */
    div[data-testid="stVerticalBlock"] > div[data-testid="element-container"],
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
    }
    section.main > div { background-color: #F0F5F9 !important; }

    /* ── Ocultar spinners de number input ──────────────────────── */
    input[type="number"]::-webkit-outer-spin-button,
    input[type="number"]::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    input[type="number"] { -moz-appearance: textfield; }
    button[data-testid="stNumberInputStepUp"],
    button[data-testid="stNumberInputStepDown"] { display: none !important; }

    /* ── Inputs: fondo gris claro + bordes redondeados ─────────── */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input {
        background-color: #F4F4F4 !important;
        border: 1.5px solid #D1D5DB !important;
        border-radius: 8px !important;
        color: #1F2937 !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        transition: border-color 0.18s, box-shadow 0.18s;
    }

    /* ── Focus: resaltado azul Nestlé ──────────────────────────── */
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stDateInput"] input:focus {
        border-color: #0056A3 !important;
        box-shadow: 0 0 0 3px rgba(0, 86, 163, 0.12) !important;
        background-color: #FFFFFF !important;
        outline: none !important;
    }

    /* ── Labels: gris oscuro, peso semibold ────────────────────── */
    div[data-testid="stTextInput"] label p,
    div[data-testid="stNumberInput"] label p,
    div[data-testid="stDateInput"] label p,
    div[data-testid="stSelectbox"] label p {
        color: #555555 !important;
        font-weight: 600 !important;
        font-size: 12.5px !important;
        letter-spacing: 0.3px;
    }

    /* ── Selectbox: mismos bordes redondeados ──────────────────── */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child {
        background-color: #F4F4F4 !important;
        border: 1.5px solid #D1D5DB !important;
        border-radius: 8px !important;
    }

    /* ── Divisores ─────────────────────────────────────────────── */
    hr { border-color: #E5E7EB !important; }

    /* ── Botones primarios: azul Nestlé ────────────────────────── */
    button[kind="primary"], button[data-testid*="primary"] {
        background-color: #0056A3 !important;
        border-color: #0056A3 !important;
        border-radius: 8px !important;
    }
    button[kind="primary"]:hover {
        background-color: #004285 !important;
    }

    /* ── Contenedores con borde ────────────────────────────────── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px !important;
        border-color: #E5E7EB !important;
        background-color: #FAFAFA !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 18px 0 10px 0;
        border-bottom: 2px solid #0056A3;
        margin-bottom: 18px;
    ">
        <div style="
            font-size: 2.6rem;
            line-height: 1;
            letter-spacing: -2px;
        ">🐄🥛</div>
        <div>
            <div style="
                font-size: 2rem;
                font-weight: 800;
                color: #0056A3;
                letter-spacing: 1px;
                line-height: 1.1;
                font-family: 'Segoe UI', sans-serif;
            ">QualiLact</div>
            <div style="
                font-size: 0.9rem;
                color: #6B7280;
                font-weight: 400;
                letter-spacing: 0.5px;
                margin-top: 2px;
                font-family: 'Segoe UI', sans-serif;
            ">Control de Calidad en Leche Fresca</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "continuar" not in st.session_state:
    st.session_state.continuar = False


def convertir_a_mayusculas(campo):
    st.session_state[campo] = st.session_state[campo].upper()


def validar_placa():
    st.session_state.placa_vehiculo = re.sub(
        r"[^A-Z0-9]", "", st.session_state.placa_vehiculo.upper()
    )


def activar_siguiente_con_enter():
    components.html(
        """
        <script>
        function obtenerInputsVisibles() {
            return Array.from(window.parent.document.querySelectorAll("input, textarea"))
                .filter(el => {
                    const tipo = el.getAttribute("type");
                    if (tipo === "hidden" || tipo === "checkbox" || tipo === "radio") return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });
        }

        function clickBtnGuardar(input) {
            // Busca el primer botón GUARDAR visible en la página y lo pulsa
            const botones = Array.from(window.parent.document.querySelectorAll("button"));
            const btnGuardar = botones.find(b =>
                b.innerText && b.innerText.includes("GUARDAR") &&
                b.offsetParent !== null
            );
            if (btnGuardar) setTimeout(() => { btnGuardar.click(); }, 80);
        }

        function moverFoco(input, delta) {
            const actualizados = obtenerInputsVisibles();
            const posActual = actualizados.indexOf(input);
            if (posActual === -1) return;          // elemento ya no está en el DOM
            const destino = actualizados[posActual + delta];
            if (destino) {
                setTimeout(() => {
                    destino.focus();
                    if (destino.select) destino.select();
                }, 60);
            }
        }

        function activarNavegacion() {
            const inputs = obtenerInputsVisibles();
            inputs.forEach((input) => {
                if (input.dataset.navActivo === "true") return;
                input.dataset.navActivo = "true";

                const esNumerico = input.getAttribute("type") === "number";

                input.addEventListener("keydown", (e) => {
                    // Enter → siguiente campo;
                    // si es OBSERVACIONES de estación, pulsa GUARDAR directo
                    if (e.key === "Enter") {
                        e.preventDefault();
                        const ph = (input.placeholder || "").toLowerCase();
                        if (ph.includes("observaciones") || ph.includes("ingrese observaciones")) {
                            clickBtnGuardar(input);
                        } else {
                            moverFoco(input, 1);
                        }
                        return;
                    }
                    // ←→: en numéricos navegan siempre; en texto solo en los extremos
                    if (e.key === "ArrowRight") {
                        if (esNumerico || input.selectionStart >= input.value.length) {
                            e.preventDefault();
                            moverFoco(input, 1);
                        }
                    } else if (e.key === "ArrowLeft") {
                        if (esNumerico || input.selectionStart <= 0) {
                            e.preventDefault();
                            moverFoco(input, -1);
                        }
                    }
                    // ↑↓ sin función de navegación (comportamiento nativo del navegador)
                });
            });
        }

        activarNavegacion();
        setInterval(() => { activarNavegacion(); }, 600);
        </script>
        """,
        height=0,
    )


# ── CONFIGURACIÓN INICIAL ────────────────────────────────────────────────────
with st.expander("CONFIGURACIÓN INICIAL", expanded=not st.session_state.continuar):
    col1, col2 = st.columns(2)

    with col1:
        fecha_analisis = st.date_input(
            "FECHA DE ANÁLISIS", datetime.now(), format="DD/MM/YYYY"
        )

    with col2:
        opciones_seguimiento = ["RUTAS", "TRANSUIZA", "SEGUIMIENTOS"]
        tipo_servicio = st.selectbox(
            "TIPO DE ANÁLISIS", opciones_seguimiento, key="tipo_servicio_select"
        )

    sub_tipo_seg = None
    if tipo_servicio == "SEGUIMIENTOS":
        sub_tipo_seg = st.selectbox(
            "📂 SUB-TIPO DE SEGUIMIENTO",
            ["TERCEROS", "ESTACIONES", "ACOMPAÑAMIENTOS", "CONTRAMUESTRAS SOLICITADAS"],
            key="sub_tipo_seg_select",
        )

    if st.button("CONTINUAR"):
        st.session_state.continuar = True
        st.session_state["_tipo_servicio_guardado"] = tipo_servicio
        st.session_state["_sub_tipo_seg_guardado"] = sub_tipo_seg
        st.rerun()

if st.session_state.continuar:
    if tipo_servicio == "RUTAS":
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;
                            margin-bottom:6px;">
                  <span style="font-size:1.35rem;">📋</span>
                  <span style="font-size:1.35rem;font-weight:700;
                               color:#0056A3;letter-spacing:.5px;
                               font-family:'Segoe UI',sans-serif;">
                    SEGUIMIENTO DE RUTAS
                  </span>
                </div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 📋 Datos de Identificación
               </div>""",
            unsafe_allow_html=True,
        )
        r1c1, r1c2 = st.columns(2)
        fecha_ruta = r1c1.date_input(
            "📅  FECHA DE LA RUTA", datetime.now(), key="fecha_ruta",
            format="DD/MM/YYYY",
        )
        nombre_ruta = r1c2.text_input(
            "📍  NOMBRE DE LA RUTA", placeholder="ESCRIBA AQUÍ...",
            key="nombre_ruta", on_change=convertir_a_mayusculas,
            args=("nombre_ruta",),
        )
        r2c1, r2c2, r2c3 = st.columns(3)
        placa = r2c1.text_input(
            "🚚  PLACA DE VEHÍCULO", placeholder="AAA000",
            key="placa_vehiculo", on_change=validar_placa,
        )
        conductor = r2c2.text_input(
            "👤  CONDUCTOR", placeholder="NOMBRE COMPLETO",
            key="conductor", on_change=convertir_a_mayusculas,
            args=("conductor",),
        )
        volumen = r2c3.number_input(
            "📦  VOLUMEN (L)", min_value=0, value=None, step=1,
            format="%d", placeholder="DIGITE VOLUMEN", key="volumen_ruta",
        )
        activar_siguiente_con_enter()

        st.markdown("---")

        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 🧪 Análisis de Calidad de Ruta
               </div>""",
            unsafe_allow_html=True,
        )
        cq1, cq2 = st.columns(2)

        with cq1:
            solidos_raw = st.text_input(
                "SÓLIDOS TOTALES (%)",
                key="solidos_totales",
                placeholder="Ej: 12.80",
            )
            try:
                solidos_totales = float(solidos_raw.replace(",", ".")) if solidos_raw else None
            except ValueError:
                solidos_totales = None
                st.warning("⚠️ Ingrese un número válido")

            if solidos_totales is not None and 0 < solidos_totales < 12.60:
                st.error("🚨 ALERTA: SÓLIDOS POR DEBAJO DE 12.60%")
                st.markdown(
                    """
                    <style>
                    div[data-testid="stTextInput"]:has(input[aria-label="SÓLIDOS TOTALES (%)"]) input {
                        border: 2px solid red !important;
                        background-color: #fff0f0 !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
            elif solidos_totales is not None and solidos_totales >= 12.60:
                st.success("✅ Sólidos dentro del parámetro")

        with cq2:
            crioscopia_raw = st.text_input(
                "CRIOSCOPIA (°C)",
                key="crioscopia",
                value="-0.",
                placeholder="-0.530",
            )
            try:
                crioscopia = float(crioscopia_raw.replace(",", ".")) if crioscopia_raw not in ("", "-", "-0", "-0.") else None
            except ValueError:
                crioscopia = None
                st.warning("⚠️ Ingrese un número válido")

            if crioscopia is not None and crioscopia > -0.535:
                st.error("🚨 ALERTA: CRIOSCOPIA FUERA DE RANGO (MAYOR A -0.535)")
            elif crioscopia is not None and crioscopia < -0.550:
                st.error("🚨 ALERTA: CRIOSCOPIA FUERA DE RANGO (MENOR A -0.550)")
            elif crioscopia is not None:
                st.success("✅ Crioscopia dentro del parámetro")

        st.markdown("---")

        # ── Imágenes de Muestras ───────────────────────────────────────
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 📷 Imágenes de Muestras
               </div>""",
            unsafe_allow_html=True,
        )
        if "imagenes_confirmadas" not in st.session_state:
            st.session_state.imagenes_confirmadas = False
        if "imagenes_nombres_guardados" not in st.session_state:
            st.session_state.imagenes_nombres_guardados = []

        imagenes_subidas = st.file_uploader(
            "ADJUNTAR IMÁGENES DE MUESTRAS DE LA RUTA",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="imagenes_muestras",
            label_visibility="visible",
        )

        if imagenes_subidas:
            nombres_actuales = [f.name for f in imagenes_subidas]
            if nombres_actuales != st.session_state.imagenes_nombres_guardados:
                st.session_state.imagenes_confirmadas = False

            # ── Miniaturas en cuadrícula HTML (bordes redondeados) ────
            confirmed = st.session_state.imagenes_confirmadas
            thumb_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin:8px 0;'>"
            for img in imagenes_subidas:
                raw_bytes = img.read()
                b64 = base64.b64encode(raw_bytes).decode()
                ext = img.name.rsplit(".", 1)[-1].lower()
                mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
                nombre_corto = img.name if len(img.name) <= 16 else img.name[:14] + "…"
                check_html = (
                    "<div style='color:#16a34a;font-size:12px;"
                    "text-align:center;font-weight:600;'>✅ Guardada</div>"
                    if confirmed else
                    f"<div style='font-size:10px;color:#888;text-align:center;'>{nombre_corto}</div>"
                )
                border_color = "#16a34a" if confirmed else "#D1D5DB"
                thumb_html += (
                    f"<div style='display:flex;flex-direction:column;"
                    f"align-items:center;gap:4px;'>"
                    f"<img src='data:{mime};base64,{b64}' "
                    f"style='width:150px;height:150px;object-fit:cover;"
                    f"border-radius:10px;border:2px solid {border_color};"
                    f"box-shadow:0 2px 6px rgba(0,0,0,0.08);background:#F4F4F4;'/>"
                    f"{check_html}</div>"
                )
                img.seek(0)  # reset cursor para uso posterior
            thumb_html += "</div>"
            st.markdown(thumb_html, unsafe_allow_html=True)

            # ── Botón guardar / confirmación ───────────────────────
            if not st.session_state.imagenes_confirmadas:
                st.markdown("<div style='margin-top:8px;'></div>",
                            unsafe_allow_html=True)
                if st.button("💾 GUARDAR IMÁGENES",
                             use_container_width=False):
                    st.session_state.imagenes_confirmadas = True
                    st.session_state.imagenes_nombres_guardados = nombres_actuales
                    st.rerun()
            else:
                st.success("✅ Imágenes guardadas correctamente.")
        else:
            st.session_state.imagenes_confirmadas = False
            st.caption("No se han adjuntado imágenes.")

        st.markdown("---")
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 📦 Calidad por Estación
               </div>""",
            unsafe_allow_html=True,
        )

        if "estaciones_guardadas" not in st.session_state:
            st.session_state.estaciones_guardadas = []
        if "form_ver" not in st.session_state:
            st.session_state.form_ver = 0

        def parse_num(val, default=None):
            if val is None:
                return default
            try:
                return float(str(val).replace(",", "."))
            except ValueError:
                return default

        # ── Data editor ────────────────────────────────────────────────
        EDITOR_COLS = ["codigo", "grasa", "solidos", "proteina", "crioscopia",
                       "agua_pct", "volumen", "alcohol", "cloruros",
                       "neutralizantes", "obs"]

        if st.session_state.estaciones_guardadas:
            df_est = pd.DataFrame(st.session_state.estaciones_guardadas,
                                  columns=EDITOR_COLS)
        else:
            df_est = pd.DataFrame(columns=EDITOR_COLS)

        for c in ["grasa", "solidos", "proteina", "agua_pct"]:
            df_est[c] = pd.to_numeric(df_est[c], errors="coerce")
        df_est["volumen"] = pd.to_numeric(df_est["volumen"],
                                          errors="coerce").astype("Int64")

        edited = st.data_editor(
            df_est,
            num_rows="dynamic",
            use_container_width=True,
            key=f"de_est_{st.session_state.form_ver}",
            column_config={
                "codigo":        st.column_config.TextColumn("CÓDIGO"),
                "grasa":         st.column_config.NumberColumn(
                                     "GRASA (%)", format="%.2f",
                                     min_value=0.0, max_value=100.0),
                "solidos":       st.column_config.NumberColumn(
                                     "SÓL.TOT. (%)", format="%.2f",
                                     min_value=0.0, max_value=100.0),
                "proteina":      st.column_config.NumberColumn(
                                     "PROTEÍNA (%)", format="%.2f",
                                     min_value=0.0, max_value=100.0),
                "crioscopia":    st.column_config.TextColumn("CRIOSCOPIA (°C)"),
                "volumen":       st.column_config.NumberColumn(
                                     "VOLUMEN (L)", format="%d",
                                     min_value=0, step=1),
                "alcohol":       st.column_config.SelectboxColumn(
                                     "ALCOHOL", options=["N/A", "+", "-"],
                                     required=True),
                "cloruros":      st.column_config.SelectboxColumn(
                                     "CLORUROS", options=["N/A", "+", "-"],
                                     required=True),
                "neutralizantes":st.column_config.SelectboxColumn(
                                     "NEUTRALIZANTES", options=["N/A", "+", "-"],
                                     required=True),
                "agua_pct":      st.column_config.NumberColumn(
                                     "% AGUA", format="%.1f",
                                     min_value=0.0, max_value=100.0),
                "obs":           st.column_config.TextColumn("OBSERVACIONES"),
            },
            hide_index=True,
        )

        # Sincronizar ediciones/eliminaciones de vuelta al estado
        raw = json.loads(edited.to_json(orient="records"))
        st.session_state.estaciones_guardadas = [
            r for r in raw
            if any(v is not None and str(v).strip() != "" for v in r.values())
        ]

        st.markdown("---")

        # ── Formulario nueva estación ──────────────────────────────────
        with st.container(border=True):
            v = st.session_state.form_ver
            num_nueva = len(st.session_state.estaciones_guardadas) + 1
            st.markdown(f"**Agregar Estación — #{num_nueva}**")

            if f"nue_crio_{v}" not in st.session_state:
                st.session_state[f"nue_crio_{v}"] = "-0."

            f1, f2, f3, f4, f5, f6 = st.columns([1.5, 1, 1, 1, 1.5, 1])
            form_codigo   = f1.text_input("CÓDIGO", key=f"nue_codigo_{v}",
                                          placeholder="CÓDIGO")
            form_grasa    = f2.number_input("GRASA (%)", key=f"nue_grasa_{v}",
                                            min_value=0.0, max_value=100.0,
                                            step=0.01, format="%.2f",
                                            value=None, placeholder="0.00")
            form_solidos  = f3.number_input("SÓL. TOT. (%)", key=f"nue_solidos_{v}",
                                            min_value=0.0, max_value=100.0,
                                            step=0.01, format="%.2f",
                                            value=None, placeholder="0.00")
            form_proteina = f4.number_input("PROTEÍNA (%)", key=f"nue_proteina_{v}",
                                            min_value=0.0, max_value=100.0,
                                            step=0.01, format="%.2f",
                                            value=None, placeholder="0.00")
            form_crio_raw = f5.text_input("CRIOSCOPIA (°C)", key=f"nue_crio_{v}",
                                          placeholder="-0.530")
            form_vol      = f6.number_input("VOLUMEN (L)", key=f"nue_vol_{v}",
                                            min_value=0, step=1,
                                            value=None, placeholder="0")

            form_crio_val = (parse_num(form_crio_raw)
                             if form_crio_raw not in ("", "-", "-0", "-0.")
                             else None)

            if form_solidos is not None and 0 < form_solidos < 12.60:
                st.error("🚨 SÓLIDOS POR DEBAJO DE 12.60%")

            form_agua_pct = None
            if form_crio_val is not None and form_crio_val > -0.530:
                aw1, aw2 = st.columns([2, 1])
                aw1.warning("💧 ALERTA: PRESENCIA DE AGUA — CRIOSCOPIA MAYOR A -0.530")
                form_agua_pct = aw2.number_input(
                    "% AGUA AÑADIDA", key=f"nue_agua_{v}",
                    min_value=0.0, max_value=100.0, step=0.1,
                    format="%.1f", value=None, placeholder="0.0")
            elif form_crio_val is not None and form_crio_val < -0.550:
                st.error("🚨 ALERTA: CRIOSCOPIA FUERA DE RANGO (MENOR A -0.550)")

            q1, q2, q3, q4 = st.columns([0.6, 0.6, 0.8, 2])
            form_alcohol  = q1.selectbox("ALCOHOL", options=["N/A", "+", "-"],
                                         key=f"nue_alcohol_{v}")
            form_cloruros = q2.selectbox("CLORUROS", options=["N/A", "+", "-"],
                                         key=f"nue_cloruros_{v}")
            form_neutral  = q3.selectbox("NEUTRALIZANTES", options=["N/A", "+", "-"],
                                         key=f"nue_neutral_{v}")
            form_obs = q4.text_input("OBSERVACIONES", key=f"nue_obs_{v}",
                                     placeholder="Ingrese observaciones...")

            if st.button("💾 GUARDAR", type="primary",
                         use_container_width=True):
                st.session_state.estaciones_guardadas.append({
                    "codigo":         form_codigo,
                    "grasa":          form_grasa,
                    "solidos":        form_solidos,
                    "proteina":       form_proteina,
                    "crioscopia":     form_crio_raw if form_crio_val is not None else None,
                    "volumen":        form_vol,
                    "alcohol":        form_alcohol,
                    "cloruros":       form_cloruros,
                    "neutralizantes": form_neutral,
                    "agua_pct":       form_agua_pct,
                    "obs":            form_obs,
                })
                st.session_state.form_ver += 1
                st.rerun()

        # ── Reconciliación de volúmenes ────────────────────────────────
        st.markdown("---")
        vol_ruta = volumen if volumen is not None else 0
        vol_est_total = 0
        for e in st.session_state.estaciones_guardadas:
            v_e = e.get("volumen")
            if v_e is not None:
                try:
                    vol_est_total += int(v_e)
                except (ValueError, TypeError):
                    pass

        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("VOLUMEN DECLARADO DE RUTA (L)",
                        f"{int(vol_ruta):,}" if vol_ruta else "—")
        col_res2.metric("VOLUMEN SUMA ESTACIONES (L)",
                        f"{int(vol_est_total):,}" if vol_est_total else "—")
        diferencia = vol_est_total - vol_ruta if vol_ruta else 0
        col_res3.metric("DIFERENCIA (L)",
                        f"{int(diferencia):+,}" if vol_ruta else "—")

        if vol_ruta and vol_est_total and vol_ruta != vol_est_total:
            st.warning(
                f"⚠️ El volumen de estaciones ({int(vol_est_total):,} L) no coincide "
                f"con el volumen declarado de la ruta ({int(vol_ruta):,} L). "
                f"Diferencia: {int(diferencia):+,} L"
            )
        elif vol_ruta and vol_est_total and vol_ruta == vol_est_total:
            st.success("✅ El volumen de estaciones coincide con el volumen de la ruta.")

        # ── Ponderados a nivel de ruta (usados en exportación y guardado) ────
        _ests = st.session_state.estaciones_guardadas
        _pond_st, _pond_ic = [], []
        for _e in _ests:
            _v  = parse_num(_e.get("volumen"))
            _s  = parse_num(_e.get("solidos"))
            _cr = parse_num(_e.get("crioscopia"))
            _pond_st.append(round(_v * _s,  2) if _v is not None and _s  is not None else None)
            _pond_ic.append(round(_v * _cr, 3) if _v is not None and _cr is not None else None)
        _vol_total = sum(parse_num(_e.get("volumen")) or 0 for _e in _ests)
        _st_pond = round(sum(x for x in _pond_st if x is not None) / _vol_total, 2) if _vol_total else None
        _ic_pond = round(sum(x for x in _pond_ic if x is not None) / _vol_total, 3) if _vol_total else None

        # ── Exportar a Excel ───────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 📊 Exportar Reporte
               </div>""",
            unsafe_allow_html=True,
        )

        def generar_excel(imagenes=None, base_nombre="reporte"):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Reporte Ruta"

            # ── Estilos ─────────────────────────────────────────────
            fill_hdr = PatternFill("solid", fgColor="BDD7EE")
            fill_sub = PatternFill("solid", fgColor="BDD7EE")
            bold = Font(bold=True, size=10)
            normal = Font(size=10)
            center = Alignment(horizontal="center", vertical="center")
            left   = Alignment(horizontal="left",   vertical="center")
            bd = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin"),
            )

            def c(fila, col, valor, fill=None, font=None, aln=None, fmt=None):
                cell = ws.cell(row=fila, column=col, value=valor)
                cell.fill   = fill  if fill  else PatternFill()
                cell.font   = font  if font  else normal
                cell.alignment = aln if aln else left
                cell.border = bd
                if fmt:
                    cell.number_format = fmt
                return cell

            # ── Calcular ponderados ──────────────────────────────────
            estaciones = st.session_state.estaciones_guardadas
            pond_st_vals, pond_ic_vals = [], []
            for est in estaciones:
                v = parse_num(est.get("volumen"))
                s = parse_num(est.get("solidos"))
                cr = parse_num(est.get("crioscopia"))
                pond_st_vals.append(round(v * s,  2)  if v is not None and s  is not None else None)
                pond_ic_vals.append(round(v * cr, 3)  if v is not None and cr is not None else None)

            vol_total_est = sum(parse_num(e.get("volumen")) or 0 for e in estaciones)
            sum_pst = sum(x for x in pond_st_vals if x is not None)
            sum_pic = sum(x for x in pond_ic_vals if x is not None)
            st_pond = round(sum_pst / vol_total_est, 2) if vol_total_est else None
            ic_pond = round(sum_pic / vol_total_est, 3) if vol_total_est else None

            # ── FILA 1: Encabezados generales ───────────────────────
            hdrs1 = ["FECHA", "RUTA", "PLACA", "CONDUCTOR",
                     "ST RUTA", "IC RUTA", "VOLUMEN", "ST POND", "IC POND"]
            for ci, h in enumerate(hdrs1, 1):
                c(1, ci, h, fill=fill_hdr, font=bold, aln=center)

            # ── FILA 2: Valores generales ────────────────────────────
            vals1 = [
                fecha_ruta.strftime("%d/%m/%Y") if fecha_ruta else "",
                nombre_ruta or "",
                placa or "",
                conductor or "",
                solidos_totales,
                crioscopia,
                int(volumen) if volumen else "",
                st_pond,
                ic_pond,
            ]
            fmts1 = [None, None, None, None, "0.00", "0.000", "0", "0.00", "0.000"]
            for ci, (val, fmt) in enumerate(zip(vals1, fmts1), 1):
                c(2, ci, val if val is not None else "", aln=center, fmt=fmt)

            # ── Estilos de alerta ────────────────────────────────────
            fill_alerta = PatternFill("solid", fgColor="FFC7CE")
            font_alerta = Font(color="9C0006", bold=True, size=10)

            # ── FILA 3: Encabezados de estaciones ───────────────────
            hdrs2 = ["CODIGO", "GRASA", "ST", "PROTEINA",
                     "CRIOSCOPIA", "AGUA", "VOLUMEN",
                     "ALCOHOL", "CLORUROS", "NEUTRALIZANTES",
                     "POND ST", "POND IC", "OBS"]
            for ci, h in enumerate(hdrs2, 1):
                c(3, ci, h, fill=fill_sub, font=bold, aln=center)

            # ── FILAS 4+: Datos de estaciones ────────────────────────
            for ri, (est, pst, pic) in enumerate(
                    zip(estaciones, pond_st_vals, pond_ic_vals), start=4):
                st_val  = parse_num(est.get("solidos"))
                ic_val  = parse_num(est.get("crioscopia"))
                alc_val = str(est.get("alcohol", "")).strip()
                clo_val = str(est.get("cloruros", "")).strip()
                neu_val = str(est.get("neutralizantes", "")).strip()

                row_vals = [
                    est.get("codigo", ""),
                    parse_num(est.get("grasa")),
                    st_val,
                    parse_num(est.get("proteina")),
                    ic_val,
                    parse_num(est.get("agua_pct")),
                    parse_num(est.get("volumen")),
                    alc_val,
                    clo_val,
                    neu_val,
                    pst,
                    pic,
                    est.get("obs", ""),
                ]
                rfmts = [None, "0.00", "0.00", "0.00", "0.000",
                         "0.0", "0", None, None, None, "0.00", "0.000", None]

                for ci, (val, fmt) in enumerate(zip(row_vals, rfmts), 1):
                    cell = c(ri, ci, val if val is not None else "", aln=center, fmt=fmt)
                    # Resaltar ST fuera de norma (col 3)
                    if ci == 3:
                        try:
                            if st_val is not None and 0 < float(st_val) < 12.60:
                                cell.fill = fill_alerta
                                cell.font = font_alerta
                        except Exception:
                            pass
                    # Resaltar CRIOSCOPIA fuera de norma (col 5)
                    elif ci == 5:
                        try:
                            if ic_val is not None and (float(ic_val) > -0.535 or float(ic_val) < -0.550):
                                cell.fill = fill_alerta
                                cell.font = font_alerta
                        except Exception:
                            pass
                    # Resaltar pruebas positivas (cols 8, 9, 10)
                    elif ci in (8, 9, 10):
                        if str(val).strip() == "+":
                            cell.fill = fill_alerta
                            cell.font = font_alerta

            # ── Anchos de columna ────────────────────────────────────
            anchos = [12, 10, 10, 14, 10, 10, 10, 10, 10, 14, 12, 12, 24]
            for ci, ancho in enumerate(anchos, 1):
                ws.column_dimensions[
                    openpyxl.utils.get_column_letter(ci)
                ].width = ancho

            # ── Hoja de Imágenes ─────────────────────────────────────
            if imagenes:
                ws_img = wb.create_sheet("Imágenes")
                IMG_W   = 320          # px de ancho destino
                ROW_H   = 14.25        # puntos por fila (altura estándar Excel)
                COL_IMG = 2            # columna B = img izquierda
                COL_IMG2 = 10          # columna J = img derecha
                GAP_COLS = 1           # columna separadora

                ws_img.column_dimensions["A"].width = 1
                ws_img.column_dimensions[
                    openpyxl.utils.get_column_letter(COL_IMG)].width = 46
                ws_img.column_dimensions[
                    openpyxl.utils.get_column_letter(COL_IMG2)].width = 46

                fila_img = 1
                imgs = list(imagenes)
                idx_global = 0
                for i in range(0, len(imgs), 2):
                    max_new_h = 0
                    for img_file, col_anchor in [
                        (imgs[i],                              COL_IMG),
                        (imgs[i+1] if i+1 < len(imgs) else None, COL_IMG2),
                    ]:
                        if img_file is None:
                            continue
                        idx_global += 1
                        etiqueta = f"{base_nombre}_{idx_global}"
                        # Etiqueta
                        lbl_cell = ws_img.cell(
                            row=fila_img,
                            column=col_anchor,
                            value=etiqueta,
                        )
                        lbl_cell.font = Font(bold=True, size=10)

                        # Procesar imagen
                        raw = io.BytesIO(img_file.read())
                        pil = PILImage.open(raw).convert("RGB")
                        w, h = pil.size
                        new_h = int(h * (IMG_W / w))
                        pil = pil.resize((IMG_W, new_h), PILImage.LANCZOS)
                        resized = io.BytesIO()
                        pil.save(resized, format="PNG")
                        resized.seek(0)

                        xl_img = XLImage(resized)
                        xl_img.width  = IMG_W
                        xl_img.height = new_h

                        anchor_letter = openpyxl.utils.get_column_letter(col_anchor)
                        ws_img.add_image(xl_img, f"{anchor_letter}{fila_img + 1}")
                        max_new_h = max(max_new_h, new_h)

                    # Filas según la imagen más alta del par
                    rows_img = int(max_new_h / ROW_H) + 2
                    for r in range(fila_img + 1, fila_img + rows_img + 1):
                        ws_img.row_dimensions[r].height = ROW_H
                    fila_img += rows_img + 2  # +2 = espacio entre pares

            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return buf

        # ── Función PDF ────────────────────────────────────────────────
        def generar_pdf(imagenes=None, base_nombre="reporte"):
            buf = io.BytesIO()
            doc = SimpleDocTemplate(
                buf,
                pagesize=landscape(A4),
                leftMargin=1.5*cm, rightMargin=1.5*cm,
                topMargin=1.5*cm, bottomMargin=1.5*cm,
            )
            styles = getSampleStyleSheet()
            titulo_style = ParagraphStyle(
                "titulo", parent=styles["Normal"],
                fontSize=13, fontName="Helvetica-Bold",
                alignment=TA_CENTER, spaceAfter=8,
            )
            seccion_style = ParagraphStyle(
                "seccion", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica-Bold",
                alignment=TA_LEFT, spaceAfter=4, spaceBefore=6,
            )

            # colores
            AZUL   = colors.HexColor("#1F4E79")
            AZUL_L = colors.HexColor("#BDD7EE")
            VERDE  = colors.HexColor("#E2EFDA")

            story = []

            # ── Título ─────────────────────────────────────────────
            story.append(Paragraph("REPORTE DE CALIDAD — RUTA", titulo_style))
            story.append(Spacer(1, 0.2*cm))

            # ── Calcular ponderados ────────────────────────────────
            estaciones = st.session_state.estaciones_guardadas
            pond_st_vals, pond_ic_vals = [], []
            for est in estaciones:
                v  = parse_num(est.get("volumen"))
                s  = parse_num(est.get("solidos"))
                cr = parse_num(est.get("crioscopia"))
                pond_st_vals.append(round(v*s,  2) if v is not None and s  is not None else None)
                pond_ic_vals.append(round(v*cr, 3) if v is not None and cr is not None else None)

            vol_total_e = sum(parse_num(e.get("volumen")) or 0 for e in estaciones)
            sum_pst = sum(x for x in pond_st_vals if x is not None)
            sum_pic = sum(x for x in pond_ic_vals if x is not None)
            st_pond = round(sum_pst / vol_total_e, 2) if vol_total_e else None
            ic_pond = round(sum_pic / vol_total_e, 3) if vol_total_e else None

            def fmt(v, dec=2):
                if v is None or v == "":
                    return ""
                try:
                    return f"{float(v):.{dec}f}"
                except Exception:
                    return str(v)

            # ── Tabla de encabezado de ruta ────────────────────────
            hdr1 = ["FECHA", "RUTA", "PLACA", "CONDUCTOR",
                    "ST RUTA", "IC RUTA", "VOLUMEN", "ST POND", "IC POND"]
            val1 = [
                fecha_ruta.strftime("%d/%m/%Y") if fecha_ruta else "",
                nombre_ruta or "",
                placa or "",
                conductor or "",
                fmt(solidos_totales, 2),
                fmt(crioscopia, 3),
                str(int(volumen)) if volumen else "",
                fmt(st_pond, 2),
                fmt(ic_pond, 3),
            ]
            t_ruta = Table(
                [hdr1, val1],
                colWidths=[2.5*cm, 3*cm, 2.2*cm, 3.5*cm,
                           2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm],
                repeatRows=1,
            )
            t_ruta.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), AZUL_L),
                ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 8),
                ("ALIGN",       (0,0), (-1,-1), "CENTER"),
                ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                ("GRID",        (0,0), (-1,-1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white]),
                ("TOPPADDING",  (0,0), (-1,-1), 3),
                ("BOTTOMPADDING",(0,0), (-1,-1), 3),
            ]))
            story.append(t_ruta)
            story.append(Spacer(1, 0.4*cm))

            # ── Tabla de estaciones ────────────────────────────────
            story.append(Paragraph("CALIDAD POR ESTACIÓN", seccion_style))

            hdr2 = ["CÓDIGO", "GRASA", "ST", "PROTEÍNA",
                    "CRIOSCOPIA", "AGUA", "VOLUMEN", "POND ST", "POND IC", "OBS"]
            filas_est = [hdr2]
            for est, pst, pic in zip(estaciones, pond_st_vals, pond_ic_vals):
                filas_est.append([
                    est.get("codigo", "") or "",
                    fmt(est.get("grasa"), 2),
                    fmt(est.get("solidos"), 2),
                    fmt(est.get("proteina"), 2),
                    fmt(est.get("crioscopia"), 3),
                    fmt(est.get("agua_pct"), 1),
                    str(int(parse_num(est.get("volumen")))) if parse_num(est.get("volumen")) is not None else "",
                    fmt(pst, 2) if pst is not None else "",
                    fmt(pic, 3) if pic is not None else "",
                    est.get("obs", "") or "",
                ])

            if len(filas_est) > 1:
                t_est = Table(
                    filas_est,
                    colWidths=[2*cm, 1.8*cm, 1.8*cm, 2*cm,
                               2.5*cm, 1.5*cm, 2*cm, 2.5*cm, 2.5*cm, 3.4*cm],
                    repeatRows=1,
                )
                t_est.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,0), AZUL_L),
                    ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0), (-1,-1), 8),
                    ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("GRID",          (0,0), (-1,-1), 0.4, colors.grey),
                    ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, VERDE]),
                    ("TOPPADDING",    (0,0), (-1,-1), 3),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                ]))
                story.append(t_est)
            else:
                story.append(Paragraph("Sin estaciones registradas.", styles["Normal"]))

            # ── Reconciliación ─────────────────────────────────────
            story.append(Spacer(1, 0.4*cm))
            story.append(Paragraph("RECONCILIACIÓN DE VOLÚMENES", seccion_style))
            rec_data = [
                ["VOLUMEN DECLARADO (L)", str(int(vol_ruta)) if vol_ruta else "—"],
                ["VOLUMEN SUMA ESTACIONES (L)", str(int(vol_est_total)) if vol_est_total else "—"],
                ["DIFERENCIA (L)", f"{int(diferencia):+}" if vol_ruta else "—"],
            ]
            t_rec = Table(rec_data, colWidths=[7*cm, 4*cm])
            t_rec.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (0,-1), AZUL_L),
                ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 8),
                ("ALIGN",       (0,0), (-1,-1), "CENTER"),
                ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                ("GRID",        (0,0), (-1,-1), 0.4, colors.grey),
                ("TOPPADDING",  (0,0), (-1,-1), 3),
                ("BOTTOMPADDING",(0,0), (-1,-1), 3),
            ]))
            story.append(t_rec)

            # ── Imágenes ───────────────────────────────────────────
            if imagenes:
                story.append(PageBreak())
                story.append(Paragraph("IMÁGENES DE MUESTRAS", seccion_style))
                story.append(Spacer(1, 0.3*cm))
                imgs = list(imagenes)
                IMG_MAX_W = 12*cm
                IMG_MAX_H = 9*cm
                idx_g = 0
                for i in range(0, len(imgs), 2):
                    row_cells = []
                    for img_file in [imgs[i], imgs[i+1] if i+1 < len(imgs) else None]:
                        if img_file is None:
                            row_cells.append("")
                            continue
                        idx_g += 1
                        raw = io.BytesIO(img_file.read())
                        pil = PILImage.open(raw).convert("RGB")
                        w, h = pil.size
                        # Escalar proporcionalmente
                        scale = min(IMG_MAX_W / (w * cm / 28.35),
                                    IMG_MAX_H / (h * cm / 28.35))
                        dw = w * scale * cm / 28.35
                        dh = h * scale * cm / 28.35
                        resized = io.BytesIO()
                        pil.save(resized, format="PNG")
                        resized.seek(0)
                        label = f"{base_nombre}_{idx_g}"
                        cell_content = [
                            Paragraph(label, ParagraphStyle(
                                "lbl", fontSize=8, fontName="Helvetica-Bold",
                                alignment=TA_CENTER)),
                            RLImage(resized, width=dw, height=dh),
                        ]
                        row_cells.append(cell_content)
                    tbl_img = Table(
                        [row_cells],
                        colWidths=[13*cm, 13*cm] if len(row_cells) == 2 else [13*cm],
                    )
                    tbl_img.setStyle(TableStyle([
                        ("ALIGN",  (0,0), (-1,-1), "CENTER"),
                        ("VALIGN", (0,0), (-1,-1), "TOP"),
                        ("GRID",   (0,0), (-1,-1), 0.3, colors.lightgrey),
                        ("TOPPADDING",    (0,0), (-1,-1), 4),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                    ]))
                    story.append(tbl_img)
                    story.append(Spacer(1, 0.3*cm))

            doc.build(story)
            buf.seek(0)
            return buf

        # ── Nombres de archivo ────────────────────────────────────────
        _placa = (placa or "SIN_PLACA").replace(" ", "_").upper()
        _ruta  = (nombre_ruta or "SIN_RUTA").replace(" ", "_").upper()
        _base  = f"{_placa}_{_ruta}"

        # Pre-leer imágenes en memoria para que ambas funciones puedan usarlas
        class _Img:
            def __init__(self, name, data):
                self.name = name
                self._data = data
            def read(self):
                return self._data

        imgs_param = (
            [_Img(f.name, f.read()) for f in imagenes_subidas]
            if imagenes_subidas and st.session_state.get("imagenes_confirmadas") else None
        )

        col_xl, col_pdf = st.columns(2)
        with col_xl:
            st.download_button(
                label="⬇️ DESCARGAR EXCEL",
                data=generar_excel(imagenes=imgs_param, base_nombre=_base),
                file_name=f"{_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
        with col_pdf:
            st.download_button(
                label="⬇️ DESCARGAR PDF",
                data=generar_pdf(imagenes=imgs_param, base_nombre=_base),
                file_name=f"{_base}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

        # ── GUARDAR RUTA EN HISTORIAL ──────────────────────────────────
        st.markdown("---")
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 💾 Guardar en Historial
               </div>""",
            unsafe_allow_html=True,
        )

        if "ruta_guardada_ok" not in st.session_state:
            st.session_state.ruta_guardada_ok = False

        if st.button(
            "💾  GUARDAR RUTA",
            type="primary",
            use_container_width=True,
            key="btn_guardar_ruta",
        ):
            save_ruta_to_csv({
                "tipo_seguimiento": "RUTAS",
                "fecha":            fecha_ruta.strftime("%d/%m/%Y") if fecha_ruta else "",
                "ruta":             nombre_ruta or "",
                "placa":            placa or "",
                "conductor":        conductor or "",
                "volumen_declarado": int(volumen) if volumen else "",
                "vol_estaciones":   int(vol_est_total) if vol_est_total else "",
                "diferencia":       int(diferencia) if vol_ruta else "",
                "solidos_ruta":     solidos_totales if solidos_totales is not None else "",
                "crioscopia_ruta":  crioscopia if crioscopia is not None else "",
                "st_pond":          _st_pond if _st_pond is not None else "",
                "ic_pond":          _ic_pond if _ic_pond is not None else "",
                "num_estaciones":   len(st.session_state.estaciones_guardadas),
                "guardado_en":      datetime.now().strftime("%d/%m/%Y %H:%M"),
                "estaciones_json":  json.dumps(
                    st.session_state.estaciones_guardadas, ensure_ascii=False
                ),
            })
            # ── Reiniciar todos los campos del formulario ──────────────
            for _k in ["fecha_ruta", "nombre_ruta", "placa_vehiculo", "conductor",
                        "solidos_totales", "crioscopia", "imagenes_muestras",
                        "volumen_ruta"]:
                st.session_state.pop(_k, None)
            st.session_state.estaciones_guardadas          = []
            st.session_state.imagenes_confirmadas          = False
            st.session_state.imagenes_nombres_guardados    = []
            st.session_state.ruta_guardada_ok              = True
            clear_draft_state()
            st.rerun()

        if st.session_state.ruta_guardada_ok:
            st.success(
                "✅ Ruta guardada exitosamente en el historial. "
                "Puedes consultarla en **📊 Historial de Rutas** al final de la página."
            )
            st.session_state.ruta_guardada_ok = False

    elif tipo_servicio == "TRANSUIZA":
        st.markdown(
            """<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                 <span style="font-size:1.35rem;">🚛</span>
                 <span style="font-size:1.35rem;font-weight:700;color:#0056A3;
                              letter-spacing:.5px;font-family:'Segoe UI',sans-serif;">
                   SEGUIMIENTO TRANSUIZA
                 </span>
               </div>""",
            unsafe_allow_html=True,
        )

        # ── Datos de identificación ────────────────────────────────────
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 📋 Datos de Identificación
               </div>""",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            tc1, tc2, tc3 = st.columns(3)
            trans_fecha = tc1.date_input(
                "📅 FECHA", datetime.now(), key="trans_fecha", format="DD/MM/YYYY"
            )
            trans_placa = tc2.text_input(
                "🚚 PLACA DEL VEHÍCULO", placeholder="AAA000", key="trans_placa",
                on_change=lambda: st.session_state.__setitem__(
                    "trans_placa",
                    re.sub(r"[^A-Z0-9]", "", st.session_state.get("trans_placa", "").upper())
                ),
            )
            trans_st_carrotanque = tc3.number_input(
                "🏷️ ST DEL CARROTANQUE (%)", min_value=0.0, max_value=100.0,
                step=0.01, format="%.2f", value=None, placeholder="0.00",
                key="trans_st_carrotanque",
            )
        activar_siguiente_con_enter()

        # ── Calidad de la muestra ──────────────────────────────────────
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 🧪 Calidad de la Muestra
               </div>""",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            qc1, qc2, qc3 = st.columns(3)
            trans_grasa = qc1.number_input(
                "GRASA (%)", min_value=0.0, max_value=100.0,
                step=0.01, format="%.2f", value=None, placeholder="0.00",
                key="trans_grasa",
            )
            trans_st_muestra = qc2.number_input(
                "ST MUESTRA (%)", min_value=0.0, max_value=100.0,
                step=0.01, format="%.2f", value=None, placeholder="0.00",
                key="trans_st_muestra",
            )
            trans_proteina = qc3.number_input(
                "PROTEÍNA (%)", min_value=0.0, max_value=100.0,
                step=0.01, format="%.2f", value=None, placeholder="0.00",
                key="trans_proteina",
            )

            # ── Diferencia de Sólidos (automática) ────────────────────
            if trans_st_carrotanque is not None and trans_st_muestra is not None:
                dif_solidos = round(trans_st_carrotanque - trans_st_muestra, 2)
                color_dif = "#9C0006" if abs(dif_solidos) > 0.5 else "#006100"
                st.markdown(
                    f"""<div style="margin-top:12px;padding:12px 16px;
                        background:#F8FAFC;border-radius:10px;
                        border:1.5px solid #D1D5DB;text-align:center;">
                        <div style="font-size:11px;font-weight:600;color:#6B7280;
                                    letter-spacing:.4px;margin-bottom:4px;">
                            DIFERENCIA DE SÓLIDOS (ST Carrotanque − ST Muestra)
                        </div>
                        <div style="font-size:2rem;font-weight:800;color:{color_dif};">
                            {dif_solidos:+.2f} %
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                dif_solidos = None
                st.info("💡 Ingrese ST del Carrotanque y ST Muestra para calcular la diferencia.")

        # ── Guardar Transuiza ──────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 💾 Guardar en Historial
               </div>""",
            unsafe_allow_html=True,
        )
        if "trans_guardado_ok" not in st.session_state:
            st.session_state.trans_guardado_ok = False

        if st.button("💾  GUARDAR TRANSUIZA", type="primary",
                     use_container_width=True, key="btn_guardar_trans"):
            if not trans_placa:
                st.warning("⚠️ Ingrese la placa del vehículo.")
            else:
                save_ruta_to_csv({
                    "tipo_seguimiento": "TRANSUIZA",
                    "fecha":            trans_fecha.strftime("%d/%m/%Y") if trans_fecha else "",
                    "ruta":             "ENTRERIOS",
                    "placa":            (trans_placa or "").upper(),
                    "st_carrotanque":   trans_st_carrotanque if trans_st_carrotanque is not None else "",
                    "solidos_ruta":     trans_st_muestra if trans_st_muestra is not None else "",
                    "grasa_muestra":    trans_grasa if trans_grasa is not None else "",
                    "proteina_muestra": trans_proteina if trans_proteina is not None else "",
                    "diferencia_solidos": dif_solidos if dif_solidos is not None else "",
                    "guardado_en":      datetime.now().strftime("%d/%m/%Y %H:%M"),
                })
                for _k in ["trans_placa", "trans_st_carrotanque", "trans_grasa",
                            "trans_st_muestra", "trans_proteina", "trans_fecha"]:
                    st.session_state.pop(_k, None)
                st.session_state.trans_guardado_ok = True
                clear_draft_state()
                st.rerun()

        if st.session_state.trans_guardado_ok:
            st.success("✅ Registro TRANSUIZA guardado en el historial.")
            st.session_state.trans_guardado_ok = False

    elif tipo_servicio == "SEGUIMIENTOS":
        _sub = sub_tipo_seg or st.session_state.get("_sub_tipo_seg_guardado", "TERCEROS")

        # ── Encabezado ────────────────────────────────────────────────
        icono_sub = {"TERCEROS": "🧾", "ESTACIONES": "🏭",
                     "ACOMPAÑAMIENTOS": "👥", "CONTRAMUESTRAS SOLICITADAS": "🧪"}.get(_sub, "📋")
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                  <span style="font-size:1.35rem;">{icono_sub}</span>
                  <span style="font-size:1.35rem;font-weight:700;color:#0056A3;
                               letter-spacing:.5px;font-family:'Segoe UI',sans-serif;">
                    SEGUIMIENTO — {_sub}
                  </span>
                </div>""",
            unsafe_allow_html=True,
        )

        # ── Datos de Identificación ───────────────────────────────────
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 📋 Datos de Identificación
               </div>""",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            if _sub in ("TERCEROS", "ESTACIONES"):
                sid1, sid2 = st.columns(2)
                seg_fecha = sid1.date_input("📅 FECHA", datetime.now(),
                                             key="seg_fecha", format="DD/MM/YYYY")
                seg_codigo = sid2.text_input("🔖 CÓDIGO", placeholder="ESCRIBA CÓDIGO",
                                              key="seg_codigo",
                                              on_change=convertir_a_mayusculas,
                                              args=("seg_codigo",))
                seg_quien_trajo = ""
                seg_ruta_acomp  = ""
                seg_responsable = ""

            elif _sub == "ACOMPAÑAMIENTOS":
                sa1, sa2, sa3 = st.columns(3)
                seg_fecha = sa1.date_input("📅 FECHA", datetime.now(),
                                            key="seg_fecha", format="DD/MM/YYYY")
                seg_quien_trajo = sa2.text_input("👤 ENTREGADO POR",
                                                  placeholder="NOMBRE...", key="seg_quien_trajo",
                                                  on_change=convertir_a_mayusculas,
                                                  args=("seg_quien_trajo",))
                seg_ruta_acomp = sa3.text_input("📍 RUTA", placeholder="NOMBRE DE RUTA",
                                                  key="seg_ruta_acomp",
                                                  on_change=convertir_a_mayusculas,
                                                  args=("seg_ruta_acomp",))
                seg_codigo      = ""
                seg_responsable = ""

            else:  # CONTRAMUESTRAS SOLICITADAS
                sc1, sc2 = st.columns(2)
                seg_fecha = sc1.date_input("📅 FECHA DE LAS MUESTRAS", datetime.now(),
                                            key="seg_fecha", format="DD/MM/YYYY")
                seg_responsable = sc2.text_input("👤 ENTREGADO POR",
                                                   placeholder="NOMBRE...", key="seg_responsable",
                                                   on_change=convertir_a_mayusculas,
                                                   args=("seg_responsable",))
                seg_codigo      = ""
                seg_quien_trajo = ""
                seg_ruta_acomp  = ""

        activar_siguiente_con_enter()

        # ── Análisis de Calidad ───────────────────────────────────────
        st.markdown(
            """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                           margin:14px 0 6px 0;letter-spacing:.4px;
                           border-left:4px solid #0056A3;padding-left:10px;">
                 🧪 Parámetros de Calidad
               </div>""",
            unsafe_allow_html=True,
        )
        _qk = st.session_state.get("seg_quality_key_counter", 0)
        with st.container(border=True):
            seg_id_muestra = ""
            if _sub in ("ACOMPAÑAMIENTOS", "CONTRAMUESTRAS SOLICITADAS"):
                _id_col, _ = st.columns([2, 4])
                with _id_col:
                    seg_id_muestra = st.text_input(
                        "🔬 ID MUESTRA", placeholder="Ej: M001-A",
                        key=f"seg_id_muestra_{_qk}",
                        on_change=convertir_a_mayusculas,
                        args=(f"seg_id_muestra_{_qk}",),
                    )

            sq1, sq2, sq3 = st.columns(3)
            seg_grasa = sq1.number_input("GRASA (%)", min_value=0.0, max_value=100.0,
                                          step=0.01, format="%.2f", value=None,
                                          placeholder="0.00", key=f"seg_grasa_{_qk}")
            seg_st    = sq2.number_input("ST (%)", min_value=0.0, max_value=100.0,
                                          step=0.01, format="%.2f", value=None,
                                          placeholder="0.00", key=f"seg_st_{_qk}")
            with sq3:
                seg_ic_raw = st.text_input("IC (°C)", key=f"seg_ic_raw_{_qk}",
                                            value="-0.", placeholder="-0.530")
                try:
                    seg_ic = float(seg_ic_raw.replace(",", ".")) \
                        if seg_ic_raw not in ("", "-", "-0", "-0.") else None
                except ValueError:
                    seg_ic = None
                    st.warning("⚠️ Ingrese un número válido")
            _ic_fuera = seg_ic is not None and seg_ic > -0.530
            _ic_bajo  = seg_ic is not None and seg_ic < -0.550
            seg_agua = None
            if _ic_fuera:
                _aw1, _aw2 = st.columns([1, 2])
                with _aw1:
                    seg_agua = st.number_input("💧 AGUA ADICIONADA (%)",
                                               min_value=0.0, max_value=100.0,
                                               step=0.01, format="%.2f", value=None,
                                               placeholder="0.00", key=f"seg_agua_{_qk}")

            # ── Alertas de calidad ─────────────────────────────────────
            if seg_st is not None and seg_st > 0 and seg_st < 12.60:
                st.error("🚨 ALERTA: ST FUERA DE RANGO (MENOR A 12.60%)")
            elif seg_st is not None and seg_st > 0:
                st.success("✅ ST dentro del parámetro")

            if _ic_fuera:
                st.error("🚨 ALERTA: CRIOSCOPIA FUERA DE RANGO (MAYOR A -0.530)")
            elif _ic_bajo:
                st.error("🚨 ALERTA: CRIOSCOPIA FUERA DE RANGO (MENOR A -0.550)")
            elif seg_ic is not None:
                st.success("✅ Crioscopia dentro del parámetro")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            sq5, sq6, sq7 = st.columns(3)
            opciones_tri = ["N/A", "NEGATIVO (−)", "POSITIVO (+)"]
            seg_alcohol        = sq5.selectbox("ALCOHOL",        opciones_tri, key=f"seg_alcohol_{_qk}")
            seg_cloruros       = sq6.selectbox("CLORUROS",       opciones_tri, key=f"seg_cloruros_{_qk}")
            seg_neutralizantes = sq7.selectbox("NEUTRALIZANTES", opciones_tri, key=f"seg_neutralizantes_{_qk}")

            _positivos = [p for p, v in [("ALCOHOL", seg_alcohol),
                                           ("CLORUROS", seg_cloruros),
                                           ("NEUTRALIZANTES", seg_neutralizantes)]
                          if v == "POSITIVO (+)"]
            if _positivos:
                st.error(f"🚨 ALERTA: {', '.join(_positivos)} POSITIVO(S) — ADULTERACIÓN")

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            seg_observaciones = st.text_area("📝 OBSERVACIONES", placeholder="ESCRIBA AQUÍ...",
                                              key=f"seg_observaciones_{_qk}", height=90)

        # ── ACOMPAÑAMIENTOS: botón agregar muestra ────────────────────
        if _sub == "ACOMPAÑAMIENTOS":
            if "acomp_muestras" not in st.session_state:
                st.session_state.acomp_muestras = []

            if st.button("➕  AGREGAR MUESTRA", use_container_width=True,
                         key="btn_agregar_muestra"):
                st.session_state.acomp_muestras.append({
                    "ID": seg_id_muestra or "",
                    "GRASA (%)": f"{seg_grasa:.2f}" if seg_grasa is not None else "",
                    "ST (%)":    f"{seg_st:.2f}"    if seg_st    is not None else "",
                    "IC (°C)":   f"{seg_ic:.3f}"    if seg_ic    is not None else "",
                    "AGUA (%)":  f"{seg_agua:.2f}"  if seg_agua  is not None else "",
                    "ALCOHOL":   seg_alcohol,
                    "CLORUROS":  seg_cloruros,
                    "NEUTRALIZANTES": seg_neutralizantes,
                    "OBS":       seg_observaciones or "",
                    "_grasa": seg_grasa, "_st": seg_st, "_ic": seg_ic,
                    "_agua": seg_agua, "_alcohol": seg_alcohol,
                    "_cloruros": seg_cloruros, "_neutralizantes": seg_neutralizantes,
                    "_obs": seg_observaciones or "",
                })
                # Rotar contador → todos los widgets de calidad quedan con clave nueva y valores por defecto
                st.session_state["seg_quality_key_counter"] = \
                    st.session_state.get("seg_quality_key_counter", 0) + 1
                st.rerun()

            if st.session_state.acomp_muestras:
                st.markdown(
                    f"""<div style="font-size:0.9rem;font-weight:700;color:#0056A3;
                                   margin:10px 0 4px 0;">
                         📋 {len(st.session_state.acomp_muestras)} muestra(s) registrada(s)
                       </div>""",
                    unsafe_allow_html=True,
                )
                df_preview = pd.DataFrame([
                    {k: v for k, v in m.items() if not k.startswith("_")}
                    for m in st.session_state.acomp_muestras
                ])
                st.dataframe(df_preview, use_container_width=True, hide_index=True)

        # ── CONTRAMUESTRAS: botón agregar muestra ────────────────────
        if _sub == "CONTRAMUESTRAS SOLICITADAS":
            if "contra_muestras" not in st.session_state:
                st.session_state.contra_muestras = []

            if st.button("➕  AGREGAR CONTRAMUESTRA", use_container_width=True,
                         key="btn_agregar_contra"):
                st.session_state.contra_muestras.append({
                    "ID": seg_id_muestra or "",
                    "GRASA (%)": f"{seg_grasa:.2f}" if seg_grasa is not None else "",
                    "ST (%)":    f"{seg_st:.2f}"    if seg_st    is not None else "",
                    "IC (°C)":   f"{seg_ic:.3f}"    if seg_ic    is not None else "",
                    "AGUA (%)":  f"{seg_agua:.2f}"  if seg_agua  is not None else "",
                    "ALCOHOL":   seg_alcohol,
                    "CLORUROS":  seg_cloruros,
                    "NEUTRALIZANTES": seg_neutralizantes,
                    "OBS":       seg_observaciones or "",
                    "_grasa": seg_grasa, "_st": seg_st, "_ic": seg_ic,
                    "_agua": seg_agua, "_alcohol": seg_alcohol,
                    "_cloruros": seg_cloruros, "_neutralizantes": seg_neutralizantes,
                    "_obs": seg_observaciones or "",
                })
                st.session_state["seg_quality_key_counter"] = \
                    st.session_state.get("seg_quality_key_counter", 0) + 1
                st.rerun()

            if st.session_state.contra_muestras:
                st.markdown(
                    f"""<div style="font-size:0.9rem;font-weight:700;color:#0056A3;
                                   margin:10px 0 4px 0;">
                         📋 {len(st.session_state.contra_muestras)} contramuestra(s) registrada(s)
                       </div>""",
                    unsafe_allow_html=True,
                )
                df_preview_c = pd.DataFrame([
                    {k: v for k, v in m.items() if not k.startswith("_")}
                    for m in st.session_state.contra_muestras
                ])
                st.dataframe(df_preview_c, use_container_width=True, hide_index=True)

        # ── Guardar Seguimiento ───────────────────────────────────────
        if _sub != "TERCEROS":
            st.markdown("---")
            st.markdown(
                """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                               margin:14px 0 6px 0;letter-spacing:.4px;
                               border-left:4px solid #0056A3;padding-left:10px;">
                     💾 Guardar en Historial
                   </div>""",
                unsafe_allow_html=True,
            )
        if "seg_guardado_ok" not in st.session_state:
            st.session_state.seg_guardado_ok = False

        if st.button(f"💾  GUARDAR {_sub}", type="primary",
                     use_container_width=True, key="btn_guardar_seg"):
            ts = datetime.now().strftime("%d/%m/%Y %H:%M")
            base = {
                "tipo_seguimiento":     "SEGUIMIENTOS",
                "sub_tipo_seguimiento": _sub,
                "fecha":                seg_fecha.strftime("%d/%m/%Y") if seg_fecha else "",
                "seg_codigo":           seg_codigo,
                "seg_quien_trajo":      seg_quien_trajo,
                "ruta":                 seg_ruta_acomp,
                "seg_responsable":      seg_responsable,
                "guardado_en":          ts,
            }
            def _guardar_lista_muestras(lista):
                for m in lista:
                    save_seguimiento_to_csv({**base,
                        "seg_id_muestra":     m.get("ID", ""),
                        "seg_grasa":          m.get("_grasa", ""),
                        "seg_st":             m.get("_st", ""),
                        "seg_ic":             m.get("_ic", ""),
                        "seg_agua":           m.get("_agua", ""),
                        "seg_alcohol":        m.get("_alcohol", ""),
                        "seg_cloruros":       m.get("_cloruros", ""),
                        "seg_neutralizantes": m.get("_neutralizantes", ""),
                        "seg_observaciones":  m.get("_obs", ""),
                    })

            if _sub == "ACOMPAÑAMIENTOS" and st.session_state.get("acomp_muestras"):
                _guardar_lista_muestras(st.session_state.acomp_muestras)
                st.session_state.acomp_muestras = []
            elif _sub == "CONTRAMUESTRAS SOLICITADAS" and st.session_state.get("contra_muestras"):
                _guardar_lista_muestras(st.session_state.contra_muestras)
                st.session_state.contra_muestras = []
            else:
                save_seguimiento_to_csv({**base,
                    "seg_id_muestra":    seg_id_muestra or "",
                    "seg_grasa":         seg_grasa if seg_grasa is not None else "",
                    "seg_st":            seg_st    if seg_st    is not None else "",
                    "seg_ic":            seg_ic    if seg_ic    is not None else "",
                    "seg_agua":          seg_agua  if seg_agua  is not None else "",
                    "seg_alcohol":       seg_alcohol,
                    "seg_cloruros":      seg_cloruros,
                    "seg_neutralizantes": seg_neutralizantes,
                    "seg_observaciones": seg_observaciones or "",
                })
            for _k in ["seg_fecha", "seg_codigo", "seg_quien_trajo", "seg_ruta_acomp",
                        "seg_responsable"]:
                st.session_state.pop(_k, None)
            st.session_state["seg_quality_key_counter"] = \
                st.session_state.get("seg_quality_key_counter", 0) + 1
            st.session_state.contra_muestras = []
            st.session_state.seg_guardado_ok = True
            clear_draft_state()
            st.rerun()

        if st.session_state.seg_guardado_ok:
            st.success(f"✅ Seguimiento {_sub} guardado en el historial.")
            st.session_state.seg_guardado_ok = False

    if st.sidebar.button("REINICIAR FORMULARIO"):
        st.session_state.continuar = False
        clear_draft_state()
        st.rerun()


st.markdown("---")

# ── Estado de gestión de historial ──────────────────────────────────────────
for _sk, _sv in [
    ("admin_accion", None), ("admin_idx", None),
    ("admin_pin_ok", False), ("admin_pin_error", False),
]:
    if _sk not in st.session_state:
        st.session_state[_sk] = _sv

# ── HISTORIAL DE RUTAS ──────────────────────────────────────────────────────
st.markdown(
    """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                   margin:14px 0 6px 0;letter-spacing:.4px;
                   border-left:4px solid #0056A3;padding-left:10px;">
         📊 Historial de Rutas
       </div>""",
    unsafe_allow_html=True,
)

with st.expander("VER HISTORIAL DE RUTAS", expanded=False):
    df_hist = load_historial()
    if df_hist.empty:
        st.info("No hay rutas guardadas aún. Complete el formulario y presione **GUARDAR RUTA** para registrar datos aquí.")
    else:
        # ── Filtros ───────────────────────────────────────────────────
        st.markdown(
            "<div style='font-weight:600;color:#374151;margin-bottom:8px;'>"
            "🔍 Filtros de búsqueda</div>",
            unsafe_allow_html=True,
        )
        hf1, hf2, hf3, hf4 = st.columns([2, 2, 2, 2])

        # 1. Tipo de Seguimiento
        with hf1:
            filtro_tipo = st.selectbox(
                "TIPO DE SEGUIMIENTO",
                ["TODOS", "RUTAS", "TRANSUIZA", "SEGUIMIENTOS"],
                key="hist_tipo",
            )

        # 2. Rango de fechas
        fechas_validas = (
            df_hist["_fecha_dt"].dropna()
            if "_fecha_dt" in df_hist.columns
            else pd.Series(dtype="datetime64[ns]")
        )
        fecha_min_val = fechas_validas.min().date() if not fechas_validas.empty else date.today()
        fecha_max_val = fechas_validas.max().date() if not fechas_validas.empty else date.today()

        with hf2:
            fecha_desde = st.date_input(
                "FECHA DESDE", value=fecha_min_val,
                format="DD/MM/YYYY", key="hist_desde",
            )
        with hf3:
            fecha_hasta = st.date_input(
                "FECHA HASTA", value=fecha_max_val,
                format="DD/MM/YYYY", key="hist_hasta",
            )

        # 3. Placa del Vehículo
        placas_unicas = (
            ["TODAS"] + sorted(df_hist["placa"].dropna().replace("", pd.NA).dropna().unique().tolist())
            if "placa" in df_hist.columns else ["TODAS"]
        )
        with hf4:
            filtro_placa = st.selectbox("PLACA DEL VEHÍCULO", placas_unicas, key="hist_placa")

        # Filtro adicional: Nombre de Ruta (solo visible cuando tipo = RUTAS)
        filtro_ruta = "TODAS"
        if filtro_tipo == "RUTAS":
            df_rutas_solo = df_hist[df_hist["tipo_seguimiento"] == "RUTAS"] \
                if "tipo_seguimiento" in df_hist.columns else df_hist
            rutas_unicas = (
                ["TODAS"] + sorted(
                    df_rutas_solo["ruta"].dropna().replace("", pd.NA).dropna().unique().tolist()
                )
                if "ruta" in df_rutas_solo.columns else ["TODAS"]
            )
            _rc, _ = st.columns([2, 4])
            with _rc:
                filtro_ruta = st.selectbox(
                    "📍 NOMBRE DE RUTA", rutas_unicas, key="hist_ruta"
                )

        # ── Aplicar filtros ───────────────────────────────────────────
        if filtro_tipo == "SEGUIMIENTOS":
            # Fuente separada: seguimientos_historial.csv
            df_filtrado = load_seguimientos()
            if "_fecha_dt" in df_filtrado.columns:
                df_filtrado = df_filtrado[
                    (df_filtrado["_fecha_dt"].dt.date >= fecha_desde) &
                    (df_filtrado["_fecha_dt"].dt.date <= fecha_hasta)
                ]
        else:
            df_filtrado = df_hist.copy()
            if "_fecha_dt" in df_filtrado.columns:
                df_filtrado = df_filtrado[
                    (df_filtrado["_fecha_dt"].dt.date >= fecha_desde) &
                    (df_filtrado["_fecha_dt"].dt.date <= fecha_hasta)
                ]
            if filtro_tipo != "TODOS" and "tipo_seguimiento" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["tipo_seguimiento"] == filtro_tipo]
            if filtro_placa != "TODAS" and "placa" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["placa"] == filtro_placa]
            if filtro_ruta != "TODAS" and "ruta" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["ruta"] == filtro_ruta]

        # ── Columna Estado de Calidad ─────────────────────────────────
        df_filtrado = df_filtrado.copy()
        df_filtrado["_estado"] = df_filtrado.apply(
            lambda r: calcular_estado_calidad(r.to_dict()), axis=1
        )

        # ── Tabla con filas en rojo para desviaciones ─────────────────
        n_desv = (df_filtrado["_estado"] == "DESVIACIÓN").sum()
        col_info, col_alerta = st.columns([3, 1])
        with col_info:
            st.markdown(f"**{len(df_filtrado)} registro(s) encontrado(s)**")
        with col_alerta:
            if n_desv:
                st.markdown(
                    f"<div style='text-align:right;font-size:13px;"
                    f"color:#9C0006;font-weight:600;'>"
                    f"⚠️ {n_desv} desviación(es)</div>",
                    unsafe_allow_html=True,
                )

        RED = "background-color:#FFC7CE;color:#9C0006;font-weight:700"

        # ── Columnas y styler según tipo de seguimiento ───────────────
        if filtro_tipo == "TRANSUIZA":
            # Columnas exclusivas TRANSUIZA
            cols_sel = ["tipo_seguimiento", "fecha", "placa",
                        "st_carrotanque", "grasa_muestra", "solidos_ruta",
                        "proteina_muestra", "diferencia_solidos", "guardado_en"]
            col_labels = {
                "tipo_seguimiento": "TIPO", "fecha": "FECHA", "placa": "PLACA",
                "st_carrotanque": "ST CARROTANQUE (%)",
                "grasa_muestra": "GRASA (%)", "solidos_ruta": "ST MUESTRA (%)",
                "proteina_muestra": "PROTEÍNA (%)",
                "diferencia_solidos": "DIF. SÓLIDOS", "guardado_en": "GUARDADO EN",
            }
            col_config_map = {
                "ST CARROTANQUE (%)": st.column_config.NumberColumn(format="%.2f"),
                "GRASA (%)":          st.column_config.NumberColumn(format="%.2f"),
                "ST MUESTRA (%)":     st.column_config.NumberColumn(format="%.2f"),
                "PROTEÍNA (%)":       st.column_config.NumberColumn(format="%.2f"),
                "DIF. SÓLIDOS":       st.column_config.NumberColumn(format="%.2f"),
            }
            def resaltar_celdas(row):
                return [""] * len(row)

        elif filtro_tipo == "RUTAS":
            # Columnas completas RUTAS
            cols_sel = ["tipo_seguimiento", "fecha", "ruta", "placa", "conductor",
                        "volumen_declarado", "vol_estaciones", "diferencia",
                        "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
                        "num_estaciones", "guardado_en"]
            col_labels = {
                "tipo_seguimiento": "TIPO", "fecha": "FECHA", "ruta": "RUTA",
                "placa": "PLACA", "conductor": "CONDUCTOR",
                "volumen_declarado": "VOL. DECL. (L)", "vol_estaciones": "VOL. EST. (L)",
                "diferencia": "DIFER. (L)", "solidos_ruta": "ST RUTA (%)",
                "crioscopia_ruta": "IC RUTA (°C)", "st_pond": "ST POND",
                "ic_pond": "IC POND", "num_estaciones": "Nº EST.",
                "guardado_en": "GUARDADO EN",
            }
            col_config_map = {
                "ST RUTA (%)":      st.column_config.NumberColumn(format="%.2f"),
                "ST POND":          st.column_config.NumberColumn(format="%.2f"),
                "IC RUTA (°C)":     st.column_config.NumberColumn(format="%.3f"),
                "IC POND":          st.column_config.NumberColumn(format="%.3f"),
                "VOL. DECL. (L)":   st.column_config.NumberColumn(format="%d"),
                "VOL. EST. (L)":    st.column_config.NumberColumn(format="%d"),
                "DIFER. (L)":       st.column_config.NumberColumn(format="%d"),
                "Nº EST.":          st.column_config.NumberColumn(format="%d"),
            }
            def resaltar_celdas(row):
                styles = [""] * len(row)
                cols = list(row.index)
                desv_st = desv_ic = False
                try:
                    v = float(str(row.get("ST RUTA (%)", "")).replace(",", "."))
                    if 0 < v < 12.60: desv_st = True
                except Exception: pass
                try:
                    v = float(str(row.get("IC RUTA (°C)", "")).replace(",", "."))
                    if v > -0.535 or v < -0.550: desv_ic = True
                except Exception: pass
                if (desv_st or desv_ic) and "RUTA" in cols:
                    styles[cols.index("RUTA")] = RED
                if desv_st and "ST RUTA (%)" in cols:
                    styles[cols.index("ST RUTA (%)")] = RED
                if desv_ic and "IC RUTA (°C)" in cols:
                    styles[cols.index("IC RUTA (°C)")] = RED
                return styles

        elif filtro_tipo == "SEGUIMIENTOS":
            cols_sel = ["sub_tipo_seguimiento", "fecha", "seg_codigo",
                        "seg_quien_trajo", "ruta", "seg_responsable",
                        "seg_id_muestra", "seg_grasa", "seg_st", "seg_ic", "seg_agua",
                        "seg_alcohol", "seg_cloruros", "seg_neutralizantes",
                        "seg_observaciones", "guardado_en"]
            col_labels = {
                "sub_tipo_seguimiento": "SUB-TIPO", "fecha": "FECHA",
                "seg_codigo": "CÓDIGO", "seg_quien_trajo": "ENTREGADO POR",
                "ruta": "RUTA", "seg_responsable": "RESPONSABLE",
                "seg_id_muestra": "ID MUESTRA",
                "seg_grasa": "GRASA (%)", "seg_st": "ST (%)",
                "seg_ic": "IC (°C)", "seg_agua": "AGUA (%)",
                "seg_alcohol": "ALCOHOL", "seg_cloruros": "CLORUROS",
                "seg_neutralizantes": "NEUTRALIZANTES",
                "seg_observaciones": "OBSERVACIONES", "guardado_en": "GUARDADO EN",
            }
            col_config_map = {
                "GRASA (%)": st.column_config.NumberColumn(format="%.2f"),
                "ST (%)":    st.column_config.NumberColumn(format="%.2f"),
                "IC (°C)":   st.column_config.NumberColumn(format="%.3f"),
                "AGUA (%)":  st.column_config.NumberColumn(format="%.2f"),
            }
            def resaltar_celdas(row):
                return [""] * len(row)

        else:
            # TODOS: columnas comunes + identificación
            cols_sel = ["tipo_seguimiento", "fecha", "ruta", "placa", "conductor",
                        "solidos_ruta", "crioscopia_ruta", "guardado_en"]
            col_labels = {
                "tipo_seguimiento": "TIPO", "fecha": "FECHA", "ruta": "RUTA",
                "placa": "PLACA", "conductor": "CONDUCTOR",
                "solidos_ruta": "ST / ST MUESTRA (%)", "crioscopia_ruta": "IC RUTA (°C)",
                "guardado_en": "GUARDADO EN",
            }
            col_config_map = {
                "ST / ST MUESTRA (%)": st.column_config.NumberColumn(format="%.2f"),
                "IC RUTA (°C)":        st.column_config.NumberColumn(format="%.3f"),
            }
            def resaltar_celdas(row):
                styles = [""] * len(row)
                # Solo resaltar filas de RUTAS, no TRANSUIZA ni SEGUIMIENTOS
                if str(row.get("TIPO", "")).strip() == "TRANSUIZA":
                    return styles
                cols = list(row.index)
                desv_st = desv_ic = False
                try:
                    v = float(str(row.get("ST / ST MUESTRA (%)", "")).replace(",", "."))
                    if 0 < v < 12.60: desv_st = True
                except Exception: pass
                try:
                    v = float(str(row.get("IC RUTA (°C)", "")).replace(",", "."))
                    if v > -0.535 or v < -0.550: desv_ic = True
                except Exception: pass
                if (desv_st or desv_ic) and "RUTA" in cols:
                    styles[cols.index("RUTA")] = RED
                if desv_st and "ST / ST MUESTRA (%)" in cols:
                    styles[cols.index("ST / ST MUESTRA (%)")] = RED
                if desv_ic and "IC RUTA (°C)" in cols:
                    styles[cols.index("IC RUTA (°C)")] = RED
                return styles

        # Filtrar solo columnas que existen
        cols_data = [c for c in CSV_COLS if c in df_filtrado.columns]
        cols_vis   = [c for c in cols_sel if c in df_filtrado.columns]
        df_display = df_filtrado[cols_vis].rename(columns=col_labels).reset_index(drop=True)

        sel = st.dataframe(
            df_display.style.apply(resaltar_celdas, axis=1),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config=col_config_map,
        )

        # ── Descarga Excel filtrado (filas rojas para desviaciones) ──
        if not df_filtrado.empty:
            df_para_excel = df_filtrado[["_estado"] + cols_data].copy()
            excel_bytes = historial_to_excel(df_para_excel)
            st.download_button(
                label="⬇️ DESCARGAR REPORTE EXCEL",
                data=excel_bytes,
                file_name=f"historial_qualilact_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=False,
            )

        # ── Botones de acción — visibles solo al seleccionar una fila ─
        orig_indices  = df_filtrado.index.tolist()
        filas_sel     = (sel.selection.rows
                         if sel and hasattr(sel, "selection") else [])
        sel_orig_idx  = orig_indices[filas_sel[0]] if filas_sel else None

        if sel_orig_idx is not None:
            st.markdown(
                "<div style='font-size:12px;color:#6B7280;margin:6px 0 4px 0;'>"
                "Fila seleccionada — elige una acción:</div>",
                unsafe_allow_html=True,
            )
            ab1, ab2, _ = st.columns([1, 1, 5])
            with ab1:
                if st.button("✏️ Modificar", key="btn_modificar", use_container_width=True,
                             help="Editar este registro"):
                    st.session_state.admin_accion    = "modificar"
                    st.session_state.admin_idx       = sel_orig_idx
                    st.session_state.admin_pin_ok    = False
                    st.session_state.admin_pin_error = False
                    st.rerun()
            with ab2:
                if st.button("🗑️ Eliminar", key="btn_eliminar", use_container_width=True,
                             help="Eliminar este registro"):
                    st.session_state.admin_accion    = "eliminar"
                    st.session_state.admin_idx       = sel_orig_idx
                    st.session_state.admin_pin_ok    = False
                    st.session_state.admin_pin_error = False
                    st.rerun()

        # ── PIN + Acción ──────────────────────────────────────────────
        accion_activa = st.session_state.get("admin_accion")
        idx_activo    = st.session_state.get("admin_idx")

        if accion_activa in ("modificar", "eliminar") and idx_activo is not None:
            with st.container(border=True):

                if not st.session_state.get("admin_pin_ok"):
                    # ── Solicitar PIN ─────────────────────────────
                    icono_acc = "✏️" if accion_activa == "modificar" else "🗑️"
                    txt_acc   = "Modificar" if accion_activa == "modificar" else "Eliminar"
                    st.markdown(
                        f"<div style='font-weight:700;color:#0056A3;margin-bottom:6px;'>"
                        f"🔐 {icono_acc} {txt_acc} — Ingrese el Código de Administrador</div>",
                        unsafe_allow_html=True,
                    )
                    pin_col, _ = st.columns([2, 3])
                    with pin_col:
                        pin_val = st.text_input(
                            "CÓDIGO", type="password", max_chars=10,
                            placeholder="••••", key="admin_pin_input",
                        )
                    if st.session_state.get("admin_pin_error"):
                        st.error("🚫 Acceso Denegado — Código incorrecto.")
                    pc1, pc2, _ = st.columns([1, 1, 3])
                    with pc1:
                        if st.button("✅ VALIDAR", type="primary",
                                     key="btn_validar_pin", use_container_width=True):
                            if pin_val == ADMIN_PIN:
                                st.session_state.admin_pin_ok    = True
                                st.session_state.admin_pin_error = False
                            else:
                                st.session_state.admin_pin_error = True
                            st.rerun()
                    with pc2:
                        if st.button("✖ CANCELAR", key="btn_cancel_pin",
                                     use_container_width=True):
                            st.session_state.admin_accion    = None
                            st.session_state.admin_idx       = None
                            st.session_state.admin_pin_ok    = False
                            st.session_state.admin_pin_error = False
                            st.rerun()

                else:
                    # PIN validado — ejecutar acción
                    row_activa = df_hist.loc[idx_activo]

                    if accion_activa == "eliminar":
                        # ── Confirmación de borrado ───────────────
                        st.markdown(
                            "<div style='font-weight:700;color:#9C0006;margin-bottom:4px;'>"
                            "🗑️ ¿Confirmar eliminación del siguiente registro?</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Fecha:** {row_activa.get('fecha','')} &nbsp;·&nbsp; "
                            f"**Ruta:** {row_activa.get('ruta','')} &nbsp;·&nbsp; "
                            f"**Placa:** {row_activa.get('placa','')}",
                        )
                        dc1, dc2, _ = st.columns([1.5, 1, 3])
                        with dc1:
                            if st.button("🗑️ CONFIRMAR", type="primary",
                                         key="btn_confirm_del", use_container_width=True):
                                if filtro_tipo == "SEGUIMIENTOS":
                                    delete_seg_row(idx_activo)
                                else:
                                    delete_row_from_csv(idx_activo)
                                st.session_state.admin_accion = None
                                st.session_state.admin_idx    = None
                                st.session_state.admin_pin_ok = False
                                st.rerun()
                        with dc2:
                            if st.button("✖ CANCELAR", key="btn_cancel_del",
                                         use_container_width=True):
                                st.session_state.admin_accion = None
                                st.session_state.admin_idx    = None
                                st.session_state.admin_pin_ok = False
                                st.rerun()

                    elif accion_activa == "modificar":
                        # ── Formulario de edición ─────────────────
                        st.markdown(
                            "<div style='font-weight:700;color:#0056A3;margin-bottom:8px;'>"
                            "✏️ Editar Registro</div>",
                            unsafe_allow_html=True,
                        )
                        try:
                            fecha_orig = datetime.strptime(
                                str(row_activa.get("fecha", "")), "%d/%m/%Y"
                            ).date()
                        except Exception:
                            fecha_orig = date.today()
                        try:
                            vol_orig = int(float(str(row_activa.get("volumen_declarado", 0) or 0)))
                        except Exception:
                            vol_orig = 0
                        try:
                            st_orig = float(str(row_activa.get("solidos_ruta", "0") or 0).replace(",", "."))
                        except Exception:
                            st_orig = 0.0
                        try:
                            ic_orig = float(str(row_activa.get("crioscopia_ruta", "0") or 0).replace(",", "."))
                        except Exception:
                            ic_orig = 0.0

                        ef1, ef2 = st.columns(2)
                        with ef1:
                            edit_fecha = st.date_input("FECHA", value=fecha_orig,
                                                       format="DD/MM/YYYY", key="edit_fecha")
                            edit_ruta  = st.text_input("RUTA",
                                                       value=str(row_activa.get("ruta", "")),
                                                       key="edit_ruta")
                            edit_placa = st.text_input("PLACA",
                                                       value=str(row_activa.get("placa", "")),
                                                       key="edit_placa")
                            edit_cond  = st.text_input("CONDUCTOR",
                                                       value=str(row_activa.get("conductor", "")),
                                                       key="edit_cond")
                        with ef2:
                            edit_vol = st.number_input("VOLUMEN DECLARADO (L)",
                                                       value=vol_orig, min_value=0, step=1,
                                                       key="edit_vol")
                            edit_st  = st.number_input("ST RUTA (%)", value=st_orig,
                                                       step=0.01, format="%.2f", key="edit_st")
                            edit_ic  = st.number_input("IC RUTA (°C)", value=ic_orig,
                                                       step=0.001, format="%.3f", key="edit_ic")

                        # ── Editor de Estaciones (solo RUTAS) ─────────────
                        es_tipo_ruta = str(row_activa.get("tipo_seguimiento", "RUTAS")).strip() == "RUTAS"
                        edited_estaciones_json = row_activa.get("estaciones_json", "") or ""
                        if es_tipo_ruta:
                            st.markdown(
                                "<div style='font-weight:700;color:#0056A3;"
                                "margin:14px 0 6px 0;font-size:0.92rem;"
                                "border-left:4px solid #0056A3;padding-left:8px;'>"
                                "🏭 Estaciones de la Ruta</div>",
                                unsafe_allow_html=True,
                            )
                            try:
                                est_data_orig = json.loads(edited_estaciones_json) \
                                    if edited_estaciones_json.strip() else []
                            except Exception:
                                est_data_orig = []
                            _ECOLS = ["codigo", "grasa", "solidos", "proteina",
                                      "crioscopia", "volumen", "alcohol",
                                      "cloruros", "neutralizantes", "agua_pct", "obs"]
                            df_est_edit = pd.DataFrame(est_data_orig, columns=_ECOLS) \
                                if est_data_orig else pd.DataFrame(columns=_ECOLS)
                            for _nc in ["grasa", "solidos", "proteina", "agua_pct"]:
                                df_est_edit[_nc] = pd.to_numeric(df_est_edit[_nc], errors="coerce")
                            df_est_edit["volumen"] = pd.to_numeric(
                                df_est_edit["volumen"], errors="coerce").astype("Int64")
                            edited_df_est = st.data_editor(
                                df_est_edit,
                                num_rows="dynamic",
                                use_container_width=True,
                                key="edit_est_editor",
                                column_config={
                                    "codigo":         st.column_config.TextColumn("CÓDIGO"),
                                    "grasa":          st.column_config.NumberColumn(
                                                          "GRASA (%)", format="%.2f",
                                                          min_value=0.0, max_value=100.0),
                                    "solidos":        st.column_config.NumberColumn(
                                                          "SÓL.TOT. (%)", format="%.2f",
                                                          min_value=0.0, max_value=100.0),
                                    "proteina":       st.column_config.NumberColumn(
                                                          "PROTEÍNA (%)", format="%.2f",
                                                          min_value=0.0, max_value=100.0),
                                    "crioscopia":     st.column_config.TextColumn("CRIOSCOPIA (°C)"),
                                    "volumen":        st.column_config.NumberColumn(
                                                          "VOLUMEN (L)", format="%d",
                                                          min_value=0, step=1),
                                    "alcohol":        st.column_config.SelectboxColumn(
                                                          "ALCOHOL", options=["N/A", "+", "-"],
                                                          required=True),
                                    "cloruros":       st.column_config.SelectboxColumn(
                                                          "CLORUROS", options=["N/A", "+", "-"],
                                                          required=True),
                                    "neutralizantes": st.column_config.SelectboxColumn(
                                                          "NEUTRALIZANTES", options=["N/A", "+", "-"],
                                                          required=True),
                                    "agua_pct":       st.column_config.NumberColumn(
                                                          "% AGUA", format="%.1f",
                                                          min_value=0.0, max_value=100.0),
                                    "obs":            st.column_config.TextColumn("OBSERVACIONES"),
                                },
                                hide_index=True,
                            )
                            edited_estaciones_json = json.dumps(
                                json.loads(edited_df_est.to_json(orient="records")),
                                ensure_ascii=False,
                            )

                        ec1, ec2, _ = st.columns([1.5, 1, 3])
                        with ec1:
                            if st.button("💾 GUARDAR CAMBIOS", type="primary",
                                         key="btn_save_edit", use_container_width=True):
                                _upd = {
                                    "fecha":            edit_fecha.strftime("%d/%m/%Y"),
                                    "ruta":             str(edit_ruta).upper(),
                                    "placa":            str(edit_placa).upper(),
                                    "conductor":        str(edit_cond).upper(),
                                    "volumen_declarado": int(edit_vol),
                                    "solidos_ruta":     round(float(edit_st), 2),
                                    "crioscopia_ruta":  round(float(edit_ic), 3),
                                }
                                if es_tipo_ruta:
                                    _upd["estaciones_json"] = edited_estaciones_json
                                    try:
                                        _ests_saved = json.loads(edited_estaciones_json) or []
                                    except Exception:
                                        _ests_saved = []
                                    _upd["num_estaciones"] = len(_ests_saved)
                                update_row_in_csv(idx_activo, _upd)
                                st.session_state.admin_accion = None
                                st.session_state.admin_idx    = None
                                st.session_state.admin_pin_ok = False
                                st.rerun()
                        with ec2:
                            if st.button("✖ CANCELAR", key="btn_cancel_edit",
                                         use_container_width=True):
                                st.session_state.admin_accion = None
                                st.session_state.admin_idx    = None
                                st.session_state.admin_pin_ok = False
                                st.rerun()

save_draft_state()
