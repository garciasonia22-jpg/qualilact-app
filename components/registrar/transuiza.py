import base64
import json
import re

import streamlit as st

from utils.time_utils import now_col
from utils.input_utils import activar_siguiente_con_enter
from utils.file_utils import save_fotos_to_disk
from utils.data_utils import save_ruta_to_csv
from utils.draft_utils import clear_draft_state


def render_transuiza():
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

    st.markdown(
        """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                       margin:14px 0 6px 0;letter-spacing:.4px;
                       border-left:4px solid #0056A3;padding-left:10px;">
             📋 Datos de Identificación
           </div>""",
        unsafe_allow_html=True,
    )
    _trans_fg = st.session_state.get("_trans_fg", 0)

    with st.container(border=True):
        tc1, tc2, tc3 = st.columns(3)
        trans_fecha = tc1.date_input(
            "📅 FECHA", now_col(), key=f"trans_fecha_{_trans_fg}", format="DD/MM/YYYY"
        )
        _trans_placa_key = f"trans_placa_{_trans_fg}"
        trans_placa = tc2.text_input(
            "🚚 PLACA DEL VEHÍCULO", placeholder="AAA000", key=_trans_placa_key,
            on_change=lambda k=_trans_placa_key: st.session_state.__setitem__(
                k, re.sub(r"[^A-Z0-9]", "", st.session_state.get(k, "").upper())
            ),
        )
        trans_st_carrotanque = tc3.number_input(
            "🏷️ ST DEL CARROTANQUE (%)", min_value=0.0, max_value=100.0,
            step=0.01, format="%.2f", value=None, placeholder="0.00",
            key=f"trans_st_carrotanque_{_trans_fg}",
        )
    activar_siguiente_con_enter()

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
            key=f"trans_grasa_{_trans_fg}",
        )
        trans_st_muestra = qc2.number_input(
            "ST MUESTRA (%)", min_value=0.0, max_value=100.0,
            step=0.01, format="%.2f", value=None, placeholder="0.00",
            key=f"trans_st_muestra_{_trans_fg}",
        )
        trans_proteina = qc3.number_input(
            "PROTEÍNA (%)", min_value=0.0, max_value=100.0,
            step=0.01, format="%.2f", value=None, placeholder="0.00",
            key=f"trans_proteina_{_trans_fg}",
        )

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

    activar_siguiente_con_enter()

    st.markdown(
        """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                       margin:14px 0 6px 0;letter-spacing:.4px;
                       border-left:4px solid #0056A3;padding-left:10px;">
             📷 Imágenes de Muestras
           </div>""",
        unsafe_allow_html=True,
    )
    if "trans_imagenes_confirmadas" not in st.session_state:
        st.session_state.trans_imagenes_confirmadas = False
    if "trans_imagenes_nombres_guardados" not in st.session_state:
        st.session_state.trans_imagenes_nombres_guardados = []

    trans_imagenes_subidas = st.file_uploader(
        "ADJUNTAR IMÁGENES DE MUESTRAS TRANSUIZA",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key=f"trans_imagenes_muestras_{_trans_fg}",
        label_visibility="visible",
    )

    if trans_imagenes_subidas:
        _t_nombres = [f.name for f in trans_imagenes_subidas]
        if _t_nombres != st.session_state.trans_imagenes_nombres_guardados:
            st.session_state.trans_imagenes_confirmadas = False

        _t_confirmed = st.session_state.trans_imagenes_confirmadas
        _t_thumb_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin:8px 0;'>"
        for _timg in trans_imagenes_subidas:
            _t_raw = _timg.read()
            _t_b64 = base64.b64encode(_t_raw).decode()
            _t_ext = _timg.name.rsplit(".", 1)[-1].lower()
            _t_mime = "image/jpeg" if _t_ext in ("jpg", "jpeg") else "image/png"
            _t_nombre_corto = _timg.name if len(_timg.name) <= 16 else _timg.name[:14] + "…"
            _t_check_html = (
                "<div style='color:#16a34a;font-size:12px;"
                "text-align:center;font-weight:600;'>✅ Guardada</div>"
                if _t_confirmed else
                f"<div style='font-size:10px;color:#888;text-align:center;'>{_t_nombre_corto}</div>"
            )
            _t_border = "#16a34a" if _t_confirmed else "#D1D5DB"
            _t_thumb_html += (
                f"<div style='display:flex;flex-direction:column;"
                f"align-items:center;gap:4px;'>"
                f"<img src='data:{_t_mime};base64,{_t_b64}' "
                f"style='width:150px;height:150px;object-fit:cover;"
                f"border-radius:10px;border:2px solid {_t_border};"
                f"box-shadow:0 2px 6px rgba(0,0,0,0.08);background:#F4F4F4;'/>"
                f"{_t_check_html}</div>"
            )
            _timg.seek(0)
        _t_thumb_html += "</div>"
        st.markdown(_t_thumb_html, unsafe_allow_html=True)

        if not st.session_state.trans_imagenes_confirmadas:
            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
            if st.button("💾 GUARDAR IMÁGENES", key=f"btn_trans_guardar_imgs_{_trans_fg}",
                         width='content'):
                st.session_state.trans_imagenes_confirmadas = True
                st.session_state.trans_imagenes_nombres_guardados = _t_nombres
                st.rerun()
        else:
            st.success("✅ Imágenes guardadas correctamente.")
    else:
        st.session_state.trans_imagenes_confirmadas = False
        st.caption("No se han adjuntado imágenes.")

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
                 width='stretch', key="btn_guardar_trans"):
        if not trans_placa:
            st.warning("⚠️ Ingrese la placa del vehículo.")
        else:
            _t_fotos_prefix = f"TRANS_{(trans_placa or 'SIN_PLACA').upper()}"
            _t_fotos_paths  = save_fotos_to_disk(
                trans_imagenes_subidas or [], _t_fotos_prefix
            )
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
                "guardado_en":      now_col().strftime("%d/%m/%Y %H:%M"),
                "fotos_json":       json.dumps(_t_fotos_paths, ensure_ascii=False),
            })
            _next_fg = _trans_fg + 1
            for _k in list(st.session_state.keys()):
                if _k.startswith("trans_") or _k == f"trans_imagenes_muestras_{_trans_fg}":
                    st.session_state.pop(_k, None)
            st.session_state["_trans_fg"]  = _next_fg
            st.session_state.trans_guardado_ok = True
            clear_draft_state()
            st.rerun()

    if st.session_state.trans_guardado_ok:
        st.success("✅ Registro TRANSUIZA guardado en el historial.")
        st.session_state.trans_guardado_ok = False
