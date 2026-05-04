from flask import Flask, render_template, request, jsonify
from chat_claude import consultar

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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    print(f"\n🚀 Omnisys Chat iniciado en http://localhost:{port}\n")
    app.run(debug=True, port=port)
