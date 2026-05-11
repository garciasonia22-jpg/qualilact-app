import json
import os
from datetime import datetime, date

import streamlit as st

from config.constants import DRAFT_PATH, DRAFT_EXACT_KEYS, DRAFT_PREFIXES


def _draft_encode(value):
    if isinstance(value, datetime):
        return {"__draft_type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__draft_type": "date", "value": value.isoformat()}
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _draft_decode(value):
    if isinstance(value, dict) and value.get("__draft_type") in ("date", "datetime"):
        raw = value.get("value", "")
        try:
            return datetime.fromisoformat(raw).date()
        except Exception:
            return date.today()
    return value


def restore_draft_state():
    if st.session_state.get("_draft_restored"):
        return
    st.session_state["_draft_restored"] = True
    if not os.path.exists(DRAFT_PATH):
        return
    try:
        with open(DRAFT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    if "tipo_servicio_select" not in data and "_tipo_servicio_guardado" in data:
        data["tipo_servicio_select"] = data.get("_tipo_servicio_guardado")
    if "sub_tipo_seg_select" not in data and "_sub_tipo_seg_guardado" in data:
        data["sub_tipo_seg_select"] = data.get("_sub_tipo_seg_guardado")
    for key, value in data.items():
        if key not in st.session_state:
            st.session_state[key] = _draft_decode(value)


def save_draft_state():
    if st.session_state.pop("_skip_draft_save_once", False):
        return
    data = {}
    for key in DRAFT_EXACT_KEYS:
        if key in st.session_state:
            data[key] = _draft_encode(st.session_state[key])
    for key, value in st.session_state.items():
        if key.startswith(DRAFT_PREFIXES):
            data[key] = _draft_encode(value)
    try:
        with open(DRAFT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_draft_state():
    st.session_state["_skip_draft_save_once"] = True
    try:
        if os.path.exists(DRAFT_PATH):
            os.remove(DRAFT_PATH)
    except Exception:
        pass
