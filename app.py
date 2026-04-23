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

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO UNIFORME ---
st.set_page_config(page_title="QualiLact - Control de Calidad", page_icon="🧪", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif !important; background-color: #F1F5F9 !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; padding: 24px !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07) !important; margin-bottom: 20px !important; }
    label p { font-size: 0.9rem !important; font-weight: 700 !important; color: #1E293B !important; text-transform: uppercase !important; letter-spacing: 0.6px !important; margin-bottom: 6px !important; }
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input, div[data-testid="stDateInput"] input, div[data-baseweb="select"] { height: 42px !important; background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important; border-radius: 8px !important; font-size: 1rem !important; color: #0F172A !important; }
    button[kind="primary"], button[data-testid*="baseButton-primary"] { background-color: #0056A3 !important; height: 48px !important; border-radius: 8px !important; font-weight: 700 !important; text-transform: uppercase !important; width: 100% !important; border: none !important; margin-top: 10px !important; color: white !important; }
    h2 { color: #0056A3 !important; font-size: 1.5rem !important; font-weight: 800 !important; border-left: 6px solid #0056A3 !important; padding-left: 15px !important; margin-bottom: 20px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- PERSISTENCIA Y LÓGICA ---
CSV_PATH = "rutas_historial.csv"
CSV_COLS = ["tipo_seguimiento", "fecha", "ruta", "placa", "conductor", "volumen_declarado", "vol_estaciones", "diferencia", "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond", "num_estaciones", "guardado_en", "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos", "estaciones_json"]
SEG_CSV_PATH = "seguimientos_historial.csv"
SEG_COLS = ["sub_tipo_seguimiento", "fecha", "seg_codigo", "seg_quien_trajo", "ruta", "seg_responsable", "seg_id_muestra", "seg_grasa", "seg_st", "seg_ic", "seg_agua", "seg_alcohol", "seg_cloruros", "seg_neutralizantes", "seg_observaciones", "guardado_en"]

def load_historial():
    if not os.path.exists(CSV_PATH): return pd.DataFrame(columns=CSV_COLS)
    df = pd.read_csv(CSV_PATH, dtype=str)
    if "fecha" in df.columns: df["_fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
    return df

def save_ruta_to_csv(row):
    df = load_historial()
    if "_fecha_dt" in df.columns: df = df.drop(columns=["_fecha_dt"])
    new_row = pd.DataFrame([row])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")

# --- INTERFAZ ---
st.markdown("## CONFIGURACIÓN INICIAL")
with st.container(border=True):
    c1, c2 = st.columns(2)
    fecha_analisis = c1.date_input("FECHA", datetime.now(), format="DD/MM/YYYY")
    tipo_servicio = c2.selectbox("TIPO DE ANÁLISIS", ["RUTAS", "TRANSUIZA", "SEGUIMIENTOS"])
    if st.button("CONTINUAR"):
        st.session_state.continuar = True

if st.session_state.get("continuar"):
    st.markdown(f"## SEGUIMIENTO DE {tipo_servicio}")
    with st.container(border=True):
        # Aquí van tus campos de entrada...
        st.info("Formulario listo para ingresar datos uniformes.")
