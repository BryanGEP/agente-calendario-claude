# Anthropic (Claude) vs Groq — Comparativa técnica y práctica

> Documento basado en la migración de un mismo agente conversacional (gestión de Google
> Calendar con *tool use*) de la API de **Groq** a la API de **Anthropic (Claude)**.
> Datos de precios y velocidad verificados a **septiembre de 2026**; conviene revisarlos en
> las páginas oficiales antes de tomar decisiones, porque cambian con frecuencia.

---

## 1. La diferencia de fondo: no son lo mismo

Antes de comparar, hay que entender que **Groq y Anthropic juegan en categorías distintas**:

- **Anthropic** es un *laboratorio* que crea sus propios modelos de frontera (la familia
  Claude) y los ofrece a través de su propia API. Pagas por acceder a un modelo propietario.
- **Groq** es un *proveedor de inferencia*: no crea modelos, sino que ejecuta modelos de
  **pesos abiertos** (Llama, GPT-OSS, Qwen, etc.) sobre un hardware propio llamado **LPU**
  (Language Processing Unit), diseñado para que respondan a gran velocidad. El modelo que
  usábamos, `openai/gpt-oss-120b`, es un modelo *open-weight* de OpenAI servido por Groq.

En resumen: **Groq compite en velocidad y precio; Anthropic compite en capacidad del
modelo.** Por eso muchos equipos usan ambos (Groq para tareas rápidas y baratas, Claude
para razonamiento complejo).

---

## 2. Diferencias en el código (lo que cambió al migrar)

La API de Groq imita el formato de OpenAI; la de Anthropic tiene el suyo propio. Estos
fueron los cambios concretos al migrar el mismo agente.

| Aspecto | Groq (formato OpenAI) | Anthropic (Claude) |
|---|---|---|
| Librería | `from groq import Groq` | `from anthropic import Anthropic` |
| Variable de entorno | Nombre libre (ej. `Pk_GROQ`) | `ANTHROPIC_API_KEY` (el SDK la lee sola) |
| `max_tokens` | Opcional | **Obligatorio** en cada llamada |
| Método | `client.chat.completions.create(...)` | `client.messages.create(...)` |
| System prompt | Un mensaje más con `role: "system"` dentro de `messages` | Parámetro aparte: `system="..."` |
| Formato de tools | Envuelto en `{"type": "function", "function": {...}}`, esquema en `parameters` | Directo: `name`, `description` y esquema en `input_schema` |
| ¿Pidió herramienta? | Se revisa `msg.tool_calls` | Se revisa `resp.stop_reason == "tool_use"` |
| Argumentos de la tool | Texto JSON (hay que hacer `json.loads`) | Ya es un `dict` de Python (`block.input`) |
| Respuesta | `msg.content` (texto directo) | `resp.content` = **lista de bloques** (texto y/o `tool_use`) |
| Devolver resultado de tool | Mensaje con `role: "tool"` | Bloque `tool_result` dentro de un mensaje `role: "user"` |

### Ejemplos lado a lado

**Cliente e inicialización**

```python
# Groq
from groq import Groq
client = Groq(api_key=os.environ.get("Pk_GROQ"))

# Anthropic
from anthropic import Anthropic
client = Anthropic()   # lee ANTHROPIC_API_KEY del entorno automáticamente
```

**System prompt**

```python
# Groq: el system va como un mensaje más
messages = [{"role": "system", "content": SYSTEM_PROMPT}, ...]
resp = client.chat.completions.create(model=MODELO, messages=messages, tools=TOOLS)

# Anthropic: el system va en su propio parámetro
resp = client.messages.create(
    model=MODELO, max_tokens=1024,
    system=SYSTEM_PROMPT,          # <— aparte
    messages=messages, tools=TOOLS,
)
```

**Definición de una herramienta**

```python
# Groq (formato OpenAI)
{
    "type": "function",
    "function": {
        "name": "check_availability",
        "description": "...",
        "parameters": { "type": "object", "properties": {...} }
    }
}

# Anthropic
{
    "name": "check_availability",
    "description": "...",
    "input_schema": { "type": "object", "properties": {...} }
}
```

**Detectar y ejecutar la herramienta**

```python
# Groq
if msg.tool_calls:
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)   # viene como texto
        resultado = funciones[tc.function.name](**args)
        messages.append({"role": "tool", "tool_call_id": tc.id,
                         "content": json.dumps(resultado)})

# Anthropic
if resp.stop_reason == "tool_use":
    tool_results = []
    for block in resp.content:
        if block.type == "tool_use":
            args = block.input                     # ya es dict
            resultado = funciones[block.name](**args)
            tool_results.append({"type": "tool_result",
                                 "tool_use_id": block.id,
                                 "content": json.dumps(resultado)})
    messages.append({"role": "user", "content": tool_results})
```

> **Dato práctico:** como el código original ya estaba escrito en formato Groq/OpenAI,
> migrarlo a **OpenAI** habría requerido casi ningún cambio, mientras que migrarlo a
> **Anthropic** implicó los ajustes de arriba. Es el precio de cambiar de "familia" de API.

