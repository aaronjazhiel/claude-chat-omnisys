# Omnisys — Chat IA con Claude

Asistente inteligente con interfaz web. Chat general + análisis de código en GitHub.

## Deploy en Render

1. Conecta el repo `aaronjazhiel/claude-chat-omnisys` en [Render](https://dashboard.render.com)
2. Configura como **Web Service** con **Docker**
3. Agrega la variable de entorno:
   - `ANTHROPIC_API_KEY` = tu key de Anthropic
   - `GITHUB_REPO` = (opcional) repo a analizar
4. Deploy

## Local

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
pip install -r requirements.txt
python app.py
```
