import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.data_utils import load_catalogo, save_catalogo


def _is_admin() -> bool:
    return st.session_state.get("_rol_usuario") == "ADMINISTRADOR"


def render_estaciones():
    if "cat_accion" not in st.session_state:
        st.session_state.cat_accion = None
    if "cat_sel_idx" not in st.session_state:
        st.session_state.cat_sel_idx = None

    st.markdown(
        """<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
              <span style="font-size:1.35rem;">🏷️</span>
              <span style="font-size:1.35rem;font-weight:700;color:#0056A3;
                           letter-spacing:.5px;font-family:'Segoe UI',sans-serif;">
                CATÁLOGO DE ESTACIONES
              </span>
            </div>""",
        unsafe_allow_html=True,
    )

    if "cat_nav_codigo" not in st.session_state:
        st.session_state.cat_nav_codigo = None

    _cat_df = load_catalogo().reset_index(drop=True)
    _asesores_lista = ["Todos"] + sorted(
        _cat_df["asesor"].dropna().unique().tolist()
    )
    _f1, _f2, _cnt_col = st.columns([2.5, 1.8, 0.7])
    with _f1:
        _cat_q = st.text_input(
            "🔍 Código / Nombre",
            key="cat_buscar_input",
            placeholder="Buscar por código o nombre…",
            label_visibility="collapsed",
        ).strip().upper()
    with _f2:
        _cat_asesor = st.selectbox(
            "Asesor",
            options=_asesores_lista,
            index=0,
            key="cat_filtro_asesor",
            label_visibility="collapsed",
        )

    _cat_filt = _cat_df.copy()
    if _cat_q:
        _mask_q = (
            _cat_filt["codigo"].str.upper().str.contains(_cat_q, na=False) |
            _cat_filt["nombre"].str.upper().str.contains(_cat_q, na=False)
        )
        _cat_filt = _cat_filt[_mask_q]
    if _cat_asesor != "Todos":
        _cat_filt = _cat_filt[_cat_filt["asesor"] == _cat_asesor]
    _cat_filt = _cat_filt.reset_index(drop=True)
    _n_filt = len(_cat_filt)
    with _cnt_col:
        st.markdown(
            f"<div style='padding:8px 0 0 2px;font-size:13px;color:#6B7280;'>"
            f"{_n_filt} reg.</div>",
            unsafe_allow_html=True,
        )

    _nav_cod = st.session_state.cat_nav_codigo
    if _nav_cod and _nav_cod in _cat_filt["codigo"].values:
        _nav_pos = int(_cat_filt[_cat_filt["codigo"] == _nav_cod].index[0])
    else:
        _nav_pos = 0 if _n_filt > 0 else None

    _cat_vis = _cat_filt[["codigo", "nombre", "asesor"]].rename(columns={
        "codigo": "CÓDIGO", "nombre": "NOMBRE", "asesor": "ASESOR"
    })
    _tabla_h = max(42 + _n_filt * 35, 70) if _n_filt > 0 else 70
    _tabla_h = min(_tabla_h, 280)
    _cat_sel_widget = st.dataframe(
        _cat_vis,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        height=_tabla_h,
        column_config={
            "CÓDIGO": st.column_config.TextColumn(width="small"),
            "NOMBRE": st.column_config.TextColumn(width="large"),
            "ASESOR": st.column_config.TextColumn(width="medium"),
        },
    )
    _cat_filas = (_cat_sel_widget.selection.rows
                  if _cat_sel_widget and hasattr(_cat_sel_widget, "selection")
                  else [])
    if _cat_filas:
        _clicked = _cat_filas[0]
        if _clicked < _n_filt:
            _nav_pos = _clicked
            st.session_state.cat_nav_codigo = _cat_filt.iloc[_nav_pos]["codigo"]
            _nav_cod = st.session_state.cat_nav_codigo

    _nv1, _nv2, _nv3, _nvsep, _nb1, _nb2, _nb3 = st.columns(
        [0.5, 0.5, 2.5, 0.2, 1, 1, 1]
    )
    with _nv1:
        if st.button("◀", key="cat_prev", width='stretch',
                     disabled=(_nav_pos is None or _nav_pos <= 0)):
            _nav_pos = max(0, _nav_pos - 1)
            st.session_state.cat_nav_codigo = _cat_filt.iloc[_nav_pos]["codigo"]
            st.rerun()
    with _nv2:
        if st.button("▶", key="cat_next", width='stretch',
                     disabled=(_nav_pos is None or _nav_pos >= _n_filt - 1)):
            _nav_pos = min(_n_filt - 1, _nav_pos + 1)
            st.session_state.cat_nav_codigo = _cat_filt.iloc[_nav_pos]["codigo"]
            st.rerun()
    with _nv3:
        if _nav_pos is not None and _n_filt > 0:
            _r_info = _cat_filt.iloc[_nav_pos]
            st.markdown(
                f"<div style='padding:6px 0 0 6px;font-size:13px;color:#0056A3;"
                f"font-weight:600;white-space:nowrap;overflow:hidden;"
                f"text-overflow:ellipsis;'>"
                f"<span style='color:#6B7280;font-weight:400;'>"
                f"{_nav_pos + 1}/{_n_filt}</span> &nbsp;"
                f"<strong>{_r_info['codigo']}</strong> — {_r_info['nombre']}"
                f"</div>",
                unsafe_allow_html=True,
            )
    with _nb1:
        if st.button("➕ Nueva", key="cat_btn_nueva", width='stretch', type="primary"):
            st.session_state.cat_accion     = "nueva"
            st.session_state.cat_nav_codigo = None
            st.rerun()
    with _nb2:
        if _is_admin():
            if st.button("✏️ Modificar", key="cat_btn_mod", width='stretch',
                         disabled=(_nav_pos is None or _n_filt == 0)):
                st.session_state.cat_accion     = "modificar"
                if _nav_pos is not None:
                    st.session_state.cat_nav_codigo = _cat_filt.iloc[_nav_pos]["codigo"]
                st.rerun()
    with _nb3:
        if _is_admin():
            if st.button("🗑️ Eliminar", key="cat_btn_del", width='stretch',
                         disabled=(_nav_pos is None or _n_filt == 0)):
                st.session_state.cat_accion     = "eliminar"
                if _nav_pos is not None:
                    st.session_state.cat_nav_codigo = _cat_filt.iloc[_nav_pos]["codigo"]
                st.rerun()

    st.markdown("<hr style='border-color:#E5E7EB;margin:8px 0 14px 0;'>",
                unsafe_allow_html=True)

    # ── Importación masiva (pegar desde Excel) ───────────────────────────
    if _is_admin():
        with st.expander("📋 Pegar / importar desde Excel", expanded=False):
            st.caption(
                "Copia las columnas **CÓDIGO · NOMBRE · ASESOR** desde Excel "
                "(Ctrl+C) y pega (Ctrl+V) directamente sobre la tabla. "
                "Si el código ya existe se **actualiza**; si es nuevo se **agrega**."
            )
            _imp_fg = st.session_state.get("_cat_imp_fg", 0)
            _empty_imp = pd.DataFrame(
                [{"CÓDIGO": "", "NOMBRE": "", "ASESOR": ""} for _ in range(8)]
            )
            _imp_edit = st.data_editor(
                _empty_imp,
                num_rows="dynamic",
                width="stretch",
                key=f"cat_imp_editor_{_imp_fg}",
                column_config={
                    "CÓDIGO": st.column_config.TextColumn("CÓDIGO", width="small"),
                    "NOMBRE": st.column_config.TextColumn("NOMBRE", width="large"),
                    "ASESOR": st.column_config.TextColumn("ASESOR", width="medium"),
                },
            )

            # Normaliza y descarta filas vacías
            _imp_df = _imp_edit.copy()
            for _c in ("CÓDIGO", "NOMBRE", "ASESOR"):
                _imp_df[_c] = _imp_df[_c].fillna("").astype(str).str.strip()
            _imp_df["CÓDIGO"] = _imp_df["CÓDIGO"].str.upper()
            _imp_df["NOMBRE"] = _imp_df["NOMBRE"].str.upper()
            _imp_df["ASESOR"] = _imp_df["ASESOR"].str.upper()
            _imp_df = _imp_df[(_imp_df["CÓDIGO"] != "") & (_imp_df["NOMBRE"] != "")]

            # Detecta duplicados internos (mismo código pegado más de una vez)
            _dup_cods = _imp_df["CÓDIGO"][_imp_df["CÓDIGO"].duplicated()].unique().tolist()

            _df_actual = load_catalogo()
            _existentes = set(_df_actual["codigo"].astype(str).str.upper())
            _n_total = len(_imp_df)
            _n_nuevos = (~_imp_df["CÓDIGO"].isin(_existentes)).sum() if _n_total else 0
            _n_actualiza = (_imp_df["CÓDIGO"].isin(_existentes)).sum() if _n_total else 0

            _ck1, _ck2, _ck3 = st.columns(3)
            with _ck1:
                st.metric("Filas válidas", _n_total)
            with _ck2:
                st.metric("Nuevas", int(_n_nuevos))
            with _ck3:
                st.metric("Actualizan existentes", int(_n_actualiza))

            if _dup_cods:
                st.error(
                    f"⚠️ Códigos repetidos en lo que pegaste: "
                    f"{', '.join(_dup_cods[:10])}"
                    + (" …" if len(_dup_cods) > 10 else "")
                )

            _ib1, _ib2, _ = st.columns([1.2, 1, 4])
            with _ib1:
                _imp_btn = st.button(
                    "💾 Importar todo",
                    type="primary",
                    width="stretch",
                    key=f"cat_imp_btn_{_imp_fg}",
                    disabled=(_n_total == 0 or bool(_dup_cods)),
                )
            with _ib2:
                _imp_clr = st.button(
                    "🧹 Limpiar tabla",
                    width="stretch",
                    key=f"cat_imp_clr_{_imp_fg}",
                )

            if _imp_clr:
                st.session_state["_cat_imp_fg"] = _imp_fg + 1
                st.rerun()

            if _imp_btn and _n_total and not _dup_cods:
                # Combina catálogo actual con lo importado: lo importado pisa.
                _final = _df_actual.copy()
                _final["codigo"] = _final["codigo"].astype(str).str.upper()
                _imp_norm = _imp_df.rename(columns={
                    "CÓDIGO": "codigo", "NOMBRE": "nombre", "ASESOR": "asesor"
                })[["codigo", "nombre", "asesor"]]
                _final = _final[~_final["codigo"].isin(_imp_norm["codigo"])]
                _final = pd.concat([_final, _imp_norm], ignore_index=True)
                save_catalogo(_final)
                load_catalogo.clear()
                st.session_state["_cat_imp_fg"] = _imp_fg + 1
                st.success(
                    f"✅ Importación completa: {_n_nuevos} nuevas · "
                    f"{_n_actualiza} actualizadas."
                )
                st.rerun()

    if st.session_state.cat_accion == "nueva":
        st.markdown(
            "<div id='nueva-est-anchor' style='font-size:1rem;font-weight:700;"
            "color:#0056A3;margin:0 0 10px 0;border-left:4px solid #0056A3;"
            "padding-left:10px;'>➕ NUEVA ESTACIÓN</div>",
            unsafe_allow_html=True,
        )
        _fg = st.session_state.get("_cat_nueva_fg", 0)

        _nc1, _nc2, _nc3 = st.columns(3)
        with _nc1:
            _new_cod = st.text_input(
                "CÓDIGO *", key=f"nv_cod_{_fg}", placeholder="Ej: 6008"
            ).strip().upper()
        with _nc2:
            _new_nom = st.text_input(
                "NOMBRE DE LA ESTACIÓN *", key=f"nv_nom_{_fg}", placeholder="Ej: LA JAGUA"
            ).strip().upper()
        with _nc3:
            _ase_opciones = sorted(
                load_catalogo()["asesor"].str.strip().str.upper()
                .dropna().unique().tolist()
            ) + ["— OTRO —"]
            _ase_idx_default = next(
                (i for i, v in enumerate(_ase_opciones) if "JUAN ORTEGA" in v), 0
            )
            _ase_sel = st.selectbox(
                "ASESOR", options=_ase_opciones,
                key=f"nv_ase_sel_{_fg}", index=_ase_idx_default,
            )
        _ase_otro_visible = (_ase_sel == "— OTRO —")
        if _ase_otro_visible:
            _new_ase = st.text_input(
                "NOMBRE DEL ASESOR *", key=f"nv_ase_otro_{_fg}",
                placeholder="Escribe el nombre del asesor…"
            ).strip().upper()
        else:
            _new_ase = _ase_sel

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        _gb1, _gb2, _ = st.columns([1, 1, 4])
        with _gb1:
            _btn_guardar = st.button(
                "💾 Guardar", type="primary", width='stretch', key="cat_guardar_nv"
            )
        with _gb2:
            _btn_cancel = st.button("✖ Cancelar", width='stretch', key="cat_cancelar_nv")

        components.html("""<script>
(function tryAttach(n){
  var doc = window.parent.document;
  var lblTexts = ['CÓDIGO *', 'NOMBRE DE LA ESTACIÓN *'];
  var inputs = lblTexts.map(function(txt){
    var cs = Array.from(doc.querySelectorAll('[data-testid="stTextInput"]'));
    var c = cs.find(function(el){
      var lbl = el.querySelector('label, p');
      return lbl && lbl.textContent.trim() === txt;
    });
    return c ? c.querySelector('input') : null;
  });
  var aOtroC = Array.from(doc.querySelectorAll('[data-testid="stTextInput"]')).find(function(el){
    var lbl=el.querySelector('label, p');
    return lbl && lbl.textContent.trim()==='NOMBRE DEL ASESOR *';
  });
  if(aOtroC) inputs.push(aOtroC.querySelector('input'));
  var missing = inputs.some(function(i){return !i;});
  if(missing && n>0){setTimeout(function(){tryAttach(n-1);},300);return;}
  inputs = inputs.filter(Boolean);
  if(inputs.length===0) return;
  var guardarBtn = Array.from(doc.querySelectorAll('button')).find(
    function(b){return b.textContent.trim().indexOf('Guardar')>=0;}
  );
  function toUpper(inp){
    var nS=Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value');
    nS.set.call(inp,inp.value.toUpperCase());
    inp.dispatchEvent(new Event('input',{bubbles:true}));
  }
  inputs.forEach(function(inp,i){
    if(inp._qlnav) return;
    inp._qlnav = true;
    inp.addEventListener('keydown',function(e){
      if(e.key==='Enter'||(e.key==='ArrowRight'&&inp.selectionStart===inp.value.length)){
        e.preventDefault();
        toUpper(inp);
        if(i<inputs.length-1){
          inputs[i+1].focus();
          inputs[i+1].setSelectionRange(0,inputs[i+1].value.length);
        } else if(guardarBtn){guardarBtn.focus();}
      } else if(e.key==='ArrowLeft'&&inp.selectionStart===0&&i>0){
        e.preventDefault();
        toUpper(inp);
        inputs[i-1].focus();
        var l=inputs[i-1].value.length;
        inputs[i-1].setSelectionRange(l,l);
      }
    });
    inp.addEventListener('blur',function(){toUpper(inp);});
  });
})(25);
</script>""", height=0)

        if _btn_cancel:
            st.session_state.cat_accion = None
            st.rerun()

        if _btn_guardar:
            if not _new_cod:
                st.error("El CÓDIGO es obligatorio.")
            elif not _new_nom:
                st.error("El NOMBRE es obligatorio.")
            elif _ase_otro_visible and not _new_ase:
                st.error("Escribe el nombre del asesor.")
            elif _new_cod in load_catalogo()["codigo"].values:
                st.error(f"El código {_new_cod} ya existe en el catálogo.")
            else:
                _df_save = load_catalogo()
                _df_save = pd.concat([_df_save, pd.DataFrame([{
                    "codigo": _new_cod, "nombre": _new_nom,
                    "asesor": _new_ase.upper()
                }])], ignore_index=True)
                save_catalogo(_df_save)
                load_catalogo.clear()
                st.session_state["_cat_nueva_fg"] = _fg + 1
                st.session_state.cat_accion       = None
                st.session_state.cat_nav_codigo   = _new_cod
                st.success(f"✅ Estación {_new_cod} — {_new_nom} agregada.")
                st.rerun()

    elif st.session_state.cat_accion == "modificar":
        _cod_m = st.session_state.cat_nav_codigo
        _df_m  = load_catalogo().reset_index(drop=True)
        _rows_m = _df_m[_df_m["codigo"] == _cod_m]
        if _cod_m and not _rows_m.empty:
            _idx_m = _rows_m.index[0]
            _row_m = _df_m.iloc[_idx_m]
            st.markdown(
                "<div style='font-size:1rem;font-weight:700;color:#0056A3;"
                "margin:0 0 10px 0;border-left:4px solid #F59E0B;"
                "padding-left:10px;'>✏️ MODIFICAR ESTACIÓN</div>",
                unsafe_allow_html=True,
            )
            _mc1, _mc2, _mc3 = st.columns(3)
            with _mc1:
                _mod_cod = st.text_input("CÓDIGO *", value=_row_m["codigo"],
                                         key="cat_mod_cod").strip().upper()
            with _mc2:
                _mod_nom = st.text_input("NOMBRE *", value=_row_m["nombre"],
                                         key="cat_mod_nom").strip().upper()
            with _mc3:
                _mod_ase = st.text_input("ASESOR", value=_row_m.get("asesor", ""),
                                         key="cat_mod_ase").strip().upper()

            _ma1, _ma2, _ = st.columns([1, 1, 4])
            with _ma1:
                if st.button("💾 Guardar cambios", key="cat_guardar_mod",
                             type="primary", width='stretch'):
                    if not _mod_cod or not _mod_nom:
                        st.error("CÓDIGO y NOMBRE son obligatorios.")
                    else:
                        _df_m.at[_idx_m, "codigo"] = _mod_cod
                        _df_m.at[_idx_m, "nombre"] = _mod_nom
                        _df_m.at[_idx_m, "asesor"] = _mod_ase
                        save_catalogo(_df_m)
                        load_catalogo.clear()
                        st.session_state.cat_accion    = None
                        st.session_state.cat_nav_codigo = _mod_cod
                        st.success(f"✅ Estación actualizada: {_mod_cod} — {_mod_nom}")
                        st.rerun()
            with _ma2:
                if st.button("✖ Cancelar", key="cat_cancelar_mod", width='stretch'):
                    st.session_state.cat_accion = None
                    st.rerun()

    elif st.session_state.cat_accion == "eliminar":
        _cod_e = st.session_state.cat_nav_codigo
        _df_e  = load_catalogo().reset_index(drop=True)
        _rows_e = _df_e[_df_e["codigo"] == _cod_e]
        if _cod_e and not _rows_e.empty:
            _idx_e = _rows_e.index[0]
            _row_e = _df_e.iloc[_idx_e]
            st.warning(
                f"⚠️ ¿Eliminar la estación **{_row_e['codigo']} — {_row_e['nombre']}**?"
                f" Esta acción no se puede deshacer."
            )
            _ea1, _ea2, _ = st.columns([1, 1, 4])
            with _ea1:
                if st.button("🗑️ Confirmar eliminación", key="cat_confirmar_del",
                             type="primary", width='stretch'):
                    _df_e = _df_e.drop(index=_idx_e).reset_index(drop=True)
                    save_catalogo(_df_e)
                    load_catalogo.clear()
                    st.session_state.cat_accion    = None
                    st.session_state.cat_nav_codigo = None
                    st.success("✅ Estación eliminada del catálogo.")
                    st.rerun()
            with _ea2:
                if st.button("✖ Cancelar", key="cat_cancelar_del", width='stretch'):
                    st.session_state.cat_accion = None
                    st.rerun()