---

## 3. Diferencias de proveedor

### Modelos disponibles

- **Anthropic:** solo modelos Claude (propietarios). A sept-2026: Haiku 4.5, Sonnet 5,
  Opus 5, Fable 5.1.
- **Groq:** solo modelos de pesos abiertos (Llama, GPT-OSS, Qwen, DeepSeek, etc.). **No**
  ofrece Claude, GPT propietario ni Gemini.

### Precios (USD por millón de tokens, entrada / salida)

| Modelo | Proveedor | Entrada | Salida |
|---|---|---|---|
| GPT-OSS 120B | Groq | $0.15 | $0.60 |
| GPT-OSS 20B | Groq | $0.075 | $0.30 |
| Llama 3.3 70B | Groq | $0.59 | $0.79 |
| Claude Haiku 4.5 | Anthropic | $1.00 | $5.00 |
| Claude Sonnet 5 | Anthropic | $2.00 | $10.00 |
| Claude Opus 5 | Anthropic | $5.00 | $25.00 |

Groq es **claramente más barato por token** (el modelo que usábamos cuesta una fracción de
lo que cuesta cualquier Claude). Ambos ofrecen descuentos por caché de prompts (~50% en
Groq, hasta ~90% en Anthropic) y por procesamiento en lote (~50%).

### Velocidad

- **Groq** es su principal ventaja: su hardware LPU alcanza cientos de tokens por segundo
  (GPT-OSS 120B ~500 t/s; algunos modelos superan los 1,000 t/s), muy por encima de los
  50–100 t/s típicos de proveedores basados en GPU.
- **Anthropic** ofrece velocidades competitivas para su gama (y un "modo rápido" en algunos
  modelos), pero su punto fuerte no es la velocidad bruta sino la capacidad del modelo.

### Capacidad y fiabilidad (especialmente en *tool use*)

- **Anthropic (Claude)** tiene ventaja reportada en fiabilidad de llamadas a herramientas y
  en seguir instrucciones con precisión, lo que lo hace muy sólido para agentes que encadenan
  varias herramientas (como buscar un evento y luego modificarlo).
- **GPT-OSS 120B en Groq** es un modelo capaz y con buen soporte de *tool use*, pero al ser
  un modelo abierto de tamaño medio puede ser menos consistente que un modelo de frontera en
  tareas de razonamiento difícil o encadenamientos largos.

### Nivel gratuito

- **Groq:** tiene un *free tier* (con límites de peticiones y tokens por minuto/día) que
  permite probar sin tarjeta.
- **Anthropic:** la API funciona con créditos de prepago; no hay un nivel gratuito
  equivalente para la API (aunque sí se puede empezar con un monto pequeño, como $5).

---

## 4. Ventajas y desventajas

### Groq

**Ventajas**
- Velocidad de respuesta muy alta (ideal para experiencias en tiempo real).
- Precio por token muy bajo.
- Nivel gratuito para prototipar sin tarjeta.
- Compatible con el formato de OpenAI (fácil de migrar desde/hacia OpenAI).

**Desventajas**
- Solo modelos de pesos abiertos; sin acceso a modelos de frontera propietarios.
- Menor consistencia posible en razonamiento complejo frente a un modelo top.
- Dependes de qué modelos abiertos decida hostear Groq (pueden cambiar o retirarse).

### Anthropic (Claude)

**Ventajas**
- Modelos de frontera con razonamiento y fiabilidad de primer nivel.
- Muy sólido en *tool use* y en seguir instrucciones al pie de la letra.
- Ecosistema maduro (caché de prompts con control fino, contexto amplio, buena documentación).

**Desventajas**
- Más caro por token que Groq.
- Sin nivel gratuito para la API (requiere créditos de prepago).
- API con formato propio: migrar desde formato OpenAI exige ajustes de código.

---

## 5. ¿Cuándo usar cada uno?

- **Elige Groq** cuando la prioridad sea **velocidad y costo bajo**, la tarea sea sencilla o
  de alto volumen (clasificación, respuestas rápidas, prototipos), o quieras probar sin
  tarjeta.
- **Elige Anthropic (Claude)** cuando la prioridad sea **calidad de razonamiento y
  fiabilidad**, sobre todo en agentes que **encadenan herramientas** o toman decisiones
  delicadas.
- **Estrategia híbrida (habitual en producción):** un *router* que manda las tareas fáciles
  y masivas a un modelo rápido y barato (Groq) y reserva las difíciles para un modelo de
  frontera (Claude). Reduce costos sin sacrificar calidad donde importa.

---

## 6. Conclusión

Para el caso de este proyecto —un agente de calendario que debe interpretar fechas y
encadenar herramientas de forma confiable— **Claude aporta más fiabilidad**, a cambio de un
costo por token mayor (que, en volúmenes de práctica, es de apenas unos centavos). **Groq**
sigue siendo una opción excelente cuando pesan más la velocidad y el precio. No existe un
"mejor" absoluto: la elección correcta depende de la carga de trabajo, y saber trabajar con
ambos formatos de API es en sí mismo una habilidad valiosa.
