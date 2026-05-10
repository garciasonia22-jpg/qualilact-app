import base64
import json

import pandas as pd
import streamlit as st

from utils.time_utils import now_col
from utils.input_utils import sanitizar_nombre_ruta, validar_placa, convertir_a_mayusculas, activar_siguiente_con_enter
from utils.file_utils import save_fotos_to_disk
from utils.data_utils import save_ruta_to_csv, load_catalogo
from utils.quality_utils import parse_num
from utils.draft_utils import clear_draft_state


def render_rutas():
    st.markdown(
        """<div style="display:flex;align-items:center;gap:10px;
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

    if "_ruta_fg" not in st.session_state:
        st.session_state._ruta_fg = 0
    _fg = st.session_state._ruta_fg

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
        "📅  FECHA DE LA RUTA", now_col(),
        key=f"fecha_ruta_{_fg}", format="DD/MM/YYYY",
    )
    nombre_ruta = r1c2.text_input(
        "📍  NOMBRE DE LA RUTA", placeholder="ESCRIBA AQUÍ...",
        key=f"nombre_ruta_{_fg}", on_change=sanitizar_nombre_ruta,
        args=(f"nombre_ruta_{_fg}",),
    )
    r2c1, r2c2, r2c3 = st.columns(3)
    placa = r2c1.text_input(
        "🚚  PLACA DE VEHÍCULO", placeholder="AAA000",
        key=f"placa_vehiculo_{_fg}", on_change=validar_placa,
    )
    conductor = r2c2.text_input(
        "👤  CONDUCTOR", placeholder="NOMBRE COMPLETO",
        key=f"conductor_{_fg}",
    )
    volumen = r2c3.number_input(
        "📦  VOLUMEN (L)", min_value=0, value=None, step=1,
        format="%d", placeholder="DIGITE VOLUMEN", key=f"volumen_ruta_{_fg}",
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
            key=f"solidos_totales_{_fg}",
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
            key=f"crioscopia_{_fg}",
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
        key=f"imagenes_muestras_{_fg}",
        label_visibility="visible",
    )

    if imagenes_subidas:
        nombres_actuales = [f.name for f in imagenes_subidas]
        if nombres_actuales != st.session_state.imagenes_nombres_guardados:
            st.session_state.imagenes_confirmadas = False

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
            img.seek(0)
        thumb_html += "</div>"
        st.markdown(thumb_html, unsafe_allow_html=True)

        if not st.session_state.imagenes_confirmadas:
            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
            if st.button("💾 GUARDAR IMÁGENES", width='content'):
                st.session_state.imagenes_confirmadas = True
                st.session_state.imagenes_nombres_guardados = nombres_actuales
                st.rerun()
        else:
            st.success("✅ Imágenes guardadas correctamente.")
    else:
        st.session_state.imagenes_confirmadas = False
        st.caption("No se han adjuntado imágenes.")

    st.markdown("---")

    if "estaciones_guardadas" not in st.session_state:
        st.session_state.estaciones_guardadas = []
    if "form_ver" not in st.session_state:
        st.session_state.form_ver = 0

    with st.container(border=True):
        v = st.session_state.form_ver
        num_nueva = len(st.session_state.estaciones_guardadas) + 1

        _cat_r = load_catalogo()
        _cat_r_cod = dict(zip(_cat_r["codigo"], _cat_r["nombre"]))
        _cod_actual = st.session_state.get(f"nue_codigo_{v}", "").strip()
        _nom_actual = _cat_r_cod.get(_cod_actual) or _cat_r_cod.get(_cod_actual.upper(), "")
        if _nom_actual:
            st.markdown(
                f"**Agregar Estación — #{num_nueva}"
                f"&nbsp;&nbsp;<span style='color:#0056A3;font-size:1em;'>"
                f"· {_nom_actual}</span>**",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**Agregar Estación — #{num_nueva}**")

        if f"nue_crio_{v}" not in st.session_state:
            st.session_state[f"nue_crio_{v}"] = "-0."

        f1, f2, f3, f4, f5, f6 = st.columns([1.5, 1, 1, 1, 1, 1.5])
        form_codigo   = f1.text_input("CÓDIGO", key=f"nue_codigo_{v}",
                                      placeholder="CÓDIGO",
                                      on_change=convertir_a_mayusculas,
                                      args=(f"nue_codigo_{v}",))
        form_vol      = f2.number_input("VOLUMEN (L)", key=f"nue_vol_{v}",
                                        min_value=0, step=1,
                                        value=None, placeholder="0")
        form_grasa    = f3.number_input("GRASA (%)", key=f"nue_grasa_{v}",
                                        min_value=0.0, max_value=100.0,
                                        step=0.01, format="%.2f",
                                        value=None, placeholder="0.00")
        form_solidos  = f4.number_input("SÓL. TOT. (%)", key=f"nue_solidos_{v}",
                                        min_value=0.0, max_value=100.0,
                                        step=0.01, format="%.2f",
                                        value=None, placeholder="0.00")
        form_proteina = f5.number_input("PROTEÍNA (%)", key=f"nue_proteina_{v}",
                                        min_value=0.0, max_value=100.0,
                                        step=0.01, format="%.2f",
                                        value=None, placeholder="0.00")
        form_crio_raw = f6.text_input("CRIOSCOPIA (°C)", key=f"nue_crio_{v}",
                                      placeholder="-0.530")

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

        activar_siguiente_con_enter()

        if st.button("💾 GUARDAR", type="primary", width='stretch'):
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

    st.markdown("---")

    st.markdown(
        """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                       margin:14px 0 6px 0;letter-spacing:.4px;
                       border-left:4px solid #0056A3;padding-left:10px;">
             📦 Calidad por Estación
           </div>""",
        unsafe_allow_html=True,
    )

    EDITOR_COLS = ["codigo", "grasa", "solidos", "proteina", "crioscopia",
                   "agua_pct", "volumen", "alcohol", "cloruros",
                   "neutralizantes", "obs"]

    if st.session_state.estaciones_guardadas:
        df_est = pd.DataFrame(st.session_state.estaciones_guardadas, columns=EDITOR_COLS)
    else:
        df_est = pd.DataFrame(columns=EDITOR_COLS)

    for c in ["grasa", "solidos", "proteina", "agua_pct"]:
        df_est[c] = pd.to_numeric(df_est[c], errors="coerce")
    df_est["volumen"] = pd.to_numeric(df_est["volumen"], errors="coerce").astype("Int64")

    _cat_tab = load_catalogo()
    _cat_tab_map = dict(zip(_cat_tab["codigo"], _cat_tab["nombre"]))
    df_est["nombre_estacion"] = df_est["codigo"].apply(
        lambda c: _cat_tab_map.get(str(c).strip(), "") if pd.notna(c) else ""
    )

    _nv = st.session_state.get("_est_nombre_ver", 0)
    edited = st.data_editor(
        df_est,
        num_rows="dynamic",
        width='stretch',
        key=f"de_est_{st.session_state.form_ver}_{_nv}",
        column_config={
            "codigo":          st.column_config.TextColumn("CÓDIGO"),
            "grasa":           st.column_config.NumberColumn("GRASA (%)", format="%.2f", min_value=0.0, max_value=100.0),
            "solidos":         st.column_config.NumberColumn("SÓL.TOT. (%)", format="%.2f", min_value=0.0, max_value=100.0),
            "proteina":        st.column_config.NumberColumn("PROTEÍNA (%)", format="%.2f", min_value=0.0, max_value=100.0),
            "crioscopia":      st.column_config.TextColumn("CRIOSCOPIA (°C)"),
            "volumen":         st.column_config.NumberColumn("VOLUMEN (L)", format="%d", min_value=0, step=1),
            "alcohol":         st.column_config.SelectboxColumn("ALCOHOL", options=["N/A", "+", "-"], required=True),
            "cloruros":        st.column_config.SelectboxColumn("CLORUROS", options=["N/A", "+", "-"], required=True),
            "neutralizantes":  st.column_config.SelectboxColumn("NEUTRALIZANTES", options=["N/A", "+", "-"], required=True),
            "agua_pct":        st.column_config.NumberColumn("% AGUA", format="%.1f", min_value=0.0, max_value=100.0),
            "obs":             st.column_config.TextColumn("OBSERVACIONES"),
            "nombre_estacion": st.column_config.TextColumn("NOMBRE ESTACIÓN", disabled=True),
        },
        hide_index=True,
    )

    _prev_codes = list(df_est["codigo"].fillna("").astype(str).str.strip())
    raw = json.loads(edited.to_json(orient="records"))
    st.session_state.estaciones_guardadas = [
        {k: v for k, v in r.items() if k != "nombre_estacion"}
        for r in raw
        if any(v is not None and str(v).strip() != ""
               for k, v in r.items() if k != "nombre_estacion")
    ]
    _new_codes = [str(r.get("codigo") or "").strip()
                  for r in st.session_state.estaciones_guardadas]
    if _prev_codes != _new_codes:
        st.session_state["_est_nombre_ver"] = st.session_state.get("_est_nombre_ver", 0) + 1
        st.rerun()

    st.markdown("---")
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

    if st.button("💾  GUARDAR RUTA", type="primary", width='stretch', key="btn_guardar_ruta"):
        _fotos_prefix = f"RUTAS_{(placa or 'SIN_PLACA').upper()}"
        _fotos_paths  = save_fotos_to_disk(imagenes_subidas or [], _fotos_prefix)
        save_ruta_to_csv({
            "tipo_seguimiento": "RUTAS",
            "fecha":            fecha_ruta.strftime("%d/%m/%Y") if fecha_ruta else "",
            "ruta":             nombre_ruta or "",
            "placa":            placa or "",
            "conductor":        (conductor or "").upper(),
            "volumen_declarado": int(volumen) if volumen else "",
            "vol_estaciones":   int(vol_est_total) if vol_est_total else "",
            "diferencia":       int(diferencia) if vol_ruta else "",
            "solidos_ruta":     solidos_totales if solidos_totales is not None else "",
            "crioscopia_ruta":  crioscopia if crioscopia is not None else "",
            "st_pond":          _st_pond if _st_pond is not None else "",
            "ic_pond":          _ic_pond if _ic_pond is not None else "",
            "num_estaciones":   len(st.session_state.estaciones_guardadas),
            "guardado_en":      now_col().strftime("%d/%m/%Y %H:%M"),
            "estaciones_json":  json.dumps(st.session_state.estaciones_guardadas, ensure_ascii=False),
            "fotos_json":       json.dumps(_fotos_paths, ensure_ascii=False),
        })
        _next_fg = _fg + 1
        for _k in list(st.session_state.keys()):
            if (
                _k.startswith(f"fecha_ruta_{_fg}") or
                _k.startswith(f"nombre_ruta_{_fg}") or
                _k.startswith(f"placa_vehiculo_{_fg}") or
                _k.startswith(f"conductor_{_fg}") or
                _k.startswith(f"volumen_ruta_{_fg}") or
                _k.startswith(f"solidos_totales_{_fg}") or
                _k.startswith(f"crioscopia_{_fg}") or
                _k.startswith(f"imagenes_muestras_{_fg}") or
                _k.startswith("nue_")
            ):
                st.session_state.pop(_k, None)
        st.session_state._ruta_fg         = _next_fg
        st.session_state.estaciones_guardadas = []
        st.session_state.form_ver         = 0
        st.session_state.imagenes_confirmadas = False
        st.session_state.imagenes_nombres_guardados = []
        st.session_state.ruta_guardada_ok = True
        clear_draft_state()
        st.rerun()

    if st.session_state.ruta_guardada_ok:
        st.success("✅ Ruta guardada en el historial correctamente.")
        st.session_state.ruta_guardada_ok = False
