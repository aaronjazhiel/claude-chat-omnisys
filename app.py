from flask import Flask, render_template, request, jsonify, send_from_directory
from chat_claude import consultar
import generar_docx
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def chat():
    pregunta = request.json.get('pregunta', '').strip()
    if not pregunta:
        return jsonify({'error': 'Pregunta vacía'})
    try:
        resultado = consultar(pregunta)
        return jsonify({
            'respuesta': resultado['respuesta'],
            'archivos': resultado['archivos'],
            'tools': resultado['tools'],
            'error': None
        })
    except Exception as e:
        return jsonify({'respuesta': None, 'archivos': [], 'tools': [], 'error': str(e)})

@app.route('/generar-doc', methods=['POST'])
def generar_doc():
    contenido = request.json.get('contenido', '')
    pregunta = request.json.get('pregunta', 'Análisis de código')
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
    print(f"\n🚀 Omnisys Chat iniciado en http://localhost:{port}\n")
    app.run(debug=True, port=port)
