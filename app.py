import base64
import os
import random as _rnd

import streamlit as st


from utils.draft_utils import restore_draft_state, save_draft_state
from utils.input_utils import activar_siguiente_con_enter
from utils.persistent_session import restore_or_sync_session
from utils.time_utils import now_col
from components.auth import render_login as render_auth
from components.header import render_header
from components.sidebar import render_sidebar
from components.registrar.rutas import render_rutas
from components.registrar.transuiza import render_transuiza
from components.registrar.seguimientos import render_seguimientos
from components.registrar.estaciones import render_estaciones
from components.historial import render_historial
from components.dashboard import render_dashboard
from components.admin_usuarios import render_admin_usuarios

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="QualiLact", page_icon="🧪", layout="wide")

# ── Draft restore (must happen before any widget renders) ────────────────────
restore_draft_state()

# ── Logo assets ──────────────────────────────────────────────────────────────
with open("attached_assets/image_1777229405853.png", "rb") as _logo_file:
    _logo_b64 = base64.b64encode(_logo_file.read()).decode("utf-8")

with open("logo_qualilact_brown.png", "rb") as _ql_file:
    _ql_logo_b64 = base64.b64encode(_ql_file.read()).decode("utf-8")

with open("logo_qualilact_cropped.png", "rb") as _ql_crop_file:
    _ql_logo_crop_b64 = base64.b64encode(_ql_crop_file.read()).decode("utf-8")

# ── Sesión persistente (sobrevive caídas de internet, se borra al cerrar pestaña) ──
restore_or_sync_session()

# ── Auth guard ───────────────────────────────────────────────────────────────
if not st.session_state.get("_logged_in", False):
    render_auth(_ql_logo_crop_b64, _logo_b64)
    st.stop()

# ── Post-login welcome flash ─────────────────────────────────────────────────
if st.session_state.get("_just_logged_in", False):
    st.session_state._just_logged_in = False
    st.info(f"💡 **Dato curioso:** {st.session_state._dato_leche}")

# ── Global CSS + Header ───────────────────────────────────────────────────────
render_header(_logo_b64)

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
    [data-testid="stStatusWidget"] > div > div { display: none !important; }
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

    /* ── Mayúsculas visuales en inputs de texto (sin rerun) ────── */
    div[data-testid="stTextInput"] input:not([type="password"]) {
        text-transform: uppercase;
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

# ── Session state defaults ───────────────────────────────────────────────────
for _sk, _sv in [
    ("continuar", False),
    ("pagina_activa", "REGISTRAR"),
    ("admin_accion", None), ("admin_idx", None), ("admin_idxs", []),
    ("admin_from_seg", False),
    ("hist_buscar_ok", False),
    ("tipo_registrar", "RUTAS"), ("sub_tipo_registrar", "ESTACIONES"),
    ("registrar_submenu_open", False),
    ("_sidebar_close", False),
    ("_logged_in", False), ("_rol_usuario", ""), ("_usuario_login", ""),
    ("_nombre_usuario", ""), ("_dato_leche", ""), ("_just_logged_in", False),
]:
    if _sk not in st.session_state:
        st.session_state[_sk] = _sv

# ── JS keyboard navigation (once per session) ────────────────────────────────
activar_siguiente_con_enter()

# ── Sidebar navigation ───────────────────────────────────────────────────────
render_sidebar(_ql_logo_b64)

# ── Sidebar-close JS injection ───────────────────────────────────────────────
if st.session_state._sidebar_close:
    st.session_state._sidebar_close = False
    st.html(
        """<script>
        (function(){
            var attempts = 0;
            function tryClose(){
                var doc = window.parent.document;
                var btn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
                          doc.querySelector('button[aria-label="Close sidebar"]') ||
                          doc.querySelector('[data-testid="stSidebarCollapseButton"]');
                if(!btn){
                    var allBtns = doc.querySelectorAll('section[data-testid="stSidebar"] button');
                    for(var i=0; i<allBtns.length; i++){
                        if(allBtns[i].textContent.trim()===''){
                            btn = allBtns[i]; break;
                        }
                    }
                }
                if(btn){ btn.click(); }
                else if(attempts < 12){ attempts++; setTimeout(tryClose, 150); }
            }
            setTimeout(tryClose, 80);
        })();
        </script>""",
        unsafe_allow_javascript=True,
    )

# ── Page routing ─────────────────────────────────────────────────────────────
if st.session_state.pagina_activa == "REGISTRAR":
    tipo_servicio = st.session_state.tipo_registrar
    st.session_state["_tipo_servicio_guardado"] = tipo_servicio
    st.session_state["_sub_tipo_seg_guardado"]  = st.session_state.sub_tipo_registrar

    if tipo_servicio == "RUTAS":
        render_rutas()
    elif tipo_servicio == "TRANSUIZA":
        render_transuiza()
    elif tipo_servicio == "SEGUIMIENTOS":
        render_seguimientos()
    elif tipo_servicio == "ESTACIONES":
        render_estaciones()

elif st.session_state.pagina_activa == "HISTORIAL":
    render_historial()

elif st.session_state.pagina_activa == "DASHBOARD":
    render_dashboard()

elif st.session_state.pagina_activa == "ADMIN_USUARIOS":
    render_admin_usuarios()

# ── Draft autosave ───────────────────────────────────────────────────────────
save_draft_state()
