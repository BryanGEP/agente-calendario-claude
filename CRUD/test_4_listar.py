import sys, os
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(BASE_DIR)

from tools import Tools

tool = Tools()

# --- Listamos todos los eventos de MANANA (de 00:00 a 00:00 del dia siguiente) ---
TZ = timezone(timedelta(hours=-6))
manana = datetime.now(TZ) + timedelta(days=1)
inicio = manana.replace(hour=0, minute=0, second=0, microsecond=0)
fin = inicio + timedelta(days=1)

print("=== LISTANDO EVENTOS ===")
listado = tool.list_events(
    time_ini=inicio.isoformat(),
    time_end=fin.isoformat(),
)

print(f"Se encontraron {listado['count']} eventos:\n")
for e in listado["events"]:
    print(f"  - {e['summary']}")
    print(f"    Inicio: {e['start']}")
    print(f"    ID:     {e['event_id']}")
    print()