import anthropic
import json
import os
import subprocess
import glob
import time

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_REPO_URL = os.environ.get("GITHUB_REPO_URL", "https://github.com/aaronjazhiel/mcp-sica-genero.git")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
REPO_DIR = os.path.join(os.path.dirname(__file__), "repo_local")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
SYSTEM_PROMPT = open(os.path.join(os.path.dirname(__file__), "prompts/system_prompt.txt")).read()


def clonar_repo():
    if os.path.exists(REPO_DIR):
        return
    print(f"Clonando {GITHUB_REPO_URL} ...")
    subprocess.run(["git", "clone", "--depth", "1", GITHUB_REPO_URL, REPO_DIR],
                    capture_output=True, timeout=300)
    print("Repo clonado.")

clonar_repo()


tools = [
    {
        "name": "ejecutar_comando",
        "description": "Ejecuta un comando del sistema (hora, fecha, calculos).",
        "input_schema": {
            "type": "object",
            "properties": {"comando": {"type": "string", "description": "Comando a ejecutar"}},
            "required": ["comando"]
        }
    },
    {
        "name": "listar_archivos",
        "description": "Lista archivos del repositorio SICA filtrando por extension.",
        "input_schema": {
            "type": "object",
            "properties": {"extension": {"type": "string", "description": "Extension a filtrar"}},
            "required": ["extension"]
        }
    },
    {
        "name": "listar_carpetas",
        "description": "Lista las carpetas/modulos del repositorio SICA.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta de la carpeta. '' para raiz.", "default": ""}
            }
        }
    },
    {
        "name": "leer_archivo",
        "description": "Lee el contenido completo de un archivo del repositorio SICA.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Ruta del archivo"}},
            "required": ["path"]
        }
    },
    {
        "name": "leer_multiples_archivos",
        "description": "Lee varios archivos de una vez. Maximo 5.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}, "description": "Rutas (max 5)", "maxItems": 5}
            },
            "required": ["paths"]
        }
    },
    {
        "name": "buscar_codigo",
        "description": "Busca un termino dentro del codigo fuente del repositorio SICA.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Texto a buscar"}},
            "required": ["query"]
        }
    }
]

COMANDOS_PERMITIDOS = ["date", "TZ=", "echo", "cal", "whoami", "uname", "python3 -c"]

TOOL_LABELS = {
    "buscar_codigo": "Buscando en el codigo",
    "leer_archivo": "Leyendo archivo",
    "leer_multiples_archivos": "Leyendo multiples archivos",
    "listar_archivos": "Listando archivos",
    "listar_carpetas": "Explorando carpetas",
    "ejecutar_comando": "Ejecutando comando"
}


def ejecutar_tool(name, inputs):
    try:
        if name == "ejecutar_comando":
            cmd = inputs["comando"]
            if not any(cmd.startswith(c) for c in COMANDOS_PERMITIDOS):
                return "Comando no permitido por seguridad."
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout or r.stderr or "(sin salida)"

        elif name == "listar_archivos":
            ext = inputs["extension"]
            archivos = []
            for f in glob.glob(f"{REPO_DIR}/**/*{ext}", recursive=True):
                archivos.append(os.path.relpath(f, REPO_DIR))
            archivos.sort()
            return json.dumps({"total": len(archivos), "archivos": archivos}, ensure_ascii=False)

        elif name == "listar_carpetas":
            path = inputs.get("path", "")
            full_path = os.path.join(REPO_DIR, path) if path else REPO_DIR
            if not os.path.isdir(full_path):
                return f"Error: carpeta '{path}' no encontrada"
            items = sorted(os.listdir(full_path))
            resultado = []
            for item in items:
                if item.startswith("."):
                    continue
                if os.path.isdir(os.path.join(full_path, item)):
                    resultado.append(item + "/")
                else:
                    resultado.append(item)
            return json.dumps(resultado, ensure_ascii=False)

        elif name == "leer_archivo":
            filepath = os.path.join(REPO_DIR, inputs["path"])
            if not os.path.isfile(filepath):
                return f"Error: archivo '{inputs['path']}' no encontrado"
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                contenido = f.read()
            if len(contenido) > 50000:
                return contenido[:50000] + f"\n--- TRUNCADO: 50K de {len(contenido)} chars ---"
            return contenido

        elif name == "leer_multiples_archivos":
            paths = inputs["paths"][:5]
            resultados = {}
            for p in paths:
                filepath = os.path.join(REPO_DIR, p)
                if not os.path.isfile(filepath):
                    resultados[p] = "Error: no encontrado"
                    continue
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
                if len(contenido) > 20000:
                    contenido = contenido[:20000] + f"\n--- TRUNCADO a 20K de {len(contenido)} ---"
                resultados[p] = contenido
            return json.dumps(resultados, ensure_ascii=False)

        elif name == "buscar_codigo":
            query = inputs["query"]
            r = subprocess.run(
                ["grep", "-rli", "--include=*.4gl", "--include=*.sql", "--include=*.per",
                 "--include=*.md", "--include=*.xcf", query, REPO_DIR],
                capture_output=True, text=True, timeout=15
            )
            archivos = []
            for line in r.stdout.strip().split("\n"):
                if line:
                    archivos.append(os.path.relpath(line, REPO_DIR))
            archivos.sort()
            return json.dumps({"total": len(archivos), "archivos": archivos[:30]}, ensure_ascii=False)

    except Exception as e:
        return f"Error: {e}"
    return "Tool no reconocida"


