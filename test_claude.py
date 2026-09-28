from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()   # lee ANTHROPIC_API_KEY del .env

resp = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "Responde solo con: conexión exitosa"}],
)

print(resp.content[0].text)