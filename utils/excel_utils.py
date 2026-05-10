import io
import json
from datetime import date

import openpyxl
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from utils.data_utils import load_seguimientos, load_catalogo


def historial_to_excel_filtrado(
    df_filtrado: pd.DataFrame,
    fecha_desde,
    fecha_hasta,
    filtro_tipo: str,
    filtro_subtipo: str = "TODOS",
) -> bytes:
    """Excel multi-hoja respetando los filtros del Historial."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    fill_hdr = PatternFill("solid", fgColor="1F4E79")
    fill_bad = PatternFill("solid", fgColor="FFC7CE")
    fill_alt = PatternFill("solid", fgColor="EEF4FB")
    font_hdr = Font(bold=True, size=10, color="FFFFFF")
    font_bad = Font(bold=True, size=10, color="9C0006")
    normal   = Font(size=10)
    center   = Alignment(horizontal="center", vertical="center")
    bd = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    def _wh(ws, cols, widths):
        for ci, hdr in enumerate(cols, 1):
            c = ws.cell(row=1, column=ci, value=hdr)
            c.fill = fill_hdr; c.font = font_hdr
            c.alignment = center; c.border = bd
        for ci, w in enumerate(widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w
        ws.row_dimensions[1].height = 20

    def _wc(ws, ri, ci, val, fmt=None, bad=False, alt=False):
        v = val if (val is not None and not (isinstance(val, float) and pd.isna(val))) else ""
        c = ws.cell(row=ri, column=ci, value=v)
        c.alignment = center; c.border = bd
        if bad:
            c.font = font_bad; c.fill = fill_bad
        else:
            c.font = normal
            if alt: c.fill = fill_alt
        if fmt: c.number_format = fmt

    if filtro_tipo in ("TODOS", "RUTAS"):
        df_r = (df_filtrado[df_filtrado["tipo_seguimiento"] == "RUTAS"].copy()
                if "tipo_seguimiento" in df_filtrado.columns else df_filtrado.copy())
        ws1 = wb.create_sheet("RUTAS")
        cols1 = [
            ("TIPO", "tipo_seguimiento"), ("FECHA", "fecha"), ("RUTA", "ruta"),
            ("PLACA", "placa"), ("CONDUCTOR", "conductor"),
            ("VOLUMEN (L)", "volumen_declarado"),
            ("VOL. ESTACIONES (L)", "vol_estaciones"),
            ("DIFERENCIA (L)", "diferencia"),
            ("SÓLIDOS RUTA (%)", "solidos_ruta"),
            ("ST POND", "st_pond"),
            ("CRIOSCOPIA RUTA (°C)", "crioscopia_ruta"),
            ("IC POND", "ic_pond"),
            ("Nº ESTACIONES", "num_estaciones"), ("GUARDADO EN", "guardado_en"),
        ]
        _wh(ws1, [h for h, _ in cols1],
            [10, 12, 18, 10, 18, 14, 18, 12, 16, 10, 18, 10, 12, 18])
        for ri, row in enumerate(df_r.itertuples(index=False), start=2):
            rd = row._asdict()
            desv_st = desv_ic = False
            try:
                v = float(str(rd.get("solidos_ruta","")).replace(",","."))
                if 0 < v < 12.60: desv_st = True
            except Exception: pass
            try:
                v = float(str(rd.get("crioscopia_ruta","")).replace(",","."))
                if v > -0.535: desv_ic = True
            except Exception: pass
            alt = (ri % 2 == 0)
            for ci, (_, col) in enumerate(cols1, 1):
                fmt = "0.00"  if col in ("solidos_ruta","st_pond") else \
                      "0.000" if col in ("crioscopia_ruta","ic_pond") else None
                bad = ((desv_st or desv_ic) and col == "ruta") or \
                      (desv_st and col == "solidos_ruta")          or \
                      (desv_st and col == "st_pond")               or \
                      (desv_ic and col == "crioscopia_ruta")       or \
                      (desv_ic and col == "ic_pond")
                _wc(ws1, ri, ci, rd.get(col,""), fmt=fmt, bad=bad, alt=alt)

    if filtro_tipo in ("TODOS", "TRANSUIZA"):
        df_t = (df_filtrado[df_filtrado["tipo_seguimiento"] == "TRANSUIZA"].copy()
                if "tipo_seguimiento" in df_filtrado.columns else df_filtrado.copy())
        ws2 = wb.create_sheet("TRANSUIZA")
        cols2 = [
            ("FECHA ANÁLISIS",       "guardado_en"),
            ("FECHA MUESTRA",        "fecha"),
            ("GRASA (%)",            "grasa_muestra"),
            ("ST MUESTRA (%)",       "solidos_ruta"),
            ("PROTEÍNA (%)",         "proteina_muestra"),
            ("ST CARROTANQUE (%)",   "st_carrotanque"),
            ("DIFERENCIA SÓLIDOS",   "diferencia_solidos"),
        ]
        _wh(ws2, [h for h, _ in cols2], [20, 16, 14, 16, 14, 20, 18])
        for ri, row in enumerate(df_t.itertuples(index=False), start=2):
            rd = row._asdict(); alt = (ri % 2 == 0)
            for ci, (_, col) in enumerate(cols2, 1):
                fmt = "0.00" if col in ("grasa_muestra", "solidos_ruta",
                                        "proteina_muestra", "st_carrotanque",
                                        "diferencia_solidos") else None
                _wc(ws2, ri, ci, rd.get(col, ""), fmt=fmt, alt=alt)

    if filtro_tipo in ("TODOS", "SEGUIMIENTOS"):
        if filtro_tipo == "SEGUIMIENTOS":
            df_seg = df_filtrado.copy()
        else:
            df_seg = load_seguimientos()
            if "_fecha_dt" in df_seg.columns:
                df_seg = df_seg[
                    (df_seg["_fecha_dt"].dt.date >= fecha_desde) &
                    (df_seg["_fecha_dt"].dt.date <= fecha_hasta)
                ]
        if filtro_subtipo != "TODOS" and "sub_tipo_seguimiento" in df_seg.columns:
            df_seg = df_seg[df_seg["sub_tipo_seguimiento"] == filtro_subtipo]
        df_seg = df_seg.drop(columns=["_fecha_dt","_estado"], errors="ignore")
        ws3 = wb.create_sheet("SEGUIMIENTOS")
        cols3 = [
            ("SUB-TIPO","sub_tipo_seguimiento"), ("FECHA","fecha"),
            ("CÓDIGO","seg_codigo"), ("ENTREGADO POR","seg_quien_trajo"),
            ("RUTA","ruta"), ("RESPONSABLE","seg_responsable"),
            ("ID MUESTRA","seg_id_muestra"), ("GRASA (%)","seg_grasa"),
            ("ST (%)","seg_st"), ("IC (°C)","seg_ic"), ("AGUA (%)","seg_agua"),
            ("ALCOHOL","seg_alcohol"), ("CLORUROS","seg_cloruros"),
            ("NEUTRALIZANTES","seg_neutralizantes"),
            ("OBSERVACIONES","seg_observaciones"), ("GUARDADO EN","guardado_en"),
        ]
        _wh(ws3, [h for h, _ in cols3],
            [18, 12, 12, 18, 16, 18, 14, 10, 10, 10, 10, 12, 12, 16, 30, 18])
        for ri, row in enumerate(df_seg.itertuples(index=False), start=2):
            rd = row._asdict(); alt = (ri % 2 == 0)
            for ci, (_, col) in enumerate(cols3, 1):
                fmt = "0.00"  if col in ("seg_grasa","seg_st","seg_agua") else \
                      "0.000" if col == "seg_ic" else None
                _wc(ws3, ri, ci, rd.get(col,""), fmt=fmt, alt=alt)

    if filtro_tipo in ("TODOS", "RUTAS"):
        df_re = (df_filtrado[df_filtrado["tipo_seguimiento"] == "RUTAS"].copy()
                 if "tipo_seguimiento" in df_filtrado.columns else df_filtrado.copy())
        ws4 = wb.create_sheet("ESTACIONES")
        hdrs4 = [
            "FECHA","RUTA","PLACA","CONDUCTOR","VOL. DECLARADO (L)",
            "# ESTACIÓN","CÓDIGO","GRASA (%)","SÓL.TOT. (%)","PROTEÍNA (%)",
            "CRIOSCOPIA (°C)","VOLUMEN (L)","ALCOHOL","CLORUROS","NEUTRALIZANTES",
            "% AGUA","OBSERVACIONES","ST RUTA (%)","IC RUTA (°C)","ESTADO CALIDAD",
        ]
        _wh(ws4, hdrs4,
            [12,18,10,18,16,10,14,10,10,10,14,12,10,10,14,9,26,12,12,14])
        est_ri = 2
        for _, ruta_row in df_re.iterrows():
            raw_json = str(ruta_row.get("estaciones_json","") or "")
            try: ests = json.loads(raw_json) if raw_json.strip() else []
            except Exception: ests = []
            if not ests: continue
            try: st_rv = float(str(ruta_row.get("solidos_ruta","")).replace(",","."))
            except Exception: st_rv = None
            try: ic_rv = float(str(ruta_row.get("crioscopia_ruta","")).replace(",","."))
            except Exception: ic_rv = None
            desv_st_r = st_rv is not None and 0 < st_rv < 12.60
            desv_ic_r = ic_rv is not None and ic_rv > -0.535
            estado_r  = "DESVIACIÓN" if (desv_st_r or desv_ic_r) else "CONFORME"

            for idx_e, est in enumerate(ests, 1):
                try:
                    st_e = float(str(est.get("solidos","")).replace(",","."))
                    desv_st_e = 0 < st_e < 12.60
                except Exception:
                    st_e = None; desv_st_e = False
                try:
                    ic_e = float(str(est.get("crioscopia","")).replace(",","."))
                    desv_ic_e = ic_e > -0.530
                except Exception:
                    ic_e = None; desv_ic_e = False
                agua_raw = est.get("agua_pct", "")
                desv_agua_e = False
                try:
                    agua_v = float(str(agua_raw).replace(",",".").replace("+",""))
                    if agua_v > 0: desv_agua_e = True
                except Exception:
                    if str(agua_raw).strip() in ("+", "SI", "si", "sí", "SÍ"): desv_agua_e = True

                row_vals = [
                    ruta_row.get("fecha",""), ruta_row.get("ruta",""),
                    ruta_row.get("placa",""), ruta_row.get("conductor",""),
                    ruta_row.get("volumen_declarado",""), idx_e,
                    est.get("codigo",""), est.get("grasa"),
                    est.get("solidos"), est.get("proteina"),
                    est.get("crioscopia"), est.get("volumen"),
                    est.get("alcohol",""), est.get("cloruros",""),
                    est.get("neutralizantes",""), agua_raw,
                    est.get("obs",""), st_rv, ic_rv, estado_r,
                ]
                fmts = [None,None,None,None,"#,##0","0",None,
                        "0.00","0.00","0.00","0.000","#,##0",
                        None,None,None,"0.0",None,"0.00","0.000",None]
                alt = (est_ri % 2 == 0)
                for ci_e, (val_e, fmt_e) in enumerate(zip(row_vals, fmts), 1):
                    bad_e = (
                        (ci_e == 2  and (desv_st_e or desv_ic_e or desv_agua_e)) or
                        (ci_e == 7  and (desv_st_e or desv_ic_e or desv_agua_e)) or
                        (ci_e == 9  and desv_st_e)    or
                        (ci_e == 11 and desv_ic_e)    or
                        (ci_e == 16 and desv_agua_e)
                    )
                    _wc(ws4, est_ri, ci_e, val_e, fmt=fmt_e, bad=bad_e, alt=alt)
                est_ri += 1

    if filtro_tipo in ("TODOS", "SEGUIMIENTOS"):
        if filtro_tipo == "SEGUIMIENTOS":
            df_acomp_xl = df_filtrado.copy()
        else:
            df_acomp_xl = load_seguimientos()
            if "_fecha_dt" in df_acomp_xl.columns:
                df_acomp_xl = df_acomp_xl[
                    (df_acomp_xl["_fecha_dt"].dt.date >= fecha_desde) &
                    (df_acomp_xl["_fecha_dt"].dt.date <= fecha_hasta)
                ]
        df_acomp_xl = (
            df_acomp_xl[df_acomp_xl.get("sub_tipo_seguimiento", pd.Series(dtype=str)) == "ACOMPAÑAMIENTOS"]
            if "sub_tipo_seguimiento" in df_acomp_xl.columns else pd.DataFrame()
        )
        if not df_acomp_xl.empty:
            try:
                _cat_xl = load_catalogo()
                _cat_xl_map = dict(zip(_cat_xl["codigo"], _cat_xl["nombre"]))
            except Exception:
                _cat_xl_map = {}
            ws5 = wb.create_sheet("ACOMPAÑAMIENTOS")
            hdrs5 = [
                "FECHA","RUTA","ENTREGADO POR","RESPONSABLE",
                "VOL. DECLARADO (L)","VOL. SUMA MUESTRAS (L)","DIFERENCIA (L)",
                "ST RUTA (%)","IC RUTA (°C)","ST PONDERADO (%)","IC PONDERADO (°C)",
                "# MUESTRA","CÓDIGO","NOMBRE ESTACIÓN","VOLUMEN (L)",
                "GRASA (%)","ST (%)","PROTEÍNA (%)","IC (°C)","AGUA (%)","POND ST","IC POND",
                "ALCOHOL","CLORUROS","NEUTRALIZANTES","OBSERVACIONES","GUARDADO EN",
            ]
            widths5 = [12,18,18,18,16,18,14,12,14,14,14,10,14,20,10,10,10,10,10,10,10,10,10,10,14,30,18]
            _wh(ws5, hdrs5, widths5)
            _am_ri = 2
            for _, _arow in df_acomp_xl.iterrows():
                _raw_mj = str(_arow.get("muestras_json","") or "")
                try: _muestras_xl = json.loads(_raw_mj) if _raw_mj.strip() else []
                except Exception: _muestras_xl = []
                def _pnxl(x):
                    try: return float(str(x).replace(",","."))
                    except: return None
                try: _st_rv = float(str(_arow.get("seg_solidos_ruta","")).replace(",","."))
                except: _st_rv = None
                try: _ic_rv = float(str(_arow.get("seg_crioscopia_ruta","")).replace(",","."))
                except: _ic_rv = None
                try: _st_pv = float(str(_arow.get("seg_st_pond","")).replace(",","."))
                except: _st_pv = None
                try: _ic_pv = float(str(_arow.get("seg_ic_pond","")).replace(",","."))
                except: _ic_pv = None
                try: _vol_decl_xl = int(float(str(_arow.get("seg_vol_declarado","")).replace(",",".")))
                except: _vol_decl_xl = None
                try: _vol_sum_xl  = int(float(str(_arow.get("seg_vol_muestras","")).replace(",",".")))
                except: _vol_sum_xl = None
                try: _dif_xl = int(float(str(_arow.get("seg_diferencia_vol","")).replace(",",".")))
                except: _dif_xl = None
                _common5 = [
                    _arow.get("fecha",""), _arow.get("ruta",""),
                    _arow.get("seg_quien_trajo",""), _arow.get("seg_responsable",""),
                    _vol_decl_xl, _vol_sum_xl, _dif_xl,
                    _st_rv, _ic_rv, _st_pv, _ic_pv,
                ]
                _alt5 = (_am_ri % 2 == 0)
                if not _muestras_xl:
                    for _ci5, _v5 in enumerate(_common5 + ["—"]*14 + [_arow.get("guardado_en","")], 1):
                        _wc(ws5, _am_ri, _ci5, _v5, alt=_alt5)
                    _am_ri += 1
                    continue
                for _idx5, _am5 in enumerate(_muestras_xl, 1):
                    _cod5 = str(_am5.get("ID","") or "").strip()
                    _vol5 = _pnxl(_am5.get("_volumen"))
                    _st5  = _pnxl(_am5.get("_st"))
                    _ic5  = _pnxl(_am5.get("_ic"))
                    _pst5 = round(_vol5 * _st5, 2) if _vol5 is not None and _st5 is not None else None
                    _pic5 = round(_vol5 * _ic5, 3) if _vol5 is not None and _ic5 is not None else None
                    _row5 = _common5 + [
                        _idx5, _cod5, _cat_xl_map.get(_cod5,""),
                        int(_vol5) if _vol5 is not None else None,
                        _pnxl(_am5.get("_grasa")), _st5, _pnxl(_am5.get("_proteina")), _ic5,
                        _pnxl(_am5.get("_agua")), _pst5, _pic5,
                        _am5.get("_alcohol",""), _am5.get("_cloruros",""),
                        _am5.get("_neutralizantes",""), _am5.get("_obs",""),
                        _arow.get("guardado_en",""),
                    ]
                    _alt5 = (_am_ri % 2 == 0)
                    for _ci5, _v5 in enumerate(_row5, 1):
                        _hdr5 = hdrs5[_ci5-1]
                        _fmt5 = "0.00"  if _hdr5 in ("ST RUTA (%)","ST PONDERADO (%)","GRASA (%)","ST (%)","PROTEÍNA (%)","AGUA (%)","POND ST") else \
                                "0.000" if _hdr5 in ("IC RUTA (°C)","IC PONDERADO (°C)","IC (°C)","IC POND") else None
                        _wc(ws5, _am_ri, _ci5, _v5, fmt=_fmt5, alt=_alt5)
                    _am_ri += 1

    if not wb.sheetnames:
        wb.create_sheet("Sin datos")
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
