import os
from datetime import datetime
import pymysql
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, or_
# Removed specific import INTEGER as we will use db.Integer and db.BigInteger

# Uygulama Ayarları
app = Flask(__name__)

# Veritabanı Ayarları
# MySQL Bağlantısı (Localhost / XAMPP)
# Format: mysql+pymysql://username:password@host/databasename
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/fleet_pro'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super_secret_key_for_demo'

# DB Nesnesi
db = SQLAlchemy(app)

# -------------------------
# MODELLER
# -------------------------

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    # Existing DB uses BIGINT for id
    id = db.Column(db.BigInteger, primary_key=True)
    plate = db.Column(db.String(20), unique=True, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    current_km = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), default='Müsait') # 'Müsait', 'Kirada', 'Bakımda'
    daily_rate = db.Column(db.Float, default=0.0)

    # İlişkiler
    rentals = db.relationship('Rental', backref='vehicle', lazy=True)
    expenses = db.relationship('Expense', backref='vehicle', lazy=True)

class Customer(db.Model):
    __tablename__ = 'customers'
    # Existing DB uses INTEGER for id
    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(100), nullable=False)
    telefon = db.Column(db.String(20), nullable=False)
    ehliyet_no = db.Column(db.String(50), unique=True, nullable=False)
    notlar = db.Column(db.Text)

    # İlişkiler
    rentals = db.relationship('Rental', backref='customer', lazy=True)

class Rental(db.Model):
    __tablename__ = 'rentals'
    id = db.Column(db.Integer, primary_key=True)
    
    # Matches Vehicle.id (BigInteger)
    vehicle_id = db.Column(db.BigInteger, db.ForeignKey('vehicles.id'), nullable=False)
    
    # Matches Customer.id (Integer)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    baslangic_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    bitis_tarihi = db.Column(db.DateTime)
    toplam_ucret = db.Column(db.Float)
    kiralama_durumu = db.Column(db.String(20), default='Aktif') # 'Aktif', 'Tamamlandı'
    initial_km = db.Column(db.Integer)
    end_km = db.Column(db.Integer)

class Expense(db.Model):
    __tablename__ = 'expenses'
    # Existing DB uses BIGINT for id
    id = db.Column(db.BigInteger, primary_key=True)
    
    # Matches Vehicle.id (BigInteger)
    vehicle_id = db.Column(db.BigInteger, db.ForeignKey('vehicles.id'), nullable=False)
    
    # Note: Column names below might differ from DB if you didn't update them,
    # but SQLAlchemy won't error unless you try to query/insert.
    masraf_turu = db.Column(db.String(50), nullable=False) # 'Bakım', 'Yakıt', 'Kaza'
    tutar = db.Column(db.Float, nullable=False)
    aciklama = db.Column(db.Text)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------
# YARDIMCI FONKSİYONLAR
# -------------------------

def update_rental_status():
    """Süresi dolan kiralamaları kontrol eder ve günceller."""
    try:
        # Aktif kiralamaları getir
        active_rentals = Rental.query.filter_by(kiralama_durumu='Aktif').all()
        changes = False
        
        for rental in active_rentals:
            # Süresi dolmuşsa
            if rental.bitis_tarihi and rental.bitis_tarihi < datetime.now():
                rental.kiralama_durumu = 'Tamamlandı'
                
                # Aracı müsait yap
                vehicle = Vehicle.query.get(rental.vehicle_id)
                if vehicle:
                    vehicle.status = 'Müsait' # Değişiklik: durum -> status
                
                changes = True
        
        if changes:
            db.session.commit()
            
    except Exception as e:
        print(f"Hata (Otomatik Kontrol): {e}")

# -------------------------
# ROTALAR
# -------------------------

@app.route('/')
def index():
    update_rental_status()
    total_vehicles = Vehicle.query.count()
    rented_vehicles = Vehicle.query.filter_by(status='Kirada').count() # Değişiklik: durum -> status
    available_vehicles = Vehicle.query.filter_by(status='Müsait').count() # Değişiklik: durum -> status
    
    total_income_query = db.session.query(db.func.sum(Rental.toplam_ucret)).scalar()
    total_income = total_income_query if total_income_query else 0
    
    total_expense_query = db.session.query(db.func.sum(Expense.tutar)).scalar()
    total_expense = total_expense_query if total_expense_query else 0

    net_profit = total_income - total_expense

    return render_template('index.html', 
                           total_vehicles=total_vehicles,
                           rented_vehicles=rented_vehicles,
                           available_vehicles=available_vehicles,
                           total_income=total_income,
                           total_expense=total_expense,
                           net_profit=net_profit)

