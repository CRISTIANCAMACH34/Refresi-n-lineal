import re
from sqlalchemy import text, try_cast
from pandas.io.formats.style import Subset
from Modelo.conexion import conectar_engine
import pandas as pd
import numpy as np
#Me sirve para las graficas
import matplotlib.pyplot as plt
#Me sirve para el entrenamiento de la IA
import sklearn
#Me sirve para dividir los datos en entrenamiento y pruebas
from sklearn.model_selection import train_test_split
#Me sirve para el entrenamiento de la IA
from sklearn.linear_model import LinearRegression
#Me sirve para medir el error
from sklearn.metrics import mean_squared_error

#Conectar a la base de datos
engine = conectar_engine()

#Insertar excel
def InsertarExcel(engine):
    try:
        conexion = engine
        excel = pd.read_csv("/home/cristian/Documentos/Personales/Adso/dataset_vivienda(in).csv", encoding='latin-1')

        #Verifica si todos los valores de la columna descripción son tipo strings, y si no los convierte en strings
        excel['descripcion'] = excel['descripcion'].apply(lambda x: str(x) if not isinstance(x, str) else x)

        #Esto maneja la conversión de codificación de caracteres  de texto para la columna descripción del excel
        excel['descripcion'] = excel['descripcion'].apply(lambda x: x.encode('latin-1').decode('utf-8') if isinstance(x, str) else x)

        excel['fecha_publicacion'] = pd.to_datetime(excel['fecha_publicacion'], errors='coerce')

        # Luego la formateas al estilo ISO para que MySQL acepte
        excel['fecha_publicacion'] = excel['fecha_publicacion'].dt.strftime('%Y-%m-%d')
        excel.rename(columns={
            'precio': 'precio', 
            'area': 'area',
            'habitaciones' : 'habitaciones',
            'antiguedad' : 'antiguedad',
            'fecha_publicacion' : 'fecha_publicacion',
            'descripcion' : 'descripcion'
        }, inplace=True)
        excel.to_sql("dataset_vivienda", conexion, if_exists="append", index=False)
        return excel
    except Exception as e:
        print("Error al insertar el excel:", e)
        return None

def ClasificarTipo(excel):

    try: 
        tiposCasas = {
            'Casa remodelada' : ['remodelada', 'renovada', 'modernizada', 'nueva'],
            'Casa espaciosa' : ['espaciosa', 'grande', 'amplia'],
            'Casa en zona residencial' : ['zona residencial', 'zona', 'residencial'],
            'Casa con jardin' : ['con jardin', 'jardin', 'con'],
            'Casa con patio' : ['con patio', 'patio', 'con']  
        }

        tipoApartamentos = {
            'Apartamento céntrico' : ['céntrico', 'centrico', 'centro'],
            'Apartamento económico' : ['económico', 'economico', 'econ0mico'],
            'Apartamento en buen estado' : ['en buen estado', 'buen estado', 'buen', 'en', 'estado'],
            'Apartamento luminoso' : ['luminoso', 'lumino', 'noso', 'mino'],
            'Apartamento con vista' : ['con vista', 'vista', 'con', 'c0n', 'vist4']
        }

        #Esta función me sirve para verificar que tipo de vivienda es con el desc buscando en la descripcion palabras como aparta para apartamento y casa para casa y así mismo determinar que es
        def DetectarTipo(desc):
            if pd.isnull(desc):   
                return 'general', 'casa'
            desc = desc.lower()
            
            #Recorre cada tipo de casa, revisa en las palabras de referencia si se encuentra en alguna
            for tipo, palabras in tiposCasas.items():
                #Any verifica si las condiciones son verdaderas, después verifica si alguna palabra está en la descripción y recorre cada palabra de la lista de palabras
                if any(palabra in desc for palabra in palabras):
                    return tipo, 'casa'

            for tipo, palabras in tipoApartamentos.items():        
                if any(palabra in desc for palabra in palabras):
                    return tipo, 'apartamento'
            
            #Retorna un valor por defecto si no se encuentra coincidencia
            return "apartamento", "apartamento" if "apart" in desc else "casa"
        
        #Me crea dos nuevas columnas nuevas a partir de una función que me devuelve dos valores
        excel[['tipo_hogar', 'categoria']] = excel['descripcion'].apply(lambda x: pd.Series(DetectarTipo(x)))
        return excel

    except Exception as e:
        print("Error al clasificar los tipos de vivienda:", e)
        return excel

