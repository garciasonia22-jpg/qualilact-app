import base64
import random as _rnd

import streamlit as st

from config.constants import _DATOS_LECHE
from db.supabase_client import init_connection
from utils.auth_utils import es_hash_bcrypt, hashear_contrasena, verificar_contrasena
from utils.input_utils import activar_siguiente_con_enter


def render_login(ql_logo_crop_b64: str, nestle_logo_b64: str):
    """Renders the login page. Calls st.stop() if not authenticated."""
    supabase = init_connection()

    st.markdown(
        """<style>
        #MainMenu{visibility:hidden;}
        [data-testid="stHeader"]{display:none;}
        footer{visibility:hidden;}
        [data-testid="stSidebar"]{display:none;}
        .block-container{padding-top:2.5rem!important;}
        </style>""",
        unsafe_allow_html=True,
    )
    _lc, _cm, _rc = st.columns([1, 2, 1])
    with _cm:
        st.markdown(
            f'<div style="background:linear-gradient(145deg,#F0F5FB 0%,#FFFFFF 60%,#EAF2FB 100%);'
            f'border-radius:20px;border:1px solid #D6E4F5;padding:28px 32px 22px;'
            f'box-shadow:0 4px 18px rgba(0,86,163,0.10);margin-bottom:22px;">'
            f'<div style="display:flex;align-items:center;justify-content:center;gap:40px;">'
            f'<img src="data:image/png;base64,{ql_logo_crop_b64}" '
            f'style="height:165px;width:165px;object-fit:contain;display:block;'
            f'filter:drop-shadow(0 3px 8px rgba(99,79,58,0.22));" alt="QualiLact">'
            f'<div style="width:1px;height:140px;background:linear-gradient(to bottom,transparent,#B8C9DF,transparent);flex-shrink:0;"></div>'
            f'<img src="data:image/png;base64,{nestle_logo_b64}" '
            f'style="height:165px;width:165px;object-fit:contain;display:block;'
            f'filter:drop-shadow(0 3px 8px rgba(0,0,0,0.12));" alt="Nestlé">'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;margin-bottom:24px;">'
            '<h2 style="color:#0056A3;font-weight:800;margin:0;font-size:1.9rem;">QualiLact</h2>'
            '<p style="color:#6B7280;font-size:0.82rem;margin:4px 0 0;">'
            'Control de Calidad Láctea &nbsp;·&nbsp; TROMS - Milksourcing</p></div>',
            unsafe_allow_html=True,
        )
        _li_u = st.text_input("👤 Usuario", placeholder="Ingrese su usuario", key="_li_user")
        _li_p = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña", key="_li_pass")
        _li_submitted = st.button(
            "Iniciar Sesión", type="primary", use_container_width=True, key="_li_submit"
        )
        activar_siguiente_con_enter()

        if _li_submitted:
            try:
                respuesta = supabase.table("usuarios_app").select("*").eq("nombre_usuario", _li_u).execute()
                usuario_db = respuesta.data[0] if respuesta.data else None
                pwd_ok = False
                if usuario_db:
                    almacenada = usuario_db.get("contrasena", "") or ""
                    if es_hash_bcrypt(almacenada):
                        pwd_ok = verificar_contrasena(_li_p, almacenada)
                    else:
                        # Compatibilidad: contraseña aún en texto plano → verificar y auto-migrar a hash
                        if _li_p == almacenada:
                            pwd_ok = True
                            try:
                                supabase.table("usuarios_app").update(
                                    {"contrasena": hashear_contrasena(_li_p)}
                                ).eq("id", usuario_db["id"]).execute()
                            except Exception:
                                pass
                if pwd_ok and usuario_db:
                    st.session_state._logged_in      = True
                    st.session_state._rol_usuario    = usuario_db["rol"]
                    st.session_state._nombre_usuario = usuario_db["nombre_usuario"]
                    st.session_state._usuario_login  = _li_u
                    st.session_state._dato_leche     = _rnd.choice(_DATOS_LECHE)
                    st.session_state._just_logged_in = True
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos. Verifique sus credenciales.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

        st.markdown(
            '<div style="text-align:center;margin-top:18px;font-size:0.72rem;color:#9CA3AF;">'
            'Acceso restringido — solo personal autorizado Milksourcing</div>',
            unsafe_allow_html=True,
        )
    st.stop()