sesiones = {}
MAX_HISTORIAL = 20


def compactar_historial(historial):
    for msg in historial:
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for item in msg["content"]:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    contenido = item.get("content", "")
                    if len(contenido) > 500:
                        item["content"] = contenido[:500] + f"\n... [compactado: {len(contenido)} chars]"


def recortar_historial(historial):
    if len(historial) > MAX_HISTORIAL:
        recortado = historial[-MAX_HISTORIAL:]
        while recortado and recortado[0]["role"] != "user":
            recortado.pop(0)
        historial.clear()
        historial.extend(recortado)


def limpiar_sesion(session_id="default"):
    if session_id in sesiones:
        sesiones[session_id] = []


def consultar_stream(pregunta, session_id="default"):
    """Genera eventos en tiempo real: progreso de tools y respuesta final."""
    if session_id not in sesiones:
        sesiones[session_id] = []
    historial = sesiones[session_id]
    historial.append({"role": "user", "content": pregunta})

    archivos_leidos = []
    tools_usadas = []
    tokens_input = 0
    tokens_output = 0

    first_thinking = True

    try:
        while True:
            if first_thinking:
                yield {"tipo": "pensando", "mensaje": "Analizando tu pregunta..."}
                first_thinking = False

            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=historial
            )

            tokens_input += response.usage.input_tokens
            tokens_output += response.usage.output_tokens

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        historial.append({"role": "assistant", "content": response.content})
                        compactar_historial(historial)
                        recortar_historial(historial)
                        yield {
                            "tipo": "respuesta",
                            "respuesta": block.text,
                            "archivos": archivos_leidos,
                            "tools": tools_usadas,
                            "tokens_input": tokens_input,
                            "tokens_output": tokens_output
                        }
                        return

            if response.stop_reason == "tool_use":
                historial.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tools_usadas.append(tool_name)

                        # Evento de progreso
                        label = TOOL_LABELS.get(tool_name, tool_name)
                        detalle = ""
                        if tool_name == "buscar_codigo":
                            detalle = f'"{tool_input.get("query", "")}"'
                        elif tool_name == "leer_archivo":
                            detalle = tool_input.get("path", "")
                        elif tool_name == "listar_archivos":
                            detalle = tool_input.get("extension", "")
                        elif tool_name == "listar_carpetas":
                            detalle = tool_input.get("path", "raiz")
                        elif tool_name == "leer_multiples_archivos":
                            detalle = f'{len(tool_input.get("paths", []))} archivos'

                        yield {"tipo": "tool", "tool": tool_name, "label": label, "detalle": detalle}

                        resultado = ejecutar_tool(tool_name, tool_input)

                        # Evento de resultado
                        resumen = ""
                        try:
                            parsed = json.loads(resultado)
                            if isinstance(parsed, dict) and "total" in parsed:
                                resumen = f"{parsed['total']} encontrados"
                            elif isinstance(parsed, dict) and "archivos" in parsed:
                                resumen = f"{len(parsed['archivos'])} archivos"
                        except Exception:
                            resumen = f"{len(resultado)} chars leidos"

                        yield {"tipo": "tool_resultado", "tool": tool_name, "resumen": resumen}

                        if tool_name not in ["ejecutar_comando"]:
                            archivos_leidos.append(json.dumps(tool_input, ensure_ascii=False))

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": resultado
                        })

                historial.append({"role": "user", "content": tool_results})

    except anthropic.RateLimitError:
        historial.pop()
        compactar_historial(historial)
        # Reintentar hasta 3 veces esperando entre cada intento
        for intento in range(3):
            espera = 15 * (intento + 1)
            yield {"tipo": "pensando", "mensaje": f"Rate limit alcanzado. Esperando {espera}s antes de reintentar ({intento+1}/3)..."}
            time.sleep(espera)
            try:
                historial.append({"role": "user", "content": pregunta})
                yield {"tipo": "pensando", "mensaje": "Reintentando..."}
                response = client.messages.create(
                    model=MODEL, max_tokens=8192, system=SYSTEM_PROMPT,
                    tools=tools, messages=historial
                )
                for block in response.content:
                    if hasattr(block, "text"):
                        historial.append({"role": "assistant", "content": response.content})
                        compactar_historial(historial)
                        recortar_historial(historial)
                        yield {
                            "tipo": "respuesta",
                            "respuesta": block.text,
                            "archivos": archivos_leidos,
                            "tools": tools_usadas,
                            "tokens_input": response.usage.input_tokens,
                            "tokens_output": response.usage.output_tokens
                        }
                        return
            except anthropic.RateLimitError:
                historial.pop()
                compactar_historial(historial)
                continue
            except Exception:
                historial.pop()
                break
        yield {"tipo": "respuesta", "respuesta": "No se pudo completar la consulta despues de 3 intentos. Tu plan de Anthropic tiene un limite de 30,000 tokens por minuto. Espera 1 minuto o inicia una nueva conversacion.", "archivos": [], "tools": [], "tokens_input": 0, "tokens_output": 0}

    except Exception as e:
        historial.pop()
        yield {"tipo": "respuesta", "respuesta": f"Error: {e}", "archivos": [], "tools": [], "tokens_input": 0, "tokens_output": 0}
