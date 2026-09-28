import sys, os
from datetime import datetime, timedelta, timezone

# Permite importar tools.py desde la carpeta padre (raiz del proyecto)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)          # carpeta raiz (padre de CRUD)
sys.path.append(BASE_DIR)
ID_FILE = os.path.join(BASE_DIR, "last_event_id.txt")  # siempre en la raiz

from tools import Tools

tool = Tools()

# --- Fechas dinamicas: el evento se crea para MANANA de 5 a 7 pm ---
# Asi la prueba siempre agenda en el futuro, sin importar el dia en que la corra.
TZ = timezone(timedelta(hours=-6))              # zona horaria de Michoacan (-06:00)
manana = datetime.now(TZ) + timedelta(days=1)
inicio = manana.replace(hour=17, minute=0, second=0, microsecond=0)
fin = manana.replace(hour=19, minute=0, second=0, microsecond=0)
time_ini = inicio.isoformat()                   # ej: 2026-09-28T17:00:00-06:00
time_end = fin.isoformat()

print("=== CREANDO EVENTO ===")
creado = tool.create_event(
    summary="Prueba ciclo de vida",
    time_ini=time_ini,
    time_end=time_end,
    description="Evento de prueba",
    location="Mi casa",
)
print(creado)

# Guardamos el ID en un archivo para reutilizarlo en los otros scripts
if creado.get("event_id"):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(creado["event_id"])
    print("\nID guardado en last_event_id.txt")
    print(f">>> Ahora ve a Google Calendar y busca el evento el {inicio.strftime('%d de %B')} <<<")