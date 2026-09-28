# --- Librería estándar de Python ---
import os
# Revisa si existen archivos en disco (token.json, credentials.json)

# --- Librerías de Google para autenticación OAuth ---

from google.auth.transport.requests import Request
# Permite refrescar un token expirado usando el refresh_token

from google.oauth2.credentials import Credentials
# Carga credenciales OAuth ya guardadas desde token.json (no crea nuevas)

from google_auth_oauthlib.flow import InstalledAppFlow
# Ejecuta el flujo de autorización OAuth para apps de escritorio:
# abre el navegador, pide login/consentimiento y genera credenciales nuevas

from googleapiclient.discovery import build
# Construye el objeto "servicio" para llamar a la API de Google Calendar

class Tools:
    def __init__(self):
        # Permisos solicitados: acceso completo (lectura/escritura) al calendario
        self.SCOPES = ["https://www.googleapis.com/auth/calendar"]
        # Archivo con las credenciales OAuth de la app (Client ID/Secret)
        self.CREDENTIALS_FILE = "credentials.json"
        # Archivo donde se guarda el token de acceso ya autorizado
        self.TOKEN_FILE = "token.json"

    def get_calendar_service(self):
        creds = None

        # Si ya existe un token guardado, lo cargamos
        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

        # Si no hay credenciales válidas, autorizar de nuevo o refrescar el token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # el token expiró pero se puede renovar
            else:
                if not os.path.exists(self.CREDENTIALS_FILE):
                    raise FileNotFoundError("No se encontró el archivo de credenciales!")
                # Abre el navegador para que el usuario inicie sesión y dé consentimiento
                flow = InstalledAppFlow.from_client_secrets_file(self.CREDENTIALS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Guardamos el token generado para no repetir el login la próxima vez
            with open(self.TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        # Regresamos el objeto "servicio" ya listo para usar la API de Calendar
        return build("calendar", "v3", credentials=creds)
    
    def check_availability(self, time_ini: str, time_end: str):
        print(f"Llamando herramienta check_availability({time_ini}, {time_end})")

        # Variable de la solicitud hacia la API de Google
        body = {
            "timeMin": time_ini,
            "timeMax": time_end,
            "items": [
                {"id": "primary"}  # Solo se está considerando UN calendario
            ]
        }

        # Obtenemos el servicio del calendario
        service = self.get_calendar_service()

        # Realizamos la consulta
        result = service.freebusy().query(body=body).execute()

        # De toda la respuesta, solo nos interesa la lista de eventos ocupados
        busy = result.get("calendars", {}).get("primary", {}).get("busy", [])

        # Regresamos datos estructurados que los modelos de lenguaje entienden bien
        return {
            "success":True,
            "calendar_id": "primary",
            "time_ini": time_ini,
            "time_end": time_end,
            "busy": busy,
            "is_free": (len(busy) == 0)
        }
    
    def create_event(self,summary:str,time_ini:str,time_end:str,description:str='',location:str=''):
        print(f"Llamada a la función create_event({summary},{time_ini},{time_end},{description},{location})")
        availabity=self.check_availability(time_ini,time_end)
        if not availabity["is_free"]:
            return{
                "success": False,
                "error": "El horario no esta disponible",
                "time_ini": time_ini,
                "time_end": time_end,
                "busy": availabity["busy"]
            }
        #Crear el body con los datos para crear el evento
        body={
            "summary":summary,
            "description":description,
            "location":location,
            "start":{"dateTime":time_ini},
            "end":{"dateTime":time_end}
        }
        #Obtener el servicio
        service=self.get_calendar_service()
        event=service.events().insert(calendarId='primary',body=body).execute()
        return{
            "success":True,
            "event_id":event.get("id"),
            "html_link":event.get("htmlLink"),
            "summary":event.get("summary"),
            "time_ini":time_ini,
            "time_end":time_end
        }

    def list_events(self, time_ini: str, time_end: str, max_results: int = 10, query: str = None):
        print(f"Llamando herramienta list_events({time_ini}, {time_end})")
        service = self.get_calendar_service()

        params = {
            "calendarId": "primary",
            "timeMin": time_ini,
            "timeMax": time_end,
            "maxResults": max_results,
            "singleEvents": True,    # expande eventos recurrentes en instancias individuales
            "orderBy": "startTime",  # OJO: solo es válido si singleEvents=True
        }
        if query:
            params["q"] = query  # búsqueda por texto en título/descripción/etc.

        result = service.events().list(**params).execute()
        items = result.get("items", [])

        # Aplanamos la respuesta a algo limpio para el modelo
        events = [
            {
                "event_id": e.get("id"),
                "summary": e.get("summary"),
                "description": e.get("description"),
                "location": e.get("location"),
                # Un evento puede ser con hora (dateTime) o de todo el día (date)
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "html_link": e.get("htmlLink"),
            }
            for e in items
        ]

        return {
            "success": True,
            "count": len(events),
            "time_ini": time_ini,
            "time_end": time_end,
            "events": events,
        }

    def update_event(self, event_id: str, summary=None, time_ini=None,
                 time_end=None, description=None, location=None):
        print(f"Llamando herramienta update_event({event_id})")
        service = self.get_calendar_service()

        body = {}
        if summary is not None:     
            body["summary"] = summary
        if description is not None:  
            body["description"] = description
        if location is not None:     
            body["location"] = location
        if time_ini is not None:    
            body["start"] = {"dateTime": time_ini}
        if time_end is not None:     
            body["end"] = {"dateTime": time_end}

        if not body:
            return {"success": False, "error": "No se especificó ningún campo a modificar"}

        try:
            event = service.events().patch(
                calendarId="primary", eventId=event_id, body=body,
            ).execute()
            return {
                "success": True,
                "event_id": event.get("id"),
                "html_link": event.get("htmlLink"),
                "summary": event.get("summary"),
            }
        except Exception as e:
            return {"success": False, "event_id": event_id, "error": str(e)}
    
    def delete_event(self, event_id: str):
        print(f"Llamando herramienta delete_event({event_id})")
        service = self.get_calendar_service()

        try:
            # delete NO regresa cuerpo: si sale bien, responde vacío (HTTP 204)
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return {
                "success": True,
                "event_id": event_id,
                "message": "Evento eliminado correctamente",
            }
        except Exception as e:
            return {
                "success": False,
                "event_id": event_id,
                "error": str(e),
            }


"""
if __name__ == "__main__":
    import time
    tool = Tools()

    time_ini = "2026-09-15T17:00:00-06:00"
    time_end = "2026-09-15T19:00:00-06:00"

    # 1) CREAR --------------------------------------------------------------
    print("\n=== 1. CREAR EVENTO ===")
    creado = tool.create_event(
        summary="Prueba ciclo de vida",
        time_ini=time_ini,
        time_end=time_end,
        description="Evento de prueba",
        location="Mi casa",
    )
    print(creado)

    # Guardamos el ID que devuelve create para usarlo en update y delete
    event_id = creado.get("event_id")
    if not event_id:
        print("No se pudo crear el evento, deteniendo prueba.")
        exit()

    # 2) LISTAR -------------------------------------------------------------
    print("\n=== 2. LISTAR EVENTOS ===")
    listado = tool.list_events(
        time_ini="2026-09-15T00:00:00-06:00",
        time_end="2026-09-16T00:00:00-06:00",
    )
    print(f"Se encontraron {listado['count']} eventos:")
    for e in listado["events"]:
        print(f"  - {e['summary']} ({e['start']}) -> {e['event_id']}")

    # 3) MODIFICAR ----------------------------------------------------------
    print("\n=== 3. MODIFICAR EVENTO ===")
    modificado = tool.update_event(
        event_id=event_id,
        summary="Prueba MODIFICADA",       # cambiamos solo el título
        location="Nueva ubicacion",        # y la ubicación
        # no mandamos las horas: se quedan igual (patch semantics)
    )
    print(modificado)

    # 4) ELIMINAR -----------------------------------------------------------
    print("\n=== 4. ELIMINAR EVENTO ===")
    time.sleep(1)  # pequeña pausa opcional para que se vea en el calendario
    eliminado = tool.delete_event(event_id=event_id)
    print(eliminado)

    # 5) VERIFICAR que ya no existe ----------------------------------------
    print("\n=== 5. VERIFICAR ELIMINACION ===")
    verificar = tool.list_events(
        time_ini="2026-09-15T00:00:00-06:00",
        time_end="2026-09-16T00:00:00-06:00",
    )
    print(f"Eventos restantes en ese rango: {verificar['count']}")
"""