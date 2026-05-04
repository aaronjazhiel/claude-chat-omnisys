# ⚡ Omnisys — Chat IA con Claude API

Asistente inteligente con interfaz web desarrollado para [Omnisys](https://e-omnisys.com/), conectado a la API de Claude (Anthropic).

![Claude](https://img.shields.io/badge/Claude-Sonnet_4-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Deploy](https://img.shields.io/badge/Deploy-Render-purple)

---

## 🎯 ¿Qué hace?

Un chat web donde puedes hacer **cualquier pregunta** y Claude responde:
- 💬 Preguntas generales (cultura, matemáticas, idiomas, consejos)
- 🕐 Información en tiempo real (hora, fecha)
- 📁 Análisis de código de repositorios en GitHub (opcional)

---

## 🏗️ Arquitectura

```
Usuario (navegador)
    │
    ▼
┌─────────────────┐
│   Flask (app.py) │  ← Servidor web
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│  chat_claude.py      │  ← Lógica de Claude API + Tools
│                      │
│  Tools disponibles:  │
│  • ejecutar_comando  │ → hora, fecha, sistema
│  • listar_archivos   │ → GitHub API
│  • leer_archivo      │ → GitHub API
│  • buscar_codigo     │ → GitHub API
└────────┬─────────────┘
         │
         ▼
   Claude API (Anthropic)
```

---

## 📁 Estructura del proyecto

```
claude-chat-omnisys/
├── app.py                    ← Entry point Flask
├── chat_claude.py            ← Claude API + herramientas
├── templates/
│   └── index.html            ← Interfaz web (branding Omnisys)
├── prompts/
│   └── system_prompt.txt     ← System prompt de Claude
├── Dockerfile                ← Para deploy en Render
├── requirements.txt          ← Dependencias Python
├── runtime.txt               ← Versión de Python
├── .gitignore
└── README.md
```

---

## 🚀 Cómo correrlo en local

### 1. Clona el repositorio
```bash
git clone https://github.com/aaronjazhiel/claude-chat-omnisys.git
cd claude-chat-omnisys
```

### 2. Instala dependencias
```bash
pip install -r requirements.txt
```

### 3. Configura tu API key de Anthropic
```bash
export ANTHROPIC_API_KEY="sk-ant-tu-key-aqui"
```
> Obtén tu key en → https://console.anthropic.com/settings/keys

### 4. Corre la app
```bash
python app.py
```

### 5. Abre en tu navegador
```
http://localhost:8080
```

---

## ☁️ Cómo desplegarlo en Render

### 1. Sube el código a GitHub
```bash
git add -A
git commit -m "Deploy"
git push origin main
```

### 2. Configura en Render
1. Ve a → https://dashboard.render.com
2. Click **New** → **Web Service**
3. Conecta el repo `aaronjazhiel/claude-chat-omnisys`
4. Configura:

| Campo | Valor |
|-------|-------|
| **Name** | omnisys-chat |
| **Environment** | Docker |
| **Plan** | Free |

5. En **Environment Variables** agrega:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-tu-key-aqui` |

6. Click **Deploy Web Service**
7. En 2-3 minutos tendrás tu URL: `https://omnisys-chat.onrender.com`

---

## 🔧 Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Sí | API key de Anthropic (Claude) |
| `GITHUB_REPO` | ❌ No | Repo de GitHub para análisis de código |
| `GITHUB_TOKEN` | ❌ No | Token de GitHub (solo repos privados) |
| `CLAUDE_MODEL` | ❌ No | Modelo de Claude (default: claude-sonnet-4-20250514) |

---

## 💰 Costo estimado

| Uso | Costo aproximado |
|-----|-----------------|
| 1 pregunta simple | ~$0.01 USD |
| Sesión de 20 preguntas | ~$0.20 USD |
| Uso mensual moderado | ~$5-10 USD |

> Requiere saldo en Anthropic → https://console.anthropic.com/settings/billing

---

## 🛠️ Tecnologías

- **Backend**: Python 3.11 + Flask
- **IA**: Claude Sonnet 4 (Anthropic API)
- **Frontend**: HTML/CSS/JS vanilla
- **Deploy**: Docker + Render
- **APIs**: GitHub REST API (opcional)

---

## 📝 Cómo se construyó

1. Se creó el backend con Flask (`app.py`) que sirve la interfaz y expone el endpoint `/consultar`
2. Se desarrolló `chat_claude.py` con la lógica de Claude API, incluyendo herramientas (tools) que Claude puede invocar automáticamente
3. Se diseñó la interfaz web con branding Omnisys (colores azul/oscuro)
4. Se configuró el system prompt en `prompts/system_prompt.txt` para que Claude sea un asistente de propósito general
5. Se creó el `Dockerfile` para deploy en Render
6. Se subió a GitHub y se conectó con Render para deploy automático

---

Desarrollado con 🤖 Claude API para [Omnisys](https://e-omnisys.com/)
