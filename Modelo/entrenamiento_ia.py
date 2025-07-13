import re

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
        excel = pd.read_csv("/Documentos/Personales/Adso/dataset_vivienda(in).csv")
        #Verifica si todos los valores de la columna descripción son tipo strings, y si no los convierte en strings
        excel['descripcion'] = excel['descripcion'].apply(lambda x: str(x) if not isinstance(x, str) else x)
        #Esto maneja la conversión de codificación de caracteres  de texto para la columna descripción del excel
        excel['descripcion'] = excel['descripcion'].apply(lambda x: x.encode('latin-1').decode('utf-8') if isinstance(x, str) else x)

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
        excel[['tipo_vivienda', 'categoria']] = excel['descripcion'].apply(lambda x: pd.Series(DetectarTipo(x)))
        return excel

    except Exception as e:
        print("Error al clasificar los tipos de vivienda:", e)
        return excel

def LimpiarDatos(excel):
    #Con esto limpiamos todos los valores nulo en los campos seleccionado
    return excel.dropna(subset=['precio', 'habitaciones', 'area', 'antiguedad'])

