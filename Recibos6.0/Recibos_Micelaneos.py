from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import pandas as pd
import base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directorio base del archivo current
DB_FOLDER = os.path.join(BASE_DIR, 'db_Recibos_Miscelaneos')  # Carpeta para la base de datos
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)  # Crear carpeta si no existe
DB_PATH = os.path.join(DB_FOLDER, 'database.db')  # Ruta completa de la base de datos

print(f"Ruta de la base de datos en Recibos_Micelaneos.py: {DB_PATH}")

# Carpeta para almacenar archivos cargados
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Crear subcarpeta para fotos de evidencia
EVIDENCE_FOLDER = os.path.join(UPLOAD_FOLDER, 'fotos_evidencia')
if not os.path.exists(EVIDENCE_FOLDER):
    os.makedirs(EVIDENCE_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv', 'png', 'jpg', 'jpeg', 'gif'}  # ✅ Agregado formatos de imagen

# Verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Página principal
@app.route('/')
def index():
    return render_template('index_recibos.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):  # user[2] es la columna de la contraseña encriptada
            session['usuario'] = usuario
            return redirect(url_for('gestion'))
        else:
            flash("Credenciales incorrectas", "error")
            return redirect(url_for('login'))
    return render_template('login_recibos.html')

# Gestión
@app.route('/gestion')
def gestion():
    if 'usuario' in session:
        return render_template('gestion.html', usuario=session['usuario'])
    return redirect(url_for('login'))

# Logout
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

# Página de Validación de Misceláneos
@app.route('/Validacion_Miscelaneos', methods=['GET', 'POST'])
def Validacion_Miscelaneos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    excel_data = []  # Lista para almacenar los datos procesados
    cajas = []  # Lista para almacenar los valores únicos de Trailer_List

    if request.method == 'POST':
        # Verificar si se cargó un archivo
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)

        file = request.files['file']

        # Verificar si el archivo tiene un nombre válido
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)

        # Verificar si el archivo tiene una extensión permitida
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Leer el archivo con pandas
            try:
                if filename.endswith('.csv'):
                    # Leer archivo CSV
                    df = pd.read_csv(filepath)
                else:
                    # Leer archivo Excel
                    df = pd.read_excel(filepath)

                # Filtrar las columnas necesarias
                columnas_necesarias = [
                    'Trailer_List', 'Factura_List', 'Orden_Compra_List',
                    'Proveedor_List', 'Ref_SL_List', 'Qty_List'
                ]
                df = df[columnas_necesarias]

                # Obtener valores únicos de Trailer_List
                cajas = df['Trailer_List'].unique().tolist()

                # Insertar los datos en la tabla 'datos' y generar registros en 'escaneos'
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for _, row in df.iterrows():
                    # Verificar si el registro ya existe en la base de datos
                    cursor.execute('''
                        SELECT COUNT(*) FROM datos WHERE 
                        Trailer_List = ? AND Factura_List = ? AND Orden_Compra_List = ? AND 
                        Proveedor_List = ? AND Ref_SL_List = ? AND Qty_List = ?
                    ''', (row['Trailer_List'], row['Factura_List'], row['Orden_Compra_List'], 
                          row['Proveedor_List'], row['Ref_SL_List'], row['Qty_List']))
                    exists = cursor.fetchone()[0]

                    # Si el registro no existe, lo insertamos en 'datos'
                    if not exists:
                        cursor.execute('''
                            INSERT INTO datos (Trailer_List, Factura_List, Orden_Compra_List, Proveedor_List, Ref_SL_List, Qty_List)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (row['Trailer_List'], row['Factura_List'], row['Orden_Compra_List'], 
                              row['Proveedor_List'], row['Ref_SL_List'], row['Qty_List']))

                        # Generar automáticamente registros en la tabla 'escaneos'
                        for i in range(1, int(row['Qty_List']) + 1):  # Crear registros según la cantidad (Qty_List)
                            cursor.execute('''
                                INSERT INTO escaneos (sl, qty, estatus, orden_compra)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                row['Ref_SL_List'],  # SL
                                i,                   # Secuencia de cantidad
                                'Pendiente',         # Estado inicial
                                row['Orden_Compra_List']  # Orden de Compra
                            ))

                conn.commit()
                conn.close()

                # Convertir los datos a una lista para enviarlos al HTML
                excel_data = df.to_dict(orient='records')
                print(df.head())
            except KeyError:
                flash('El archivo no contiene las columnas necesarias.', 'error')
                return redirect(request.url)
            except Exception as e:
                flash(f'Error al procesar el archivo: {e}', 'error')
                return redirect(request.url)
        else:
            flash('Archivo no permitido. Solo se permiten archivos Excel (.xls, .xlsx) y CSV (.csv)', 'error')
            return redirect(request.url)

    return render_template('Validacion_Miscelaneos.html', usuario=session['usuario'], excel_data=excel_data, cajas=cajas)

