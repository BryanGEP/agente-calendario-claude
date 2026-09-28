from dotenv import load_dotenv
from anthropic import Anthropic         
import os
import json
from datetime import datetime

from simple_memory import SimpleMemory
from tools import Tools  

load_dotenv()

# El SDK de Anthropic lee automaticamente la variable ANTHROPIC_API_KEY.
# Basta con tenerla en el .env; ni siquiera hace falta pasarla a mano.
# Si prefieres pasarla explicita:  Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = Anthropic()

memory = SimpleMemory(max_messages=10)
calendar = Tools()   # instancia real que ejecuta las acciones en Google Calendar

# Modelos de pago disponibles (autoservicio) a sept-2026. Cambia solo esta linea:
#   "claude-haiku-4-5-20251001"  -> el mas barato ($1 / $5 por millon de tokens)
#   "claude-sonnet-5"            -> equilibrio precio/capacidad ($2 / $10)  <- recomendado
#   "claude-opus-5"              -> el mas potente ($5 / $25)
MODELO = "claude-sonnet-5"
MAX_TOOL_ROUNDS = 5   # tope de seguridad: evita bucles infinitos de herramientas
MAX_TOKENS = 1024     # NUEVO: Anthropic exige indicar el maximo de tokens de salida

# ---------------------------------------------------------------------------
# Definicion de las herramientas que el modelo puede usar
#
# CAMBIO IMPORTANTE respecto a Groq/OpenAI:
#   Groq envolvia cada tool en  {"type": "function", "function": {...}}
#   y usaba la clave "parameters".
#   Anthropic NO usa ese envoltorio: pones name/description directos
#   y el esquema va en "input_schema" (no "parameters").
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "check_availability",
        "description": (
            "Consulta la disponibilidad del calendario del usuario para un intervalo "
            "determinado. Usa esta herramienta cuando el usuario pregunte si tiene "
            "disponibilidad en una fecha u horario. Los parametros time_ini y time_end "
            "DEBEN estar en formato RFC3339 e incluir el offset de zona horaria. "
            "Ejemplo: 2026-09-15T00:00:00-06:00"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_ini": {
                    "type": "string",
                    "description": "La fecha de inicio para revisar disponibilidad en formato RFC3339."
                },
                "time_end": {
                    "type": "string",
                    "description": "La fecha fin para revisar disponibilidad en formato RFC3339."
                },
            },
            "required": ["time_ini", "time_end"]
        }
    },
    {
        "name": "create_event",
        "description": (
            "Crea un evento nuevo en el calendario del usuario. Usa esta herramienta cuando "
            "el usuario quiera agendar, crear o registrar una cita o evento. Antes de crear, "
            "la herramienta verifica que el horario este libre. Las fechas DEBEN estar en "
            "formato RFC3339 con offset de zona horaria. Ejemplo: 2026-09-15T17:00:00-06:00"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "El titulo o nombre del evento."
                },
                "time_ini": {
                    "type": "string",
                    "description": "Fecha y hora de inicio del evento en formato RFC3339."
                },
                "time_end": {
                    "type": "string",
                    "description": "Fecha y hora de fin del evento en formato RFC3339."
                },
                "description": {
                    "type": "string",
                    "description": "Descripcion opcional del evento."
                },
                "location": {
                    "type": "string",
                    "description": "Ubicacion opcional del evento."
                },
            },
            "required": ["summary", "time_ini", "time_end"]
        }
    },
    {
        "name": "list_events",
        "description": (
            "Lista los eventos del calendario dentro de un rango de fechas. Usa esta "
            "herramienta cuando el usuario pregunte que tiene agendado, o cuando necesites "
            "obtener el event_id de un evento para poder modificarlo o eliminarlo. "
            "Devuelve cada evento con su event_id. Las fechas DEBEN estar en formato RFC3339."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_ini": {
                    "type": "string",
                    "description": "Inicio del rango a listar en formato RFC3339."
                },
                "time_end": {
                    "type": "string",
                    "description": "Fin del rango a listar en formato RFC3339."
                },
            },
            "required": ["time_ini", "time_end"]
        }
    },
    {
        "name": "update_event",
        "description": (
            "Modifica un evento existente. Solo cambia los campos que le pases; los demas "
            "se quedan igual. REQUIERE el event_id del evento a modificar. Si no lo conoces, "
            "primero usa list_events para obtenerlo. Las fechas van en formato RFC3339."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "El ID del evento a modificar (se obtiene de create_event o list_events)."
                },
                "summary": {
                    "type": "string",
                    "description": "Nuevo titulo del evento (opcional)."
                },
                "time_ini": {
                    "type": "string",
                    "description": "Nueva fecha/hora de inicio en formato RFC3339 (opcional)."
                },
                "time_end": {
                    "type": "string",
                    "description": "Nueva fecha/hora de fin en formato RFC3339 (opcional)."
                },
                "description": {
                    "type": "string",
                    "description": "Nueva descripcion (opcional)."
                },
                "location": {
                    "type": "string",
                    "description": "Nueva ubicacion (opcional)."
                },
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "delete_event",
        "description": (
            "Elimina un evento del calendario. REQUIERE el event_id del evento a eliminar. "
            "Si no lo conoces, primero usa list_events para obtenerlo. Confirma con el "
            "usuario antes de eliminar si hay ambiguedad sobre cual evento borrar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "El ID del evento a eliminar (se obtiene de list_events)."
                },
            },
            "required": ["event_id"]
        }
    },
]

