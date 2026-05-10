from datetime import datetime
from config.constants import COL_TZ


def now_col() -> datetime:
    """Hora actual en zona horaria Colombia."""
    return datetime.now(tz=COL_TZ)