def LimpiarDatos(excel):
    #Con esto limpiamos y eliminamos todas las filas con los valores nulo en los campos seleccionado ya que si falta una el modelo no podrá servir correctamente
    return excel.dropna(subset=['precio', 'habitaciones', 'area', 'antiguedad'])

def CodificarDatos(excel):
    #Crea una copia para no modificar de forma directa al dataframe original
    excel = excel.copy()    

    #Se convierte los datos de tipo_hogar a tipo categoria  con el astype y asígna un número único a cada categoría 
    excel['tipo_hogar'] = excel['tipo_hogar'].astype('category').cat.codes

    #Hacemos lo mismo que la anterior solo que con categoria 
    excel['categoria'] = excel['categoria'].astype('category').cat.codes

    return excel

def SeleccionarVariables(excel):
    ## X son los atributos que usarás para hacer predicciones
    x= excel[['area', 'habitaciones', 'antiguedad', 'tipo_hogar', 'categoria']]

    #Y es el valor que deseas predecir
    y= excel['precio']

    return x, y

def PrepararDatos(x, y ):
    try: 
        excel = LimpiarDatos(engine)
        excel = CodificarDatos(excel)
        x, y = SeleccionarVariables(excel)
        return x, y
    except Exception as e:
        print("Error al preparar los datos:", e)
        return None

def InsertarDatosEnBD(df, engine):
    MAX_LENGTH = 20  # Longitud máxima permitida en la columna 'tipo'

    try:
        with engine.begin() as conn:
            for index, row in df.iterrows():
                # Inserta en casa o apartamento según categoría
                if row['categoria'] == 'casa':
                    conn.execute(text("""
                        INSERT INTO casa (precio, area, habitaciones, antiguedad)
                        VALUES (:precio, :area, :habitaciones, :antiguedad)
                    """), {
                        'precio': row['precio'],
                        'area': row['area'],
                        'habitaciones': row['habitaciones'],
                        'antiguedad': row['antiguedad']
                    })
                    ref_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                else:
                    conn.execute(text("""
                        INSERT INTO apartamento (precio, area, habitaciones, antiguedad)
                        VALUES (:precio, :area, :habitaciones, :antiguedad)
                    """), {
                        'precio': row['precio'],
                        'area': row['area'],
                        'habitaciones': row['habitaciones'],
                        'antiguedad': row['antiguedad']
                    })
                    ref_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                # Truncar el tipo para que no exceda el tamaño máximo
                tipo_truncado = row['tipo_hogar'][:MAX_LENGTH]

                # Inserta en tipo_hogar
                conn.execute(text("""
                    INSERT INTO tipo_hogar (tipo, referencia_id)
                    VALUES (:tipo, :ref_id)
                """), {
                    'tipo': tipo_truncado,
                    'ref_id': ref_id
                })

                tipo_hogar_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                # Inserta en hogar
                conn.execute(text("""
                    INSERT INTO hogar (fecha_publicacion, descripcion, tipo_hogar_id)
                    VALUES (:fecha, :descripcion, :tipo_hogar_id)
                """), {
                    'fecha': row['fecha_publicacion'],
                    'descripcion': row['descripcion'],
                    'tipo_hogar_id': tipo_hogar_id
                })
        print("Datos insertados correctamente en las tablas reales.")
    except Exception as e:
        print("Error al insertar en la base de datos relacional:", e)
 

#(Total de viviendas en el sistema, promedio del precio por metro cuadrado de la vivienda en la región, clasificación y total de viviendas por tipo de vivienda)

