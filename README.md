# 🗓️ Agente de IA para Google Calendar

Agente conversacional en Python que gestiona tu **Google Calendar** mediante lenguaje
natural, usando la **API de Claude (Anthropic)** con *tool use* (function calling).

Escribes cosas como *"agéndame una reunión mañana a las 5"* o *"¿qué tengo esta semana?"*
y el modelo decide qué herramienta llamar (consultar, crear, listar, modificar o eliminar
eventos) y ejecuta la acción real sobre tu calendario.

## ✨ Características

- Conversación en lenguaje natural, con cálculo automático de fechas relativas
  ("hoy", "mañana", "el próximo lunes") en la zona horaria configurada.
- CRUD completo sobre Google Calendar: **crear, consultar, listar, modificar y eliminar** eventos.
- Encadenamiento de herramientas: por ejemplo, para modificar un evento el agente primero
  lo busca (`list_events`) para obtener su ID y luego lo actualiza (`update_event`), en una
  sola instrucción del usuario.
- Verificación de disponibilidad antes de crear un evento (evita empalmes).
- Memoria de conversación de corto plazo (últimos mensajes).

## 🧰 Tecnologías

- **Python 3.13**
- **Anthropic** — API de Claude (modelo `claude-sonnet-5`)
- **Google Calendar API** (OAuth 2.0)
- `python-dotenv` para el manejo de variables de entorno

## 📁 Estructura del proyecto

```
.
├── agente1.py            # Bucle principal del agente y definición de herramientas
├── tools.py              # Clase Tools: acciones reales sobre Google Calendar
├── simple_memory.py      # Memoria de conversación de corto plazo
├── CRUD/                 # Pruebas de la capa de calendario (sin usar el modelo)
│   ├── test_1_crear.py
│   ├── test_2_modificar.py
│   ├── test_3_eliminar.py
│   └── test_4_listar.py
├── requirements.txt
├── .env                  # (NO se sube) Clave de la API de Claude
├── credentials.json      # (NO se sube) Credenciales OAuth de Google
└── token.json            # (NO se sube) Token OAuth generado tras el primer login
```

## ✅ Requisitos previos

1. **Python 3.13** instalado.
2. Una **clave de API de Claude**, obtenida en [console.anthropic.com](https://console.anthropic.com)
   (requiere créditos de uso).
3. Un proyecto de **Google Cloud** con la **Google Calendar API** habilitada y un archivo
   de credenciales OAuth de tipo *App de escritorio* (`credentials.json`).

## 🚀 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/BryanGEP/<nombre-del-repo>.git
cd <nombre-del-repo>

# 2. Crear y activar el entorno virtual
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate
# Linux / macOS:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

## 🔧 Configuración

1. **Clave de Claude.** Crea un archivo `.env` en la raíz del proyecto con:

   ```
   ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui
   ```

2. **Credenciales de Google.** Coloca tu archivo `credentials.json` (descargado de Google
   Cloud) en la raíz del proyecto. La primera vez que ejecutes el agente se abrirá el
   navegador para que autorices el acceso; al aceptar se generará automáticamente
   `token.json` y no volverá a pedirte permiso.

3. **Zona horaria.** El proyecto está configurado para Michoacán, México (offset `-06:00`).
   Si estás en otra zona, ajusta el `SYSTEM_PROMPT` en `agente1.py`.

## ▶️ Uso

```bash
python agente1.py
```

Ejemplos de lo que puedes pedirle:

- `¿Qué tengo agendado esta semana?`
- `¿Estoy libre mañana de 5 a 6 de la tarde?`
- `Agéndame una reunión de práctica mañana a las 5 de la tarde`
- `Cambia esa reunión para las 6 de la tarde`
- `Elimina la reunión de práctica`

Escribe `salir` para terminar.

## 🧪 Pruebas del calendario (carpeta `CRUD/`)

Estos scripts prueban directamente la capa de Google Calendar **sin llamar al modelo**
(por lo tanto, sin consumir créditos de Claude). Son útiles para verificar que la
integración con Calendar funciona de forma aislada. Ejecútalos en orden:

```bash
python CRUD/test_1_crear.py       # crea un evento de prueba (mañana) y guarda su ID
python CRUD/test_4_listar.py      # lista los eventos de mañana
python CRUD/test_2_modificar.py   # modifica el evento creado
python CRUD/test_3_eliminar.py    # elimina el evento creado
```

## 🔒 Seguridad

Los archivos `.env`, `credentials.json` y `token.json` contienen credenciales privadas y
**nunca deben subirse al repositorio** (están excluidos en `.gitignore`). Si una clave de
API se filtra públicamente, revócala de inmediato desde la consola y genera una nueva.

## 📄 Documentación adicional

- [Comparativa Anthropic (Claude) vs Groq](comparativa-anthropic-vs-groq.md)

## 👤 Autor

**Bryan Gael Esquivel Pérez** — [@BryanGEP](https://github.com/BryanGEP)
