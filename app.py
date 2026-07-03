import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuración del disco permanente de Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/data/catalogo_fijo.db'
app.config['STATIC_UPLOADS'] = '/var/data/uploads'
app.config['SECRET_KEY'] = 'mi_clave_secreta_123'

# Asegurar que la carpeta del disco exista
os.makedirs(app.config['STATIC_UPLOADS'], exist_ok=True)

db = SQLAlchemy(app)

# --- MODELOS ---
class Inmueble(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.String(50), nullable=False)
    google_maps = db.Column(db.String(500))
    imagen_principal = db.Column(db.String(200))
    disponible = db.Column(db.Boolean, default=True) # Mantiene el estado activo/oculto
    galeria = db.relationship('FotoGaleria', backref='inmueble', cascade="all, delete-orphan", lazy=True)

class FotoGaleria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inmueble_id = db.Column(db.Integer, db.ForeignKey('inmueble.id'), nullable=False)
    ruta_foto = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

# --- RUTA CLAVE: Servir las imágenes de forma correcta y con permisos ---
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['STATIC_UPLOADS'], filename, as_attachment=False)

# --- RUTAS PÚBLICAS ---
@app.route('/')
def index():
    # Solo muestra en la web principal los inmuebles que tengan disponible = True
    todos_inmuebles = Inmueble.query.filter_by(disponible=True).order_by(Inmueble.sector).all()
    inmuebles_por_sector = {}
    for inm in todos_inmuebles:
        if inm.sector not in inmuebles_por_sector:
            inmuebles_por_sector[inm.sector] = []
        inmuebles_por_sector[inm.sector].append(inm)
    return render_template('index.html', sectores=inmuebles_por_sector)

# --- RUTAS DE ADMINISTRACIÓN ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        titulo = request.form['titulo']
        sector = request.form['sector']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        google_maps = request.form['google_maps']
        
        foto_principal = request.files['imagen_principal']
        filename_principal = 'default.jpg'
        if foto_principal and foto_principal.filename != '':
            filename_principal = 'principal_' + secure_filename(foto_principal.filename)
            foto_principal.save(os.path.join(app.config['STATIC_UPLOADS'], filename_principal))
        
        nuevo_inmueble = Inmueble(
            titulo=titulo, sector=sector, descripcion=descripcion,
            precio=precio, google_maps=google_maps, imagen_principal=filename_principal, disponible=True
        )
        db.session.add(nuevo_inmueble)
        db.session.commit()
        
        fotos_galeria = request.files.getlist('galeria_fotos')
        for idx, foto in enumerate(fotos_galeria):
            if foto and foto.filename != '':
                filename_galeria = f"galeria_{nuevo_inmueble.id}_{idx}_{secure_filename(foto.filename)}"
                foto.save(os.path.join(app.config['STATIC_UPLOADS'], filename_galeria))
                nueva_foto = FotoGaleria(inmueble_id=nuevo_inmueble.id, ruta_foto=filename_galeria)
                db.session.add(nueva_foto)
        
        db.session.commit()
        return redirect(url_for('admin'))
        
    lista_inmuebles = Inmueble.query.all()
    return render_template('admin.html', inmuebles=lista_inmuebles)

# --- NUEVA RUTA: Botón de Alternar Visibilidad (Mostrar/Ocultar) ---
@app.route('/admin/alternar/<int:id>')
def alternar_disponibilidad(id):
    inmueble = Inmueble.query.get_or_404(id)
    inmueble.disponible = not inmueble.disponible
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/eliminar/<int:id>')
def eliminar(id):
    inmueble = Inmueble.query.get_or_404(id)
    db.session.delete(inmueble)
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)