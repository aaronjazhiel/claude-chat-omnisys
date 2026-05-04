from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from chat_claude import consultar_stream, limpiar_sesion
import generar_docx
import os
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def chat():
    pregunta = request.json.get('pregunta', '').strip()
    if not pregunta:
        return jsonify({'error': 'Pregunta vacia'})

    def stream():
        for evento in consultar_stream(pregunta):
            yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

    return Response(stream(), mimetype='text/event-stream')

@app.route('/nueva-sesion', methods=['POST'])
def nueva_sesion():
    limpiar_sesion()
    return jsonify({'ok': True})

@app.route('/generar-doc', methods=['POST'])
def generar_doc():
    contenido = request.json.get('contenido', '')
    pregunta = request.json.get('pregunta', 'Analisis de codigo')
    if not contenido:
        return jsonify({'error': 'Sin contenido'})
    try:
        filename = generar_docx.generar(contenido, pregunta)
        return jsonify({'archivo': filename, 'error': None})
    except Exception as e:
        return jsonify({'archivo': None, 'error': str(e)})

@app.route('/descargar/<filename>')
def descargar(filename):
    return send_from_directory(generar_docx.DOCS_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"\nOmnisys Chat iniciado en http://localhost:{port}\n")
    app.run(debug=True, port=port)