def TotalViviendas(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM hogar"))
            total = result.scalar()
            return total
    except Exception as e:
        print("Error al obtener el total de viviendas:", e)
        return None

def PromedioPrecio(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT AVG(precio) FROM hogar"))
            #Se usa el scalar para obtener un valor unico de la consulta sql
            promedio = result.scalar()
            return promedio
    except Exception as e:
        print("Error al obtener el promedio de precio:", e)
        return None

def PromedioPrecioMetro(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT AVG(precio/area) FROM hogar"))
            promedio = result.scalar()
            return promedio
    except Exception as e:
        print("Error al obtener el promedio de precio por metro cuadrado:", e)
        return None
    
def ClasificacionViviendas(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT tipo_hogar, COUNT(*) FROM tipo_hogar GROUP BY tipo_hogar"))
            #Se usa el fetchall para obtener todos los valores de la consulta sql
            clasificacion = result.fetchall()
            return clasificacion
    except Exception as e:
        print("Error al obtener la clasificación de viviendas:", e)
        return None

def TotalViviendasPorTipo(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT tipo_hogar, COUNT(*) FROM tipo_hogar GROUP BY tipo_hogar"))
            #Se usa el fetchall para obtener todos los valores de la consulta sql
            total = result.fetchall()
            return total
    except Exception as e:
        print("Error al obtener el total de viviendas por tipo:", e)
        return None

#Sacar el aproximado de precio de un hogar con el area, habitaciones y antiguedad y el tipo de vivienda usando la regresión lineal y marchinlerming ingresado por el usuario usando las variables dependiente y independiente
def ObtenerTodasLasViviendas(engine):
    """Obtiene todas las viviendas con sus detalles"""
    try:
        with engine.connect() as connection:
            query = """
                SELECT h.id, h.descripcion, h.fecha_publicacion,
                       c.precio, c.area, c.habitaciones, c.antiguedad,
                       th.tipo as tipo_hogar, 'Casa' as categoria
                FROM hogar h
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                JOIN casa c ON th.referencia_id = c.id
                UNION ALL
                SELECT h.id, h.descripcion, h.fecha_publicacion,
                       a.precio, a.area, a.habitaciones, a.antiguedad,
                       th.tipo as tipo_hogar, 'Apartamento' as categoria
                FROM hogar h
                JOIN tipo_hogar th ON h.tipo_hogar_id = th.id
                JOIN apartamento a ON th.referencia_id = a.id
                ORDER BY id
            """
            result = connection.execute(text(query))
            columnas = result.keys()
            viviendas = [dict(zip(columnas, row)) for row in result.fetchall()]
            return viviendas
    except Exception as e:
        print("Error al obtener las viviendas:", e)
        return []

def AproximadoValor(engine, area, habitaciones, antiguedad, tipo_hogar, categoria):
    try:
        # Obtener los datos para entrenar el modelo
        query = """
            SELECT c.area, c.habitaciones, c.antiguedad, 
                   th.tipo as tipo_hogar, 'Casa' as tipo_vivienda, c.precio
            FROM casa c
            JOIN tipo_hogar th ON c.id = th.referencia_id
            WHERE th.tipo = :tipo_hogar
            UNION ALL
            SELECT a.area, a.habitaciones, a.antiguedad, 
                   th.tipo as tipo_hogar, 'Apartamento' as tipo_vivienda, a.precio
            FROM apartamento a
            JOIN tipo_hogar th ON a.id = th.referencia_id
            WHERE th.tipo = :tipo_hogar
        """
        
        with engine.connect() as connection:
            # Obtener datos de entrenamiento
            df = pd.read_sql_query(text(query), connection, params={'tipo_hogar': tipo_hogar})
            
            if df.empty:
                return None
                
            # Codificar las variables categóricas
            df['tipo_hogar'] = df['tipo_hogar'].astype('category').cat.codes
            df['tipo_vivienda'] = df['tipo_vivienda'].astype('category').cat.codes
            
            # Separar características (X) y variable objetivo (y)
            X = df[['area', 'habitaciones', 'antiguedad', 'tipo_hogar', 'tipo_vivienda']]
            y = df['precio']
            
            # Crear y entrenar el modelo
            modelo = LinearRegression()
            modelo.fit(X, y)
            
            # Preparar los datos de entrada para la predicción
            tipo_vivienda_cod = 0 if categoria.lower() == 'casa' else 1
            tipo_hogar_cod = df['tipo_hogar'].iloc[0]  # Tomamos el código del tipo de hogar del dataframe
            
            datos_prediccion = pd.DataFrame({
                'area': [area],
                'habitaciones': [habitaciones],
                'antiguedad': [antiguedad],
                'tipo_hogar': [tipo_hogar_cod],
                'tipo_vivienda': [tipo_vivienda_cod]
            })
            
            # Realizar la predicción
            precio_predicho = modelo.predict(datos_prediccion)[0]
            return round(precio_predicho, 2)
            
    except Exception as e:
        print("Error al calcular el valor aproximado de la vivienda:", e)
        return None

        

            