from flask import Flask, jsonify, request
from flask_cors import CORS
from Modelo.entrenamiento_ia import *
from Modelo.conexion import conectar_engine
import pandas as pd

app = Flask(__name__)
CORS(app)

# Configuración de la base de datos
engine = conectar_engine()

@app.route('/api/viviendas', methods=['GET'])
def obtener_viviendas():
    try:
        viviendas = ObtenerTodasLasViviendas(engine)
        return jsonify(viviendas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/prediccion', methods=['POST'])
def predecir_precio():
    try:
        data = request.get_json()
        
        # Validar datos de entrada
        required_fields = ['area', 'habitaciones', 'antiguedad', 'tipo_hogar', 'categoria']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo requerido faltante: {field}"}), 400
        
        # Realizar la predicción
        precio = AproximadoValor(
            engine=engine,
            area=float(data['area']),
            habitaciones=int(data['habitaciones']),
            antiguedad=int(data['antiguedad']),
            tipo_hogar=data['tipo_hogar'],
            categoria=data['categoria']
        )
        
        if precio is None:
            return jsonify({"error": "No se pudo realizar la predicción"}), 400
            
        return jsonify({"precio": precio})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/tipos', methods=['GET'])
def obtener_estadisticas_tipos():
    try:
        # Obtener el conteo de tipos de vivienda
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT 
                    th.tipo as tipo_hogar, 
                    COUNT(*) as cantidad
                FROM tipo_hogar th
                JOIN hogar h ON th.id = h.tipo_hogar_id
                GROUP BY th.tipo
                ORDER BY cantidad DESC
            """)
            
            tipos = result.fetchall()
            
            return jsonify({
                "labels": [tipo[0] for tipo in tipos],
                "values": [tipo[1] for tipo in tipos]
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/precios', methods=['GET'])
def obtener_estadisticas_precios():
    try:
        with engine.connect() as conn:
            # Obtener precios para el histograma
            result = conn.execute("""
                SELECT c.precio 
                FROM casa c
                UNION ALL
                SELECT a.precio 
                FROM apartamento a
                WHERE a.precio > 0
            """)
            
            precios = [row[0] for row in result.fetchall()]
            
            return jsonify({"prices": precios})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/antiguedad', methods=['GET'])
def obtener_estadisticas_antiguedad():
    try:
        with engine.connect() as conn:
            # Obtener antigüedades para el histograma
            result = conn.execute("""
                SELECT c.antiguedad 
                FROM casa c
                WHERE c.antiguedad > 0
                UNION ALL
                SELECT a.antiguedad 
                FROM apartamento a
                WHERE a.antiguedad > 0
            """)
            
            antiguedades = [row[0] for row in result.fetchall()]
            
            return jsonify({"antiguedades": antiguedades})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/area', methods=['GET'])
def obtener_estadisticas_area():
    try:
        with engine.connect() as conn:
            # Obtener áreas para el histograma
            result = conn.execute("""
                SELECT c.area 
                FROM casa c
                WHERE c.area > 0
                UNION ALL
                SELECT a.area 
                FROM apartamento a
                WHERE a.area > 0
            """)
            
            areas = [row[0] for row in result.fetchall()]
            
            return jsonify({"areas": areas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/promedio-precio', methods=['GET'])
def obtener_promedio_precio():
    try:
        promedio = PromedioPrecio(engine)
        return jsonify(promedio if promedio is not None else 0)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/promedio-metro', methods=['GET'])
def obtener_promedio_metro():
    try:
        promedio = PromedioPrecioMetro(engine)
        return jsonify(promedio if promedio is not None else 0)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/total-viviendas', methods=['GET'])
def obtener_total_viviendas():
    try:
        total = TotalViviendas(engine)
        return jsonify(total if total is not None else 0)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