@app.route('/Entrega_Material')
def Entrega_Material():
    if 'usuario' in session:
       return render_template('Entrega_Material.html', usuario=session['usuario'])
    return redirect(url_for('login'))

@app.route('/filter_data')
def filter_data():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    caja = request.args.get('caja')  # Obtener el valor de la caja seleccionada
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Filtrar los datos según la caja seleccionada
    cursor.execute('''
        SELECT Trailer_List, Factura_List, Orden_Compra_List, Proveedor_List, Ref_SL_List, Qty_List, Estatus_List
        FROM datos
        WHERE Trailer_List = ?
    ''', (caja,))
    rows = cursor.fetchall()
    conn.close()

    # Convertir los datos a un formato JSON
    data = [
        {
            'Trailer_List': row[0],
            'Factura_List': row[1],
            'Orden_Compra_List': row[2],
            'Proveedor_List': row[3],
            'Ref_SL_List': row[4],
            'Qty_List': row[5],
            'Estatus_List': row[6]  # Incluir el estado
        }
        for row in rows
    ]
    return jsonify(data)

@app.route('/expand_data')
def expand_data():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    sl = request.args.get('sl')  # Obtener el SL desde el frontend
    orden_compra = request.args.get('orden_compra')  # Obtener la Orden de Compra desde el frontend

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Obtener los datos de la tabla 'datos' para el SL y Orden de Compra específicos
    cursor.execute('''
        SELECT Trailer_List, Factura_List, Orden_Compra_List, Proveedor_List, Ref_SL_List, Qty_List
        FROM datos
        WHERE Ref_SL_List = ? AND Orden_Compra_List = ?
    ''', (sl, orden_compra))
    rows = cursor.fetchall()

    # ✅ FIX APLICADO: Obtener los QR escaneados filtrando por SL Y Orden de Compra
    cursor.execute('''
        SELECT qty, Foto_entregado
        FROM escaneos
        WHERE sl = ? AND orden_compra = ? AND estatus = 'Completado'
    ''', (sl, orden_compra))
    scanned_data = cursor.fetchall()
    scanned_qr = {row[0]: row[1] for row in scanned_data}  # Diccionario {qty: foto_entregado}

    conn.close()

    # Generar la secuencia expandida
    expanded_data = []
    for row in rows:
        trailer_list, factura_list, orden_compra_list, proveedor_list, ref_sl_list, qty_list = row
        for i in range(1, qty_list + 1):  # Generar secuencia basada en Qty_List
            expanded_data.append({
                'SL': ref_sl_list,
                'OrdenCompra': orden_compra_list,
                'QR_Val': i in scanned_qr,  # Marcar como escaneado si está en el conjunto
                'Sequence': i,  # Número de la secuencia
                'Pending': i not in scanned_qr and len(scanned_qr) > 0,  # Solo marcar como pendiente si hay QR escaneados
                'Foto': scanned_qr.get(i, '')  # ✅ Incluir la foto si existe
            })

    return jsonify(expanded_data)

