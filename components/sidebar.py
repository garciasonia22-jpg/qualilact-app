import streamlit as st

from utils.time_utils import now_col
from utils.draft_utils import clear_draft_state
from utils.persistent_session import request_logout


def render_sidebar(ql_logo_b64: str):
    """Renders the sidebar navigation."""
    with st.sidebar:
        st.markdown(
            f'<div style="text-align:center;padding:16px 14px 18px;background:linear-gradient(160deg,#EAF2FB 0%,#F6F9FC 100%);border-radius:14px;border-bottom:3px solid #0056A3;margin-bottom:22px;box-shadow:0 3px 12px rgba(0,86,163,0.10);"><div style="margin:4px auto 8px;"><img src="data:image/png;base64,{ql_logo_b64}" style="width:185px;height:auto;display:block;margin:0 auto;filter:drop-shadow(0 3px 8px rgba(99,79,58,0.25));" alt="QualiLact logo"></div><div style="font-size:0.74rem;color:#6B7280;letter-spacing:0.3px;font-family:Segoe UI,sans-serif;margin-top:0px;margin-bottom:10px;">Control de Calidad L&#225;ctea</div><div style="height:1px;background:linear-gradient(90deg,transparent,#B8966A,transparent);margin:0 18px 12px;">&nbsp;</div><div style="display:inline-block;background:#634F3A;color:#FFF8F0;font-size:0.65rem;font-weight:800;letter-spacing:2px;padding:3px 14px;border-radius:20px;font-family:Segoe UI,sans-serif;margin-bottom:6px;box-shadow:0 2px 6px rgba(99,79,58,0.30);">TROMS</div><div style="font-size:0.63rem;color:#8B7355;font-style:italic;font-family:Segoe UI,sans-serif;line-height:1.5;">Transformaci&#243;n Operativa Milk Sourcing</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] .stButton > button {
                width: 100%;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                padding: 10px 14px;
                margin-bottom: 6px;
                border: 2px solid transparent;
                background: #F0F4FA;
                color: #1F2937;
                transition: all 0.15s;
            }
            [data-testid="stSidebar"] .stButton > button:hover {
                background: #DBEAFE;
                border-color: #0056A3;
                color: #0056A3;
            }
            [data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: #0056A3 !important;
                color: #FFFFFF !important;
                border-color: #003D7A !important;
            }
            [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
                background: #003D7A !important;
                color: #FFFFFF !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        _reg_active = st.session_state.pagina_activa == "REGISTRAR"
        _arrow = "▾" if st.session_state.registrar_submenu_open else "▸"
        _reg_lbl = f"📝 **Registrar** {_arrow}" if _reg_active else f"📝 Registrar {_arrow}"
        if st.button(
            _reg_lbl,
            key="_nav_REGISTRAR",
            width='stretch',
            type="primary" if _reg_active else "secondary",
        ):
            if st.session_state.pagina_activa == "REGISTRAR":
                st.session_state.registrar_submenu_open = not st.session_state.registrar_submenu_open
            else:
                st.session_state.pagina_activa = "REGISTRAR"
                st.session_state.registrar_submenu_open = True
            st.rerun()

        if st.session_state.registrar_submenu_open:
            _tipo_opts = ["RUTAS", "TRANSUIZA", "SEGUIMIENTOS"]
            _t_icons = {"RUTAS": "🚛", "TRANSUIZA": "🏭", "SEGUIMIENTOS": "🔬"}
            st.markdown(
                "<div style='margin:4px 0 4px 10px;border-left:3px solid #0056A3;"
                "padding-left:8px;'>"
                "<span style='font-size:0.68rem;font-weight:700;color:#6B7280;"
                "letter-spacing:.06em;'>TIPO DE ANÁLISIS</span></div>",
                unsafe_allow_html=True,
            )
            for _t in _tipo_opts:
                _t_active = (
                    st.session_state.pagina_activa == "REGISTRAR"
                    and st.session_state.tipo_registrar == _t
                )
                _t_lbl = f"  {_t_icons[_t]} **{_t}**" if _t_active else f"  {_t_icons[_t]} {_t}"
                if st.button(
                    _t_lbl,
                    key=f"_subnav_{_t}",
                    width='stretch',
                    type="primary" if _t_active else "secondary",
                ):
                    st.session_state.pagina_activa = "REGISTRAR"
                    st.session_state.tipo_registrar = _t
                    st.session_state.registrar_submenu_open = False
                    st.session_state._sidebar_close = True
                    st.rerun()

        _hist_active = st.session_state.pagina_activa == "HISTORIAL"
        _hist_lbl = "🗂️ **Historial**" if _hist_active else "🗂️ Historial"
        if st.button(
            _hist_lbl,
            key="_nav_HISTORIAL",
            width='stretch',
            type="primary" if _hist_active else "secondary",
        ):
            st.session_state.pagina_activa = "HISTORIAL"
            st.session_state.registrar_submenu_open = False
            st.session_state._sidebar_close = True
            st.rerun()

        _dash_active = st.session_state.pagina_activa == "DASHBOARD"
        _dash_lbl = "📊 **Dashboard**" if _dash_active else "📊 Dashboard"
        if st.button(
            _dash_lbl,
            key="_nav_DASHBOARD",
            width='stretch',
            type="primary" if _dash_active else "secondary",
        ):
            st.session_state.pagina_activa = "DASHBOARD"
            st.session_state.registrar_submenu_open = False
            st.session_state._sidebar_close = True
            st.rerun()

        _est_active = (
            st.session_state.pagina_activa == "REGISTRAR"
            and st.session_state.tipo_registrar == "ESTACIONES"
        )
        _est_lbl = "🏷️ **Estaciones**" if _est_active else "🏷️ Estaciones"
        if st.button(
            _est_lbl,
            key="_nav_ESTACIONES",
            width='stretch',
            type="primary" if _est_active else "secondary",
        ):
            st.session_state.pagina_activa = "REGISTRAR"
            st.session_state.tipo_registrar = "ESTACIONES"
            st.session_state.registrar_submenu_open = False
            st.session_state.cat_accion = None
            st.session_state._sidebar_close = True
            st.rerun()

        if st.session_state.get("_rol_usuario") == "ADMINISTRADOR":
            _adm_active = st.session_state.pagina_activa == "ADMIN_USUARIOS"
            _adm_lbl = "👥 **Gestión de Usuarios**" if _adm_active else "👥 Gestión de Usuarios"
            if st.button(
                _adm_lbl,
                key="_nav_ADMIN_USUARIOS",
                width='stretch',
                type="primary" if _adm_active else "secondary",
            ):
                st.session_state.pagina_activa = "ADMIN_USUARIOS"
                st.session_state.registrar_submenu_open = False
                st.session_state._sidebar_close = True
                st.rerun()

        st.markdown("<hr style='border-color:#E5E7EB;margin:18px 0;'>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.72rem;color:#9CA3AF;text-align:center;'>"
            f"Sección activa:<br><strong style='color:#0056A3;'>"
            f"{st.session_state.pagina_activa}</strong></div>",
            unsafe_allow_html=True,
        )
        _sb_hora = now_col().hour
        _sb_saludo = "Buenos días" if _sb_hora < 12 else ("Buenas tardes" if _sb_hora < 18 else "Buenas noches")
        _sb_rol_icon = "🔑" if st.session_state._rol_usuario == "ADMINISTRADOR" else "👤"
        _sb_rol_color = "#0056A3" if st.session_state._rol_usuario == "ADMINISTRADOR" else "#059669"
        _sb_rol_label = "Administrador" if st.session_state._rol_usuario == "ADMINISTRADOR" else "Operador"
        _es_admin = st.session_state._rol_usuario == "ADMINISTRADOR"
        _sb_nombre_html = (
            f"<div style='font-size:0.95rem;font-weight:800;color:#1E293B;margin-bottom:6px;'>"
            f"Abimelec T.</div>"
            if _es_admin else ""
        )
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#EAF2FB 0%,#F0F7FF 100%);"
            f"border-radius:14px;border:1px solid #C8DEFA;padding:12px 14px 10px;"
            f"margin-bottom:10px;box-shadow:0 2px 8px rgba(0,86,163,0.08);'>"
            f"<div style='font-size:0.72rem;color:#6B7280;margin-bottom:4px;'>{_sb_saludo}</div>"
            f"{_sb_nombre_html}"
            f"<div style='display:inline-flex;align-items:center;gap:5px;"
            f"background:{_sb_rol_color};color:#fff;font-size:0.62rem;font-weight:700;"
            f"letter-spacing:.06em;padding:2px 8px;border-radius:20px;'>"
            f"{_sb_rol_icon}&nbsp;{_sb_rol_label}</div>"
            f"<div style='font-size:0.65rem;color:#9CA3AF;margin-top:5px;'>"
            f"{st.session_state._usuario_login}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Cerrar Sesión", key="_btn_logout", width='stretch', type="secondary"):
            request_logout()
            st.rerun()

        if st.button("REINICIAR FORMULARIO", key="_btn_reiniciar", width='stretch'):
            st.session_state.continuar = False
            clear_draft_state()
            st.rerun()

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
