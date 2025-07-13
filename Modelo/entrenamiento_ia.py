import re
from sqlalchemy import text
from pandas.io.formats.style import Subset
from conexion import conectar_engine
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
            if pd.isnull(desc):  # Corregido: excel.pd.isnull no existe
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
        excel = LimpiarDatos(excel)
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

if __name__ == "__main__":
    # 1. Leer y guardar el Excel en la tabla temporal
    excel = InsertarExcel(engine)
    
    # 2. Continuar si se leyó correctamente
    if excel is not None:
        # 3. Clasificar el tipo de hogar
        excel = ClasificarTipo(excel)

        # 4. Insertar los datos clasificados en las tablas reales
        InsertarDatosEnBD(excel, engine)