@app.route('/guardar_escaneo', methods=['POST'])
def guardar_escaneo():
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401

    data = request.get_json()
    sl = data.get('sl')
    qty = data.get('qty')
    orden_compra = data.get('orden_compra')  # Obtener la Orden de Compra del frontend
    estatus = data.get('estatus')
    fecha_hora_escaneo = data.get('fecha_hora_escaneo')
    foto_entregado = data.get('foto_entregado', '')  # Foto opcional, valor predeterminado vacío

    # Si no se envía la fecha desde el cliente, generar una fecha con el formato correcto
    if not fecha_hora_escaneo:
        fecha_hora_escaneo = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Formato esperado

    if not sl or not qty or not orden_compra or not estatus or not fecha_hora_escaneo:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Validar que la Orden de Compra y el SL existan en la tabla 'datos'
        cursor.execute('''
            SELECT COUNT(*) FROM datos
            WHERE Ref_SL_List = ? AND Orden_Compra_List = ?
        ''', (sl, orden_compra))
        validacion = cursor.fetchone()[0]

        if validacion == 0:
            return jsonify({'success': False, 'message': 'La Orden de Compra no coincide con el SL proporcionado.'}), 400

        # Contar cuántos códigos ya han sido escaneados para este SL y Orden de Compra
        cursor.execute('''
            SELECT COUNT(*) FROM escaneos WHERE sl = ? AND orden_compra = ? AND estatus = 'Completado'
        ''', (sl, orden_compra))
        scanned_count = cursor.fetchone()[0]

        # Obtener el total de códigos esperados (Qty_List)
        cursor.execute('''
            SELECT Qty_List FROM datos WHERE Ref_SL_List = ? AND Orden_Compra_List = ?
        ''', (sl, orden_compra))
        total_qty = cursor.fetchone()[0]

        # Determinar el nuevo estado
        if scanned_count + 1 < total_qty:
            new_status = 'En Proceso'
        else:
            new_status = 'Completado'

        # Guardar el escaneo en la tabla 'escaneos', incluyendo la Orden de Compra
        cursor.execute('''
            INSERT INTO escaneos (sl, qty, orden_compra, estatus, Fecha_hora_escaneo, Foto_entregado)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sl, qty, orden_compra, 'Completado', fecha_hora_escaneo, foto_entregado))

        # Actualizar el estado en la tabla 'datos'
        cursor.execute('''
            UPDATE datos
            SET Estatus_List = ?, Fecha_hora_escaneo = ?
            WHERE Ref_SL_List = ? AND Orden_Compra_List = ?
        ''', (new_status, fecha_hora_escaneo, sl, orden_compra))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'sl': sl, 'orden_compra': orden_compra, 'qty': qty})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ✅ NUEVO ENDPOINT: Guardar foto de evidencia
@app.route('/guardar_foto_evidencia', methods=['POST'])
def guardar_foto_evidencia():
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401

    data = request.get_json()
    sl = data.get('sl')
    qty = data.get('qty')
    orden_compra = data.get('orden_compra')
    foto_base64 = data.get('foto')

    if not sl or not qty or not orden_compra or not foto_base64:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    try:
        # Decodificar la imagen base64
        foto_data = base64.b64decode(foto_base64.split(',')[1])
        
        # Crear un nombre único para la imagen
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        foto_filename = f"evidencia_{sl}_{orden_compra}_{qty}_{timestamp}.png"
        foto_path = os.path.join(EVIDENCE_FOLDER, foto_filename)  # Guardar en la nueva carpeta
        
        # Guardar la imagen en el servidor
        with open(foto_path, 'wb') as f:
            f.write(foto_data)

        # Actualizar la base de datos
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar el registro específico y actualizar la foto
        cursor.execute('''
            UPDATE escaneos
            SET Foto_entregado = ?
            WHERE sl = ? AND qty = ? AND orden_compra = ? AND estatus = 'Completado'
        ''', (foto_filename, sl, qty, orden_compra))
        
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'foto_filename': foto_filename})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/guardar_datos', methods=['POST'])
def guardar_datos():
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401

    data = request.get_json()
    caja = data.get('caja')
    fotos = data.get('data')

    if not caja or not fotos:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    try:
        for sl, imagen_base64 in fotos.items():
            # Decodificar la imagen base64 y guardarla en el servidor
            imagen_data = base64.b64decode(imagen_base64.split(',')[1])
            imagen_filename = f"{caja}_{sl}.png"
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename)
            with open(imagen_path, 'wb') as f:
                f.write(imagen_data)

            # Guardar los datos en la base de datos
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO escaneos (sl, qty, estatus, orden_compra)
                VALUES (?, ?, ?, ?)
            ''', (sl, 1, 'Guardado',))  # Agregar el valor de orden_compra
            conn.commit()
            conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Eliminar registros duplicados en la tabla 'datos'
