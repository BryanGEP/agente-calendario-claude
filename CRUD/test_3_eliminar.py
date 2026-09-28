import sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(BASE_DIR)
ID_FILE = os.path.join(BASE_DIR, "last_event_id.txt")

from tools import Tools

tool = Tools()

with open(ID_FILE, "r", encoding="utf-8") as f:
    event_id = f.read().strip()

print(f"=== ELIMINANDO EVENTO {event_id} ===")
eliminado = tool.delete_event(event_id=event_id)
print(eliminado)
print("\n>>> Refresca Google Calendar: el evento ya no debe aparecer <<<")