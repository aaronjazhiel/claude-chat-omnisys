import anthropic
import requests
import json
import os
import base64
import subprocess

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPO", "aaronjazhiel/mcp-sica-genero")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = open(os.path.join(os.path.dirname(__file__), "prompts/system_prompt.txt")).read()

tools = [
    {
        "name": "ejecutar_comando",
        "description": "Ejecuta un comando del sistema. Usa para hora, fecha, cálculos, etc.",
        "input_schema": {
            "type": "object",
            "properties": {"comando": {"type": "string", "description": "Comando a ejecutar"}},
            "required": ["comando"]
        }
    },
    {
        "name": "listar_archivos",
        "description": "Lista archivos del repositorio filtrando por extensión",
        "input_schema": {
            "type": "object",
            "properties": {"extension": {"type": "string", "description": "Extensión: .py .sql .md etc."}},
            "required": ["extension"]
        }
    },
    {
        "name": "leer_archivo",
        "description": "Lee el contenido completo de un archivo del repositorio",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Ruta del archivo"}},
            "required": ["path"]
        }
    },
    {
        "name": "buscar_codigo",
        "description": "Busca texto dentro del código fuente del repositorio",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Texto a buscar"}},
            "required": ["query"]
        }
    }
]

COMANDOS_PERMITIDOS = ["date", "TZ=", "echo", "cal", "whoami", "uname", "python3 -c"]

def ejecutar_tool(name, inputs):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        if name == "ejecutar_comando":
            cmd = inputs["comando"]
            if not any(cmd.startswith(c) for c in COMANDOS_PERMITIDOS):
                return "Comando no permitido por seguridad."
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout or r.stderr or "(sin salida)"

        elif name == "listar_archivos":
            r = requests.get(f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1", headers=headers)
            tree = r.json().get("tree", [])
            archivos = [f["path"] for f in tree if f["path"].endswith(inputs["extension"])]
            return json.dumps({"total": len(archivos), "archivos": archivos}, ensure_ascii=False)

        elif name == "leer_archivo":
            r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{inputs['path']}", headers=headers)
            if r.status_code != 200:
                return f"Error: archivo '{inputs['path']}' no encontrado"
            return base64.b64decode(r.json()["content"]).decode("utf-8")[:5000]

        elif name == "buscar_codigo":
            r = requests.get(f"https://api.github.com/search/code?q={inputs['query']}+repo:{REPO}", headers=headers)
            items = r.json().get("items", [])
            return json.dumps([{"archivo": i["path"], "url": i["html_url"]} for i in items[:10]], ensure_ascii=False)
    except Exception as e:
        return f"Error: {e}"
    return "Tool no reconocida"


# Historial por sesión (en memoria)
sesiones = {}

def consultar(pregunta, session_id="default"):
    if session_id not in sesiones:
        sesiones[session_id] = []
    historial = sesiones[session_id]
    historial.append({"role": "user", "content": pregunta})

    archivos_leidos = []
    tools_usadas = []

    try:
        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=historial
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        historial.append({"role": "assistant", "content": response.content})
                        return {
                            "respuesta": block.text,
                            "archivos": archivos_leidos,
                            "tools": tools_usadas
                        }

            if response.stop_reason == "tool_use":
                historial.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tools_usadas.append(block.name)
                        resultado = ejecutar_tool(block.name, block.input)
                        if block.name in ["leer_archivo", "buscar_codigo"]:
                            archivos_leidos.append(json.dumps(block.input, ensure_ascii=False))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": resultado
                        })
                historial.append({"role": "user", "content": tool_results})

    except Exception as e:
        historial.pop()
        return {"respuesta": f"Error: {e}", "archivos": [], "tools": []}