def eliminar_registros_duplicados():
    try:
        print(f"Intentando abrir la base de datos en: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Eliminar registros duplicados, conservando solo el primero
        cursor.execute('''
            DELETE FROM datos
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM datos
                GROUP BY Trailer_List, Factura_List, Orden_Compra_List, Proveedor_List, Ref_SL_List, Qty_List, Estatus_List
            )
        ''')
        conn.commit()
        conn.close()
        print("Registros duplicados eliminados con éxito.")
    except sqlite3.OperationalError as e:
        print(f"Error al abrir la base de datos: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

# Llamar a la función para eliminar registros duplicados al iniciar la aplicación
eliminar_registros_duplicados()

@app.route('/upload_evidence', methods=['POST'])
def upload_evidence():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if 'evidence' not in request.files:
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.referrer)

    file = request.files['evidence']
    sl = request.form.get('sl')

    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'error')
        return redirect(request.referrer)

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{sl}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        flash('Evidencia subida correctamente', 'success')
    else:
        flash('Archivo no permitido. Solo se permiten imágenes.', 'error')

    return redirect(request.referrer)

@app.route('/reset_estatus', methods=['POST'])
def reset_estatus():
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401

    data = request.get_json()
    sl = data.get('sl')
    orden_compra = data.get('orden_compra')

    if not sl or not orden_compra:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Actualizar el estado en la tabla 'datos' a su valor predeterminado
        cursor.execute('''
            UPDATE datos
            SET Estatus_List = 'Por_Validar'
            WHERE Ref_SL_List = ? AND Orden_Compra_List = ?
        ''', (sl, orden_compra))

        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/ver_escaneos')
def ver_escaneos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        # Obtener los datos actualizados de la tabla 'escaneos'
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sl, qty, estatus, Fecha_hora_escaneo, Foto_entregado
            FROM escaneos
        """)
        escaneos = cursor.fetchall()
        conn.close()

        return render_template('Codigos_escaneados.html', escaneos=escaneos)
    except Exception as e:
        flash(f"Error al cargar los escaneos: {e}", "error")
        return redirect(url_for('gestion'))

@app.route('/eliminar_escaneos', methods=['POST'])
def eliminar_escaneos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    ids = request.form.getlist('ids[]')  # Obtener los IDs seleccionados
    if not ids:
        flash('No se seleccionó ningún escaneo para eliminar.', 'error')
        return redirect(url_for('ver_escaneos'))

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Obtener los SL y Orden de Compra de los registros seleccionados antes de eliminarlos
        cursor.execute(
            f"SELECT sl FROM escaneos WHERE id IN ({','.join('?' for _ in ids)})",
            ids
        )
        registros_a_actualizar = cursor.fetchall()

        # Eliminar los registros seleccionados de la tabla 'escaneos'
        cursor.executemany('DELETE FROM escaneos WHERE id = ?', [(id,) for id in ids])

        # Actualizar el estado de los registros correspondientes en la tabla 'datos'
        for registro in registros_a_actualizar:
            sl = registro[0]
            cursor.execute('''
                UPDATE datos
                SET Estatus_List = 'Por_Validar'
                WHERE Ref_SL_List = ?
            ''', (sl,))

        conn.commit()
        conn.close()

        flash('Escaneos eliminados y estados actualizados correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar escaneos: {e}', 'error')

    return redirect(url_for('ver_escaneos'))

# Código para depuración: Imprimir todos los escaneos al iniciar la aplicación
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM escaneos")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()

#import sqlite3
#DB_PATH = "c:\\Users\\MXRLuna03\\OneDrive - DENSO\\MTS Warehouse - Documents\\WH DX\\Scripts\\Scripts python\\DZ\\PowerApps\\Recibos3.0\\db_Recibos_Micelaneos\\database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def verificar_columnas_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(datos)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'Fecha_hora_escaneo' not in columns:
        print("Agregando columna 'Fecha_hora_escaneo' a la tabla 'datos'...")
        cursor.execute("ALTER TABLE datos ADD COLUMN Fecha_hora_escaneo TEXT DEFAULT ''")
        conn.commit()
        print("Columna 'Fecha_hora_escaneo' agregada con éxito.")
    conn.close()

# Llamar a esta función al iniciar la aplicación
verificar_columnas_datos()

if __name__ == '__main__':
    app.run(debug=True)