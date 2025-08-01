import os
import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import numpy as np
from sqlalchemy import text

# Asegurarse de que el directorio Modelo esté en el path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modelo.entrenamiento_ia import conectar_engine, PromedioPrecio, PromedioPrecioMetro, TotalViviendasPorTipo, AproximadoValor

app = Flask(__name__, static_folder='../Vista')

# Configuración de CORS
CORS(app, resources={
    r"/api/*": {"origins": ["http://localhost:8000", "http://127.0.0.1:8000"]},
    r"/static/*": {"origins": "*"}
})

# Configuración de la base de datos
try:
    engine = conectar_engine()
    print("Conexión a la base de datos exitosa")
except Exception as e:
    print(f"Error al conectar a la base de datos: {e}")
    engine = None

# Ruta para servir archivos estáticos
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../Vista', path)

# Ruta raíz
@app.route('/')
def serve_index():
    return send_from_directory('../Vista', 'index.html')

@app.route('/api/prediccion', methods=['POST'])
# Entrenar el modelo al inicio
def entrenar_modelo():
    try:
        # Obtener datos de entrenamiento
        with engine.connect() as connection:
            # Consulta para obtener datos de casas
            result_casas = connection.execute(text("""
                SELECT c.id, c.precio, c.area, c.habitaciones, c.antiguedad,
                th.tipo, th.referencia_id
                FROM casa c
                JOIN hogar h ON c.id = h.id
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
            """))
            data_casas = result_casas.fetchall()

            # Consulta para obtener datos de apartamentos
            result_apartamentos = connection.execute(text("""
                SELECT a.id, a.precio, a.area, a.habitaciones, a.antiguedad,
                th.tipo, th.referencia_id
                FROM apartamento a
                JOIN hogar h ON a.id = h.id
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
            """))
            data_apartamentos = result_apartamentos.fetchall()

            # Combinar los datos
            data = data_casas + data_apartamentos
            
            # Extraer datos
            areas = [float(row[2]) for row in data]
            habitaciones = [int(row[3]) for row in data]
            antiguedades = [int(row[4]) for row in data]
            tipos = [row[5] for row in data]  # tipo (string)
            referencias = [int(row[6]) for row in data]  # referencia_id
            precios = [float(row[1]) for row in data]

            # Codificar tipos como números
            from sklearn.preprocessing import LabelEncoder
            encoder = LabelEncoder()
            tipos_codificados = encoder.fit_transform(tipos)
            
            # Combinar todas las características
            x = np.array(list(zip(areas, habitaciones, antiguedades, tipos_codificados, referencias)))
            y = np.array(precios)
            
            # Crear y entrenar el modelo
            from sklearn.linear_model import LinearRegression
            modelo = LinearRegression()
            modelo.fit(x, y)
            
            # Guardar el encoder para usarlo en predicciones
            import pickle
            with open('tipo_encoder.pkl', 'wb') as f:
                pickle.dump(encoder, f)
            
            return modelo
    except Exception as e:
        print(f"Error al entrenar el modelo: {str(e)}")
        return None

# Función auxiliar para codificar tipos durante predicción
def codificar_tipo(tipo):
    try:
        import pickle
        with open('tipo_encoder.pkl', 'rb') as f:
            encoder = pickle.load(f)
        return encoder.transform([tipo])[0]
    except Exception as e:
        print(f"Error al codificar tipo: {str(e)}")
        return None

# Entrenar el modelo al inicio
modelo = entrenar_modelo()

