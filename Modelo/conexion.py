from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def conectar_engine():
    try:
        engine =create_engine(
            "mysql+mysqlconnector://cristian:12345@localhost/Regresion"
        )
        with engine.connect() as connection:
            print ("Conexión exitosa")

        return engine
    except Exception as e:
        print("Error al conectar a la base de datos:", e)
        return None
