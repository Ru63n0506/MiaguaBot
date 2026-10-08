import mysql.connector

conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Reyes41879!123",
    database="miagua"
)

print("Conexión exitosa")

conexion.close()