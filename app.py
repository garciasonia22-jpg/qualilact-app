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

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO (ESTILO REPLIT UNIFORME) ---
st.set_page_config(page_title="QualiLact - Control de Calidad", page_icon="🧪", layout="wide")

st.markdown(
    """
    <style>
    /* Fuente profesional Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #F1F5F9 !important;
    }

    /* Tarjetas Blancas Uniformes con Sombra */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        padding: 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07) !important;
        margin-bottom: 20px !important;
    }

    /* Etiquetas de campo (Labels) - Mismo tamaño y peso */
    label p {
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        color: #1E293B !important;
        text-transform: uppercase !important;
        letter-spacing: 0.6px !important;
        margin-bottom: 6px !important;
    }

    /* Inputs Uniformes - Todos a 42px de altura */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-baseweb="select"] {
        height: 42px !important;
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        color: #0F172A !important;
    }

    /* Botones Primarios - Grandes y Azules Nestlé */
    button[kind="primary"], button[data-testid*="baseButton-primary"] {
        background-color: #0056A3 !important;
        height: 48px !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        width: 100% !important;
        border: none !important;
        margin-top: 10px !important;
        color: white !important;
        transition: background-color 0.2s;
    }
    button[kind="primary"]:hover {
        background-color: #004482 !important;
    }

    /* Títulos de sección uniformes */
    h2 {
        color: #0056A3 !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        border-left: 6px solid #0056A3 !important;
        padding-left: 15px !important;
        margin-bottom: 20px !important;
        font-family: 'Segoe UI', sans-serif;
    }

    /* Ajuste de carga (Spinner) */
    @keyframes _ql_icono {
        0%, 30% { content: "🐄 Cargando..."; }
        33%, 63% { content: "🥛 Cargando..."; }
        66%, 96% { content: "🧪 Cargando..."; }
        100% { content: "🐄 Cargando..."; }
    }
    [data-testid="stStatusWidget"]::after {
        content: "🐄 Cargando...";
        position: fixed;
        top: 10px;
        right: 24px;
        font-size: 0.9rem;
        font-weight: 600;
        color: #0056A3;
        background: white;
        border: 1px solid #BDD7EE;
        border-radius: 20px;
        padding: 5px 15px;
        animation: _ql_icono 2.4s linear infinite;
        z-index: 9999;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── PERSISTENCIA CSV (TU LÓGICA ORIGINAL) ──
CSV_PATH = "rutas_historial.csv"
CSV_COLS = [
    "tipo_seguimiento", "fecha", "ruta", "placa", "conductor",
    "volumen_declarado", "vol_estaciones", "diferencia",
    "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
    "num_estaciones", "guardado_en",
    "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos",
    "estaciones_json",
]

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
DRAFT_PREFIXES = ("nue_", "seg_id_muestra_", "seg_grasa_", "seg_st_", "seg_ic_raw_", "seg_agua_", "seg_alcohol_", "seg_cloruros_", "seg_neutralizantes_", "seg_observaciones_",)

def _draft_encode(value):
    if isinstance(value, datetime): return {"__draft_type": "datetime", "value": value.isoformat()}
    if isinstance(value, date): return {"__draft_type": "date", "value": value.isoformat()}
    try: json.dumps(value); return value
    except TypeError: return str(value)

def _draft_decode(value):
    if isinstance(value, dict) and value.get("__draft_type") in ("date", "datetime"):
        raw = value.get("value", "")
        try: return datetime.fromisoformat(raw).date()
        except: return date.today()
    return value

def restore_draft_state():
    if st.session_state.get("_draft_restored"): return
    st.session_state["_draft_restored"] = True
    if not os.path.exists(DRAFT_PATH): return
    try:
        with open(DRAFT_PATH, "r", encoding="utf-8") as f: data = json.load(f)
    except: return
    if "tipo_servicio_select" not in data and "_tipo_servicio_guardado" in data: data["tipo_servicio_select"] = data.get("_tipo_servicio_guardado")
    if "sub_tipo_seg_select" not in data and "_sub_tipo_seg_guardado" in data: data["sub_tipo_seg_select"] = data.get("_sub_tipo_seg_guardado")
    for key, value in data.items():
        if key not in st.session_state: st.session_state[key] = _draft_decode(value)

def save_draft_state():
    if st.session_state.pop("_skip_draft_save_once", False): return
    data = {}
    for key in DRAFT_EXACT_KEYS:
        if key in st.session_state: data[key] = _draft_encode(st.session_state[key])
    for key, value in st.session_state.items():
        if key.startswith(DRAFT_PREFIXES): data[key] = _draft_encode(value)
    try:
        with open(DRAFT_PATH, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def clear_draft_state():
    st.session_state["_skip_draft_save_once"] = True
    try:
        if os.path.exists(DRAFT_PATH): os.remove(DRAFT_PATH)
    except: pass

def load_historial() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH): return pd.DataFrame(columns=CSV_COLS)
    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
        for col in CSV_COLS:
            if col not in df.columns: df[col] = ""
        df["tipo_seguimiento"] = df["tipo_seguimiento"].fillna("RUTAS").replace("", "RUTAS")
        for col in ["volumen_declarado", "vol_estaciones", "diferencia", "num_estaciones"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond", "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
        if "fecha" in df.columns: df["_fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
        return df
    except: return pd.DataFrame(columns=CSV_COLS)

def save_ruta_to_csv(row: dict):
    df = load_historial()
    if "_fecha_dt" in df.columns: df = df.drop(columns=["_fecha_