# Yeni API JSON Endpoint
@app.route('/api/vehicles')
def get_vehicles_json():
    vehicles = Vehicle.query.all()
    data = []
    for v in vehicles:
        data.append({
            'id': v.id,
            'plate': v.plate,
            'brand': v.brand,
            'model': v.model,
            'year': v.year,
            'current_km': v.current_km,
            'status': v.status,
            'daily_rate': v.daily_rate
        })
    return jsonify(data)

@app.route('/vehicles', methods=['GET', 'POST'])
def vehicles():
    if request.method == 'POST':
        try:
            # HTML Form eski isimleri kullanıyor olabilir, onları alıyoruz
            plaka = request.form.get('plaka')
            marka = request.form.get('marka')
            model = request.form.get('model')
            yil = request.form.get('yil')
            guncel_km = request.form.get('guncel_km')
            daily_rate = request.form.get('daily_rate')

            new_vehicle = Vehicle(
                plate=plaka,         # Mapping: plaka -> plate
                brand=marka,         # Mapping: marka -> brand
                model=model,
                year=int(yil) if yil else 0,              # Mapping: yil -> year
                current_km=int(guncel_km) if guncel_km else 0,  # Mapping: guncel_km -> current_km
                daily_rate=float(daily_rate) if daily_rate else 0.0
            )
            # Default status zaten 'Müsait'
            
            db.session.add(new_vehicle)
            db.session.commit()
            flash('Araç başarıyla eklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('vehicles'))

    vehicles = Vehicle.query.all()
    return render_template('vehicles.html', vehicles=vehicles)

@app.route('/delete_vehicle/<int:id>')
def delete_vehicle(id):
    try:
        vehicle = Vehicle.query.get_or_404(id)
        
        # İlişkili kayıtları temizle
        Rental.query.filter_by(vehicle_id=id).delete()
        Expense.query.filter_by(vehicle_id=id).delete()

        db.session.delete(vehicle)
        db.session.commit()
        flash('Araç ve geçmiş kayıtları başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Silme işleminde hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('vehicles'))

@app.route('/delete_customer/<int:id>')
def delete_customer(id):
    try:
        customer = Customer.query.get_or_404(id)
        
        # 1. Aktif kiralamaları bul ve araçları boşa çıkar
        active_rentals = Rental.query.filter_by(customer_id=id, kiralama_durumu='Aktif').all()
        for rental in active_rentals:
            vehicle = Vehicle.query.get(rental.vehicle_id)
            if vehicle:
                vehicle.status = 'Müsait' # Değişiklik: durum -> status
        
        # 2. Geçmiş kiralamaları sil
        Rental.query.filter_by(customer_id=id).delete()
        
        # 3. Müşteriyi sil
        db.session.delete(customer)
        db.session.commit()
        flash(f'{customer.ad_soyad} ve tüm geçmiş kayıtları başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Silme işleminde hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('customers'))

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'POST':
        try:
            ad_soyad = request.form.get('ad_soyad')
            telefon = request.form.get('telefon')
            ehliyet_no = request.form.get('ehliyet_no')
            notlar = request.form.get('notlar')

            new_customer = Customer(
                ad_soyad=ad_soyad, telefon=telefon,
                ehliyet_no=ehliyet_no, notlar=notlar
            )
            db.session.add(new_customer)
            db.session.commit()
            flash('Müşteri başarıyla eklendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('customers'))

    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/rentals', methods=['GET', 'POST'])
def rentals():
    update_rental_status()
    if request.method == 'POST':
        try:
            vehicle_id = request.form.get('vehicle_id')
            customer_id = request.form.get('customer_id')
            baslangic_tarihi_str = request.form.get('baslangic_tarihi')
            bitis_tarihi_str = request.form.get('bitis_tarihi')
            initial_km_str = request.form.get('initial_km')

            if not vehicle_id or not customer_id or not baslangic_tarihi_str or not bitis_tarihi_str:
                flash('Lütfen tüm alanları doldurun.', 'error')
                return redirect(url_for('rentals'))

            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                flash('Araç bulunamadı.', 'error')
                return redirect(url_for('rentals'))
            
            # Allow rental if status is 'active' OR 'Müsait'
            if vehicle.status not in ['active', 'Müsait']:
                flash('Bu araç şu anda müsait değil!', 'error')
                return redirect(url_for('rentals'))
            
            initial_km = int(initial_km_str) if initial_km_str else vehicle.current_km
            
            # Tarih Hesaplama
            baslangic_tarihi = datetime.strptime(baslangic_tarihi_str, '%Y-%m-%dT%H:%M')
            bitis_tarihi = datetime.strptime(bitis_tarihi_str, '%Y-%m-%dT%H:%M')
            
            if bitis_tarihi <= baslangic_tarihi:
                flash('Bitiş tarihi başlangıç tarihinden sonra olmalıdır.', 'error')
                return redirect(url_for('rentals'))

            new_rental = Rental(
                vehicle_id=vehicle_id, customer_id=customer_id,
                baslangic_tarihi=baslangic_tarihi,
                bitis_tarihi=bitis_tarihi,
                initial_km=initial_km,
                toplam_ucret=0.0 # Will be calculated later or manually
            )
            
            # Aracın durumunu güncelle
            vehicle.status = 'Kirada'
            
            db.session.add(new_rental)
            db.session.commit()
            flash(f'Kiralama işlemi başlatıldı.', 'success')
            return redirect(url_for('rentals'))

        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
            return redirect(url_for('rentals'))

    # GET
    rental_list = Rental.query.filter_by(kiralama_durumu='Aktif').all()
    # Fetch available vehicles (status='active' OR status='Müsait')
    available_vehicles = Vehicle.query.filter(or_(Vehicle.status == 'active', Vehicle.status == 'Müsait')).all()
    customers = Customer.query.all()
    print(f"DEBUG: Found {len(available_vehicles)} available vehicles")
    
    return render_template('rentals.html', 
                           rental_list=rental_list, 
                           vehicles=available_vehicles, 
                           customers=customers)

@app.route('/complete_rental/<int:id>', methods=['POST'])
def complete_rental(id):
    try:
        rental = Rental.query.get_or_404(id)
        
        if rental.kiralama_durumu == 'Tamamlandı':
             flash('Bu kiralama zaten tamamlanmış.', 'warning')
             return redirect(url_for('rentals'))

        end_km_str = request.form.get('end_km')
        end_km = int(end_km_str) if end_km_str else 0

        vehicle = Vehicle.query.get(rental.vehicle_id)
        
        # Validation
        if vehicle and end_km < vehicle.current_km:
            flash(f'Hata: Yeni KM ({end_km}) eskiden ({vehicle.current_km}) düşük olamaz!', 'error')
            return redirect(url_for('rentals'))

        # Update Vehicle
        if vehicle:
            vehicle.current_km = end_km
            vehicle.status = 'active' # Reset to active (English key) as requested
        
        # Update Rental
        rental.end_km = end_km
        rental.kiralama_durumu = 'Tamamlandı'
        
        # Calculate Fee
        now = datetime.now()
        # Ensure we are using compatible datetime objects (naive vs naive)
        # baslangic_tarihi comes from strptime so it is naive
        duration = now - rental.baslangic_tarihi
        days = duration.days
        if days == 0:
            days = 1
            
        # Use daily_rate from vehicle
        daily_rate = vehicle.daily_rate if vehicle.daily_rate else 0.0
        total_price = days * daily_rate
        
        rental.toplam_ucret = total_price
            
        db.session.commit()
        flash(f'Araç ({vehicle.plate}) başarıyla teslim alındı. Yeni KM: {end_km}. Toplam Ücret: {total_price:.2f} TL', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Teslim alma sırasında hata oluştu: {str(e)}', 'error')
        
    return redirect(url_for('rentals'))

@app.route('/expenses/new', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        try:
            vehicle_id = request.form.get('vehicle_id')
            masraf_turu = request.form.get('masraf_turu')
            tutar_str = request.form.get('tutar')
            aciklama = request.form.get('aciklama')
            
            tutar = float(tutar_str) if tutar_str and tutar_str.strip() else 0.0

            new_expense = Expense(
                vehicle_id=vehicle_id, masraf_turu=masraf_turu,
                tutar=tutar, aciklama=aciklama
            )
            db.session.add(new_expense)
            db.session.commit()
            flash('Masraf başarıyla kaydedildi.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Hata: {str(e)}', 'error')
            return redirect(url_for('add_expense'))

    vehicles = Vehicle.query.all()
    return render_template('add_expense.html', vehicles=vehicles)


@app.route('/expenses')
def expenses():
    expenses = Expense.query.order_by(Expense.tarih.desc()).all()
    
    total_expense_query = db.session.query(db.func.sum(Expense.tutar)).scalar()
    total_expense = total_expense_query if total_expense_query else 0
    
    return render_template('expenses.html', expenses=expenses, total_expense=total_expense)

@app.route('/delete_expense/<int:id>')
def delete_expense(id):
    try:
        expense = Expense.query.get_or_404(id)
        db.session.delete(expense)
        db.session.commit()
        flash('Masraf kaydı başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Silme işleminde hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('expenses'))

# Veritabanını Başlatma Yardımcısı
def init_db():
    with app.app_context():
        # Tabloları oluştur (SQLAlchemy, mevcut tabloları overwrite etmez, yoksa oluşturur)
        # MySQL tarafında tablolar zaten varsa bu işlem güvenlidir.
        db.create_all()
        # Migration veya kolon ekleme işlemleri kaldırıldı çünkü "EXISTING" tablo kullanılması istendi.

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
