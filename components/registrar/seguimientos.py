import base64
import json

import pandas as pd
import streamlit as st

from utils.time_utils import now_col
from utils.input_utils import convertir_a_mayusculas, activar_siguiente_con_enter
from utils.file_utils import save_fotos_to_disk
from utils.data_utils import load_catalogo, save_seguimiento_to_csv
from utils.draft_utils import clear_draft_state


def render_seguimientos():
    st.markdown(
        """<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
              <span style="font-size:1.35rem;">🔬</span>
              <span style="font-size:1.35rem;font-weight:700;color:#0056A3;
                           letter-spacing:.5px;font-family:'Segoe UI',sans-serif;">
                SEGUIMIENTOS
              </span>
            </div>""",
        unsafe_allow_html=True,
    )

    _seg_sub_vals  = ["ESTACIONES", "ACOMPAÑAMIENTOS", "CONTRAMUESTRAS SOLICITADAS"]
    _seg_tab_labels = ["🏭 ESTACIONES", "👥 ACOMPAÑAMIENTOS", "🧪 CONTRAMUESTRAS"]
    _seg_tabs = st.tabs(_seg_tab_labels)

    for _ti, (_tab_ctx, _sub) in enumerate(zip(_seg_tabs, _seg_sub_vals)):
        with _tab_ctx:
            _fg_seg = st.session_state.get(f"_fg_seg_{_ti}", 0)

            st.markdown(
                """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                               margin:14px 0 6px 0;letter-spacing:.4px;
                               border-left:4px solid #0056A3;padding-left:10px;">
                     📋 Datos de Identificación
                   </div>""",
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                if _sub == "ESTACIONES":
                    _cat_df = load_catalogo()
                    _cat_map_cod = dict(zip(_cat_df["codigo"], _cat_df["nombre"]))
                    _cat_map_nom = dict(zip(_cat_df["nombre"], _cat_df["codigo"]))

                    def _fill_nombre_from_cod(_ti=_ti, _m=_cat_map_cod):
                        cod = st.session_state.get(f"seg_codigo_{_ti}", "").strip()
                        nom = _m.get(cod) or _m.get(cod.upper())
                        if nom:
                            st.session_state[f"seg_nombre_{_ti}"] = nom

                    def _fill_cod_from_nombre(_ti=_ti, _m=_cat_map_nom):
                        raw = st.session_state.get(f"seg_nombre_{_ti}", "")
                        nom = raw.upper()
                        st.session_state[f"seg_nombre_{_ti}"] = nom
                        cod = _m.get(nom.strip())
                        if cod:
                            st.session_state[f"seg_codigo_{_ti}"] = cod

                    sid1, sid2, sid3 = st.columns([1, 1, 2])
                    seg_fecha = sid1.date_input(
                        "📅 FECHA", now_col(),
                        key=f"seg_fecha_{_ti}", format="DD/MM/YYYY",
                    )
                    seg_codigo = sid2.text_input(
                        "🔖 CÓDIGO", placeholder="Ej: 6085",
                        key=f"seg_codigo_{_ti}",
                        on_change=_fill_nombre_from_cod,
                    )
                    st.session_state.setdefault(f"seg_nombre_{_ti}", "")
                    sid3.text_input(
                        "📍 NOMBRE ESTACIÓN", placeholder="Ej: LUCERITO",
                        key=f"seg_nombre_{_ti}",
                        on_change=_fill_cod_from_nombre,
                    )
                    activar_siguiente_con_enter()
                    seg_quien_trajo = ""
                    seg_ruta_acomp  = ""
                    seg_responsable = ""

                elif _sub == "ACOMPAÑAMIENTOS":
                    sa1, sa2 = st.columns(2)
                    seg_fecha = sa1.date_input(
                        "📅 FECHA", now_col(),
                        key=f"seg_fecha_{_ti}_{_fg_seg}", format="DD/MM/YYYY",
                    )
                    seg_ruta_acomp = sa2.text_input(
                        "📍 NOMBRE DE LA RUTA", placeholder="ESCRIBA AQUÍ...",
                        key=f"seg_ruta_acomp_{_ti}_{_fg_seg}",
                    )
                    sb1, sb2 = st.columns(2)
                    seg_quien_trajo = sb1.text_input(
                        "👤 ENTREGADO POR", placeholder="NOMBRE COMPLETO",
                        key=f"seg_quien_trajo_{_ti}_{_fg_seg}",
                    )
                    seg_vol_declarado_id = sb2.number_input(
                        "🪣 VOLUMEN (L)", min_value=0, step=1,
                        value=None, placeholder="DIGITE VOLUMEN",
                        key=f"seg_vol_declarado_{_ti}_{_fg_seg}",
                    )
                    seg_codigo      = ""
                    seg_responsable = ""

                else:  # CONTRAMUESTRAS SOLICITADAS
                    _cat_df_ct   = load_catalogo()
                    _cat_ct_cod  = dict(zip(_cat_df_ct["codigo"], _cat_df_ct["nombre"]))
                    _cat_ct_nom  = dict(zip(_cat_df_ct["nombre"],  _cat_df_ct["codigo"]))

                    def _fill_nom_ct(_ti=_ti, _fg=_fg_seg, _m=_cat_ct_cod):
                        cod = st.session_state.get(f"seg_id_muestra_ct_{_ti}_{_fg}", "").strip()
                        st.session_state[f"seg_id_muestra_ct_{_ti}_{_fg}"] = cod.upper()
                        nom = _m.get(cod) or _m.get(cod.upper())
                        if nom:
                            st.session_state[f"seg_nom_muestra_ct_{_ti}_{_fg}"] = nom

                    def _fill_cod_ct(_ti=_ti, _fg=_fg_seg, _m=_cat_ct_nom):
                        raw = st.session_state.get(f"seg_nom_muestra_ct_{_ti}_{_fg}", "")
                        nom = raw.upper()
                        st.session_state[f"seg_nom_muestra_ct_{_ti}_{_fg}"] = nom
                        cod = _m.get(nom.strip())
                        if cod:
                            st.session_state[f"seg_id_muestra_ct_{_ti}_{_fg}"] = cod

                    sc1, sc2, sc3, sc4 = st.columns([1.5, 1.5, 1, 2])
                    seg_fecha = sc1.date_input(
                        "📅 FECHA DE LAS MUESTRAS", now_col(),
                        key=f"seg_fecha_{_ti}_{_fg_seg}", format="DD/MM/YYYY",
                    )
                    seg_responsable = sc2.text_input(
                        "👤 ENTREGADO POR", placeholder="NOMBRE...",
                        key=f"seg_responsable_{_ti}_{_fg_seg}",
                    )
                    st.session_state.setdefault(f"seg_id_muestra_ct_{_ti}_{_fg_seg}", "")
                    seg_id_muestra_ct = sc3.text_input(
                        "🔖 CÓDIGO", placeholder="Ej: 6085",
                        key=f"seg_id_muestra_ct_{_ti}_{_fg_seg}",
                        on_change=_fill_nom_ct,
                    )
                    st.session_state.setdefault(f"seg_nom_muestra_ct_{_ti}_{_fg_seg}", "")
                    sc4.text_input(
                        "📍 NOMBRE ESTACIÓN", placeholder="Ej: LUCERITO",
                        key=f"seg_nom_muestra_ct_{_ti}_{_fg_seg}",
                        on_change=_fill_cod_ct,
                    )
                    seg_codigo      = ""
                    seg_quien_trajo = ""
                    seg_ruta_acomp  = ""

            activar_siguiente_con_enter()

            if _sub == "ACOMPAÑAMIENTOS":
                st.markdown("---")
                st.markdown(
                    """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                                   margin:10px 0 6px 0;letter-spacing:.4px;
                                   border-left:4px solid #0056A3;padding-left:10px;">
                         🔬 Análisis de Calidad de Ruta
                       </div>""",
                    unsafe_allow_html=True,
                )
                _aq1, _aq2 = st.columns(2)
                seg_solidos_ruta = _aq1.number_input(
                    "SÓLIDOS TOTALES (%)", min_value=0.0, max_value=100.0,
                    step=0.01, format="%.2f", value=None, placeholder="Ej: 12.80",
                    key=f"seg_solidos_ruta_{_ti}_{_fg_seg}",
                )
                seg_crios_raw = _aq2.text_input(
                    "CRIOSCOPIA (°C)", value="-0.", placeholder="-0.530",
                    key=f"seg_crios_raw_{_ti}_{_fg_seg}",
                )
                try:
                    seg_crioscopia_ruta = float(seg_crios_raw.replace(",", ".")) if seg_crios_raw.strip() else None
                except Exception:
                    seg_crioscopia_ruta = None
                st.markdown("---")
            else:
                seg_solidos_ruta    = None
                seg_crioscopia_ruta = None

            st.markdown(
                """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                               margin:14px 0 6px 0;letter-spacing:.4px;
                               border-left:4px solid #0056A3;padding-left:10px;">
                     🧪 Parámetros de Calidad
                   </div>""",
                unsafe_allow_html=True,
            )
            _qk = st.session_state.get(f"seg_quality_key_counter_{_ti}", 0)
            with st.container(border=True):
                seg_id_muestra = ""
                seg_volumen    = None
                seg_proveedor  = ""
                if _sub == "ACOMPAÑAMIENTOS":
                    _cat_df_m  = load_catalogo()
                    _cat_m_cod = dict(zip(_cat_df_m["codigo"], _cat_df_m["nombre"]))
                    _cat_m_nom = dict(zip(_cat_df_m["nombre"], _cat_df_m["codigo"]))

                    def _fill_nom_m(_ti=_ti, _qk=_qk, _m=_cat_m_cod):
                        cod = st.session_state.get(f"seg_id_muestra_{_ti}_{_qk}", "").strip()
                        st.session_state[f"seg_id_muestra_{_ti}_{_qk}"] = cod.upper()
                        nom = _m.get(cod) or _m.get(cod.upper())
                        if nom:
                            st.session_state[f"seg_nom_muestra_{_ti}_{_qk}"] = nom

                    def _fill_cod_m(_ti=_ti, _qk=_qk, _m=_cat_m_nom):
                        raw = st.session_state.get(f"seg_nom_muestra_{_ti}_{_qk}", "")
                        nom = raw.upper()
                        st.session_state[f"seg_nom_muestra_{_ti}_{_qk}"] = nom
                        cod = _m.get(nom.strip())
                        if cod:
                            st.session_state[f"seg_id_muestra_{_ti}_{_qk}"] = cod

                    _idc1, _idc2, _idc3 = st.columns([1, 2, 1])
                    seg_id_muestra = _idc1.text_input(
                        "🔖 CÓDIGO", placeholder="Ej: 6085",
                        key=f"seg_id_muestra_{_ti}_{_qk}",
                        on_change=_fill_nom_m,
                    )
                    st.session_state.setdefault(f"seg_nom_muestra_{_ti}_{_qk}", "")
                    _idc2.text_input(
                        "📍 NOMBRE ESTACIÓN", placeholder="Ej: LUCERITO",
                        key=f"seg_nom_muestra_{_ti}_{_qk}",
                        on_change=_fill_cod_m,
                    )
                    seg_volumen = _idc3.number_input(
                        "VOLUMEN (L)", min_value=0, step=1,
                        value=None, placeholder="0",
                        key=f"seg_volumen_{_ti}_{_qk}",
                    )
                    activar_siguiente_con_enter()
                elif _sub == "CONTRAMUESTRAS SOLICITADAS":
                    seg_id_muestra = st.session_state.get(f"seg_id_muestra_ct_{_ti}_{_fg_seg}", "").strip()
                    seg_proveedor = st.text_input(
                        "🏭 PROVEEDOR", placeholder="Nombre proveedor...",
                        key=f"seg_proveedor_{_ti}_{_qk}",
                    )
                    activar_siguiente_con_enter()

                sq1, sq2, sq3, sq4 = st.columns(4)
                seg_grasa = sq1.number_input(
                    "GRASA (%)", min_value=0.0, max_value=100.0,
                    step=0.01, format="%.2f", value=None,
                    placeholder="0.00", key=f"seg_grasa_{_ti}_{_qk}",
                )
                seg_st = sq2.number_input(
                    "ST (%)", min_value=0.0, max_value=100.0,
                    step=0.01, format="%.2f", value=None,
                    placeholder="0.00", key=f"seg_st_{_ti}_{_qk}",
                )
                seg_proteina = sq3.number_input(
                    "PROTEÍNA (%)", min_value=0.0, max_value=100.0,
                    step=0.01, format="%.2f", value=None,
                    placeholder="0.00", key=f"seg_proteina_{_ti}_{_qk}",
                )
                with sq4:
                    seg_ic_raw = st.text_input(
                        "IC (°C)", key=f"seg_ic_raw_{_ti}_{_qk}",
                        value="-0.", placeholder="-0.530",
                    )
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
                        seg_agua = st.number_input(
                            "💧 AGUA ADICIONADA (%)",
                            min_value=0.0, max_value=100.0,
                            step=0.01, format="%.2f", value=None,
                            placeholder="0.00", key=f"seg_agua_{_ti}_{_qk}",
                        )

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
                seg_alcohol        = sq5.selectbox("ALCOHOL",        opciones_tri, key=f"seg_alcohol_{_ti}_{_qk}")
                seg_cloruros       = sq6.selectbox("CLORUROS",       opciones_tri, key=f"seg_cloruros_{_ti}_{_qk}")
                seg_neutralizantes = sq7.selectbox("NEUTRALIZANTES", opciones_tri, key=f"seg_neutralizantes_{_ti}_{_qk}")

                _positivos = [p for p, v in [
                    ("ALCOHOL", seg_alcohol), ("CLORUROS", seg_cloruros),
                    ("NEUTRALIZANTES", seg_neutralizantes),
                ] if v == "POSITIVO (+)"]
                if _positivos:
                    st.error(f"🚨 ALERTA: {', '.join(_positivos)} POSITIVO(S) — ADULTERACIÓN")

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                seg_observaciones = st.text_area(
                    "📝 OBSERVACIONES", placeholder="ESCRIBA AQUÍ...",
                    key=f"seg_observaciones_{_ti}_{_qk}", height=90,
                )

            activar_siguiente_con_enter()

            if _sub == "ACOMPAÑAMIENTOS":
                _acomp_key = "acomp_muestras"
                if _acomp_key not in st.session_state:
                    st.session_state[_acomp_key] = []
                if st.button("➕  AGREGAR MUESTRA", width='stretch',
                             key=f"btn_agregar_muestra_{_ti}"):
                    st.session_state[_acomp_key].append({
                        "ID": seg_id_muestra or "",
                        "VOLUMEN (L)": seg_volumen,
                        "GRASA (%)":    seg_grasa,
                        "ST (%)":       seg_st,
                        "PROTEÍNA (%)": seg_proteina,
                        "IC (°C)":      f"{seg_ic:.3f}" if seg_ic is not None else "",
                        "AGUA (%)":     seg_agua,
                        "ALCOHOL":      seg_alcohol,
                        "CLORUROS":     seg_cloruros,
                        "NEUTRALIZANTES": seg_neutralizantes,
                        "OBS":          seg_observaciones or "",
                        "_volumen": seg_volumen,
                        "_grasa": seg_grasa, "_st": seg_st, "_ic": seg_ic,
                        "_proteina": seg_proteina,
                        "_agua": seg_agua, "_alcohol": seg_alcohol,
                        "_cloruros": seg_cloruros, "_neutralizantes": seg_neutralizantes,
                        "_obs": seg_observaciones or "",
                    })
                    st.session_state[f"seg_quality_key_counter_{_ti}"] = _qk + 1
                    st.rerun()
                if st.session_state[_acomp_key]:
                    st.markdown(
                        f"""<div style="font-size:0.9rem;font-weight:700;color:#0056A3;
                                       margin:10px 0 4px 0;">
                             📋 {len(st.session_state[_acomp_key])} muestra(s) registrada(s)
                           </div>""",
                        unsafe_allow_html=True,
                    )
                    _cat_pa     = load_catalogo()
                    _cat_pa_map = dict(zip(_cat_pa["codigo"], _cat_pa["nombre"]))
                    _rows_pa = []
                    for _m in st.session_state[_acomp_key]:
                        _cod_pa = str(_m.get("ID", "") or "").strip()
                        _rows_pa.append({
                            "ID":             _cod_pa,
                            "NOMBRE ESTACIÓN": _cat_pa_map.get(_cod_pa, ""),
                            "VOLUMEN (L)":    _m.get("VOLUMEN (L)"),
                            "GRASA (%)":      _m.get("GRASA (%)"),
                            "ST (%)":         _m.get("ST (%)"),
                            "PROTEÍNA (%)":   _m.get("PROTEÍNA (%)"),
                            "IC (°C)":        _m.get("IC (°C)", ""),
                            "AGUA (%)":       _m.get("AGUA (%)"),
                            "ALCOHOL":        _m.get("ALCOHOL", "N/A"),
                            "CLORUROS":       _m.get("CLORUROS", "N/A"),
                            "NEUTRALIZANTES": _m.get("NEUTRALIZANTES", "N/A"),
                            "OBS":            _m.get("OBS", ""),
                        })
                    df_prev_a = pd.DataFrame(_rows_pa)
                    _acomp_de_key = f"de_acomp_{_ti}_{len(st.session_state[_acomp_key])}"
                    _edited_a = st.data_editor(
                        df_prev_a,
                        num_rows="dynamic",
                        width='stretch',
                        hide_index=True,
                        key=_acomp_de_key,
                        column_config={
                            "ID":             st.column_config.TextColumn("ID"),
                            "NOMBRE ESTACIÓN": st.column_config.TextColumn("NOMBRE ESTACIÓN", disabled=True),
                            "VOLUMEN (L)":    st.column_config.NumberColumn("VOLUMEN (L)", format="%d", min_value=0, step=1),
                            "GRASA (%)":      st.column_config.NumberColumn("GRASA (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "ST (%)":         st.column_config.NumberColumn("ST (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "PROTEÍNA (%)":   st.column_config.NumberColumn("PROTEÍNA (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "IC (°C)":        st.column_config.TextColumn("IC (°C)"),
                            "AGUA (%)":       st.column_config.NumberColumn("AGUA (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "ALCOHOL":        st.column_config.SelectboxColumn("ALCOHOL", options=["N/A", "NEGATIVO (−)", "POSITIVO (+)"], required=True),
                            "CLORUROS":       st.column_config.SelectboxColumn("CLORUROS", options=["N/A", "NEGATIVO (−)", "POSITIVO (+)"], required=True),
                            "NEUTRALIZANTES": st.column_config.SelectboxColumn("NEUTRALIZANTES", options=["N/A", "NEGATIVO (−)", "POSITIVO (+)"], required=True),
                            "OBS":            st.column_config.TextColumn("OBS"),
                        },
                    )
                    def _pn(x):
                        try:
                            return float(str(x).replace(",", ".")) if x is not None and str(x).strip() not in ("", "None", "nan") else None
                        except Exception:
                            return None
                    _synced = []
                    for _r in _edited_a.to_dict(orient="records"):
                        if all(str(_r.get(c, "")).strip() in ("", "None", "nan")
                               for c in ["ID", "VOLUMEN (L)", "GRASA (%)", "ST (%)",
                                         "PROTEÍNA (%)", "IC (°C)", "OBS"]):
                            continue
                        _ic_s = str(_r.get("IC (°C)") or "").strip()
                        _ic_n = _pn(_ic_s) if _ic_s not in ("", "-", "-0", "-0.") else None
                        _synced.append({
                            "ID":             str(_r.get("ID") or "").strip(),
                            "VOLUMEN (L)":    _pn(_r.get("VOLUMEN (L)")),
                            "GRASA (%)":      _pn(_r.get("GRASA (%)")),
                            "ST (%)":         _pn(_r.get("ST (%)")),
                            "PROTEÍNA (%)":   _pn(_r.get("PROTEÍNA (%)")),
                            "IC (°C)":        _ic_s,
                            "AGUA (%)":       _pn(_r.get("AGUA (%)")),
                            "ALCOHOL":        _r.get("ALCOHOL") or "N/A",
                            "CLORUROS":       _r.get("CLORUROS") or "N/A",
                            "NEUTRALIZANTES": _r.get("NEUTRALIZANTES") or "N/A",
                            "OBS":            str(_r.get("OBS") or ""),
                            "_volumen":       _pn(_r.get("VOLUMEN (L)")),
                            "_grasa":         _pn(_r.get("GRASA (%)")),
                            "_st":            _pn(_r.get("ST (%)")),
                            "_proteina":      _pn(_r.get("PROTEÍNA (%)")),
                            "_ic":            _ic_n,
                            "_agua":          _pn(_r.get("AGUA (%)")),
                            "_alcohol":       _r.get("ALCOHOL") or "N/A",
                            "_cloruros":      _r.get("CLORUROS") or "N/A",
                            "_neutralizantes": _r.get("NEUTRALIZANTES") or "N/A",
                            "_obs":           str(_r.get("OBS") or ""),
                        })
                    st.session_state[_acomp_key] = _synced

            if _sub == "ACOMPAÑAMIENTOS":
                seg_vol_declarado = seg_vol_declarado_id
                _acomp_vols_f = [
                    (lambda v: v if v is not None else None)(
                        (lambda s: float(s.replace(",", "."))
                         if s and str(s).strip() not in ("", "None", "nan") else None
                        )(str(m.get("_volumen", "") or ""))
                    )
                    for m in st.session_state.get(_acomp_key, [])
                ]
                _acomp_vol_muestras = int(sum(v for v in _acomp_vols_f if v is not None))
                _acomp_pond_st, _acomp_pond_ic = [], []
                for _am in st.session_state.get(_acomp_key, []):
                    def _pn_form(x):
                        try: return float(str(x).replace(",", "."))
                        except: return None
                    _av  = _pn_form(_am.get("_volumen"))
                    _ast = _pn_form(_am.get("_st"))
                    _aic = _pn_form(_am.get("_ic"))
                    _acomp_pond_st.append(_av * _ast if _av is not None and _ast is not None else None)
                    _acomp_pond_ic.append(_av * _aic if _av is not None and _aic is not None else None)
                _acomp_vol_total_f = sum(v for v in _acomp_vols_f if v is not None)
                _acomp_st_pond = (round(sum(x for x in _acomp_pond_st if x is not None) / _acomp_vol_total_f, 2)
                                  if _acomp_vol_total_f else None)
                _acomp_ic_pond = (round(sum(x for x in _acomp_pond_ic if x is not None) / _acomp_vol_total_f, 3)
                                  if _acomp_vol_total_f else None)
                _acomp_diferencia_vol = (int(seg_vol_declarado) - _acomp_vol_muestras
                                         if seg_vol_declarado is not None else None)

            if _sub == "CONTRAMUESTRAS SOLICITADAS":
                _contra_key = "contra_muestras"
                if _contra_key not in st.session_state:
                    st.session_state[_contra_key] = []
                if st.button("➕  AGREGAR CONTRAMUESTRA", width='stretch',
                             key=f"btn_agregar_contra_{_ti}"):
                    st.session_state[_contra_key].append({
                        "ID":           seg_id_muestra or "",
                        "PROVEEDOR":    (seg_proveedor or "").upper(),
                        "GRASA (%)":    f"{seg_grasa:.2f}"    if seg_grasa    is not None else "",
                        "ST (%)":       f"{seg_st:.2f}"       if seg_st       is not None else "",
                        "PROTEÍNA (%)": f"{seg_proteina:.2f}" if seg_proteina is not None else "",
                        "IC (°C)":      f"{seg_ic:.3f}"       if seg_ic       is not None else "",
                        "AGUA (%)":     f"{seg_agua:.2f}"     if seg_agua     is not None else "",
                        "ALCOHOL":      seg_alcohol,
                        "CLORUROS":     seg_cloruros,
                        "NEUTRALIZANTES": seg_neutralizantes,
                        "OBS":          seg_observaciones or "",
                        "_proveedor":   (seg_proveedor or "").upper(),
                        "_grasa": seg_grasa, "_st": seg_st, "_ic": seg_ic,
                        "_proteina": seg_proteina,
                        "_agua": seg_agua, "_alcohol": seg_alcohol,
                        "_cloruros": seg_cloruros, "_neutralizantes": seg_neutralizantes,
                        "_obs": seg_observaciones or "",
                    })
                    st.session_state[f"seg_quality_key_counter_{_ti}"] = _qk + 1
                    st.rerun()
                if st.session_state[_contra_key]:
                    st.markdown(
                        f"""<div style="font-size:0.9rem;font-weight:700;color:#0056A3;
                                       margin:10px 0 4px 0;">
                             📋 {len(st.session_state[_contra_key])} contramuestra(s) registrada(s)
                           </div>""",
                        unsafe_allow_html=True,
                    )
                    _cat_cp     = load_catalogo()
                    _cat_cp_map = dict(zip(_cat_cp["codigo"].astype(str), _cat_cp["nombre"]))
                    _rows_cp    = []
                    for _mc in st.session_state[_contra_key]:
                        _cod_cp = str(_mc.get("ID", "") or "").strip()
                        _nom_cp = _cat_cp_map.get(_cod_cp, "")
                        _row_cp = {"ID": _cod_cp, "NOMBRE ESTACIÓN": _nom_cp}
                        _row_cp.update({k: v for k, v in _mc.items()
                                        if not k.startswith("_") and k != "ID"})
                        _rows_cp.append(_row_cp)
                    df_prev_c = pd.DataFrame(_rows_cp)
                    st.dataframe(df_prev_c, width='stretch', hide_index=True)

            st.markdown(
                """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                               margin:14px 0 6px 0;letter-spacing:.4px;
                               border-left:4px solid #0056A3;padding-left:10px;">
                     📷 Imágenes de Muestras
                   </div>""",
                unsafe_allow_html=True,
            )
            _s_imgs_conf_key   = f"seg_imgs_confirmadas_{_ti}"
            _s_imgs_noms_key   = f"seg_imgs_nombres_{_ti}"
            _s_img_gen_key     = f"_seg_img_gen_{_ti}"
            if _s_imgs_conf_key not in st.session_state:
                st.session_state[_s_imgs_conf_key] = False
            if _s_imgs_noms_key not in st.session_state:
                st.session_state[_s_imgs_noms_key] = []
            _s_img_gen = st.session_state.get(_s_img_gen_key, 0)

            _s_imgs_subidas = st.file_uploader(
                "ADJUNTAR IMÁGENES",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
                key=f"seg_imgs_uploader_{_ti}_{_s_img_gen}",
                label_visibility="visible",
            )
            if _s_imgs_subidas:
                _s_nombres = [f.name for f in _s_imgs_subidas]
                if _s_nombres != st.session_state[_s_imgs_noms_key]:
                    st.session_state[_s_imgs_conf_key] = False
                _s_confirmed = st.session_state[_s_imgs_conf_key]
                _s_thumb = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin:8px 0;'>"
                for _si in _s_imgs_subidas:
                    _sb64 = base64.b64encode(_si.read()).decode()
                    _sext = _si.name.rsplit(".", 1)[-1].lower()
                    _smime = "image/jpeg" if _sext in ("jpg", "jpeg") else "image/png"
                    _snc   = _si.name if len(_si.name) <= 16 else _si.name[:14] + "…"
                    _schk  = ("<div style='color:#16a34a;font-size:12px;"
                              "text-align:center;font-weight:600;'>✅ Guardada</div>"
                              if _s_confirmed else
                              f"<div style='font-size:10px;color:#888;text-align:center;'>{_snc}</div>")
                    _sbrd  = "#16a34a" if _s_confirmed else "#D1D5DB"
                    _s_thumb += (f"<div style='display:flex;flex-direction:column;"
                                 f"align-items:center;gap:4px;'>"
                                 f"<img src='data:{_smime};base64,{_sb64}' "
                                 f"style='width:150px;height:150px;object-fit:cover;"
                                 f"border-radius:10px;border:2px solid {_sbrd};"
                                 f"box-shadow:0 2px 6px rgba(0,0,0,0.08);'/>"
                                 f"{_schk}</div>")
                    _si.seek(0)
                _s_thumb += "</div>"
                st.markdown(_s_thumb, unsafe_allow_html=True)
                if not st.session_state[_s_imgs_conf_key]:
                    if st.button("💾 GUARDAR IMÁGENES",
                                 key=f"btn_seg_save_imgs_{_ti}",
                                 width='content'):
                        st.session_state[_s_imgs_conf_key] = True
                        st.session_state[_s_imgs_noms_key] = _s_nombres
                        st.rerun()
                else:
                    st.success("✅ Imágenes guardadas correctamente.")
            else:
                st.session_state[_s_imgs_conf_key] = False
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
            if st.button(
                f"💾  GUARDAR {_sub}", type="primary",
                width='stretch', key=f"btn_guardar_seg_{_ti}",
            ):
                ts = now_col().strftime("%d/%m/%Y %H:%M")
                _s_fotos_prefix = f"SEG_{_sub[:3].upper()}_{(seg_codigo or seg_quien_trajo or seg_responsable or 'X').replace(' ','_')[:12]}"
                _s_fotos_paths  = save_fotos_to_disk(
                    _s_imgs_subidas or [], _s_fotos_prefix
                )
                base_row = {
                    "tipo_seguimiento":     "SEGUIMIENTOS",
                    "sub_tipo_seguimiento": _sub,
                    "fecha":                seg_fecha.strftime("%d/%m/%Y") if seg_fecha else "",
                    "seg_codigo":           seg_codigo,
                    "seg_quien_trajo":      (seg_quien_trajo or "").upper(),
                    "ruta":                 (seg_ruta_acomp or "").upper(),
                    "seg_responsable":      (seg_responsable or "").upper(),
                    "guardado_en":          ts,
                    "fotos_json":           json.dumps(_s_fotos_paths, ensure_ascii=False),
                }
                if _sub == "ACOMPAÑAMIENTOS" and st.session_state.get("acomp_muestras"):
                    _sv_muestras = st.session_state.acomp_muestras
                    def _pn_sv(x):
                        try: return float(str(x).replace(",", "."))
                        except: return None
                    _sv_vols = [_pn_sv(m.get("_volumen")) for m in _sv_muestras]
                    _sv_vol_tot = sum(v for v in _sv_vols if v is not None)
                    _sv_pond_st = [(_pn_sv(m.get("_volumen")) or 0) * (_pn_sv(m.get("_st")) or 0)
                                   for m in _sv_muestras
                                   if _pn_sv(m.get("_volumen")) is not None and _pn_sv(m.get("_st")) is not None]
                    _sv_pond_ic = [(_pn_sv(m.get("_volumen")) or 0) * (_pn_sv(m.get("_ic")) or 0)
                                   for m in _sv_muestras
                                   if _pn_sv(m.get("_volumen")) is not None and _pn_sv(m.get("_ic")) is not None]
                    _sv_st_pond = round(sum(_sv_pond_st) / _sv_vol_tot, 2) if _sv_vol_tot and _sv_pond_st else ""
                    _sv_ic_pond = round(sum(_sv_pond_ic) / _sv_vol_tot, 3) if _sv_vol_tot and _sv_pond_ic else ""
                    _sv_vol_dec = int(seg_vol_declarado) if seg_vol_declarado is not None else ""
                    _sv_vol_m   = int(_sv_vol_tot) if _sv_vol_tot else ""
                    _sv_dif_vol = (int(seg_vol_declarado) - int(_sv_vol_tot)
                                   if seg_vol_declarado is not None and _sv_vol_tot else "")
                    save_seguimiento_to_csv({**base_row,
                        "seg_vol_declarado":   _sv_vol_dec,
                        "seg_vol_muestras":    _sv_vol_m,
                        "seg_diferencia_vol":  _sv_dif_vol,
                        "seg_solidos_ruta":    seg_solidos_ruta if seg_solidos_ruta is not None else "",
                        "seg_crioscopia_ruta": seg_crioscopia_ruta if seg_crioscopia_ruta is not None else "",
                        "seg_st_pond":         _sv_st_pond,
                        "seg_ic_pond":         _sv_ic_pond,
                        "muestras_json":       json.dumps(_sv_muestras, ensure_ascii=False),
                    })
                    st.session_state.acomp_muestras = []
                elif _sub == "CONTRAMUESTRAS SOLICITADAS" and st.session_state.get("contra_muestras"):
                    _cm_list = st.session_state.contra_muestras
                    save_seguimiento_to_csv({**base_row,
                        "seg_id_muestra": _cm_list[0].get("ID", "") if _cm_list else "",
                        "muestras_json":  json.dumps(_cm_list, ensure_ascii=False),
                    })
                    st.session_state.contra_muestras = []
                else:
                    save_seguimiento_to_csv({**base_row,
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
                st.session_state[f"_fg_seg_{_ti}"]                 = _fg_seg + 1
                st.session_state[f"seg_quality_key_counter_{_ti}"] = _qk + 1
                st.session_state[_s_img_gen_key]                   = _s_img_gen + 1
                st.session_state[_s_imgs_conf_key]                 = False
                st.session_state[_s_imgs_noms_key]                 = []
                st.session_state[f"seg_guardado_ok_{_ti}"] = True
                clear_draft_state()
                st.rerun()

            if st.session_state.get(f"seg_guardado_ok_{_ti}"):
                st.success(f"✅ Seguimiento {_sub} guardado en el historial.")
                st.session_state[f"seg_guardado_ok_{_ti}"] = False