@app.route('/api/prediccion', methods=['POST'])
def prediccion():
    try:
        if modelo is None:
            return jsonify({"error": "El modelo no está entrenado"}), 500
            
        data = request.get_json()
        area = float(data.get('area'))
        habitaciones = int(data.get('habitaciones'))
        antiguedad = int(data.get('antiguedad'))
        tipo = data.get('tipo')  # Ahora recibimos el tipo como string
        referencia_id = int(data.get('referencia_id'))

        # Codificar el tipo
        tipo_codificado = codificar_tipo(tipo)
        if tipo_codificado is None:
            return jsonify({"error": "Tipo de vivienda no reconocido"}), 400

        # Crear array numpy con los datos
        x = np.array([[area, habitaciones, antiguedad, tipo_codificado, referencia_id]])

        # Hacer la predicción
        precio = modelo.predict(x)[0]
        
        return jsonify({"precio": float(precio)})

    except Exception as e:
        print(f"Error en la predicción: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/tipos')
def estadisticas_tipos():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT th.tipo, COUNT(*) as cantidad
                FROM hogar h
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                GROUP BY th.tipo
            """))
            data = result.fetchall()
            labels = [row[0] for row in data]
            values = [row[1] for row in data]
            return jsonify({"labels": labels, "values": values})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/precios')
def estadisticas_precios():
    try:
        with engine.connect() as connection:
            # Consultar precios de casas y apartamentos
            result_casas = connection.execute(text("SELECT precio FROM casa ORDER BY precio"))
            result_apartamentos = connection.execute(text("SELECT precio FROM apartamento ORDER BY precio"))
            
            # Combinar los resultados
            data_casas = result_casas.fetchall()
            data_apartamentos = result_apartamentos.fetchall()
            
            prices = [float(row[0]) for row in data_casas + data_apartamentos]
            return jsonify({"prices": prices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/antiguedad')
def estadisticas_antiguedad():
    try:
        with engine.connect() as connection:
            # Consultar antigüedades de casas y apartamentos
            result_casas = connection.execute(text("SELECT antiguedad FROM casa ORDER BY antiguedad"))
            result_apartamentos = connection.execute(text("SELECT antiguedad FROM apartamento ORDER BY antiguedad"))
            
            # Combinar los resultados
            data_casas = result_casas.fetchall()
            data_apartamentos = result_apartamentos.fetchall()
            
            ages = [int(row[0]) for row in data_casas + data_apartamentos]
            return jsonify({"antiguedades": ages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas/area')
def estadisticas_area():
    try:
        with engine.connect() as connection:
            # Consultar áreas de casas y apartamentos
            result_casas = connection.execute(text("SELECT area FROM casa ORDER BY area"))
            result_apartamentos = connection.execute(text("SELECT area FROM apartamento ORDER BY area"))
            
            # Combinar los resultados
            data_casas = result_casas.fetchall()
            data_apartamentos = result_apartamentos.fetchall()
            
            areas = [float(row[0]) for row in data_casas + data_apartamentos]
            return jsonify({"areas": areas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/promedio-precio')
def promedio_precio():
    try:
        promedio = PromedioPrecio(engine)
        return jsonify(promedio)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/promedio-metro')
def promedio_metro():
    try:
        promedio = PromedioPrecioMetro(engine)
        return jsonify(promedio)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/total-viviendas')
def total_viviendas():
    try:
        total = TotalViviendasPorTipo(engine)
        return jsonify(len(total))  # Devolvemos el total de registros
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/distribucion-tipos')
def distribucion_tipos():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT tipo_hogar, COUNT(*) as cantidad FROM tipo_hogar GROUP BY tipo_hogar"))
            data = result.fetchall()
            labels = [row[0] for row in data]
            values = [row[1] for row in data]
            return jsonify({"labels": labels, "values": values})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/distribucion-precios')
def distribucion_precios():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT precio FROM hogar ORDER BY precio"))
            data = result.fetchall()
            prices = [float(row[0]) for row in data]
            return jsonify({"prices": prices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/distribucion-antiguedad')
def distribucion_antiguedad():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT antiguedad FROM hogar ORDER BY antiguedad"))
            data = result.fetchall()
            ages = [int(row[0]) for row in data]
            return jsonify({"antiguedades": ages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/distribucion-area')
def distribucion_area():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT area FROM hogar ORDER BY area"))
            data = result.fetchall()
            areas = [float(row[0]) for row in data]
            return jsonify({"areas": areas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/viviendas', methods=['GET'])
def obtener_todas_viviendas():
    try:
        with engine.connect() as connection:
            # Obtener todas las viviendas con sus detalles
            result = connection.execute(text("""
                SELECT 
                    h.id, 
                    h.descripcion, 
                    h.fecha_publicacion,
                    c.precio AS precio, 
                    c.area, 
                    c.habitaciones, 
                    c.antiguedad,
                    th.tipo AS tipo_hogar,
                    'Casa' AS categoria
                FROM hogar h
                JOIN casa c ON h.id = c.id
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                
                UNION ALL
                
                SELECT 
                    h.id, 
                    h.descripcion, 
                    h.fecha_publicacion,
                    a.precio AS precio, 
                    a.area, 
                    a.habitaciones, 
                    a.antiguedad,
                    th.tipo AS tipo_hogar,
                    'Apartamento' AS categoria
                FROM hogar h
                JOIN apartamento a ON h.id = a.id
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                ORDER BY id
            """))
            
            # Convertir resultados a lista de diccionarios
            columns = ['id', 'descripcion', 'fecha_publicacion', 'precio', 'area', 
                      'habitaciones', 'antiguedad', 'tipo_hogar', 'categoria']
            viviendas = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # Convertir Decimal a float para serialización JSON
            for v in viviendas:
                v['precio'] = float(v['precio']) if v['precio'] is not None else 0
                v['area'] = float(v['area']) if v['area'] is not None else 0
                v['antiguedad'] = int(v['antiguedad']) if v['antiguedad'] is not None else 0
                v['habitaciones'] = int(v['habitaciones']) if v['habitaciones'] is not None else 0
                v['fecha_publicacion'] = str(v['fecha_publicacion'])
            
            return jsonify(viviendas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/graficos/dispersion-precio-area', methods=['GET'])
def grafico_dispersion_precio_area():
    try:
        import matplotlib.pyplot as plt
        import io
        import base64
        from matplotlib.ticker import FuncFormatter
        
        with engine.connect() as connection:
            # Obtener datos de precios y áreas para casas y apartamentos
            result = connection.execute(text("""
                SELECT 
                    c.precio, 
                    c.area,
                    th.tipo AS tipo_hogar,
                    'Casa' AS categoria
                FROM hogar h
                JOIN casa c ON h.id = c.id
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                WHERE c.precio > 0 AND c.area > 0
                
                UNION ALL
                
                SELECT 
                    a.precio, 
                    a.area,
                    th.tipo AS tipo_hogar,
                    'Apartamento' AS categoria
                FROM hogar h
                JOIN apartamento a ON h.id = a.id
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                WHERE a.precio > 0 AND a.area > 0
            """))
            
            data = result.fetchall()
            
            if not data:
                return jsonify({"error": "No hay datos suficientes para generar el gráfico"}), 404
            
            # Convertir a DataFrame para facilitar el procesamiento
            import pandas as pd
            df = pd.DataFrame(data, columns=['precio', 'area', 'tipo_hogar', 'categoria'])
            
            # Calcular precio por m²
            df['precio_m2'] = df['precio'] / df['area']
            
            # Crear el gráfico de dispersión
            plt.figure(figsize=(12, 8))
            
            # Colores diferentes para casas y apartamentos
            colors = {'Casa': 'blue', 'Apartamento': 'orange'}
            
            # Crear scatter plot para cada categoría
            for categoria, group in df.groupby('categoria'):
                plt.scatter(
                    group['area'], 
                    group['precio'],
                    alpha=0.6,
                    label=f'{categoria}s',
                    color=colors[categoria]
                )
            
            # Añadir líneas de tendencia para cada categoría
            for categoria, group in df.groupby('categoria'):
                if len(group) > 1:  # Necesitamos al menos 2 puntos para una línea de tendencia
                    z = np.polyfit(group['area'], group['precio'], 1)
                    p = np.poly1d(z)
                    plt.plot(
                        group['area'], 
                        p(group['area']), 
                        color=colors[categoria],
                        linestyle='--',
                        label=f'Tendencia {categoria}s',
                        alpha=0.7
                    )
            
            # Configurar el gráfico
            plt.title('Relación entre Área y Precio de las Viviendas', fontsize=14, pad=20)
            plt.xlabel('Área (m²)', fontsize=12)
            plt.ylabel('Precio (COP)', fontsize=12)
            
            # Formatear ejes con separadores de miles
            plt.gca().yaxis.set_major_formatter(
                FuncFormatter(lambda x, p: f'${x:,.0f}'.replace(',', '.'))
            )
            
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()
            
            # Añadir anotación con la correlación
            corr = df['area'].corr(df['precio'])
            plt.annotate(
                f'Correlación: {corr:.2f}',
                xy=(0.02, 0.95),
                xycoords='axes fraction',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=1, alpha=0.9)
            )
            
            # Guardar el gráfico en un buffer
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close()
            
            # Convertir la imagen a base64
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            # Análisis de la correlación
            analisis = """
            <h3>Análisis de la Relación Precio vs. Área</h3>
            <p>El gráfico de dispersión muestra la relación entre el área (en m²) y el precio de las viviendas, 
            diferenciando entre casas y apartamentos.</p>
            """
            
            if abs(corr) > 0.7:
                tendencia = "fuerte positiva" if corr > 0 else "fuerte negativa"
                analisis += f"""
                <p><strong>Correlación {tendencia}:</strong> El coeficiente de correlación de {corr:.2f} indica que existe 
                una relación {tendencia} entre el área y el precio de las viviendas. Esto significa que, en general, 
                a mayor área, mayor es el precio de la vivienda.</p>
                """
            elif abs(corr) > 0.3:
                tendencia = "moderada positiva" if corr > 0 else "moderada negativa"
                analisis += f"""
                <p><strong>Correlación {tendencia}:</strong> El coeficiente de correlación de {corr:.2f} sugiere que existe 
                una relación {tendencia} entre el área y el precio de las viviendas. Sin embargo, hay otros factores 
                que también pueden estar influyendo en el precio.</p>
                """
            else:
                analisis += f"""
                <p><strong>Correlación débil o nula:</strong> El coeficiente de correlación de {corr:.2f} indica que 
                no hay una relación lineal fuerte entre el área y el precio de las viviendas. Esto sugiere que otros 
                factores (ubicación, acabados, antigüedad, etc.) pueden estar teniendo un mayor impacto en el precio.</p>
                """
            
            # Identificar valores atípicos
            if len(df) > 0:
                q1 = df['precio'].quantile(0.25)
                q3 = df['precio'].quantile(0.75)
                iqr = q3 - q1
                umbral_superior = q3 + 1.5 * iqr
                
                atipicos = df[df['precio'] > umbral_superior]
                if not atipicos.empty:
                    analisis += """
                    <h4>Valores Atípicos</h4>
                    <p>Se han identificado algunas viviendas con precios significativamente más altos que la mayoría, 
                    considerando su área. Estas propiedades podrían ser:</p>
                    <ul>
                        <li>Propiedades de lujo con acabados de alta gama</li>
                        <li>Ubicaciones premium dentro de la región</n>
                        <li>Propiedades con características especiales no capturadas en los datos</li>
                    </ul>
                    """
            
            return jsonify({
                'imagen': f"data:image/png;base64,{image_base64}",
                'analisis': analisis,
                'correlacion': corr,
                'total_viviendas': len(df)
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Función para obtener estadísticas combinadas
@app.route('/api/estadisticas', methods=['GET'])
def estadisticas():
    try:
        with engine.connect() as connection:
            # Obtener estadísticas básicas
            avg_price = connection.execute(text("SELECT AVG(precio) as avg_price FROM casa UNION ALL SELECT AVG(precio) FROM apartamento")).scalar()
            avg_m2 = connection.execute(text("SELECT AVG(precio/NULLIF(area, 0)) as avg_m2 FROM casa WHERE area > 0 UNION ALL SELECT AVG(precio/NULLIF(area, 0)) FROM apartamento WHERE area > 0")).scalar()
            total = connection.execute(text("SELECT COUNT(*) FROM casa UNION ALL SELECT COUNT(*) FROM apartamento")).scalar()
            
            return jsonify({
                'promedioPrecio': float(avg_price or 0),
                'promedioMetro': float(avg_m2 or 0),
                'totalViviendas': int(total or 0)
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Registrar rutas de la API
app.add_url_rule('/api/viviendas', 'obtener_todas_viviendas', obtener_todas_viviendas, methods=['GET'])
app.add_url_rule('/api/estadisticas', 'estadisticas', estadisticas, methods=['GET'])
app.add_url_rule('/api/graficos/dispersion-precio-area', 'grafico_dispersion_precio_area', grafico_dispersion_precio_area, methods=['GET'])

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
