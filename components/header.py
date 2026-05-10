import streamlit as st


def render_header(nestle_logo_b64: str):
    """Renders the top header bar with QualiLact branding."""
    st.markdown(
        f"""
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        padding: 12px 8px 8px 8px;
        border-bottom: 2px solid #0056A3;
    ">
        <div style="display:flex;flex-direction:column;align-items:flex-start;">
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
            <div style="
                font-size: 0.72rem;
                color: #634F3A;
                font-weight: 700;
                letter-spacing: 0.4px;
                margin-top: 5px;
                font-family: 'Segoe UI', sans-serif;
            ">TROMS &nbsp;·&nbsp; <span style="font-weight:400;font-style:italic;color:#8B7355;">Transformación Operativa Milksourcing</span></div>
        </div>
        <img src="data:image/png;base64,{nestle_logo_b64}" alt="Nestlé logo"
             style="
                width: min(10vw, 90px);
                max-width: 90px;
                height: auto;
                display: block;
                object-fit: contain;
                margin: 0;
                padding: 0;
             ">
    </div>
    <style>
    @media (max-width: 640px) {{
        div[style*="justify-content: space-between"] {{
            padding: 10px 8px 6px 8px !important;
        }}
        div[style*="justify-content: space-between"] img {{
            width: min(12vw, 46px) !important;
            max-width: 46px !important;
        }}
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_css():
    """Injects the global QualiLact CSS."""
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
