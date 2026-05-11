import json
import os
import re
from datetime import datetime, date

import pandas as pd
import streamlit as st

from utils.time_utils import now_col
from utils.input_utils import convertir_a_mayusculas, activar_siguiente_con_enter
from utils.data_utils import (
    load_historial, load_seguimientos, load_catalogo,
    delete_row_from_csv, delete_rows_from_csv, update_row_in_csv,
    delete_seg_rows, update_seg_row_in_csv,
)
from utils.excel_utils import historial_to_excel_filtrado
from utils.file_utils import get_image_url, generar_zip_imagenes
from config.constants import CSV_COLS


def _is_admin() -> bool:
    return st.session_state.get("_rol_usuario") == "ADMINISTRADOR"


def render_historial():
    st.markdown("---")
    st.markdown(
        """<div style="font-size:1rem;font-weight:700;color:#0056A3;
                       margin:14px 0 6px 0;letter-spacing:.4px;
                       border-left:4px solid #0056A3;padding-left:10px;">
             📊 Historial de Rutas
           </div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-weight:600;color:#374151;margin-bottom:8px;'>"
        "🔍 Filtros de búsqueda</div>",
        unsafe_allow_html=True,
    )

    # Limpia valores viejos de session_state que puedan persistir de versiones anteriores
    for _dk in ("hist_desde", "hist_hasta"):
        if _dk in st.session_state:
            del st.session_state[_dk]

    ff1, ff2, _ = st.columns([2, 2, 4])
    with ff1:
        fecha_desde = st.date_input(
            "FECHA DESDE", value=None,
            format="DD/MM/YYYY", key="hist_fecha_desde",
        )
    with ff2:
        fecha_hasta = st.date_input(
            "FECHA HASTA", value=None,
            format="DD/MM/YYYY", key="hist_fecha_hasta",
        )

    filtro_subtipo = "TODOS"
    _fr2a, _fr2b, _ = st.columns([2, 2, 2])
    with _fr2a:
        filtro_tipo = st.selectbox(
            "REGISTRO",
            ["TODOS", "RUTAS", "TRANSUIZA", "SEGUIMIENTOS"],
            key="hist_tipo",
        )
    with _fr2b:
        if filtro_tipo == "SEGUIMIENTOS":
            filtro_subtipo = st.selectbox(
                "📋 SUB-TIPO",
                ["TODOS", "ESTACIONES", "ACOMPAÑAMIENTOS", "CONTRAMUESTRAS SOLICITADAS"],
                key="hist_subtipo",
            )

    fr1, fr2, fr3 = st.columns([2, 2, 2])
    with fr1:
        filtro_ruta = st.text_input(
            "📍 RUTA", placeholder="Nombre de ruta…",
            key="hist_ruta",
        ).strip().upper()
    with fr2:
        filtro_placa = st.text_input(
            "🚛 PLACA", placeholder="Ej: ABC123",
            key="hist_placa",
        ).strip().upper()
    with fr3:
        filtro_codigo = st.text_input(
            "🔖 CÓDIGO ESTACIÓN", placeholder="Ej: 6008",
            key="hist_codigo_seg",
        ).strip().upper()

    _fechas_validas = (fecha_desde is not None and fecha_hasta is not None)

    _fbrow, _ = st.columns([1, 5])
    with _fbrow:
        if st.button("🔍 BUSCAR", type="primary",
                     key="btn_buscar_hist", width='stretch'):
            if _fechas_validas:
                st.session_state.hist_buscar_ok = True
                st.rerun()
            else:
                st.warning("⚠️ Debes seleccionar ambas fechas para buscar.")

    if not st.session_state.hist_buscar_ok or not _fechas_validas:
        st.info("Selecciona el rango de fechas y presiona **🔍 BUSCAR** para ver el historial.")
        return

    # ── Carga de datos (solo tras presionar BUSCAR) ───────────────────────────
    df_hist = load_historial()
    if df_hist.empty:
        st.info("No hay rutas guardadas aún. Complete el formulario y presione **GUARDAR RUTA** para registrar datos aquí.")
        return

    _buscar_por_codigo = bool(filtro_codigo)

    if _buscar_por_codigo or filtro_tipo in ("TODOS", "SEGUIMIENTOS"):
        df_filtrado = load_seguimientos()
        if "_fecha_dt" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                (df_filtrado["_fecha_dt"].dt.date >= fecha_desde) &
                (df_filtrado["_fecha_dt"].dt.date <= fecha_hasta)
            ]
        if not _buscar_por_codigo and filtro_subtipo != "TODOS" \
                and "sub_tipo_seguimiento" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado["sub_tipo_seguimiento"] == filtro_subtipo
            ]
        if _buscar_por_codigo and "seg_codigo" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["seg_codigo"] == filtro_codigo]
        if filtro_ruta and "ruta" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado["ruta"].str.contains(filtro_ruta, na=False, case=False)
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
        if filtro_placa and "placa" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado["placa"].str.contains(filtro_placa, na=False, case=False)
            ]
        if filtro_ruta and "ruta" in df_filtrado.columns:
            df_filtrado = df_filtrado[
                df_filtrado["ruta"].str.contains(filtro_ruta, na=False, case=False)
            ]

    from utils.quality_utils import calcular_estado_calidad
    df_filtrado = df_filtrado.copy()
    df_filtrado["_estado"] = df_filtrado.apply(
        lambda r: calcular_estado_calidad(r.to_dict()), axis=1
    )

    RED = "background-color:#FFC7CE;color:#9C0006;font-weight:700"

    _SEG_COLS = ["sub_tipo_seguimiento", "fecha", "seg_codigo", "seg_quien_trajo",
                 "ruta", "seg_responsable", "seg_id_muestra",
                 "seg_grasa", "seg_st", "seg_ic", "seg_agua",
                 "seg_alcohol", "seg_cloruros", "seg_neutralizantes",
                 "seg_observaciones", "guardado_en"]
    _SEG_LBLS = {
        "sub_tipo_seguimiento": "SUB-TIPO", "fecha": "FECHA",
        "seg_codigo": "CÓDIGO", "seg_quien_trajo": "ENTREGADO POR",
        "ruta": "RUTA", "seg_responsable": "RESPONSABLE",
        "seg_id_muestra": "ID MUESTRA", "seg_grasa": "GRASA (%)",
        "seg_st": "ST (%)", "seg_ic": "IC (°C)", "seg_agua": "AGUA (%)",
        "seg_alcohol": "ALCOHOL", "seg_cloruros": "CLORUROS",
        "seg_neutralizantes": "NEUTRALIZANTES",
        "seg_observaciones": "OBSERVACIONES", "guardado_en": "GUARDADO EN",
    }
    _SEG_CFG = {
        "GRASA (%)": st.column_config.NumberColumn(format="%.2f"),
        "ST (%)":    st.column_config.NumberColumn(format="%.2f"),
        "IC (°C)":   st.column_config.NumberColumn(format="%.3f"),
        "AGUA (%)":  st.column_config.NumberColumn(format="%.2f"),
    }

    def _render_seccion_cod(titulo, emoji, df_sec):
        st.markdown(
            f"<div style='font-size:1rem;font-weight:700;color:#0056A3;"
            f"margin:14px 0 6px 0;border-left:4px solid #0056A3;"
            f"padding-left:10px;letter-spacing:.4px;'>"
            f"{emoji} {titulo} — {len(df_sec)} registro(s)</div>",
            unsafe_allow_html=True,
        )
        if df_sec.empty:
            st.info("No hay datos para este código en esta sección.")
        else:
            _vis = [c for c in _SEG_COLS if c in df_sec.columns]
            df_d = df_sec[_vis].rename(columns=_SEG_LBLS).reset_index(drop=True)
            st.dataframe(df_d, width='stretch',
                         hide_index=True, column_config=_SEG_CFG)

    if _buscar_por_codigo:
        import json as _json_hist

        _df_seg_cod = df_filtrado

        if "sub_tipo_seguimiento" in _df_seg_cod.columns:
            _df_est_cod   = _df_seg_cod[_df_seg_cod["sub_tipo_seguimiento"] == "ESTACIONES"]
            _df_acomp_cod = _df_seg_cod[_df_seg_cod["sub_tipo_seguimiento"] == "ACOMPAÑAMIENTOS"]
            _df_ct_cod    = _df_seg_cod[_df_seg_cod["sub_tipo_seguimiento"] == "CONTRAMUESTRAS SOLICITADAS"]
        else:
            _df_est_cod = _df_acomp_cod = _df_ct_cod = pd.DataFrame()

        _df_rutas_src = df_hist.copy()
        if "_fecha_dt" in _df_rutas_src.columns:
            _df_rutas_src = _df_rutas_src[
                (_df_rutas_src["_fecha_dt"].dt.date >= fecha_desde) &
                (_df_rutas_src["_fecha_dt"].dt.date <= fecha_hasta)
            ]
        _idxs_ruta_cod = []
        for _ri, _rrow in _df_rutas_src.iterrows():
            try:
                _ests = _json_hist.loads(
                    _rrow.get("estaciones_json", "[]") or "[]"
                )
                if any(
                    str(_e.get("codigo", "")).strip().upper()
                    == str(filtro_codigo).strip().upper()
                    for _e in _ests
                ):
                    _idxs_ruta_cod.append(_ri)
            except Exception:
                pass
        _df_rutas_cod = _df_rutas_src.loc[_idxs_ruta_cod]

        _total_cod = len(_df_est_cod) + len(_df_acomp_cod) + len(_df_ct_cod) + len(_df_rutas_cod)
        st.markdown(
            f"<div style='font-weight:700;color:#374151;margin:4px 0 10px 0;'>"
            f"🔍 Resultados para código <span style='color:#0056A3;'>{filtro_codigo}</span>"
            f" — {_total_cod} registro(s) en total</div>",
            unsafe_allow_html=True,
        )

        _render_seccion_cod("ESTACIONES",              "🏗️", _df_est_cod)
        _render_seccion_cod("ACOMPAÑAMIENTOS",         "🚌", _df_acomp_cod)
        _render_seccion_cod("CONTRAMUESTRAS SOLICITADAS", "🧪", _df_ct_cod)

        st.markdown(
            "<div style='font-size:1rem;font-weight:700;color:#0056A3;"
            "margin:14px 0 6px 0;border-left:4px solid #0056A3;"
            "padding-left:10px;letter-spacing:.4px;'>"
            f"🚛 RUTAS — {len(_df_rutas_cod)} registro(s)</div>",
            unsafe_allow_html=True,
        )
        if _df_rutas_cod.empty:
            st.info("No hay datos para este código en esta sección.")
        else:
            _rcols = ["fecha", "ruta", "placa", "conductor",
                      "volumen_declarado", "vol_estaciones",
                      "solidos_ruta", "crioscopia_ruta", "guardado_en"]
            _rlbls = {
                "fecha": "FECHA", "ruta": "RUTA", "placa": "PLACA",
                "conductor": "CONDUCTOR",
                "volumen_declarado": "VOL. DECL. (L)",
                "vol_estaciones": "VOL. EST. (L)",
                "solidos_ruta": "ST RUTA (%)",
                "crioscopia_ruta": "IC RUTA (°C)",
                "guardado_en": "GUARDADO EN",
            }
            _rcfg = {
                "ST RUTA (%)":  st.column_config.NumberColumn(format="%.2f"),
                "IC RUTA (°C)": st.column_config.NumberColumn(format="%.3f"),
                "VOL. DECL. (L)": st.column_config.NumberColumn(format="%d"),
                "VOL. EST. (L)":  st.column_config.NumberColumn(format="%d"),
            }
            _rvis = [c for c in _rcols if c in _df_rutas_cod.columns]
            st.dataframe(
                _df_rutas_cod[_rvis].rename(columns=_rlbls).reset_index(drop=True),
                width='stretch', hide_index=True, column_config=_rcfg,
            )

        if _total_cod > 0:
            _ts = now_col().strftime('%Y%m%d_%H%M')
            _cx, _czip, _ = st.columns([1, 1, 2])
            with _cx:
                st.download_button(
                    label="⬇️ DESCARGAR REPORTE EXCEL",
                    data=historial_to_excel_filtrado(
                        df_filtrado, fecha_desde, fecha_hasta,
                        filtro_tipo, filtro_subtipo
                    ),
                    file_name=f"historial_qualilact_{_ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary", width='stretch',
                )
            with _czip:
                _zip_bytes_cod, _zip_n_cod = generar_zip_imagenes(df_filtrado)
                if _zip_n_cod > 0:
                    st.download_button(
                        label=f"📸 Descargar Evidencias ({_zip_n_cod})",
                        data=_zip_bytes_cod,
                        file_name=f"Evidencias_QualiLact_{_ts}.zip",
                        mime="application/zip",
                        width='stretch',
                    )
                else:
                    st.info("Sin imágenes adjuntas en estos registros.")

        sel = None
        sel_orig_idxs = []
        sel_orig_idx  = None

    else:
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

        if not _buscar_por_codigo and filtro_tipo == "TRANSUIZA":
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

        elif filtro_tipo == "RUTAS" and not _buscar_por_codigo:
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
                        "seg_quien_trajo", "ruta",
                        "seg_id_muestra", "seg_grasa", "seg_st", "seg_ic", "seg_agua",
                        "seg_alcohol", "seg_cloruros", "seg_neutralizantes",
                        "seg_observaciones", "guardado_en"]
            col_labels = {
                "sub_tipo_seguimiento": "SUB-TIPO", "fecha": "FECHA",
                "seg_codigo": "CÓDIGO", "seg_quien_trajo": "ENTREGADO POR",
                "ruta": "RUTA",
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
            cols_sel = ["sub_tipo_seguimiento", "fecha", "seg_codigo",
                        "seg_quien_trajo", "ruta",
                        "seg_id_muestra", "seg_grasa", "seg_st", "seg_ic", "seg_agua",
                        "seg_alcohol", "seg_cloruros", "seg_neutralizantes",
                        "seg_observaciones", "guardado_en"]
            col_labels = {
                "sub_tipo_seguimiento": "SUB-TIPO", "fecha": "FECHA",
                "seg_codigo": "CÓDIGO", "seg_quien_trajo": "ENTREGADO POR",
                "ruta": "RUTA",
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

        cols_vis   = [c for c in cols_sel if c in df_filtrado.columns]
        df_display = df_filtrado[cols_vis].rename(columns=col_labels).reset_index(drop=True)

        sel = st.dataframe(
            df_display.style.apply(resaltar_celdas, axis=1),
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            column_config=col_config_map,
        )

        orig_indices  = df_filtrado.index.tolist()
        filas_sel     = (sel.selection.rows
                         if sel and hasattr(sel, "selection") else [])
        sel_orig_idxs = [orig_indices[i] for i in filas_sel
                         if i < len(orig_indices)]
        sel_orig_idx  = sel_orig_idxs[0] if len(sel_orig_idxs) == 1 else None

        df_para_excel = (df_filtrado.loc[sel_orig_idxs]
                         if sel_orig_idxs else df_filtrado)

        if not df_filtrado.empty:
            _ts = now_col().strftime('%Y%m%d_%H%M')
            _n  = len(df_para_excel)
            _msg = (f"📋 {_n} fila(s) seleccionada(s)"
                    if sel_orig_idxs
                    else f"📋 {_n} registro(s) filtrados")
            _cx, _czip, _mx = st.columns([1, 1, 3])
            with _cx:
                st.download_button(
                    label="⬇️ DESCARGAR EXCEL",
                    data=historial_to_excel_filtrado(
                        df_para_excel, fecha_desde, fecha_hasta,
                        filtro_tipo, filtro_subtipo
                    ),
                    file_name=f"historial_qualilact_{_ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    width='stretch',
                )
            with _czip:
                _zip_bytes, _zip_n = generar_zip_imagenes(df_para_excel)
                if _zip_n > 0:
                    st.download_button(
                        label=f"📸 EVIDENCIAS ({_zip_n})",
                        data=_zip_bytes,
                        file_name=f"Evidencias_QualiLact_{_ts}.zip",
                        mime="application/zip",
                        width='stretch',
                    )
                else:
                    st.markdown(
                        "<div style='padding:8px 0 0 4px;font-size:12px;"
                        "color:#6B7280;'>📷 Sin imágenes adjuntas</div>",
                        unsafe_allow_html=True,
                    )
            with _mx:
                st.markdown(
                    f"<div style='padding:8px 0 0 4px;font-size:13px;"
                    f"color:#374151;'>{_msg}</div>",
                    unsafe_allow_html=True,
                )

        if sel_orig_idxs:
            n_sel = len(sel_orig_idxs)
            _accion_hint = " — elige una acción:" if _is_admin() else " — seleccionada para ver detalle:"
            st.markdown(
                f"<div style='font-size:12px;color:#6B7280;margin:6px 0 4px 0;'>"
                f"{'1 fila seleccionada' if n_sel == 1 else f'{n_sel} filas seleccionadas'}"
                f"{_accion_hint}</div>",
                unsafe_allow_html=True,
            )
            if _is_admin():
                ab1, ab2, _ = st.columns([1, 1, 5])
                with ab1:
                    if st.button("✏️ Modificar", key="btn_modificar",
                                 width='stretch',
                                 help="Editar este registro",
                                 disabled=(n_sel != 1)):
                        st.session_state.admin_accion = "modificar"
                        st.session_state.admin_idx    = sel_orig_idx
                        st.rerun()
                with ab2:
                    if st.button("🗑️ Eliminar", key="btn_eliminar",
                                 width='stretch',
                                 help=f"Eliminar {n_sel} registro(s) seleccionado(s)"):
                        st.session_state.admin_accion    = "eliminar"
                        st.session_state.admin_idxs      = sel_orig_idxs
                        st.session_state.admin_idx       = sel_orig_idx
                        st.session_state.admin_from_seg  = filtro_tipo in ("SEGUIMIENTOS", "TODOS")
                        st.rerun()

        _ss_accion = st.session_state.get("admin_accion")
        _ss_idx    = st.session_state.get("admin_idx")
        if (sel_orig_idx is None and _ss_accion == "modificar"
                and _ss_idx is not None):
            sel_orig_idx = _ss_idx

        if (sel_orig_idx is not None and filtro_tipo == "SEGUIMIENTOS"
                and st.session_state.hist_buscar_ok):
            if sel_orig_idx in df_filtrado.index:
                _srow = df_filtrado.loc[sel_orig_idx]
            else:
                _srow = {}
            _s_sub = str(_srow.get("sub_tipo_seguimiento", "")).strip()
            if _s_sub == "ACOMPAÑAMIENTOS":
                _mj_raw = str(_srow.get("muestras_json", "") or "").strip()
                try:
                    _mj_data = json.loads(_mj_raw) if _mj_raw else []
                except Exception:
                    _mj_data = []
                if _mj_data:
                    st.markdown("---")
                    _ac_entreg  = str(_srow.get("seg_quien_trajo", "") or "").strip() or "—"
                    _ac_ruta    = str(_srow.get("ruta", "") or "").strip() or "—"
                    _ac_resp    = str(_srow.get("seg_responsable", "") or "").strip() or "—"
                    _ac_cod     = str(_srow.get("seg_codigo", "") or "").strip() or "—"
                    _ac_fecha   = str(_srow.get("fecha", "") or "").strip() or "—"
                    st.markdown(
                        f"""<div style="background:#0056A3;border-radius:8px;
                                       padding:10px 16px;margin-bottom:14px;">
                              <span style="font-size:1rem;font-weight:700;color:#fff;
                                           letter-spacing:.05em;">
                                👥 DETALLE ACOMPAÑAMIENTO
                              </span>
                              <span style="font-size:.85rem;color:#cce0f5;margin-left:12px;">
                                {_ac_cod} &nbsp;·&nbsp; {_ac_fecha}
                              </span>
                            </div>""",
                        unsafe_allow_html=True,
                    )
                    _det_accion_ac = st.session_state.get("admin_accion")
                    _det_idx_ac    = st.session_state.get("admin_idx")
                    _edit_mode_ac  = (
                        _det_accion_ac == "modificar"
                        and _det_idx_ac == sel_orig_idx
                    )

                    if _edit_mode_ac:
                        def _pn_ed(x, default=0.0):
                            try: return float(str(x).replace(",","."))
                            except: return default
                        try:
                            _fe_ac = datetime.strptime(str(_srow.get("fecha", "")), "%d/%m/%Y").date()
                        except Exception:
                            _fe_ac = date.today()
                        try:
                            _ac_vol_d_v = int(_pn_ed(_srow.get("seg_vol_declarado", "") or 0))
                        except Exception:
                            _ac_vol_d_v = 0

                        st.markdown("<div style='font-size:11px;font-weight:700;color:#0056A3;letter-spacing:.05em;margin-bottom:6px;'>📋 ENCABEZADO</div>", unsafe_allow_html=True)
                        aci1, aci2 = st.columns(2)
                        _ace_fecha = aci1.date_input("📅 FECHA", value=_fe_ac, format="DD/MM/YYYY", key="edit_ac_fecha")
                        _ace_ruta = aci2.text_input("📍 NOMBRE DE LA RUTA", value=_ac_ruta if _ac_ruta != "—" else "", key="edit_ac_ruta", on_change=convertir_a_mayusculas, args=("edit_ac_ruta",))
                        acj1, acj2, acj3, acj4 = st.columns(4)
                        _ace_ent = acj1.text_input("👤 ENTREGADO POR", value=_ac_entreg if _ac_entreg != "—" else "", key="edit_ac_ent", on_change=convertir_a_mayusculas, args=("edit_ac_ent",))
                        _ace_vol = acj2.number_input("🪣 VOL. DECLARADO (L)", value=_ac_vol_d_v, min_value=0, step=1, key="edit_ac_vol")
                        _ace_str = acj3.number_input("📊 ST RUTA (%)", value=_pn_ed(_srow.get("seg_solidos_ruta", "")), min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key="edit_ac_str")
                        _ace_icr = acj4.number_input("🌡 IC RUTA (°C)", value=_pn_ed(_srow.get("seg_crioscopia_ruta", ""), -0.530), step=0.001, format="%.3f", key="edit_ac_icr")

                        st.markdown("<div style='font-size:11px;font-weight:700;color:#0056A3;letter-spacing:.05em;margin:10px 0 4px;'>🔬 ESTACIONES</div>", unsafe_allow_html=True)
                        st.caption("💡 Tab / → / Enter → siguiente celda · ← → anterior · Enter en última celda → guarda")

                        _AC_COLS = ["ID","_volumen","_grasa","_st","_proteina","_ic","_agua","_alcohol","_cloruros","_neutralizantes","_obs"]
                        _ac_cache_key = f"_ac_m_cache_{sel_orig_idx}"
                        _cat_ac_ed = load_catalogo()
                        _cat_ac_ed_m = dict(zip(_cat_ac_ed["codigo"], _cat_ac_ed["nombre"]))

                        if _ac_cache_key in st.session_state:
                            _df_ac_ed = st.session_state[_ac_cache_key].copy()
                        else:
                            _df_ac_ed = pd.DataFrame([{k: m.get(k, "") for k in _AC_COLS} for m in _mj_data], columns=_AC_COLS)
                            for _nc in ["_volumen","_grasa","_st","_proteina","_agua","_ic"]:
                                _df_ac_ed[_nc] = pd.to_numeric(_df_ac_ed[_nc], errors="coerce")

                        _df_ac_ed["nombre_estacion"] = _df_ac_ed["ID"].apply(lambda c: _cat_ac_ed_m.get(str(c).strip(), "") if pd.notna(c) else "")
                        _tri_ac_de = ["N/A", "NEGATIVO (−)", "POSITIVO (+)"]
                        _edited_ac = st.data_editor(_df_ac_ed, num_rows="dynamic", width='stretch', key="edit_ac_de",
                            column_config={
                                "ID": st.column_config.TextColumn("CÓDIGO"),
                                "nombre_estacion": st.column_config.TextColumn("NOMBRE", disabled=True),
                                "_volumen": st.column_config.NumberColumn("VOL (L)", format="%.0f", min_value=0, step=1),
                                "_grasa":   st.column_config.NumberColumn("GRASA (%)", format="%.2f", min_value=0.0, max_value=100.0),
                                "_st":      st.column_config.NumberColumn("ST (%)",    format="%.2f", min_value=0.0, max_value=100.0),
                                "_proteina":st.column_config.NumberColumn("PROT. (%)", format="%.2f", min_value=0.0, max_value=100.0),
                                "_ic":      st.column_config.NumberColumn("IC (°C)",   format="%.3f"),
                                "_agua":    st.column_config.NumberColumn("AGUA (%)",  format="%.2f", min_value=0.0, max_value=100.0),
                                "_alcohol": st.column_config.SelectboxColumn("ALCOHOL",    options=_tri_ac_de, required=True),
                                "_cloruros":st.column_config.SelectboxColumn("CLORUROS",   options=_tri_ac_de, required=True),
                                "_neutralizantes":st.column_config.SelectboxColumn("NEUT.", options=_tri_ac_de, required=True),
                                "_obs":     st.column_config.TextColumn("OBS"),
                            }, hide_index=True)
                        _ac_prev_ids = list(_df_ac_ed["ID"].fillna("").astype(str))
                        _ac_new_ids  = list(_edited_ac["ID"].fillna("").astype(str))
                        _ac_cache_df = _edited_ac.drop(columns=["nombre_estacion"], errors="ignore").copy()
                        st.session_state[_ac_cache_key] = _ac_cache_df
                        if _ac_prev_ids != _ac_new_ids:
                            st.rerun()

                        activar_siguiente_con_enter()
                        ac_s1, ac_s2, _ = st.columns([1.5, 1, 3])
                        with ac_s1:
                            if st.button("💾 GUARDAR CAMBIOS", type="primary", width='stretch', key="btn_save_edit_ac"):
                                def _pf(v, d=0.0):
                                    try:
                                        f = float(str(v).replace(",","."))
                                        return f if f == f else d
                                    except: return d
                                def _pi(v, d=0):
                                    try:
                                        f = float(str(v).replace(",","."))
                                        return int(f) if f == f else d
                                    except: return d
                                _save_df = _edited_ac.drop(columns=["nombre_estacion"], errors="ignore")
                                _new_muestras = []
                                for _, _row in _save_df.iterrows():
                                    _new_muestras.append({
                                        "ID": str(_row.get("ID","") or "").upper().strip(),
                                        "_volumen":  _pi(_row.get("_volumen", 0)),
                                        "_grasa":    round(_pf(_row.get("_grasa",0)), 2),
                                        "_st":       round(_pf(_row.get("_st",0)), 2),
                                        "_ic":       round(_pf(_row.get("_ic", -0.530), -0.530), 3),
                                        "_agua":     round(_pf(_row.get("_agua",0)), 2),
                                        "_proteina": round(_pf(_row.get("_proteina",0)), 2),
                                        "_alcohol":  str(_row.get("_alcohol","N/A") or "N/A"),
                                        "_cloruros": str(_row.get("_cloruros","N/A") or "N/A"),
                                        "_neutralizantes": str(_row.get("_neutralizantes","N/A") or "N/A"),
                                        "_obs":      str(_row.get("_obs","") or ""),
                                    })
                                _nv_tot   = sum(m["_volumen"] for m in _new_muestras)
                                _npond_st = [m["_volumen"]*m["_st"] for m in _new_muestras if m["_volumen"] and m["_st"] is not None]
                                _npond_ic = [m["_volumen"]*m["_ic"] for m in _new_muestras if m["_volumen"] and m["_ic"] is not None]
                                _nst_p = round(sum(_npond_st)/_nv_tot,2) if _nv_tot and _npond_st else ""
                                _nic_p = round(sum(_npond_ic)/_nv_tot,3) if _nv_tot and _npond_ic else ""
                                _n_vol_dec = _pi(st.session_state.get("edit_ac_vol", _ac_vol_d_v) or _ac_vol_d_v)
                                update_seg_row_in_csv(sel_orig_idx, {
                                    "fecha":              _ace_fecha.strftime("%d/%m/%Y"),
                                    "ruta":               str(st.session_state.get("edit_ac_ruta","")).upper().strip(),
                                    "seg_quien_trajo":    str(st.session_state.get("edit_ac_ent","")).upper().strip(),
                                    "seg_vol_declarado":  _n_vol_dec,
                                    "seg_vol_muestras":   _pi(_nv_tot) if _nv_tot else "",
                                    "seg_diferencia_vol": _pi(_n_vol_dec - _nv_tot) if _nv_tot else "",
                                    "seg_solidos_ruta":   round(_pf(st.session_state.get("edit_ac_str",0)), 2),
                                    "seg_crioscopia_ruta":round(_pf(st.session_state.get("edit_ac_icr",-0.530),-0.530), 3),
                                    "seg_st_pond":        _nst_p,
                                    "seg_ic_pond":        _nic_p,
                                    "muestras_json":      json.dumps(_new_muestras, ensure_ascii=False),
                                })
                                st.session_state.pop(_ac_cache_key, None)
                                st.session_state.admin_accion = None
                                st.session_state.admin_idx    = None
                                st.rerun()
                        with ac_s2:
                            if st.button("✖ CANCELAR", width='stretch', key="btn_cancel_edit_ac"):
                                st.session_state.pop(_ac_cache_key, None)
                                st.session_state.admin_accion = None
                                st.session_state.admin_idx    = None
                                st.rerun()
                    else:
                        def _kpi_card_ac(label, value, badge=None, badge_ok=True):
                            badge_html = ""
                            if badge:
                                bg  = "#D4EDDA" if badge_ok else "#F8D7DA"
                                col = "#155724" if badge_ok else "#721C24"
                                badge_html = (f'<div style="margin-top:4px;font-size:.65rem;font-weight:700;color:{col};background:{bg};border-radius:4px;padding:1px 5px;display:inline-block;">{badge}</div>')
                            return (f'<div style="background:#fff;border:1px solid #dde6f0;border-radius:8px;padding:10px 12px;text-align:center;height:100%;"><div style="font-size:.62rem;font-weight:700;color:#6c8ca8;letter-spacing:.06em;margin-bottom:4px;">{label}</div><div style="font-size:1.05rem;font-weight:800;color:#0056A3;">{value}</div>{badge_html}</div>')

                        def _pnac(x):
                            try: return float(str(x).replace(",", "."))
                            except: return None

                        _ac_n_muestras  = len(_mj_data)
                        _entreg_short   = (_ac_entreg[:16]+"…") if len(_ac_entreg) > 16 else _ac_entreg
                        _ac_vol_dec = _srow.get("seg_vol_declarado", "")
                        _ac_vol_m   = _srow.get("seg_vol_muestras",  "")
                        _ac_dif_vol = _srow.get("seg_diferencia_vol","")
                        _ac_st_r    = _srow.get("seg_solidos_ruta",  "")
                        _ac_ic_r    = _srow.get("seg_crioscopia_ruta","")
                        _ac_st_p    = _srow.get("seg_st_pond",       "")
                        _ac_ic_p    = _srow.get("seg_ic_pond",       "")

                        try:    _v_ac_vol_dec = f"{int(float(_ac_vol_dec)):,} L"
                        except: _v_ac_vol_dec = "—"
                        try:    _v_ac_vol_m   = f"{int(float(_ac_vol_m)):,} L"
                        except: _v_ac_vol_m   = "—"
                        try:
                            _dif_v = int(float(_ac_dif_vol))
                            _dif_ok = abs(_dif_v) <= 20
                            _v_ac_dif = f"{_dif_v:+,} L"
                        except:
                            _v_ac_dif = "—"; _dif_ok = True

                        try:    _v_ac_str = f"{float(_ac_st_r):.2f} %"
                        except: _v_ac_str = "—"
                        try:    _v_ac_icr = f"{float(_ac_ic_r):.3f} °C"
                        except: _v_ac_icr = "—"
                        try:    _v_ac_stp = f"{float(_ac_st_p):.2f} %"
                        except: _v_ac_stp = "—"
                        try:    _v_ac_icp = f"{float(_ac_ic_p):.3f} °C"
                        except: _v_ac_icp = "—"

                        _acr1 = ('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">'
                                 + _kpi_card_ac("RUTA", _ac_ruta[:20] if len(_ac_ruta) <= 20 else _ac_ruta[:18]+"…")
                                 + _kpi_card_ac("ENTREGADO POR", _entreg_short)
                                 + _kpi_card_ac("MUESTRAS", str(_ac_n_muestras))
                                 + _kpi_card_ac("VOL. DECLARADO", _v_ac_vol_dec)
                                 + '</div>')
                        _acr2 = ('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">'
                                 + _kpi_card_ac("VOL. MUESTRAS", _v_ac_vol_m)
                                 + _kpi_card_ac("DIFERENCIA", _v_ac_dif, badge="OK" if _dif_ok else "⚠ DIFER.", badge_ok=_dif_ok)
                                 + _kpi_card_ac("ST RUTA (%)", _v_ac_str)
                                 + _kpi_card_ac("IC RUTA (°C)", _v_ac_icr)
                                 + '</div>')
                        st.markdown(_acr1 + _acr2, unsafe_allow_html=True)

                        _cat_ac = load_catalogo()
                        _cat_ac_map = dict(zip(_cat_ac["codigo"], _cat_ac["nombre"]))
                        _ac_rows_v = []
                        _RED_AC = "background-color:#FFC7CE;color:#9C0006;font-weight:700"
                        for _am in _mj_data:
                            def _pnv2(x):
                                try: return float(str(x).replace(",",".")) if str(x).strip() not in ("","None","nan") else None
                                except: return None
                            _cod_am = str(_am.get("ID","") or "").strip()
                            _nom_am = _cat_ac_map.get(_cod_am, "")
                            _am_st = _pnv2(_am.get("_st"))
                            _am_ic = _pnv2(_am.get("_ic"))
                            _am_vol = _pnv2(_am.get("_volumen"))
                            _am_pond_st = round((_am_vol or 0)*(_am_st or 0), 2) if _am_vol and _am_st else None
                            _am_pond_ic = round((_am_vol or 0)*(_am_ic or 0), 3) if _am_vol and _am_ic else None
                            _ac_rows_v.append({
                                "CÓDIGO":          _cod_am,
                                "NOMBRE ESTACIÓN": _nom_am,
                                "VOL (L)":         int(_am_vol) if _am_vol is not None else None,
                                "GRASA (%)":       _pnv2(_am.get("_grasa")),
                                "ST (%)":          _am_st,
                                "PROT. (%)":       _pnv2(_am.get("_proteina")),
                                "IC (°C)":         _am_ic,
                                "AGUA (%)":        _pnv2(_am.get("_agua")),
                                "POND ST":         _am_pond_st,
                                "POND IC":         _am_pond_ic,
                                "ALC.":            str(_am.get("_alcohol","N/A") or "N/A"),
                                "CLOR.":           str(_am.get("_cloruros","N/A") or "N/A"),
                                "NEUT.":           str(_am.get("_neutralizantes","N/A") or "N/A"),
                                "OBS":             str(_am.get("_obs","") or ""),
                            })
                        if _ac_rows_v:
                            _df_ac_v = pd.DataFrame(_ac_rows_v)
                            st.dataframe(_df_ac_v, width='stretch', hide_index=True,
                                height=min(38+35*len(_ac_rows_v), 420),
                                column_config={
                                    "VOL (L)":      st.column_config.NumberColumn(format="%d"),
                                    "GRASA (%)":    st.column_config.NumberColumn(format="%.2f"),
                                    "ST (%)":       st.column_config.NumberColumn(format="%.2f"),
                                    "PROT. (%)":    st.column_config.NumberColumn(format="%.2f"),
                                    "IC (°C)":      st.column_config.NumberColumn(format="%.3f"),
                                    "AGUA (%)":     st.column_config.NumberColumn(format="%.2f"),
                                    "POND ST":      st.column_config.NumberColumn(format="%.2f"),
                                    "POND IC":      st.column_config.NumberColumn(format="%.3f"),
                                })
                            _acr3 = ('<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:8px;">'
                                     + _kpi_card_ac("ST PONDERADO (%)", _v_ac_stp)
                                     + _kpi_card_ac("IC PONDERADO (°C)", _v_ac_icp)
                                     + '</div>')
                            st.markdown(_acr3, unsafe_allow_html=True)

                    _ac_fotos_raw = str(_srow.get("fotos_json", "") or "").strip()
                    if _ac_fotos_raw and _ac_fotos_raw not in ("[]", ""):
                        try:
                            _ac_fotos_list = json.loads(_ac_fotos_raw)
                        except Exception:
                            _ac_fotos_list = []
                        _ac_fotos_urls = [(_p, get_image_url(_p)) for _p in _ac_fotos_list if _p]
                        _ac_fotos_urls = [(p, u) for p, u in _ac_fotos_urls if u]
                        if _ac_fotos_urls:
                            st.markdown(
                                "<div style='font-size:11px;font-weight:700;color:#0056A3;"
                                "letter-spacing:.05em;margin:12px 0 6px;'>"
                                "📷 IMÁGENES DE MUESTRAS</div>",
                                unsafe_allow_html=True,
                            )
                            _ac_cols_f = st.columns(min(len(_ac_fotos_urls), 4))
                            for _afi, (_afp, _afurl) in enumerate(_ac_fotos_urls):
                                with _ac_cols_f[_afi % 4]:
                                    st.image(_afurl, width='stretch')

            elif _s_sub == "CONTRAMUESTRAS SOLICITADAS":
                st.markdown("---")
                _ct_fecha  = str(_srow.get("fecha", "") or "").strip() or "—"
                _ct_resp   = str(_srow.get("seg_responsable", "") or "").strip() or "—"
                _ct_id     = str(_srow.get("seg_id_muestra", "") or "").strip() or "—"
                _ct_cat     = load_catalogo()
                _ct_cat_map = dict(zip(_ct_cat["codigo"].astype(str), _ct_cat["nombre"]))
                _ct_nombre  = _ct_cat_map.get(_ct_id, "")
                _ct_grasa   = _srow.get("seg_grasa",  "")
                _ct_st      = _srow.get("seg_st",     "")
                _ct_ic      = _srow.get("seg_ic",     "")
                _ct_agua    = _srow.get("seg_agua",   "")
                _ct_alc     = str(_srow.get("seg_alcohol",        "") or "").strip() or "N/A"
                _ct_clor    = str(_srow.get("seg_cloruros",       "") or "").strip() or "N/A"
                _ct_neut    = str(_srow.get("seg_neutralizantes", "") or "").strip() or "N/A"
                _ct_obs     = str(_srow.get("seg_observaciones",  "") or "").strip()
                _ct_mj_raw  = str(_srow.get("muestras_json", "") or "").strip()
                try:
                    _ct_mj_data = json.loads(_ct_mj_raw) if _ct_mj_raw else []
                except Exception:
                    _ct_mj_data = []
                _ct_is_multi = bool(_ct_mj_data)
                if not _ct_is_multi:
                    _ct_mj_data = [{
                        "ID": _ct_id if _ct_id != "—" else "",
                        "_grasa": _ct_grasa, "_st": _ct_st,
                        "_ic": _ct_ic, "_agua": _ct_agua,
                        "_alcohol": _ct_alc, "_cloruros": _ct_clor,
                        "_neutralizantes": _ct_neut, "_obs": _ct_obs,
                    }]
                _ct_n_muestras = len(_ct_mj_data)
                _ct_header_sub = (f"{_ct_n_muestras} muestra(s)" if _ct_is_multi
                                  else f"{_ct_id}{f' — {_ct_nombre}' if _ct_nombre else ''}")
                st.markdown(
                    f"""<div style="background:#0056A3;border-radius:8px;padding:10px 16px;margin-bottom:14px;">
                          <span style="font-size:1rem;font-weight:700;color:#fff;letter-spacing:.05em;">🧪 DETALLE CONTRAMUESTRA</span>
                          <span style="font-size:.85rem;color:#cce0f5;margin-left:12px;">{_ct_header_sub} &nbsp;·&nbsp; {_ct_fecha}</span>
                        </div>""",
                    unsafe_allow_html=True,
                )
                _det_accion_ct = st.session_state.get("admin_accion")
                _det_idx_ct    = st.session_state.get("admin_idx")
                _edit_mode_ct  = (_det_accion_ct == "modificar" and _det_idx_ct == sel_orig_idx)

                if _edit_mode_ct:
                    try:
                        _fe_ct = datetime.strptime(str(_srow.get("fecha", "")), "%d/%m/%Y").date()
                    except Exception:
                        _fe_ct = date.today()
                    cta1, cta2 = st.columns(2)
                    _cte_fecha = cta1.date_input("📅 FECHA", value=_fe_ct, format="DD/MM/YYYY", key="edit_ct_fecha")
                    _cte_resp = cta2.text_input("👤 ENTREGADO POR", value=_ct_resp if _ct_resp != "—" else "", key="edit_ct_resp", on_change=convertir_a_mayusculas, args=("edit_ct_resp",))
                    st.markdown("<div style='font-size:11px;font-weight:700;color:#0056A3;letter-spacing:.05em;margin:10px 0 4px;'>🔬 MUESTRAS</div>", unsafe_allow_html=True)
                    st.caption("💡 Tab / → / Enter → siguiente celda · ← → anterior · Enter en última celda → guarda")
                    _CT_COLS = ["ID","_proveedor","_grasa","_st","_ic","_agua","_alcohol","_cloruros","_neutralizantes","_obs"]
                    _ct_cache_k = f"_ct_m_cache_{sel_orig_idx}"
                    _cat_ct_ed = load_catalogo()
                    _cat_ct_ed_m = dict(zip(_cat_ct_ed["codigo"], _cat_ct_ed["nombre"]))
                    if _ct_cache_k in st.session_state:
                        _df_ct_ed = st.session_state[_ct_cache_k].copy()
                    else:
                        _df_ct_ed = pd.DataFrame([{k: m.get(k, "") for k in _CT_COLS} for m in _ct_mj_data], columns=_CT_COLS)
                        for _nc in ["_grasa","_st","_ic","_agua"]:
                            _df_ct_ed[_nc] = pd.to_numeric(_df_ct_ed[_nc], errors="coerce")
                    _df_ct_ed["nombre_estacion"] = _df_ct_ed["ID"].apply(lambda c: _cat_ct_ed_m.get(str(c).strip(), "") if pd.notna(c) else "")
                    _tri_ct_de = ["N/A", "NEGATIVO (−)", "POSITIVO (+)"]
                    _edited_ct = st.data_editor(_df_ct_ed, num_rows="dynamic", width='stretch', key="edit_ct_de",
                        column_config={
                            "ID":              st.column_config.TextColumn("CÓDIGO"),
                            "nombre_estacion": st.column_config.TextColumn("NOMBRE", disabled=True),
                            "_proveedor":      st.column_config.TextColumn("PROVEEDOR"),
                            "_grasa":          st.column_config.NumberColumn("GRASA (%)",  format="%.2f", min_value=0.0, max_value=100.0),
                            "_st":             st.column_config.NumberColumn("ST (%)",     format="%.2f", min_value=0.0, max_value=100.0),
                            "_ic":             st.column_config.NumberColumn("IC (°C)",    format="%.3f"),
                            "_agua":           st.column_config.NumberColumn("AGUA (%)",   format="%.2f", min_value=0.0, max_value=100.0),
                            "_alcohol":        st.column_config.SelectboxColumn("ALCOHOL",        options=_tri_ct_de, required=True),
                            "_cloruros":       st.column_config.SelectboxColumn("CLORUROS",       options=_tri_ct_de, required=True),
                            "_neutralizantes": st.column_config.SelectboxColumn("NEUT.",           options=_tri_ct_de, required=True),
                            "_obs":            st.column_config.TextColumn("OBS"),
                        }, hide_index=True)
                    _ct_prev_ids = list(_df_ct_ed["ID"].fillna("").astype(str))
                    _ct_new_ids  = list(_edited_ct["ID"].fillna("").astype(str))
                    _ct_save_df  = _edited_ct.drop(columns=["nombre_estacion"], errors="ignore").copy()
                    st.session_state[_ct_cache_k] = _ct_save_df
                    if _ct_prev_ids != _ct_new_ids:
                        st.rerun()
                    activar_siguiente_con_enter()
                    ct_s1, ct_s2, _ = st.columns([1.5, 1, 3])
                    with ct_s1:
                        if st.button("💾 GUARDAR CAMBIOS", type="primary", width='stretch', key="btn_save_edit_ct"):
                            def _pf_ct(v, d=0.0):
                                try: return float(str(v).replace(",","."))
                                except: return d
                            _new_ct_ms = []
                            for _, _ctrow in _ct_save_df.iterrows():
                                _new_ct_ms.append({
                                    "ID": str(_ctrow.get("ID","") or "").upper().strip(),
                                    "_proveedor":      str(_ctrow.get("_proveedor","") or "").upper().strip(),
                                    "_grasa":          round(_pf_ct(_ctrow.get("_grasa",0)), 2),
                                    "_st":             round(_pf_ct(_ctrow.get("_st",0)), 2),
                                    "_ic":             round(_pf_ct(_ctrow.get("_ic",-0.530) or -0.530), 3),
                                    "_agua":           round(_pf_ct(_ctrow.get("_agua",0)), 2),
                                    "_alcohol":        str(_ctrow.get("_alcohol","N/A") or "N/A"),
                                    "_cloruros":       str(_ctrow.get("_cloruros","N/A") or "N/A"),
                                    "_neutralizantes": str(_ctrow.get("_neutralizantes","N/A") or "N/A"),
                                    "_obs":            str(_ctrow.get("_obs","") or ""),
                                })
                            update_seg_row_in_csv(sel_orig_idx, {
                                "fecha":           _cte_fecha.strftime("%d/%m/%Y"),
                                "seg_responsable": str(_cte_resp).upper().strip(),
                                "seg_id_muestra":  _new_ct_ms[0].get("ID","") if _new_ct_ms else "",
                                "muestras_json":   json.dumps(_new_ct_ms, ensure_ascii=False),
                            })
                            st.session_state.pop(_ct_cache_k, None)
                            st.session_state.admin_accion = None
                            st.session_state.admin_idx    = None
                            st.rerun()
                    with ct_s2:
                        if st.button("✖ CANCELAR", width='stretch', key="btn_cancel_edit_ct"):
                            st.session_state.pop(_ct_cache_k, None)
                            st.session_state.admin_accion = None
                            st.session_state.admin_idx    = None
                            st.rerun()
                else:
                    if _ct_resp and _ct_resp != "—":
                        st.markdown(f'<div style="font-size:.85rem;color:#555;margin-bottom:8px;"><b>Entregado por:</b> {_ct_resp}</div>', unsafe_allow_html=True)
                    _ct_view_rows = []
                    _RED_CT = "background-color:#FFC7CE;color:#9C0006;font-weight:700"
                    for _mv in _ct_mj_data:
                        def _pnv(x):
                            try:
                                s = str(x).strip()
                                return float(s.replace(",",".")) if s not in ("","None","nan") else None
                            except: return None
                        _cod_v = str(_mv.get("ID","") or "").strip()
                        _nom_v = _ct_cat_map.get(_cod_v, "")
                        _ct_view_rows.append({
                            "CÓDIGO": _cod_v, "NOMBRE ESTACIÓN": _nom_v,
                            "PROVEEDOR":  str(_mv.get("_proveedor","") or ""),
                            "GRASA (%)":  _pnv(_mv.get("_grasa")),
                            "ST (%)":     _pnv(_mv.get("_st")),
                            "PROT. (%)":  _pnv(_mv.get("_proteina")),
                            "IC (°C)":    _pnv(_mv.get("_ic")),
                            "AGUA (%)":   _pnv(_mv.get("_agua")),
                            "ALCOHOL":    str(_mv.get("_alcohol","N/A") or "N/A"),
                            "CLORUROS":   str(_mv.get("_cloruros","N/A") or "N/A"),
                            "NEUTRALIZANTES": str(_mv.get("_neutralizantes","N/A") or "N/A"),
                            "OBS":        str(_mv.get("_obs","") or ""),
                        })
                    if _ct_view_rows:
                        _df_ct_v = pd.DataFrame(_ct_view_rows)
                        def _color_ct_v(row):
                            styles = [""] * len(row)
                            cols = list(row.index)
                            try:
                                st_v = float(str(row.get("ST (%)", "")).replace(",","."))
                                if 0 < st_v < 12.60 and "ST (%)" in cols:
                                    styles[cols.index("ST (%)")] = _RED_CT
                            except: pass
                            try:
                                ic_v = float(str(row.get("IC (°C)", "")).replace(",","."))
                                if ic_v > -0.530 and "IC (°C)" in cols:
                                    styles[cols.index("IC (°C)")] = _RED_CT
                            except: pass
                            for _qc in ("ALCOHOL", "CLORUROS", "NEUTRALIZANTES"):
                                try:
                                    if row.get(_qc) == "POSITIVO (+)" and _qc in cols:
                                        styles[cols.index(_qc)] = _RED_CT
                                except: pass
                            return styles
                        _fmt_ct_v = {"GRASA (%)":"{:.2f}", "ST (%)":"{:.2f}", "PROT. (%)":"{:.2f}", "IC (°C)":"{:.3f}", "AGUA (%)":"{:.2f}"}
                        st.dataframe(_df_ct_v.style.apply(_color_ct_v, axis=1).format(_fmt_ct_v, na_rep="—"),
                            width='stretch', hide_index=True,
                            height=min(38+35*len(_ct_view_rows), 420),
                            column_config={
                                "CÓDIGO":          st.column_config.TextColumn("CÓDIGO",         width="small"),
                                "NOMBRE ESTACIÓN": st.column_config.TextColumn("NOMBRE ESTACIÓN",width="medium"),
                                "PROVEEDOR":       st.column_config.TextColumn("PROVEEDOR",      width="medium"),
                                "GRASA (%)":       st.column_config.NumberColumn("GRASA (%)",     width="small", format="%.2f"),
                                "ST (%)":          st.column_config.NumberColumn("ST (%)",        width="small", format="%.2f"),
                                "PROT. (%)":       st.column_config.NumberColumn("PROT. (%)",     width="small", format="%.2f"),
                                "IC (°C)":         st.column_config.NumberColumn("IC (°C)",       width="small", format="%.3f"),
                                "AGUA (%)":        st.column_config.NumberColumn("AGUA (%)",      width="small", format="%.2f"),
                                "ALCOHOL":         st.column_config.TextColumn("ALC.",            width="small"),
                                "CLORUROS":        st.column_config.TextColumn("CLOR.",           width="small"),
                                "NEUTRALIZANTES":  st.column_config.TextColumn("NEUT.",           width="small"),
                                "OBS":             st.column_config.TextColumn("OBSERVACIONES",   width="medium"),
                            })

                    _ct_fotos_raw = str(_srow.get("fotos_json", "") or "").strip()
                    if _ct_fotos_raw and _ct_fotos_raw not in ("[]", ""):
                        try:
                            _ct_fotos_list = json.loads(_ct_fotos_raw)
                        except Exception:
                            _ct_fotos_list = []
                        _ct_fotos_urls = [(_p, get_image_url(_p)) for _p in _ct_fotos_list if _p]
                        _ct_fotos_urls = [(p, u) for p, u in _ct_fotos_urls if u]
                        if _ct_fotos_urls:
                            st.markdown(
                                "<div style='font-size:11px;font-weight:700;color:#0056A3;"
                                "letter-spacing:.05em;margin:12px 0 6px;'>"
                                "📷 IMÁGENES DE MUESTRAS</div>",
                                unsafe_allow_html=True,
                            )
                            _ct_cols_f = st.columns(min(len(_ct_fotos_urls), 4))
                            for _cfi, (_cfp, _cfurl) in enumerate(_ct_fotos_urls):
                                with _ct_cols_f[_cfi % 4]:
                                    st.image(_cfurl, width='stretch')

        if (sel_orig_idx is not None and filtro_tipo in ("RUTAS", "TODOS", "TRANSUIZA")
                and st.session_state.hist_buscar_ok):
            if sel_orig_idx in df_filtrado.index:
                _drow = df_filtrado.loc[sel_orig_idx]
            else:
                _df_all = load_historial()
                _drow   = (_df_all.loc[sel_orig_idx] if sel_orig_idx in _df_all.index else {})
            _tipo_reg = str(_drow.get("tipo_seguimiento", "RUTAS")).strip()
            _d_nombre = str(_drow.get("ruta", "")).strip() or "—"
            _d_fecha  = str(_drow.get("fecha", "")).strip() or "—"
            _d_placa  = str(_drow.get("placa",     "")).strip() or "—"
            _d_cond   = str(_drow.get("conductor", "")).strip() or "—"
            _d_vold   = _drow.get("volumen_declarado", "")
            _d_vole   = _drow.get("vol_estaciones",    "")
            _d_dif    = _drow.get("diferencia",        "")
            _d_st     = _drow.get("solidos_ruta",      "")
            _d_ic     = _drow.get("crioscopia_ruta",   "")
            _d_stpond = _drow.get("st_pond",           "")
            _d_icpond = _drow.get("ic_pond",           "")
            _d_nest   = _drow.get("num_estaciones",    "")
            _d_st_car = _drow.get("st_carrotanque",   "")
            _d_grasa  = _drow.get("grasa_muestra",    "")
            _d_prot   = _drow.get("proteina_muestra", "")
            _d_dif_s  = _drow.get("diferencia_solidos","")

            st.markdown("---")
            _panel_titulo = "🔍 DETALLE TRANSUIZA" if _tipo_reg == "TRANSUIZA" else "🔍 DETALLE DE RUTA"
            st.markdown(
                f"""<div style="background:#0056A3;border-radius:8px;padding:10px 16px;margin-bottom:14px;">
                      <span style="font-size:1rem;font-weight:700;color:#fff;letter-spacing:.05em;">{_panel_titulo}</span>
                      <span style="font-size:.85rem;color:#cce0f5;margin-left:12px;">{_d_placa} &nbsp;·&nbsp; {_d_fecha}</span>
                    </div>""",
                unsafe_allow_html=True,
            )
            _det_accion = st.session_state.get("admin_accion")
            _det_idx    = st.session_state.get("admin_idx")
            _edit_mode  = (_det_accion == "modificar" and _det_idx == sel_orig_idx)

            if _edit_mode:
                try:
                    _fe_orig = datetime.strptime(str(_drow.get("fecha", "")), "%d/%m/%Y").date()
                except Exception:
                    _fe_orig = date.today()

                if _tipo_reg == "TRANSUIZA":
                    try:    _stcar_orig = float(str(_d_st_car or 0).replace(",","."))
                    except: _stcar_orig = 0.0
                    try:    _grasa_orig = float(str(_d_grasa or 0).replace(",","."))
                    except: _grasa_orig = 0.0
                    try:    _stm_orig   = float(str(_d_st or 0).replace(",","."))
                    except: _stm_orig   = 0.0
                    try:    _prot_orig  = float(str(_d_prot or 0).replace(",","."))
                    except: _prot_orig  = 0.0
                    te1, te2 = st.columns(2)
                    with te1:
                        _te_fecha = st.date_input("FECHA", value=_fe_orig, format="DD/MM/YYYY", key="edit_t_fecha")
                        _te_placa = st.text_input("PLACA", value=_d_placa, key="edit_t_placa")
                        _te_stcar = st.number_input("ST DEL CARROTANQUE (%)", value=_stcar_orig, min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key="edit_t_stcar")
                    with te2:
                        _te_grasa = st.number_input("GRASA (%)", value=_grasa_orig, min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key="edit_t_grasa")
                        _te_stm   = st.number_input("ST MUESTRA (%)", value=_stm_orig, min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key="edit_t_stm")
                        _te_prot  = st.number_input("PROTEÍNA (%)", value=_prot_orig, min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key="edit_t_prot")
                    _te_dif = round(_te_stcar - _te_stm, 2)
                    _dif_col = "#9C0006" if abs(_te_dif) > 0.5 else "#006100"
                    st.markdown(f"<div style='text-align:center;padding:8px;background:#F8FAFC;border-radius:8px;border:1px solid #D1D5DB;'><div style='font-size:11px;font-weight:600;color:#6B7280;'>DIFERENCIA DE SÓLIDOS</div><div style='font-size:1.5rem;font-weight:800;color:{_dif_col};'>{_te_dif:+.2f} %</div></div>", unsafe_allow_html=True)
                    tec1, tec2, _ = st.columns([1.5, 1, 3])
                    with tec1:
                        if st.button("💾 GUARDAR CAMBIOS", type="primary", key="btn_save_edit_t", width='stretch'):
                            update_row_in_csv(_det_idx, {
                                "fecha":              _te_fecha.strftime("%d/%m/%Y"),
                                "placa":              str(_te_placa).upper(),
                                "st_carrotanque":     round(float(_te_stcar), 2),
                                "solidos_ruta":       round(float(_te_stm), 2),
                                "grasa_muestra":      round(float(_te_grasa), 2),
                                "proteina_muestra":   round(float(_te_prot), 2),
                                "diferencia_solidos": _te_dif,
                            })
                            st.session_state.admin_accion = None
                            st.session_state.admin_idx    = None
                            st.rerun()
                    with tec2:
                        if st.button("✖ CANCELAR", key="btn_cancel_edit_t", width='stretch'):
                            st.session_state.admin_accion = None
                            st.session_state.admin_idx    = None
                            st.rerun()

                else:
                    try:    _vol_orig = int(float(str(_drow.get("volumen_declarado", 0) or 0)))
                    except: _vol_orig = 0
                    try:    _st_orig  = float(str(_drow.get("solidos_ruta", "0") or 0).replace(",", "."))
                    except: _st_orig  = 0.0
                    try:    _ic_orig  = float(str(_drow.get("crioscopia_ruta", "0") or 0).replace(",", "."))
                    except: _ic_orig  = 0.0
                    ef1, ef2 = st.columns(2)
                    with ef1:
                        _e_fecha = st.date_input("FECHA", value=_fe_orig, format="DD/MM/YYYY", key="edit_fecha")
                        _e_ruta  = st.text_input("RUTA", value=str(_drow.get("ruta", "")), key="edit_ruta")
                        _e_placa = st.text_input("PLACA", value=str(_drow.get("placa", "")), key="edit_placa")
                        _e_cond  = st.text_input("CONDUCTOR", value=str(_drow.get("conductor", "")), key="edit_cond")
                    with ef2:
                        _e_vol = st.number_input("VOLUMEN DECLARADO (L)", value=_vol_orig, min_value=0, step=1, key="edit_vol")
                        _e_st  = st.number_input("ST RUTA (%)", value=_st_orig, step=0.01, format="%.2f", key="edit_st")
                        _e_ic  = st.number_input("IC RUTA (°C)", value=_ic_orig, step=0.001, format="%.3f", key="edit_ic")
                    st.markdown("<div style='font-weight:700;color:#0056A3;margin:12px 0 6px;font-size:.9rem;border-left:4px solid #0056A3;padding-left:8px;'>🏭 Estaciones</div>", unsafe_allow_html=True)
                    _ECOLS_E = ["codigo", "grasa", "solidos", "proteina", "crioscopia", "agua_pct", "volumen", "alcohol", "cloruros", "neutralizantes", "obs"]
                    _est_json_e = str(_drow.get("estaciones_json", "") or "").strip()
                    try:    _est_data_e = json.loads(_est_json_e) if _est_json_e else []
                    except: _est_data_e = []
                    _h_cache_key = f"_h_est_cache_{st.session_state.get('admin_idx', 0)}"
                    _cat_h = load_catalogo()
                    _cat_h_map = dict(zip(_cat_h["codigo"], _cat_h["nombre"]))
                    if _h_cache_key in st.session_state:
                        _df_est_e = st.session_state[_h_cache_key].copy()
                    else:
                        _df_est_e = (pd.DataFrame(_est_data_e, columns=_ECOLS_E) if _est_data_e else pd.DataFrame(columns=_ECOLS_E))
                        for _nc in ["grasa", "solidos", "proteina", "agua_pct"]:
                            _df_est_e[_nc] = pd.to_numeric(_df_est_e[_nc], errors="coerce")
                        _df_est_e["volumen"] = pd.to_numeric(_df_est_e["volumen"], errors="coerce")
                    _df_est_e["nombre_estacion"] = _df_est_e["codigo"].apply(lambda c: _cat_h_map.get(str(c).strip(), "") if pd.notna(c) else "")
                    st.caption("💡 Tab / → / Enter → siguiente celda · ← → anterior · Enter en última celda → guarda")
                    _edited_df_e = st.data_editor(_df_est_e, num_rows="dynamic", width='stretch', key="edit_est_editor",
                        column_config={
                            "codigo":          st.column_config.TextColumn("CÓDIGO"),
                            "grasa":           st.column_config.NumberColumn("GRASA (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "solidos":         st.column_config.NumberColumn("SÓL.TOT. (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "proteina":        st.column_config.NumberColumn("PROTEÍNA (%)", format="%.2f", min_value=0.0, max_value=100.0),
                            "crioscopia":      st.column_config.TextColumn("CRIOSCOPIA (°C)"),
                            "volumen":         st.column_config.NumberColumn("VOLUMEN (L)", format="%.0f", min_value=0, step=1),
                            "alcohol":         st.column_config.SelectboxColumn("ALCOHOL", options=["N/A", "+", "-"], required=True),
                            "cloruros":        st.column_config.SelectboxColumn("CLORUROS", options=["N/A", "+", "-"], required=True),
                            "neutralizantes":  st.column_config.SelectboxColumn("NEUTRALIZANTES", options=["N/A", "+", "-"], required=True),
                            "agua_pct":        st.column_config.NumberColumn("% AGUA", format="%.1f", min_value=0.0, max_value=100.0),
                            "obs":             st.column_config.TextColumn("OBSERVACIONES"),
                            "nombre_estacion": st.column_config.TextColumn("NOMBRE ESTACIÓN", disabled=True),
                        }, hide_index=True)
                    _h_prev_codes = list(_df_est_e["codigo"].fillna("").astype(str).str.strip())
                    _h_new_codes  = list(_edited_df_e["codigo"].fillna("").astype(str).str.strip())
                    _cache_df = _edited_df_e.drop(columns=["nombre_estacion"], errors="ignore").copy()
                    st.session_state[_h_cache_key] = _cache_df
                    if _h_prev_codes != _h_new_codes:
                        st.rerun()

                    def _sanitize_est_df(df):
                        df = df.copy()
                        if "codigo" in df.columns:
                            df["codigo"] = (df["codigo"].fillna("").astype(str).str.strip().str.upper()
                                            .apply(lambda x: re.sub(r"[^A-Z0-9ÁÉÍÓÚÑ\-/]", "", x)))
                        if "obs" in df.columns:
                            df["obs"] = df["obs"].fillna("").astype(str).str.strip().str.upper()
                        if "crioscopia" in df.columns:
                            df["crioscopia"] = df["crioscopia"].fillna("").astype(str).str.strip()
                        return df

                    _clean_df = _sanitize_est_df(_edited_df_e)
                    _est_records = []
                    for _, _er in _clean_df.iterrows():
                        _rec = {}
                        for _ck in _clean_df.columns:
                            if _ck == "nombre_estacion":
                                continue
                            _v = _er[_ck]
                            try:
                                if pd.isna(_v):
                                    _rec[_ck] = None
                                elif _ck == "volumen":
                                    _rec[_ck] = int(float(_v))
                                elif hasattr(_v, "item"):
                                    _rec[_ck] = _v.item()
                                else:
                                    _rec[_ck] = _v
                            except (TypeError, ValueError):
                                _rec[_ck] = str(_v) if _v is not None else None
                        _est_records.append(_rec)
                    _edited_est_json = json.dumps(_est_records, ensure_ascii=False)

                    _e_vols_p, _e_sum_st, _e_sum_ic = [], [], []
                    for _er2 in _est_records:
                        try:   _ev2 = float(_er2.get("volumen") or 0)
                        except: _ev2 = 0.0
                        try:   _es2 = float(str(_er2.get("solidos","") or "").replace(",","."))
                        except: _es2 = None
                        try:
                            _ec2_raw = str(_er2.get("crioscopia","") or "").strip()
                            _ec2 = float(_ec2_raw.replace(",",".")) if _ec2_raw else None
                        except Exception: _ec2 = None
                        if _ev2 > 0:
                            _e_vols_p.append(_ev2)
                            if _es2 is not None: _e_sum_st.append(_ev2 * _es2)
                            if _ec2 is not None: _e_sum_ic.append(_ev2 * _ec2)
                    _e_vol_total  = sum(_e_vols_p)
                    _e_vol_ests   = int(_e_vol_total) if _e_vol_total else 0
                    _e_diferencia = int(_e_vol) - _e_vol_ests
                    _e_st_pond    = round(sum(_e_sum_st)/_e_vol_total,2) if _e_vol_total and _e_sum_st else ""
                    _e_ic_pond    = round(sum(_e_sum_ic)/_e_vol_total,3) if _e_vol_total and _e_sum_ic else ""

                    ec1, ec2, _ = st.columns([1.5, 1, 3])
                    with ec1:
                        if st.button("💾 GUARDAR CAMBIOS", type="primary", key="btn_save_edit", width='stretch'):
                            try:    _ests_cnt = len(json.loads(_edited_est_json) or [])
                            except: _ests_cnt = 0
                            update_row_in_csv(_det_idx, {
                                "fecha":             _e_fecha.strftime("%d/%m/%Y"),
                                "ruta":              str(_e_ruta).upper(),
                                "placa":             str(_e_placa).upper(),
                                "conductor":         str(_e_cond).upper(),
                                "volumen_declarado": int(_e_vol),
                                "solidos_ruta":      round(float(_e_st), 2),
                                "crioscopia_ruta":   round(float(_e_ic), 3),
                                "vol_estaciones":    _e_vol_ests,
                                "diferencia":        _e_diferencia,
                                "st_pond":           _e_st_pond,
                                "ic_pond":           _e_ic_pond,
                                "estaciones_json":   _edited_est_json,
                                "num_estaciones":    _ests_cnt,
                            })
                            st.session_state.pop(f"_h_est_cache_{st.session_state.get('admin_idx', 0)}", None)
                            st.session_state.admin_accion = None
                            st.session_state.admin_idx    = None
                            st.rerun()
                    with ec2:
                        if st.button("✖ CANCELAR", key="btn_cancel_edit", width='stretch'):
                            st.session_state.pop(f"_h_est_cache_{st.session_state.get('admin_idx', 0)}", None)
                            st.session_state.admin_accion = None
                            st.session_state.admin_idx    = None
                            st.rerun()

            if not _edit_mode:
                def _kpi_card(label, value, badge=None, badge_ok=True):
                    badge_html = ""
                    if badge:
                        bg = "#D4EDDA" if badge_ok else "#F8D7DA"
                        col = "#155724" if badge_ok else "#721C24"
                        badge_html = (f'<div style="margin-top:4px;font-size:.65rem;font-weight:700;color:{col};background:{bg};border-radius:4px;padding:1px 5px;display:inline-block;">{badge}</div>')
                    return (f'<div style="background:#fff;border:1px solid #dde6f0;border-radius:8px;padding:10px 12px;text-align:center;height:100%;"><div style="font-size:.62rem;font-weight:700;color:#6c8ca8;letter-spacing:.06em;margin-bottom:4px;">{label}</div><div style="font-size:1.05rem;font-weight:800;color:#0056A3;">{value}</div>{badge_html}</div>')

                if _tipo_reg == "TRANSUIZA":
                    try:    _v_stcar  = f"{float(_d_st_car):.2f} %"
                    except: _v_stcar  = "—"
                    try:    _v_grasa  = f"{float(_d_grasa):.2f} %"
                    except: _v_grasa  = "—"
                    try:    _v_stm    = f"{float(_d_st):.2f} %"
                    except: _v_stm    = "—"
                    try:    _v_prot   = f"{float(_d_prot):.2f} %"
                    except: _v_prot   = "—"
                    try:
                        _dif_s_v = float(_d_dif_s)
                        _dif_s_ok = abs(_dif_s_v) <= 0.5
                        _v_difs   = f"{_dif_s_v:+.2f} %"
                        _b_difs   = ("✔ OK" if _dif_s_ok else "⚠ ALERTA", _dif_s_ok)
                    except:
                        _v_difs = "—"; _b_difs = (None, True)
                    _tr1 = ('<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px;">'
                            + _kpi_card("PLACA", _d_placa)
                            + _kpi_card("FECHA", _d_fecha)
                            + _kpi_card("ST CARROTANQUE (%)", _v_stcar)
                            + _kpi_card("ST MUESTRA (%)", _v_stm)
                            + _kpi_card("DIF. SÓLIDOS", _v_difs, _b_difs[0], _b_difs[1])
                            + '</div>')
                    _tr2 = ('<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:8px;">'
                            + _kpi_card("GRASA (%)", _v_grasa)
                            + _kpi_card("PROTEÍNA (%)", _v_prot)
                            + '</div>')
                    st.markdown(_tr1 + _tr2, unsafe_allow_html=True)
                else:
                    try:    _v_vd  = f"{int(float(_d_vold)):,} L"
                    except: _v_vd  = "—"
                    try:    _v_ve  = f"{int(float(_d_vole)):,} L"
                    except: _v_ve  = "—"
                    try:
                        _dif_v = int(float(_d_dif))
                        _dif_ok = abs(_dif_v) <= 20
                        _v_dif  = f"{_dif_v:+,} L"
                        _b_dif  = ("✔ OK" if _dif_ok else "⚠ DIFER.", _dif_ok)
                    except:
                        _v_dif = "—"; _b_dif = (None, True)
                    try:
                        _st_v = float(str(_d_st).replace(",","."))
                        _v_st = f"{_st_v:.2f} %"
                        _b_st = ("✔ CONFORME" if _st_v >= 12.60 else "✖ DESVIACIÓN", _st_v >= 12.60)
                    except:
                        _v_st = "—"; _b_st = (None, True)
                    try:
                        _ic_v = float(str(_d_ic).replace(",","."))
                        _v_ic = f"{_ic_v:.3f} °C"
                        _ic_ok = -0.550 <= _ic_v <= -0.530
                        _b_ic = ("✔ CONFORME" if _ic_ok else "✖ DESVIACIÓN", _ic_ok)
                    except:
                        _v_ic = "—"; _b_ic = (None, True)
                    try:    _v_stp = f"{float(_d_stpond):.2f} %"
                    except: _v_stp = "—"
                    try:    _v_icp = f"{float(_d_icpond):.3f} °C"
                    except: _v_icp = "—"
                    try:    _v_ne  = str(int(float(_d_nest)))
                    except: _v_ne  = "—"

                    _r1 = ('<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">'
                           + _kpi_card("RUTA", _d_nombre[:24]+"…" if len(_d_nombre)>24 else _d_nombre)
                           + _kpi_card("PLACA", _d_placa)
                           + _kpi_card("CONDUCTOR", _d_cond[:18]+"…" if len(_d_cond)>18 else _d_cond)
                           + _kpi_card("Nº ESTACIONES", _v_ne)
                           + '</div>')
                    _r2 = ('<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px;">'
                           + _kpi_card("VOL. DECLARADO", _v_vd)
                           + _kpi_card("VOL. ESTACIONES", _v_ve)
                           + _kpi_card("DIFERENCIA", _v_dif, _b_dif[0], _b_dif[1])
                           + _kpi_card("ST RUTA (%)", _v_st, _b_st[0], _b_st[1])
                           + _kpi_card("IC RUTA (°C)", _v_ic, _b_ic[0], _b_ic[1])
                           + '</div>')
                    _r3 = ('<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:8px;">'
                           + _kpi_card("ST PONDERADO (%)", _v_stp)
                           + _kpi_card("IC PONDERADO (°C)", _v_icp)
                           + '</div>')
                    st.markdown(_r1 + _r2 + _r3, unsafe_allow_html=True)

                    _det_json_raw = str(_drow.get("estaciones_json", "") or "").strip()
                    if _det_json_raw and _det_json_raw not in ("[]", ""):
                        try:
                            _det_rows = json.loads(_det_json_raw) if _det_json_raw else []
                        except Exception:
                            _det_rows = []
                        if _det_rows:
                            st.markdown("<div style='font-size:11px;font-weight:700;color:#0056A3;letter-spacing:.05em;margin:10px 0 6px;'>🏭 DETALLE DE ESTACIONES</div>", unsafe_allow_html=True)
                            try:
                                _cat_det = load_catalogo()
                                _cat_det_map = dict(zip(_cat_det["codigo"], _cat_det["nombre"]))
                                _RED_EST = "background-color:#FFC7CE;color:#9C0006;font-weight:700"
                                _det_vis = []
                                for _dr in _det_rows:
                                    _cod_d = str(_dr.get("codigo","") or "").strip()
                                    _nom_d = _cat_det_map.get(_cod_d, "")
                                    _agua_d_raw = _dr.get("agua_pct","")
                                    try:    _agua_d = float(str(_agua_d_raw).replace("+","").replace(",","."))
                                    except: _agua_d = None
                                    _crio_d_raw = str(_dr.get("crioscopia","") or "").strip()
                                    try:    _crio_d_f = float(_crio_d_raw.replace(",",".")) if _crio_d_raw else None
                                    except: _crio_d_f = None
                                    _det_vis.append({
                                        "CÓDIGO":           _cod_d,
                                        "NOMBRE ESTACIÓN":  _nom_d,
                                        "GRASA (%)":        _dr.get("grasa"),
                                        "SÓLIDOS TOT. (%)": _dr.get("solidos"),
                                        "PROTEÍNA (%)":     _dr.get("proteina"),
                                        "CRIOSCOPIA":       _crio_d_f,
                                        "AGUA (%)":         _agua_d,
                                        "VOLUMEN (L)":      int(_dr["volumen"]) if _dr.get("volumen") is not None else None,
                                        "ALC.":             str(_dr.get("alcohol","N/A") or "N/A"),
                                        "CLOR.":            str(_dr.get("cloruros","N/A") or "N/A"),
                                        "NEUT.":            str(_dr.get("neutralizantes","N/A") or "N/A"),
                                        "OBSERVACIONES":    str(_dr.get("obs","") or ""),
                                    })
                                _df_det = pd.DataFrame(_det_vis)
                                for _nc2 in ["GRASA (%)","SÓLIDOS TOT. (%)","PROTEÍNA (%)","CRIOSCOPIA","AGUA (%)","VOLUMEN (L)"]:
                                    if _nc2 in _df_det.columns:
                                        _df_det[_nc2] = pd.to_numeric(_df_det[_nc2], errors="coerce")

                                def _color_est(row):
                                    styles = [""] * len(row)
                                    cols = list(row.index)
                                    try:
                                        st_e = float(str(row.get("SÓLIDOS TOT. (%)","")).replace(",","."))
                                        if 0 < st_e < 12.60 and "SÓLIDOS TOT. (%)" in cols:
                                            styles[cols.index("SÓLIDOS TOT. (%)")] = _RED_EST
                                    except Exception: pass
                                    try:
                                        ic_e = float(str(row.get("CRIOSCOPIA","")).replace(",","."))
                                        if ic_e > -0.530 and "CRIOSCOPIA" in cols:
                                            styles[cols.index("CRIOSCOPIA")] = _RED_EST
                                    except Exception: pass
                                    try:
                                        ag_e = float(str(row.get("AGUA (%)","")).replace("+","").replace(",","."))
                                        if ag_e > 0 and "AGUA (%)" in cols:
                                            styles[cols.index("AGUA (%)")] = _RED_EST
                                    except Exception: pass
                                    for _qcol in ("ALC.", "CLOR.", "NEUT."):
                                        try:
                                            if row.get(_qcol) == "+" and _qcol in cols:
                                                styles[cols.index(_qcol)] = _RED_EST
                                        except Exception: pass
                                    return styles

                                _fmt_det = {"GRASA (%)":"{:.2f}", "SÓLIDOS TOT. (%)":"{:.2f}", "PROTEÍNA (%)":"{:.2f}", "CRIOSCOPIA":"{:.3f}", "AGUA (%)":"{:.1f}"}
                                st.dataframe(
                                    _df_det.style.apply(_color_est, axis=1).format(_fmt_det, na_rep="—"),
                                    width='stretch', hide_index=True,
                                    height=min(38+35*len(_det_rows), 420),
                                    column_config={
                                        "CÓDIGO":           st.column_config.TextColumn("CÓDIGO",         width="small"),
                                        "GRASA (%)":        st.column_config.NumberColumn("GRASA (%)",     width="small", format="%.2f"),
                                        "SÓLIDOS TOT. (%)": st.column_config.NumberColumn("ST (%)",        width="small", format="%.2f"),
                                        "PROTEÍNA (%)":     st.column_config.NumberColumn("PROT. (%)",     width="small", format="%.2f"),
                                        "CRIOSCOPIA":       st.column_config.NumberColumn("CRIOS.",        width="small", format="%.3f"),
                                        "AGUA (%)":         st.column_config.NumberColumn("AGUA (%)",      width="small", format="%.1f"),
                                        "VOLUMEN (L)":      st.column_config.NumberColumn("VOL. (L)",      width="small", format="%d"),
                                        "ALC.":             st.column_config.TextColumn("ALC.",            width="small"),
                                        "CLOR.":            st.column_config.TextColumn("CLOR.",           width="small"),
                                        "NEUT.":            st.column_config.TextColumn("NEUT.",           width="small"),
                                        "OBSERVACIONES":    st.column_config.TextColumn("OBSERVACIONES",   width="medium"),
                                    })
                            except Exception:
                                pass
                    else:
                        st.caption("Esta ruta no tiene datos de estaciones registrados.")

                _fotos_raw = str(_drow.get("fotos_json", "") or "").strip()
                if _fotos_raw and _fotos_raw not in ("[]", ""):
                    try:    _fotos_list = json.loads(_fotos_raw)
                    except: _fotos_list = []
                    _fotos_urls = [(_p, get_image_url(_p)) for _p in _fotos_list if _p]
                    _fotos_urls = [(p, u) for p, u in _fotos_urls if u]
                    if _fotos_urls:
                        st.markdown("<div style='font-size:11px;font-weight:700;color:#0056A3;letter-spacing:.05em;margin:10px 0 6px;'>📷 IMÁGENES DE MUESTRAS</div>", unsafe_allow_html=True)
                        _cols_fotos = st.columns(min(len(_fotos_urls), 4))
                        for _fi, (_fp, _furl) in enumerate(_fotos_urls):
                            with _cols_fotos[_fi % 4]:
                                st.image(_furl, width='stretch')

        accion_activa  = st.session_state.get("admin_accion")
        idx_activo     = st.session_state.get("admin_idx")
        _from_seg      = st.session_state.get("admin_from_seg", False)
        _tiene_indices = (idx_activo is not None or bool(st.session_state.get("admin_idxs")))
        if accion_activa == "eliminar" and _tiene_indices:
            with st.container(border=True):
                _idxs_del = st.session_state.get("admin_idxs") or ([idx_activo] if idx_activo is not None else [])
                n_del = len(_idxs_del)
                st.markdown(
                    f"<div style='font-weight:700;color:#9C0006;margin-bottom:4px;'>"
                    f"🗑️ ¿Confirmar eliminación de {'1 registro' if n_del == 1 else f'{n_del} registros'}?</div>",
                    unsafe_allow_html=True,
                )
                _df_src_del = load_seguimientos() if _from_seg else df_hist
                if n_del == 1 and idx_activo is not None:
                    row_a = _df_src_del.loc[idx_activo] if idx_activo in _df_src_del.index else {}
                    _lbl_extra = (
                        f"**Código:** {row_a.get('seg_codigo','')} &nbsp;·&nbsp; **Sub-tipo:** {row_a.get('sub_tipo_seguimiento','')}"
                        if _from_seg else
                        f"**Ruta:** {row_a.get('ruta','')} &nbsp;·&nbsp; **Placa:** {row_a.get('placa','')}"
                    )
                    st.markdown(f"**Fecha:** {row_a.get('fecha','')} &nbsp;·&nbsp; {_lbl_extra}")
                else:
                    for _di in _idxs_del:
                        if _di in _df_src_del.index:
                            _r = _df_src_del.loc[_di]
                            _r_extra = (
                                f"{_r.get('seg_codigo','')} / {_r.get('sub_tipo_seguimiento','')}"
                                if _from_seg else
                                f"{_r.get('ruta','')} / {_r.get('placa','')}"
                            )
                            st.markdown(f"· **{_r.get('fecha','')}** — {_r_extra}")
                dc1, dc2, _ = st.columns([1.5, 1, 3])
                with dc1:
                    if st.button("🗑️ CONFIRMAR", type="primary", key="btn_confirm_del", width='stretch'):
                        if _from_seg:
                            delete_seg_rows(_idxs_del)
                        else:
                            delete_rows_from_csv(_idxs_del)
                        st.session_state.admin_accion   = None
                        st.session_state.admin_idx      = None
                        st.session_state.admin_idxs     = []
                        st.session_state.admin_from_seg = False
                        st.rerun()
                with dc2:
                    if st.button("✖ CANCELAR", key="btn_cancel_del", width='stretch'):
                        st.session_state.admin_accion   = None
                        st.session_state.admin_idx      = None
                        st.session_state.admin_idxs     = []
                        st.session_state.admin_from_seg = False
                        st.rerun()
