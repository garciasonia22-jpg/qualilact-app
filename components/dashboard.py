import json
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_utils import load_historial, load_seguimientos
from utils.time_utils import now_col


def render_dashboard():
    _ST_MIN     = 12.60
    _IC_REF     = -0.530
    _TRANS_ALRT = 0.5
    _CLR_AZUL   = "#0056A3"
    _CLR_AZUL2  = "#3A7CC8"
    _CLR_ROJO   = "#EF4444"
    _CLR_VERDE  = "#10B981"
    _CLR_AMBAR  = "#F59E0B"
    _CLR_GRIS   = "#6B7280"
    _PLT_TMPL   = "plotly_white"

    def _sh(txt, icon=""):
        st.markdown(
            f"<div style='font-size:.93rem;font-weight:700;color:{_CLR_AZUL};"
            f"border-left:4px solid {_CLR_AZUL};padding-left:10px;"
            f"margin:16px 0 6px 0;letter-spacing:.02em'>{icon} {txt}</div>",
            unsafe_allow_html=True,
        )

    def _base_layout(fig, h=300, mb=60, mr=80):
        fig.update_layout(
            template=_PLT_TMPL, height=h,
            margin=dict(l=20, r=mr, t=34, b=mb),
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="Arial", size=11),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
        )
        return fig

    _df_raw     = load_historial()
    _df_seg_raw = load_seguimientos()
    _df_rutas   = _df_raw[_df_raw["tipo_seguimiento"] == "RUTAS"].copy()
    _df_trans   = _df_raw[_df_raw["tipo_seguimiento"] == "TRANSUIZA"].copy()

    for _df in [_df_rutas, _df_trans]:
        _df["_fecha_dt"] = pd.to_datetime(_df["fecha"], format="%d/%m/%Y", errors="coerce")
        for _c in ["solidos_ruta", "crioscopia_ruta", "st_carrotanque",
                   "diferencia_solidos", "volumen_declarado"]:
            if _c in _df.columns:
                _df[_c] = pd.to_numeric(_df[_c], errors="coerce")

    _df_rutas = _df_rutas.dropna(subset=["_fecha_dt"])
    _df_trans = _df_trans.dropna(subset=["_fecha_dt"])

    _estac_rows = []
    for _, _rrow in _df_rutas.iterrows():
        _js_raw = str(_rrow.get("estaciones_json", "") or "")
        if _js_raw.strip() in ("", "[]", "nan"):
            continue
        try:
            _est_list = json.loads(_js_raw)
        except Exception:
            continue
        for _e in _est_list:
            _cod = str(_e.get("codigo", "")).strip()
            if not _cod:
                continue
            _estac_rows.append({
                "_fecha_dt": _rrow["_fecha_dt"],
                "fecha":     _rrow["fecha"],
                "ruta":      _rrow.get("ruta", ""),
                "placa":     _rrow.get("placa", ""),
                "codigo":    _cod,
                "solidos":   pd.to_numeric(_e.get("solidos"), errors="coerce"),
                "crioscopia": pd.to_numeric(
                    str(_e.get("crioscopia", "")).replace(",", "."), errors="coerce"
                ),
            })

    _df_estac_ok = pd.DataFrame(_estac_rows) if _estac_rows else pd.DataFrame(
        columns=["_fecha_dt", "fecha", "ruta", "placa", "codigo", "solidos", "crioscopia"]
    )

    _hay_rutas = not _df_rutas.empty
    _hay_trans = not _df_trans.empty
    _hay_estac = not _df_estac_ok.empty

    _tab_r, _tab_e, _tab_t = st.tabs([
        "  📊  GESTIÓN DE RUTAS  ",
        "  🏠  ESTACIONES  ",
        "  🏭  AUDITORÍA TRANSUIZA  ",
    ])

    with _tab_r:
        if not _hay_rutas and not _hay_estac:
            st.info("No hay registros de RUTAS o ESTACIONES disponibles.")
        else:
            _sh("FILTROS", "🔎")
            _rf1, _rf2, _rf3, _rf4 = st.columns([1.5, 1.5, 2, 2])

            _r_f_min = _df_rutas["_fecha_dt"].min().date() if _hay_rutas else date.today()
            _r_f_max = _df_rutas["_fecha_dt"].max().date() if _hay_rutas else date.today()

            with _rf1:
                _r_desde = st.date_input("DESDE", value=_r_f_min,
                    min_value=_r_f_min, max_value=_r_f_max,
                    key="r_desde", format="DD/MM/YYYY")
            with _rf2:
                _r_hasta = st.date_input("HASTA", value=_r_f_max,
                    min_value=_r_f_min, max_value=_r_f_max,
                    key="r_hasta", format="DD/MM/YYYY")
            with _rf3:
                _r_ruta_opts = (
                    sorted(_df_rutas["ruta"].dropna().unique().tolist())
                    if _hay_rutas else []
                )
                _r_sel_rutas = st.multiselect("RUTA", _r_ruta_opts,
                    key="r_sel_rutas", placeholder="Todas las rutas")
            with _rf4:
                _r_placa_opts = (
                    sorted(_df_rutas["placa"].dropna().unique().tolist())
                    if _hay_rutas else []
                )
                _r_sel_placas = st.multiselect("PLACA", _r_placa_opts,
                    key="r_sel_placas", placeholder="Todas las placas")

            _dfr = _df_rutas[
                (_df_rutas["_fecha_dt"].dt.date >= _r_desde) &
                (_df_rutas["_fecha_dt"].dt.date <= _r_hasta)
            ].copy()
            if _r_sel_rutas:
                _dfr = _dfr[_dfr["ruta"].isin(_r_sel_rutas)]
            if _r_sel_placas:
                _dfr = _dfr[_dfr["placa"].isin(_r_sel_placas)]

            st.markdown("<hr style='border-color:#E5E7EB;margin:4px 0 10px;'>", unsafe_allow_html=True)

            if not _dfr.empty:
                _n_r    = len(_dfr)
                _avg_st = float(_dfr["solidos_ruta"].mean())
                _avg_ic = float(_dfr["crioscopia_ruta"].mean())
                _pct_st = (_dfr["solidos_ruta"] >= _ST_MIN).mean() * 100
                _pct_ic = (_dfr["crioscopia_ruta"] <= _IC_REF).mean() * 100
                _k1, _k2, _k3, _k4 = st.columns(4)
                _k1.metric("REGISTROS", str(_n_r))
                _k2.metric("ST PROM.", f"{_avg_st:.2f}%",
                    f"{'✔ OK' if _avg_st >= _ST_MIN else '⚠ BAJO'} — mín {_ST_MIN}%",
                    delta_color="off")
                _k3.metric("IC PROM.", f"{_avg_ic:.3f} °H",
                    f"{'✔ OK' if _avg_ic <= _IC_REF else '⚠ AGUA'} — ref {_IC_REF}",
                    delta_color="off")
                _k4.metric("CONF. ST/IC",
                    f"{_pct_st:.0f}% / {_pct_ic:.0f}%",
                    "ST conforme / IC conforme", delta_color="off")

            _sh("COMPORTAMIENTO POR RUTAS", "🚛")

            if _dfr.empty:
                st.info("Sin registros RUTAS para el período/filtros seleccionados.")
            else:
                _dfr_d = (
                    _dfr.groupby(_dfr["_fecha_dt"].dt.date)
                    .agg(st_avg=("solidos_ruta", "mean"),
                         ic_avg=("crioscopia_ruta", "mean"),
                         n=("solidos_ruta", "count"))
                    .reset_index().rename(columns={"_fecha_dt": "fecha"})
                )
                _dfr_d["fecha"] = pd.to_datetime(_dfr_d["fecha"])

                _tc1, _tc2 = st.columns(2)
                with _tc1:
                    _fig_r_st = go.Figure()
                    _fig_r_st.add_trace(go.Scatter(
                        x=_dfr_d["fecha"], y=_dfr_d["st_avg"],
                        mode="lines+markers", name="ST prom.",
                        line=dict(color=_CLR_AZUL, width=2),
                        marker=dict(size=7,
                            color=[_CLR_ROJO if v < _ST_MIN else _CLR_AZUL
                                   for v in _dfr_d["st_avg"]]),
                        hovertemplate="%{x|%d/%m/%Y}<br>ST: %{y:.2f}%<extra></extra>",
                    ))
                    _fig_r_st.add_hline(
                        y=_ST_MIN, line_dash="dash", line_color=_CLR_ROJO,
                        annotation_text=f"mín {_ST_MIN}%",
                        annotation_position="right",
                    )
                    _base_layout(_fig_r_st, h=270, mb=40, mr=80)
                    _fig_r_st.update_layout(
                        title=dict(text="TENDENCIA ST — RUTAS (%)",
                                   font=dict(size=12, color=_CLR_AZUL)),
                        yaxis_title="ST (%)", xaxis_title=None, showlegend=False,
                    )
                    st.plotly_chart(_fig_r_st, width='stretch')

                with _tc2:
                    _fig_r_ic = go.Figure()
                    _fig_r_ic.add_trace(go.Scatter(
                        x=_dfr_d["fecha"], y=_dfr_d["ic_avg"],
                        mode="lines+markers", name="IC prom.",
                        line=dict(color=_CLR_VERDE, width=2),
                        marker=dict(size=7,
                            color=[_CLR_ROJO if v > _IC_REF else _CLR_VERDE
                                   for v in _dfr_d["ic_avg"]]),
                        hovertemplate="%{x|%d/%m/%Y}<br>IC: %{y:.3f} °H<extra></extra>",
                    ))
                    _fig_r_ic.add_hline(
                        y=_IC_REF, line_dash="dash", line_color=_CLR_ROJO,
                        annotation_text=f"ref {_IC_REF} °H",
                        annotation_position="right",
                    )
                    _base_layout(_fig_r_ic, h=270, mb=40, mr=80)
                    _fig_r_ic.update_layout(
                        title=dict(text="TENDENCIA IC — RUTAS (°H)",
                                   font=dict(size=12, color=_CLR_AZUL)),
                        yaxis_title="IC (°H)", xaxis_title=None, showlegend=False,
                    )
                    st.plotly_chart(_fig_r_ic, width='stretch')

                _dfr_ruta = (
                    _dfr.groupby("ruta")
                    .agg(st_avg=("solidos_ruta", "mean"),
                         ic_avg=("crioscopia_ruta", "mean"),
                         n=("solidos_ruta", "count"))
                    .reset_index()
                    .sort_values("st_avg", ascending=False)
                )

                _fig_ruta_bar = go.Figure()
                _fig_ruta_bar.add_trace(go.Bar(
                    x=_dfr_ruta["ruta"],
                    y=_dfr_ruta["st_avg"],
                    name="ST prom. (%)",
                    marker_color=[
                        _CLR_ROJO if v < _ST_MIN else _CLR_AZUL
                        for v in _dfr_ruta["st_avg"]
                    ],
                    text=_dfr_ruta["st_avg"].round(2),
                    textposition="outside",
                    yaxis="y1",
                    hovertemplate="<b>%{x}</b><br>ST: %{y:.2f}%<extra></extra>",
                ))
                _fig_ruta_bar.add_trace(go.Scatter(
                    x=_dfr_ruta["ruta"],
                    y=_dfr_ruta["ic_avg"],
                    mode="lines+markers",
                    name="IC prom. (°H)",
                    line=dict(color=_CLR_AMBAR, width=2),
                    marker=dict(size=8, color=_CLR_AMBAR),
                    yaxis="y2",
                    hovertemplate="<b>%{x}</b><br>IC: %{y:.3f} °H<extra></extra>",
                ))
                _fig_ruta_bar.add_hline(
                    y=_ST_MIN, line_dash="dash", line_color=_CLR_ROJO,
                    annotation_text=f"ST mín {_ST_MIN}%",
                    annotation_position="right",
                )
                _base_layout(_fig_ruta_bar, h=320, mb=80, mr=100)
                _fig_ruta_bar.update_layout(
                    title=dict(text="ST E IC PROMEDIO POR RUTA",
                               font=dict(size=12, color=_CLR_AZUL)),
                    barmode="group",
                    xaxis=dict(tickangle=-30, title=None),
                    yaxis=dict(title="ST (%)", range=[11.5, 14.2]),
                    yaxis2=dict(title="IC (°H)", overlaying="y",
                                side="right", range=[-0.58, -0.49]),
                    legend=dict(orientation="h", yanchor="bottom",
                                y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(_fig_ruta_bar, width='stretch')

    with _tab_e:
        _sh("FILTROS", "🔎")
        _e_all_fechas = (
            _df_estac_ok["_fecha_dt"] if _hay_estac and not _df_estac_ok.empty
            else pd.Series(dtype="datetime64[ns]")
        )
        _e_f_min = _e_all_fechas.min().date() if not _e_all_fechas.empty else date.today()
        _e_f_max = _e_all_fechas.max().date() if not _e_all_fechas.empty else date.today()

        _ef1, _ef2, _ef3 = st.columns([1.5, 1.5, 3])
        with _ef1:
            _e_desde = st.date_input("DESDE", value=_e_f_min,
                min_value=_e_f_min, max_value=_e_f_max,
                key="e_desde", format="DD/MM/YYYY")
        with _ef2:
            _e_hasta = st.date_input("HASTA", value=_e_f_max,
                min_value=_e_f_min, max_value=_e_f_max,
                key="e_hasta", format="DD/MM/YYYY")
        with _ef3:
            _e_ruta_opts = (
                sorted(_df_estac_ok["ruta"].dropna().unique().tolist())
                if _hay_estac else []
            )
            _e_sel_rutas = st.multiselect("RUTA", _e_ruta_opts,
                key="e_sel_rutas", placeholder="Todas las rutas")

        if not _hay_estac:
            st.info("No hay datos de estaciones disponibles.")
        else:
            _dfe_base = _df_estac_ok[
                (_df_estac_ok["_fecha_dt"].dt.date >= _e_desde) &
                (_df_estac_ok["_fecha_dt"].dt.date <= _e_hasta)
            ].copy()
            if _e_sel_rutas:
                _dfe_base = _dfe_base[_dfe_base["ruta"].isin(_e_sel_rutas)]

            _est_opts2 = sorted(
                _dfe_base["codigo"].dropna().astype(str).unique().tolist()
            ) if not _dfe_base.empty else []
            _sel_est2 = st.multiselect(
                "CÓDIGO DE ESTACIÓN", _est_opts2,
                key="e_sel_est", placeholder="Todas las estaciones"
            )
            if _sel_est2:
                _dfe_base = _dfe_base[_dfe_base["codigo"].astype(str).isin(_sel_est2)]

            st.markdown("<hr style='border-color:#E5E7EB;margin:4px 0 10px;'>", unsafe_allow_html=True)

            if _dfe_base.empty:
                st.warning("Sin datos para los filtros seleccionados.")
            else:
                _ne  = len(_dfe_base)
                _ast = _dfe_base["solidos"].mean()
                _aic = _dfe_base["crioscopia"].mean()
                _pst = (_dfe_base["solidos"] >= _ST_MIN).mean() * 100
                _ek1, _ek2, _ek3, _ek4 = st.columns(4)
                _ek1.metric("LECTURAS", str(_ne))
                _ek2.metric("ST PROM.", f"{_ast:.2f}%",
                    f"{'✔ OK' if _ast >= _ST_MIN else '⚠ BAJO'} — mín {_ST_MIN}%",
                    delta_color="off")
                _ek3.metric("IC PROM.", f"{_aic:.3f} °H",
                    f"{'✔ OK' if _aic <= _IC_REF else '⚠ AGUA'} — ref {_IC_REF}",
                    delta_color="off")
                _ek4.metric("CONF. ST", f"{_pst:.0f}%",
                    "Lecturas ≥ 12.60%", delta_color="off")

                _dfe_base["Estación"] = _dfe_base["codigo"].astype(str)

                _sh("SÓLIDOS TOTALES POR ESTACIÓN", "📈")
                _fig_est_st2 = go.Figure()
                for _cod in sorted(_dfe_base["Estación"].unique()):
                    _sub = (_dfe_base[_dfe_base["Estación"] == _cod].sort_values("_fecha_dt"))
                    _fig_est_st2.add_trace(go.Scatter(
                        x=_sub["_fecha_dt"], y=_sub["solidos"],
                        mode="lines+markers", name=f"Est. {_cod}",
                        hovertemplate=(
                            f"<b>Estación {_cod}</b><br>"
                            "Fecha: %{x|%d/%m/%Y}<br>"
                            "ST: %{y:.2f}%<extra></extra>"
                        ),
                    ))
                _fig_est_st2.add_hline(
                    y=_ST_MIN, line_dash="dash", line_color=_CLR_ROJO,
                    annotation_text=f"mín {_ST_MIN}%",
                    annotation_position="right",
                )
                _base_layout(_fig_est_st2, h=310, mb=40, mr=80)
                _fig_est_st2.update_layout(yaxis_title="ST (%)", xaxis_title=None)
                st.plotly_chart(_fig_est_st2, width='stretch')

                _sh("CRIOSCOPIA POR ESTACIÓN", "🌡️")
                _fig_est_ic2 = go.Figure()
                for _cod in sorted(_dfe_base["Estación"].unique()):
                    _sub = (_dfe_base[_dfe_base["Estación"] == _cod].sort_values("_fecha_dt"))
                    _fig_est_ic2.add_trace(go.Scatter(
                        x=_sub["_fecha_dt"], y=_sub["crioscopia"],
                        mode="lines+markers", name=f"Est. {_cod}",
                        hovertemplate=(
                            f"<b>Estación {_cod}</b><br>"
                            "Fecha: %{x|%d/%m/%Y}<br>"
                            "IC: %{y:.3f} °H<extra></extra>"
                        ),
                    ))
                _fig_est_ic2.add_hline(
                    y=_IC_REF, line_dash="dash", line_color=_CLR_ROJO,
                    annotation_text=f"ref {_IC_REF} °H",
                    annotation_position="right",
                )
                _base_layout(_fig_est_ic2, h=310, mb=40, mr=80)
                _fig_est_ic2.update_layout(yaxis_title="IC (°H)", xaxis_title=None)
                st.plotly_chart(_fig_est_ic2, width='stretch')

                _sh("RESUMEN POR ESTACIÓN", "📋")
                _df_est_agg = (
                    _dfe_base.groupby("codigo")
                    .agg(
                        lecturas   =("solidos",    "count"),
                        st_prom    =("solidos",    "mean"),
                        st_min     =("solidos",    "min"),
                        st_max     =("solidos",    "max"),
                        ic_prom    =("crioscopia", "mean"),
                        ic_min     =("crioscopia", "min"),
                        ic_max     =("crioscopia", "max"),
                    )
                    .reset_index()
                    .rename(columns={"codigo": "CÓDIGO"})
                )
                _df_est_agg["ST OK"] = (
                    _df_est_agg["st_prom"] >= _ST_MIN
                ).map({True: "✔", False: "✖"})
                _df_est_agg["IC OK"] = (
                    _df_est_agg["ic_prom"] <= _IC_REF
                ).map({True: "✔", False: "✖"})

                def _est_row_style(row):
                    if row["ST OK"] == "✖" or row["IC OK"] == "✖":
                        return ["background-color:#FEF2F2;color:#B91C1C"] * len(row)
                    return ["background-color:#F0FDF4;color:#15803D"] * len(row)

                st.dataframe(
                    _df_est_agg.style.apply(_est_row_style, axis=1)
                    .format({
                        "st_prom": "{:.2f}", "st_min": "{:.2f}", "st_max": "{:.2f}",
                        "ic_prom": "{:.3f}", "ic_min": "{:.3f}", "ic_max": "{:.3f}",
                    }),
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "CÓDIGO":   "CÓDIGO",
                        "lecturas": "LECTURAS",
                        "st_prom":  "ST PROM. (%)",
                        "st_min":   "ST MÍN. (%)",
                        "st_max":   "ST MÁX. (%)",
                        "ic_prom":  "IC PROM. (°H)",
                        "ic_min":   "IC MÍN. (°H)",
                        "ic_max":   "IC MÁX. (°H)",
                        "ST OK":    "ST ≥ 12.60",
                        "IC OK":    "IC ≤ −0.530",
                    },
                )

    with _tab_t:
        if not _hay_trans:
            st.info("No hay registros TRANSUIZA disponibles.")
        else:
            _sh("FILTRO DE FECHA", "📅")
            _t_f_min = _df_trans["_fecha_dt"].min().date()
            _t_f_max = _df_trans["_fecha_dt"].max().date()

            _tf1, _tf2 = st.columns([2, 2])
            with _tf1:
                _t_desde = st.date_input("DESDE", value=_t_f_min,
                    min_value=_t_f_min, max_value=_t_f_max,
                    key="t_desde", format="DD/MM/YYYY")
            with _tf2:
                _t_hasta = st.date_input("HASTA", value=_t_f_max,
                    min_value=_t_f_min, max_value=_t_f_max,
                    key="t_hasta", format="DD/MM/YYYY")

            _dft = _df_trans[
                (_df_trans["_fecha_dt"].dt.date >= _t_desde) &
                (_df_trans["_fecha_dt"].dt.date <= _t_hasta)
            ].copy()

            st.markdown("<hr style='border-color:#E5E7EB;margin:4px 0 10px;'>", unsafe_allow_html=True)

            if _dft.empty:
                st.warning("No hay datos TRANSUIZA para el período seleccionado.")
            else:
                _dft["ST MUESTRA (%)"]     = pd.to_numeric(_dft["solidos_ruta"],   errors="coerce")
                _dft["ST CARROTANQUE (%)"] = pd.to_numeric(_dft["st_carrotanque"], errors="coerce")
                _dft["DIFERENCIA (%)"]     = (
                    _dft["ST MUESTRA (%)"] - _dft["ST CARROTANQUE (%)"]
                ).abs().round(3)
                _dft["ALERTA"]  = _dft["DIFERENCIA (%)"] > _TRANS_ALRT
                _dft["_eje_x"]  = (
                    _dft["fecha"].astype(str) + " — " + _dft["placa"].fillna("").astype(str)
                )

                _kt1, _kt2, _kt3 = st.columns(3)
                _kt1.metric("REGISTROS TRANSUIZA", str(len(_dft)))
                _kt2.metric("ST MUESTRA PROM.", f"{_dft['ST MUESTRA (%)'].mean():.2f}%")
                _kt3.metric("ALERTAS DIFERENCIA",
                    str(int(_dft["ALERTA"].sum())),
                    f"Diferencia > {_TRANS_ALRT}%",
                    delta_color="inverse" if _dft["ALERTA"].any() else "off")

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

                _sh("ST MUESTRA vs. ST CARROTANQUE", "📊")

                _fig_t = go.Figure()
                _fig_t.add_trace(go.Bar(
                    name="ST MUESTRA (%)",
                    x=_dft["_eje_x"],
                    y=_dft["ST MUESTRA (%)"],
                    marker_color=_CLR_AZUL,
                    text=_dft["ST MUESTRA (%)"].round(2),
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>ST Muestra: %{y:.2f}%<extra></extra>",
                ))
                _fig_t.add_trace(go.Bar(
                    name="ST CARROTANQUE (%)",
                    x=_dft["_eje_x"],
                    y=_dft["ST CARROTANQUE (%)"],
                    marker_color=_CLR_AMBAR,
                    text=_dft["ST CARROTANQUE (%)"].round(2),
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>ST Carrotanque: %{y:.2f}%<extra></extra>",
                ))
                _fig_t.add_trace(go.Scatter(
                    x=_dft["_eje_x"],
                    y=_dft["DIFERENCIA (%)"],
                    mode="lines+markers",
                    name="DIFERENCIA (%)",
                    yaxis="y2",
                    line=dict(color=_CLR_ROJO, width=2, dash="dot"),
                    marker=dict(size=8,
                        color=[_CLR_ROJO if a else _CLR_GRIS for a in _dft["ALERTA"]]),
                    hovertemplate="<b>%{x}</b><br>Diferencia: %{y:.3f}%<extra></extra>",
                ))
                _fig_t.add_hline(
                    y=_ST_MIN, line_dash="dash", line_color=_CLR_ROJO,
                    annotation_text=f"ST mín {_ST_MIN}%",
                    annotation_position="right",
                )
                _base_layout(_fig_t, h=340, mb=80, mr=100)
                _fig_t.update_layout(
                    barmode="group",
                    xaxis=dict(tickangle=-35, title=None),
                    yaxis=dict(title="Sólidos Totales (%)", range=[11.0, 15.0]),
                    yaxis2=dict(title="Diferencia (%)", overlaying="y",
                                side="right", range=[0, 3], showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom",
                                y=1.02, xanchor="right", x=1),
                    title=dict(
                        text="COMPARACIÓN ST MUESTRA vs. CARROTANQUE POR REGISTRO",
                        font=dict(size=12, color=_CLR_AZUL),
                    ),
                )
                st.plotly_chart(_fig_t, width='stretch')

                _n_alt = int(_dft["ALERTA"].sum())
                if _n_alt > 0:
                    st.markdown(
                        f"<div style='background:#FEF2F2;border:1px solid #FECACA;"
                        f"border-radius:6px;padding:8px 14px;margin:6px 0;"
                        f"color:#B91C1C;font-weight:600;font-size:.88rem;'>"
                        f"⚠️ {_n_alt} registro(s) con diferencia ST &gt; {_TRANS_ALRT}%"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.success(f"✅ Ningún registro supera la diferencia límite de {_TRANS_ALRT}%.")

                _sh("DETALLE DE REGISTROS", "📋")
                _tbl = (
                    _dft[["fecha", "placa", "ST MUESTRA (%)",
                           "ST CARROTANQUE (%)", "DIFERENCIA (%)", "ALERTA"]]
                    .rename(columns={"fecha": "FECHA", "placa": "PLACA"})
                    .reset_index(drop=True)
                )

                def _style_alerta(row):
                    if _tbl.loc[row.name, "ALERTA"]:
                        return ["background-color:#FEE2E2;color:#B91C1C"] * len(row)
                    return [""] * len(row)

                st.dataframe(
                    _tbl.drop(columns=["ALERTA"])
                    .style.apply(_style_alerta, axis=1)
                    .format({"ST MUESTRA (%)": "{:.2f}",
                             "ST CARROTANQUE (%)": "{:.2f}",
                             "DIFERENCIA (%)": "{:.3f}"}),
                    width='stretch',
                    hide_index=True,
                    height=min(70 + len(_tbl) * 36, 380),
                )

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                _sh("REPORTE DE ALERTAS", "🚨")

                _rep_trans = _dft[
                    _dft["DIFERENCIA (%)"] > _TRANS_ALRT
                ][["fecha", "placa", "ST MUESTRA (%)",
                   "ST CARROTANQUE (%)", "DIFERENCIA (%)"]].copy()
                _rep_trans["TIPO ALERTA"] = (
                    "DIFERENCIA ST > " + str(_TRANS_ALRT) + "%"
                )
                _rep_trans.rename(columns={"fecha": "FECHA", "placa": "PLACA"}, inplace=True)

                _rep_ic = pd.DataFrame()
                if _hay_rutas and not _df_rutas.empty:
                    _dfr_ic = _df_rutas[
                        (_df_rutas["_fecha_dt"].dt.date >= _t_desde) &
                        (_df_rutas["_fecha_dt"].dt.date <= _t_hasta) &
                        (_df_rutas["crioscopia_ruta"] > _IC_REF)
                    ][["fecha", "ruta", "placa", "solidos_ruta", "crioscopia_ruta"]].copy()
                    if not _dfr_ic.empty:
                        _dfr_ic.rename(columns={
                            "fecha": "FECHA", "ruta": "RUTA", "placa": "PLACA",
                            "solidos_ruta": "ST MUESTRA (%)",
                            "crioscopia_ruta": "IC (°H)",
                        }, inplace=True)
                        _dfr_ic["TIPO ALERTA"] = "IC FUERA DE RANGO (> " + str(_IC_REF) + " °H)"
                        _rep_ic = _dfr_ic

                _dfs_concat = [df for df in [_rep_trans, _rep_ic] if not df.empty]
                _reporte_final = (
                    pd.concat(_dfs_concat, ignore_index=True)
                    if _dfs_concat
                    else pd.DataFrame()
                )

                _n_rep = len(_reporte_final)
                if _n_rep == 0:
                    st.success("✅ No se encontraron alertas en el período seleccionado.")
                else:
                    st.error(f"⚠️ {_n_rep} alerta(s) detectada(s) en el período.")
                    st.dataframe(
                        _reporte_final,
                        width='stretch',
                        hide_index=True,
                        height=min(70 + _n_rep * 36, 320),
                    )

                _csv_alertas = _reporte_final.to_csv(
                    index=False, encoding="utf-8-sig"
                ).encode()
                st.download_button(
                    label="🚨  GENERAR REPORTE DE ALERTAS (CSV)",
                    data=_csv_alertas,
                    file_name=f"alertas_transuiza_{now_col().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    type="primary",
                )
