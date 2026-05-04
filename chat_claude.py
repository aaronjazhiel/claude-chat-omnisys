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
        "description": "Ejecuta un comando del sistema (hora, fecha, cálculos).",
        "input_schema": {
            "type": "object",
            "properties": {"comando": {"type": "string", "description": "Comando a ejecutar"}},
            "required": ["comando"]
        }
    },
    {
        "name": "listar_archivos",
        "description": "Lista archivos del repositorio SICA filtrando por extensión (.4gl, .sql, .per, .md, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {"extension": {"type": "string", "description": "Extensión a filtrar"}},
            "required": ["extension"]
        }
    },
    {
        "name": "listar_carpetas",
        "description": "Lista las carpetas/módulos del repositorio SICA para explorar su estructura.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta de la carpeta. Usa '' para la raíz.", "default": ""}
            }
        }
    },
    {
        "name": "leer_archivo",
        "description": "Lee el contenido de un archivo del repositorio SICA. Para archivos grandes, devuelve las primeras 50,000 caracteres. Si necesitas más, usa leer_archivo_parte.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Ruta del archivo"}},
            "required": ["path"]
        }
    },
    {
        "name": "leer_archivo_parte",
        "description": "Lee una parte específica de un archivo grande. Útil para archivos .4gl o .sql que superan 50K caracteres. Especifica desde qué carácter empezar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta del archivo"},
                "inicio": {"type": "integer", "description": "Carácter desde donde empezar a leer (0 = inicio)", "default": 0}
            },
            "required": ["path"]
        }
    },
    {
        "name": "leer_multiples_archivos",
        "description": "Lee varios archivos de una vez. Útil para analizar un módulo completo o comparar programas relacionados. Máximo 5 archivos por llamada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de rutas de archivos (máximo 5)",
                    "maxItems": 5
                }
            },
            "required": ["paths"]
        }
    },
    {
        "name": "buscar_codigo",
        "description": "Busca un término dentro del código fuente del repositorio SICA. Devuelve hasta 30 archivos donde aparece el término.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Texto a buscar (función, SP, tabla, variable, etc.)"}},
            "required": ["query"]
        }
    }
]

COMANDOS_PERMITIDOS = ["date", "TZ=", "echo", "cal", "whoami", "uname", "python3 -c"]
MAX_CHARS = 50000
CHUNK_SIZE = 50000


def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def leer_archivo_github(path, inicio=0):
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{path}", headers=github_headers())
    if r.status_code != 200:
        return f"Error: archivo '{path}' no encontrado"
    contenido = base64.b64decode(r.json()["content"]).decode("utf-8")
    total = len(contenido)
    fragmento = contenido[inicio:inicio + CHUNK_SIZE]
    if total > inicio + CHUNK_SIZE:
        return f"{fragmento}\n\n--- ARCHIVO TRUNCADO: mostrando caracteres {inicio}-{inicio + CHUNK_SIZE} de {total} total. Usa leer_archivo_parte con inicio={inicio + CHUNK_SIZE} para continuar. ---"
    return fragmento


def ejecutar_tool(name, inputs):
    try:
        if name == "ejecutar_comando":
            cmd = inputs["comando"]
            if not any(cmd.startswith(c) for c in COMANDOS_PERMITIDOS):
                return "Comando no permitido por seguridad."
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout or r.stderr or "(sin salida)"

        elif name == "listar_archivos":
            r = requests.get(f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1", headers=github_headers())
            tree = r.json().get("tree", [])
            archivos = [f["path"] for f in tree if f["path"].endswith(inputs["extension"])]
            return json.dumps({"total": len(archivos), "archivos": archivos}, ensure_ascii=False)

        elif name == "listar_carpetas":
            path = inputs.get("path", "")
            r = requests.get(f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1", headers=github_headers())
            tree = r.json().get("tree", [])
            carpetas = set()
            for f in tree:
                p = f["path"]
                if path and not p.startswith(path + "/"):
                    continue
                resto = p[len(path):].lstrip("/") if path else p
                parte = resto.split("/")[0]
                if "/" in resto:
                    carpetas.add(parte + "/")
                else:
                    carpetas.add(parte)
            return json.dumps(sorted(carpetas), ensure_ascii=False)

        elif name == "leer_archivo":
            return leer_archivo_github(inputs["path"])

        elif name == "leer_archivo_parte":
            return leer_archivo_github(inputs["path"], inputs.get("inicio", 0))

        elif name == "leer_multiples_archivos":
            paths = inputs["paths"][:5]
            resultados = {}
            for p in paths:
                contenido = leer_archivo_github(p)
                # Limitar cada archivo a 15K cuando se leen múltiples
                resultados[p] = contenido[:15000] + (f"\n--- TRUNCADO a 15K de {len(contenido)} chars ---" if len(contenido) > 15000 else "")
            return json.dumps(resultados, ensure_ascii=False)

        elif name == "buscar_codigo":
            r = requests.get(
                f"https://api.github.com/search/code?q={inputs['query']}+repo:{REPO}&per_page=30",
                headers=github_headers()
            )
            data = r.json()
            items = data.get("items", [])
            total = data.get("total_count", 0)
            resultado = [{"archivo": i["path"], "url": i["html_url"]} for i in items[:30]]
            return json.dumps({"total_encontrados": total, "mostrando": len(resultado), "resultados": resultado}, ensure_ascii=False)

    except Exception as e:
        return f"Error: {e}"
    return "Tool no reconocida"


sesiones = {}
MAX_HISTORIAL = 12


def compactar_historial(historial):
    """Reemplaza tool_results pesados con resumenes cortos para ahorrar tokens."""
    for msg in historial:
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for item in msg["content"]:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    contenido = item.get("content", "")
                    if len(contenido) > 300:
                        item["content"] = contenido[:300] + f"\n... [compactado: {len(contenido)} chars]"


def recortar_historial(historial):
    """Mantiene solo los últimos MAX_HISTORIAL mensajes."""
    if len(historial) > MAX_HISTORIAL:
        # Siempre empezar con un mensaje de user
        recortado = historial[-MAX_HISTORIAL:]
        while recortado and recortado[0]["role"] != "user":
            recortado.pop(0)
        historial.clear()
        historial.extend(recortado)


def limpiar_sesion(session_id="default"):
    if session_id in sesiones:
        sesiones[session_id] = []


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
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=historial
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        historial.append({"role": "assistant", "content": response.content})
                        # Compactar y recortar después de cada respuesta completa
                        compactar_historial(historial)
                        recortar_historial(historial)
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
                        if block.name not in ["ejecutar_comando"]:
                            archivos_leidos.append(json.dumps(block.input, ensure_ascii=False))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": resultado
                        })
                historial.append({"role": "user", "content": tool_results})

    except anthropic.RateLimitError:
        historial.pop()
        # Compactar agresivamente e intentar de nuevo
        compactar_historial(historial)
        if len(historial) > 6:
            recortado = historial[-6:]
            while recortado and recortado[0]["role"] != "user":
                recortado.pop(0)
            historial.clear()
            historial.extend(recortado)
        return {"respuesta": "La conversacion acumulo mucho contexto. Se limpio el historial automaticamente. Por favor, repite tu pregunta.", "archivos": [], "tools": []}
    except Exception as e:
        historial.pop()
        return {"respuesta": f"Error: {e}", "archivos": [], "tools": []}
