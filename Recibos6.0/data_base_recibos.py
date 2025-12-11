import sqlite3
import os
from werkzeug.security import generate_password_hash
from tabulate import tabulate

# Ruta de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), 'db_Recibos_Miscelaneos', 'database.db')
if not os.path.exists(os.path.dirname(DB_PATH)):
    os.makedirs(os.path.dirname(DB_PATH))

print(f"Ruta de la base de datos en data_base_recibos.py: {DB_PATH}")

# Crear tabla usuarios
def crear_tabla_usuarios():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Crear tabla datos
def crear_tabla_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Trailer_List TEXT NOT NULL,
            Factura_List TEXT NOT NULL,
            Orden_Compra_List TEXT NOT NULL,
            Proveedor_List TEXT NOT NULL,
            Ref_SL_List TEXT NOT NULL,
            Qty_List INTEGER NOT NULL,
            Estatus_List TEXT DEFAULT 'Por_Validar',
            Fecha_hora_escaneo TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()


# Crear tabla escaneos
def crear_tabla_escaneos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS escaneos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sl TEXT NOT NULL,
            qty INTEGER NOT NULL,
            estatus TEXT NOT NULL,
            Fecha_hora_escaneo TEXT DEFAULT '',
            Foto_entregado TEXT DEFAULT '',
            orden_compra TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    
# Insertar usuario de prueba
def insertar_usuario_prueba():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        hashed_password = generate_password_hash("1234")
        cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, password) VALUES (?, ?)", ("admin", hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # El usuario ya existe
    conn.close()


# Mostrar tablas y datos
def mostrar_tablas_y_datos():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Obtener todas las tablas en la base de datos
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()

        if tablas:
            print("\n=== TABLAS EN LA BASE DE DATOS ===")
            for tabla in tablas:
                print(f"\nTabla: {tabla[0]}")

                # Obtener los datos de cada tabla
                cursor.execute(f"SELECT * FROM {tabla[0]}")
                rows = cursor.fetchall()

                # Obtener los nombres de las columnas
                cursor.execute(f"PRAGMA table_info({tabla[0]})")
                column_names = [column[1] for column in cursor.fetchall()]

                if rows:
                    print(tabulate(rows, headers=column_names, tablefmt='grid'))
                    print(f"Total de registros: {len(rows)}")
                else:
                    print("La tabla está vacía.")
        else:
            print("No hay tablas en la base de datos.")

        conn.close()
    except sqlite3.OperationalError as e:
        print("Error al acceder a la base de datos:", e)
    except Exception as e:
        print("Error inesperado:", e)

# Inicializar la base de datos
def inicializar_base_datos():
    if not os.path.exists(DB_PATH):
        crear_tabla_usuarios()
        crear_tabla_datos()
        crear_tabla_escaneos()
        insertar_usuario_prueba()
    else:
        print("La base de datos ya existe. No se inicializará nuevamente.")

if __name__ == "__main__":
    inicializar_base_datos()
    mostrar_tablas_y_datos()

print("\nPresiona Enter para continuar...")
input()