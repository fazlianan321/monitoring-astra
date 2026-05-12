from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# --- KONFIGURASI DATABASE XAMPP ---
# Pastikan XAMPP MySQL sudah Running. Nama database: db_astra
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/db_astra'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Folder untuk menyimpan foto rating
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- MODEL DATABASE (Tabel Kendaraan) ---
class Kendaraan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    no_polisi = db.Column(db.String(20), unique=True, nullable=False)
    nama_customer = db.Column(db.String(100))
    tipe_motor = db.Column(db.String(50))
    status = db.Column(db.String(50))
    persen = db.Column(db.Integer)
    mekanik = db.Column(db.String(100))
    estimasi = db.Column(db.String(50))
    rincian = db.Column(db.Text) 

# --- MODEL DATABASE (Tabel Rating) ---
class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    no_polisi = db.Column(db.String(20), nullable=False)
    bintang = db.Column(db.Integer, nullable=False)
    pesan = db.Column(db.Text)
    foto = db.Column(db.String(255))
    waktu = db.Column(db.DateTime, default=db.func.current_timestamp())

# Perintah otomatis buat tabel saat aplikasi jalan
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# --- FUNGSI CEK STATUS (UNTUK CUSTOMER) ---
@app.route('/cek-status', methods=['POST'])
def cek_status():
    raw_no_pol = request.form.get('no_polisi', '')
    no_pol = raw_no_pol.upper().replace(" ", "").strip()
    
    motor = Kendaraan.query.filter_by(no_polisi=no_pol).first()
    
    if motor:
        return jsonify({
            "success": True, 
            "data": {
                "nama": motor.nama_customer,
                "tipe": motor.tipe_motor,
                "status": motor.status,
                "persen": motor.persen,
                "mekanik": motor.mekanik,
                "estimasi": motor.estimasi,
                "rincian": motor.rincian.split(',') if motor.rincian else []
            }
        })
    return jsonify({"success": False, "message": "Nomor Polisi tidak ditemukan!"})

# --- FUNGSI UPDATE DATA (UNTUK MEKANIK) ---
@app.route('/update-progres', methods=['POST'])
def update_progres():
    # .replace(" ", "") ini WAJIB agar BE 123 AB jadi BE123AB di database
    no_pol = request.form.get('no_polisi', '').upper().replace(" ", "").strip()
    
    if not no_pol:
        return jsonify({"success": False, "message": "Nomor Polisi kosong!"})

    # Cari apakah motor ini sudah ada di database?
    motor = Kendaraan.query.filter_by(no_polisi=no_pol).first()
    
    if motor:
        # JIKA ADA: Lakukan UPDATE (Bukan tambah baru)
        motor.nama_customer = request.form.get('nama_customer')
        motor.tipe_motor = request.form.get('tipe_motor')
        motor.status = request.form.get('status')
        motor.persen = int(request.form.get('persen', 0))
        motor.mekanik = request.form.get('mekanik')
        motor.estimasi = request.form.get('estimasi')
        motor.rincian = request.form.get('rincian')
        db.session.commit()
        return jsonify({"success": True, "message": "Data Kendaraan BERHASIL DIUPDATE!"})
    else:
        # JIKA TIDAK ADA: Tambahkan Data Baru
        baru = Kendaraan(
            no_polisi=no_pol,
            nama_customer=request.form.get('nama_customer', 'Customer Astra'),
            tipe_motor=request.form.get('tipe_motor', 'Honda'),
            status=request.form.get('status'),
            persen=int(request.form.get('persen', 0)),
            mekanik=request.form.get('mekanik'),
            estimasi=request.form.get('estimasi'),
            rincian=request.form.get('rincian')
        )
        db.session.add(baru)
        db.session.commit()
        return jsonify({"success": True, "message": "Kendaraan Baru Berhasil Didaftarkan!"})

# --- FUNGSI SIMPAN RATING KE DATABASE ---
@app.route('/kirim-rating', methods=['POST'])
def kirim_rating():
    try:
        rating_val = request.form.get('rating')
        pesan_val = request.form.get('pesan')
        no_pol = request.form.get('no_polisi', 'ANONIM').upper().replace(" ", "")
        foto = request.files.get('foto')

        nama_file = None
        if foto and foto.filename != '':
            nama_file = f"rating_{no_pol}_{foto.filename}"
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nama_file))

        # Masukkan ke Tabel Rating
        baru_rating = Rating(
            no_polisi=no_pol,
            bintang=int(rating_val),
            pesan=pesan_val,
            foto=nama_file
        )
        db.session.add(baru_rating)
        db.session.commit()

        return jsonify({"success": True, "message": "Penilaian berhasil disimpan ke database!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# --- PINDAHKAN KE SINI (DI ATAS IF NAME) ---
@app.route('/get-semua-kendaraan')
def get_semua_kendaraan():
    # Mengambil semua data kendaraan, urutkan dari yang terbaru ditambahkan
    semua = Kendaraan.query.order_by(Kendaraan.id.desc()).all()
    data = []
    for k in semua:
        data.append({
            "no_polisi": k.no_polisi,
            "nama": k.nama_customer,
            "tipe": k.tipe_motor,
            "status": k.status,
            "persen": k.persen,
            "mekanik": k.mekanik,
            "estimasi": k.estimasi,
            "rincian": k.rincian
        })
    return jsonify(data)
@app.route('/hapus-kendaraan/<no_polisi>', methods=['DELETE'])
def hapus_kendaraan(no_polisi):
    try:
        # PENTING: Bersihkan spasi agar BE 123 AB (dari URL) cocok dengan BE123AB di database
        clean_no_pol = no_polisi.upper().replace(" ", "").strip()
        
        motor = Kendaraan.query.filter_by(no_polisi=clean_no_pol).first()
        
        if motor:
            db.session.delete(motor)
            db.session.commit()
            return jsonify({"success": True, "message": "Data berhasil dihapus"})
            
        return jsonify({"success": False, "message": "Data tidak ditemukan di database"}), 404
    except Exception as e:
        db.session.rollback() # Batalkan transaksi jika error agar DB tidak corrupt
        return jsonify({"success": False, "message": str(e)}), 500
# BARIS INI HARUS PALING BAWAH
if __name__ == '__main__':
    app.run(debug=True)