# Mapa que conecta el NOMBRE que usa el modelo con la FUNCION real de tu clase
FUNCIONES_DISPONIBLES = {
    "check_availability": calendar.check_availability,
    "create_event": calendar.create_event,
    "list_events": calendar.list_events,
    "update_event": calendar.update_event,
    "delete_event": calendar.delete_event,
}

# ---------------------------------------------------------------------------
# System prompt
#
# CAMBIO IMPORTANTE: en Anthropic el system prompt NO va dentro de "messages"
# como un mensaje con role "system". Va en un parametro aparte: system=...
# (lo veras mas abajo en client.messages.create).
# ---------------------------------------------------------------------------
ahora = datetime.now().astimezone()
fecha_hoy = ahora.strftime("%Y-%m-%d %H:%M:%S")
dia_semana = ahora.strftime("%A")

SYSTEM_PROMPT = (
    "Eres un asistente que gestiona el calendario de Google del usuario. "
    f"La fecha y hora actual es: {fecha_hoy} ({dia_semana}). "
    "El usuario se encuentra en la zona horaria de Michoacan, Mexico, con offset -06:00. "
    "Cuando el usuario mencione fechas u horas relativas como 'hoy', 'manana', "
    "'el proximo lunes' o 'a las 5 de la tarde', calcula tu mismo la fecha completa "
    "en formato RFC3339 usando el offset -06:00. NUNCA le pidas al usuario la zona "
    "horaria; ya la conoces. Solo pide aclaraciones si la fecha o la hora son "
    "realmente ambiguas."
)


def ejecutar_tool_call(block):
    """Ejecuta una herramienta pedida por el modelo y devuelve un bloque
    'tool_result' listo para mandarlo de vuelta a Claude.

    CAMBIO respecto a Groq: los argumentos (block.input) YA vienen como dict
    de Python, no como texto JSON. Aqui NO hace falta json.loads."""
    nombre = block.name
    argumentos = block.input   # ya es un dict

    print(f"  [El modelo llamo a: {nombre}({argumentos})]")

    funcion = FUNCIONES_DISPONIBLES.get(nombre)
    if funcion:
        try:
            resultado = funcion(**argumentos)   # ejecutamos tu funcion real
        except Exception as e:
            resultado = {"success": False, "error": str(e)}
    else:
        resultado = {"success": False, "error": f"Funcion desconocida: {nombre}"}

    # El content de un tool_result debe ser texto (string). Como tus funciones
    # devuelven dicts, los serializamos a JSON.
    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(resultado, ensure_ascii=False),
    }


# ---------------------------------------------------------------------------
# Bucle principal de conversacion
# ---------------------------------------------------------------------------
print("Mi primer agente de IA con Claude (escribe 'salir' para terminar)")

while True:

    user_input = input("Tu: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ('exit', 'salir'):
        print("Hasta luego")
        break

    # Copia defensiva de la memoria. OJO: aqui ya NO insertamos el system prompt;
    # en Anthropic va aparte. messages solo lleva turnos user/assistant.
    messages = list(memory.messages())
    messages.append({"role": "user", "content": user_input})

    assistant_text = ""

    # --- Bucle de herramientas: seguimos llamando al modelo mientras pida tools ---
    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.messages.create(
            model=MODELO,
            max_tokens=MAX_TOKENS,     # obligatorio en Anthropic
            system=SYSTEM_PROMPT,      # el system prompt va aqui, no en messages
            tools=TOOLS,               # SIEMPRE pasamos las tools, en cada ronda
            messages=messages,
        )

        # Si el modelo NO pidio herramientas, ya tiene la respuesta final.
        # En Anthropic esto se detecta con stop_reason != "tool_use".
        if resp.stop_reason != "tool_use":
            # resp.content es una LISTA de bloques; juntamos el texto.
            assistant_text = "".join(
                b.text for b in resp.content if b.type == "text"
            )
            break

        # Si pidio herramientas, guardamos su turno completo (incluye los
        # bloques tool_use) y luego ejecutamos cada herramienta.
        messages.append({"role": "assistant", "content": resp.content})

        # Los resultados de TODAS las tools de esta ronda van juntos
        # en UN solo mensaje con role "user".
        tool_results = [
            ejecutar_tool_call(block)
            for block in resp.content
            if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})
        # Damos otra vuelta para que el modelo decida el siguiente paso.
    else:
        # Se agotaron las rondas sin una respuesta de texto final
        assistant_text = (
            "Lo siento, la tarea requirio demasiados pasos y la detuve por seguridad. "
            "Intenta pedirmelo de nuevo de forma mas simple."
        )

    print(f"Asistente: {assistant_text}")

    # Guardar en memoria el turno del usuario y la respuesta final del asistente
    # (igual que antes: solo texto plano, sin los bloques intermedios de tools)
    memory.add("user", user_input)
    memory.add("assistant", assistant_text)