import sys, os
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(BASE_DIR)
ID_FILE = os.path.join(BASE_DIR, "last_event_id.txt")

from tools import Tools
tool = Tools()

# Leemos el ID que guardo el script de crear
with open(ID_FILE, "r", encoding="utf-8") as f:
    event_id = f.read().strip()

# --- Movemos el evento a MANANA de 6 a 8 pm ---
TZ = timezone(timedelta(hours=-6))
manana = datetime.now(TZ) + timedelta(days=1)
inicio = manana.replace(hour=18, minute=0, second=0, microsecond=0)
fin = manana.replace(hour=20, minute=0, second=0, microsecond=0)

print(f"=== MODIFICANDO EVENTO {event_id} ===")
modificado = tool.update_event(
    event_id=event_id,
    summary="Prueba MODIFICADA",       # cambiamos el titulo
    location="Nueva ubicacion",        # y la ubicacion
    time_ini=inicio.isoformat(),       # movemos la hora a las 6 pm
    time_end=fin.isoformat(),          # y termina a las 8 pm
)
print(modificado)
print("\n>>> Refresca Google Calendar: el titulo, ubicacion y hora deben haber cambiado <<<")