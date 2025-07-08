import mysql.connector
from mysql.connector import Error

def conectar_mysql():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="cristian",   
            password="12345",      
            database="Regresion"        
        )

        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Conectado a MySQL versión " + db_Info)

            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print("Conectado a la base de datos: " + str(record[0]))
    
    except Error as e:
        print("Error al conectar a MySQL:", e)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión cerrada.")

conectar_mysql()
