import re

import streamlit as st


def convertir_a_mayusculas(campo):
    st.session_state[campo] = st.session_state[campo].upper()


def sanitizar_nombre_ruta(campo):
    val = st.session_state.get(campo, "")
    st.session_state[campo] = re.sub(r"[^A-ZÁÉÍÓÚÑÜ0-9]", "", val.upper())


def validar_placa():
    _k = f"placa_vehiculo_{st.session_state.get('_ruta_fg', 0)}"
    if _k in st.session_state:
        st.session_state[_k] = re.sub(
            r"[^A-Z0-9]", "", st.session_state[_k].upper()
        )


def activar_siguiente_con_enter():
    # Sin guard de Python: st.html() se renderiza en CADA render para que
    # el árbol de widgets sea estable entre reruns (un st.html() ausente
    # desplaza las claves auto-generadas de todos los widgets siguientes,
    # incluyendo st.tabs(), lo que causa que React los remonte y reinicie al tab 0).
    # El guard JavaScript (window._navInstalled) impide listeners duplicados.
    st.html(
        """
        <script>
        (function(){
          /* Remover listeners previos (permite actualizar el script
             sin requerir hard refresh del navegador) */
          if (window._qlNavKeydown) document.removeEventListener('keydown', window._qlNavKeydown, true);
          if (window._qlNavFocusin) document.removeEventListener('focusin', window._qlNavFocusin);
          if (window._qlNavClick)   document.removeEventListener('click',   window._qlNavClick,   true);
          if (window._qlNavObs && window._qlNavObs.disconnect) window._qlNavObs.disconnect();

          /* ── Selectores de widgets Streamlit ─────────────────────── */
          var ST_FORM = [
            '[data-testid="stTextInput"]',
            '[data-testid="stNumberInput"]',
            '[data-testid="stDateInput"]',
            '[data-testid="stTimeInput"]',
            '[data-testid="stTextArea"]',
            '[data-testid="stSelectbox"]'
          ].join(',');

          function esFormInput(el) {
            return !!(el.closest && el.closest(ST_FORM));
          }
          function esSelectbox(el) {
            return !!(el.closest && el.closest('[data-testid="stSelectbox"]'));
          }
          function selectboxAbierto(el) {
            var c = el.closest('[data-testid="stSelectbox"]');
            if (!c) return false;
            return !!(c.querySelector('[class*="menu"]'));
          }
          function hayDataEditor() {
            var g = document.querySelector('[data-testid="stDataEditor"]');
            if (!g) return false;
            var r = g.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          }

          /* ── Visibilidad real del elemento ───────────────────────── */
          function esVisible(el) {
            var r = el.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0) return false;
            var cs = window.getComputedStyle(el);
            if (cs.display === 'none' || cs.visibility === 'hidden') return false;
            return true;
          }

          /* ── Botón GUARDAR dentro del panel activo ───────────────── */
          function clickBtnGuardar() {
            var vis = function(b) {
              if (!b.innerText) return false;
              if (b.offsetParent === null) return false;
              var cs = window.getComputedStyle(b);
              if (cs.display === 'none' || cs.visibility === 'hidden') return false;
              var r = b.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            };
            var btns = Array.from(document.querySelectorAll('button'));
            var btn = btns.find(function(b) { return vis(b) && b.innerText.includes('AGREGAR MUESTRA'); })
                  || btns.find(function(b) { return vis(b) && b.innerText.includes('GUARDAR'); })
                  || btns.find(function(b) { return vis(b) && b.innerText.toUpperCase().includes('INICIAR SESI'); });
            if (btn) setTimeout(function() { btn.click(); }, 120);
          }

          /* ── Inputs visibles en la página ────────────────────────── */
          function obtenerInputsVisibles() {
            var sels = [
              '[data-testid="stTextInput"] input',
              '[data-testid="stTextInputRootElement"] input',
              '[data-testid="stNumberInput"] input',
              '[data-testid="stDateInput"] input',
              '[data-testid="stTimeInput"] input',
              '[data-testid="stTextArea"] textarea',
              '[data-testid="stSelectbox"] input',
              'input[type="password"]',
              'input[type="text"]',
              'input[type="email"]'
            ].join(',');
            var seen = new Set();
            return Array.from(document.querySelectorAll(sels)).filter(function(el) {
              if (seen.has(el)) return false;
              seen.add(el);
              if (el.disabled || el.readOnly) return false;
              var t = el.getAttribute('type');
              if (t === 'hidden' || t === 'checkbox' || t === 'radio') return false;
              if (el.getAttribute('aria-hidden') === 'true') return false;
              return esVisible(el);
            });
          }

          function moverFoco(input, delta) {
            var todos = obtenerInputsVisibles();
            var pos = todos.indexOf(input);
            if (pos === -1) return;
            var dest = todos[pos + delta];
            if (dest) setTimeout(function() { dest.focus(); try { dest.select(); } catch(e) {} }, 60);
          }

          /* Busca el siguiente input visible que viene DESPUÉS del actual
             en orden del DOM, sin depender de selectores de contenedor. */
          function siguienteInput(actual) {
            var cands = Array.from(document.querySelectorAll('input,textarea')).filter(function(el) {
              if (el === actual) return false;
              if (el.disabled || el.readOnly) return false;
              var t = el.getAttribute('type');
              if (t === 'hidden' || t === 'checkbox' || t === 'radio' ||
                  t === 'submit' || t === 'button' || t === 'file') return false;
              if (el.getAttribute('aria-hidden') === 'true') return false;
              return esVisible(el);
            });
            for (var i = 0; i < cands.length; i++) {
              if (actual.compareDocumentPosition(cands[i]) & Node.DOCUMENT_POSITION_FOLLOWING) {
                return cands[i];
              }
            }
            return null;
          }

          /* ══════════════════════════════════════════════════════════
             PRESERVACIÓN DE TAB ACTIVO ENTRE RERUNS DE STREAMLIT
             ──────────────────────────────────────────────────────────
             st.tabs() reinicia al tab 0 en cada rerun de Streamlit.
             Guardamos el tab activo en sessionStorage y lo restauramos
             automáticamente después de cada rerun via MutationObserver.
          ══════════════════════════════════════════════════════════ */
          var _qlTabKey    = '_ql_seg_tab';
          var _qlRestTimer = null;
          var _qlLocked    = false;   // evita restauraciones re-entrantes

          function _qlGetSegTabs() {
            /* Busca el grupo de tabs de SEGUIMIENTOS por sus etiquetas */
            var all = Array.from(document.querySelectorAll('[data-testid="stTab"]'));
            for (var i = 0; i < all.length; i++) {
              var txt = (all[i].textContent || '').toUpperCase();
              if (txt.includes('ESTACIONES') || txt.includes('ACOMP') || txt.includes('CONTRA')) {
                /* Encontramos el primer tab del grupo; recogemos el contenedor */
                var wrap = all[i].closest('[data-baseweb="tab-list"]')
                        || all[i].closest('[role="tablist"]')
                        || all[i].parentElement;
                if (!wrap) return [];
                return Array.from(wrap.querySelectorAll('[data-testid="stTab"]'));
              }
            }
            return [];
          }

          function _qlActiveIdx(tabs) {
            for (var i = 0; i < tabs.length; i++) {
              if (tabs[i].getAttribute('aria-selected') === 'true') return i;
            }
            return 0;
          }

          function _qlSaveTab() {
            var tabs = _qlGetSegTabs();
            if (!tabs.length) return;
            var idx = _qlActiveIdx(tabs);
            sessionStorage.setItem(_qlTabKey, String(idx));
          }

          function _qlRestoreTab() {
            if (_qlLocked) return;
            var saved = sessionStorage.getItem(_qlTabKey);
            if (saved === null) return;
            var idx = parseInt(saved, 10);
            if (idx === 0) return;          /* tab 0 es el default, no hace falta restaurar */
            var tabs = _qlGetSegTabs();
            if (!tabs.length || idx >= tabs.length) return;
            var current = _qlActiveIdx(tabs);
            if (current === idx) return;    /* ya estamos en el tab correcto */
            _qlLocked = true;
            tabs[idx].click();
            setTimeout(function() { _qlLocked = false; }, 600);
          }

          /* Escuchar clics de usuario en los tabs → guardar índice */
          var _qlClickH = function(e) {
            if (!e.target || !e.target.closest) return;
            var tab = e.target.closest('[data-testid="stTab"]');
            if (tab) setTimeout(_qlSaveTab, 80);
          };
          document.addEventListener('click', _qlClickH, true);
          window._qlNavClick = _qlClickH;

          /* MutationObserver: detectar reruns de Streamlit y restaurar tab */
          var _qlObserver = new MutationObserver(function() {
            clearTimeout(_qlRestTimer);
            _qlRestTimer = setTimeout(_qlRestoreTab, 200);
          });
          _qlObserver.observe(document.body, { childList: true, subtree: true });
          window._qlNavObs = _qlObserver;

          /* ── Manejo de Data Editor (grilla) ──────────────────────── */
          var _inGrid = false;

          var _qlFocusH = function(e) {
            if (!_inGrid) return;
            var t = e.target, tag = t.tagName;
            if ((tag === 'INPUT' || tag === 'TEXTAREA') && !esFormInput(t)) return;
            if (tag === 'CANVAS' && t.closest('[data-testid="stDataEditor"]')) return;
            _inGrid = false; clickBtnGuardar();
          };
          document.addEventListener('focusin', _qlFocusH);
          window._qlNavFocusin = _qlFocusH;

          /* ── Navegación por teclado ───────────────────────────────── */
          var _qlKeyH = function(e) {
            var a = document.activeElement;
            if (!a) return;
            var tag = a.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA') return;

            if (esFormInput(a)) {
              var esSel = esSelectbox(a);
              if (esSel && selectboxAbierto(a)) return;

              var esNum = a.getAttribute('type') === 'number';
              var todos = obtenerInputsVisibles();
              var pos   = todos.indexOf(a);
              var esUlt = pos !== -1 && pos === todos.length - 1;
              var ph    = (a.placeholder || '').toLowerCase();

              if (e.key === 'Enter') {
                e.preventDefault(); e.stopPropagation();
                if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                if (ph.includes('observaciones')) {
                  clickBtnGuardar();
                } else {
                  var dest = siguienteInput(a);
                  if (dest) {
                    setTimeout(function() { dest.focus(); try { dest.select(); } catch(_) {} }, 60);
                  } else {
                    clickBtnGuardar();
                  }
                }
              } else if (e.key === 'ArrowRight' && !esSel && (esNum || a.selectionStart >= a.value.length)) {
                e.preventDefault(); e.stopPropagation(); moverFoco(a, 1);
              } else if (e.key === 'ArrowLeft' && !esSel && (esNum || a.selectionStart <= 0)) {
                e.preventDefault(); e.stopPropagation(); moverFoco(a, -1);
              }
              return;
            }

            if (!hayDataEditor()) return;
            var isNum = a.getAttribute('type') === 'number';
            var tab = function(sh) {
              a.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Tab', code: 'Tab', keyCode: 9, which: 9,
                shiftKey: !!sh, bubbles: true, cancelable: true, composed: true
              }));
            };
            if (e.key === 'Enter') {
              e.preventDefault(); e.stopPropagation(); _inGrid = true; tab(false);
            } else if (e.key === 'ArrowRight' && (isNum || a.selectionStart >= a.value.length)) {
              e.preventDefault(); e.stopPropagation(); tab(false);
            } else if (e.key === 'ArrowLeft' && (isNum || a.selectionStart <= 0)) {
              e.preventDefault(); e.stopPropagation(); tab(true);
            }
          };
          document.addEventListener('keydown', _qlKeyH, true);
          window._qlNavKeydown = _qlKeyH;

          /* ══════════════════════════════════════════════════════════
             HANDLER DIRECTO PARA st.form (LOGIN, ETC.)
             ──────────────────────────────────────────────────────────
             Adjunta el listener directamente a cada input dentro de
             un st.form. Bypasea cualquier interferencia del nivel
             document. Garantiza que Enter mueva al siguiente input
             del mismo form, o haga click en el submit si es el último.
          ══════════════════════════════════════════════════════════ */
          function _qlSetupForm(form) {
            var inputs = form.querySelectorAll('input,textarea');
            var subBtn = form.querySelector('button[type="submit"]')
                      || form.querySelector('[data-testid="stFormSubmitButton"] button')
                      || form.querySelector('button');
            for (var i = 0; i < inputs.length; i++) {
              var inp = inputs[i];
              var t = inp.getAttribute('type');
              if (t === 'hidden' || t === 'checkbox' || t === 'radio' ||
                  t === 'submit' || t === 'button' || t === 'file') continue;
              if (inp._qlFormBound) continue;
              inp._qlFormBound = true;
              var nextInp = null;
              for (var j = i + 1; j < inputs.length; j++) {
                var nt = inputs[j].getAttribute('type');
                if (nt === 'hidden' || nt === 'checkbox' || nt === 'radio' ||
                    nt === 'submit' || nt === 'button' || nt === 'file') continue;
                nextInp = inputs[j];
                break;
              }
              (function(next, btn) {
                inp.addEventListener('keydown', function(e) {
                  if (e.key !== 'Enter') return;
                  e.preventDefault();
                  e.stopPropagation();
                  if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                  if (next) {
                    setTimeout(function() {
                      next.focus();
                      try { next.select(); } catch(_) {}
                    }, 30);
                  } else if (btn) {
                    setTimeout(function() { btn.click(); }, 30);
                  }
                }, true);
              })(nextInp, subBtn);
            }
          }

          function _qlScanForms() {
            var forms = document.querySelectorAll('[data-testid="stForm"]');
            for (var i = 0; i < forms.length; i++) _qlSetupForm(forms[i]);
          }
          _qlScanForms();
          var _qlFormObs = new MutationObserver(_qlScanForms);
          _qlFormObs.observe(document.body, { childList: true, subtree: true });
          if (window._qlFormObs && window._qlFormObs.disconnect) window._qlFormObs.disconnect();
          window._qlFormObs = _qlFormObs;

        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
