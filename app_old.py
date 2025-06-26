from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_mail import Mail, Message
import sqlite3
import os
from datetime import datetime, timedelta
import schedule
import time
import threading
from dotenv import load_dotenv
import logging

# Çevre değişkenlerini yükle
load_dotenv()

# Flask uygulamasını oluştur
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'inditex-stok-takip-secret-key-2025')

# E-posta yapılandırması
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)

# Veritabanı dosyası
DB_NAME = 'inditex_stok.db'

# Admin e-posta adresi
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@company.com')

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Veritabanını başlat ve örnek veriler ekle"""
    with sqlite3.connect(DB_NAME) as conn:
        # Ürünler tablosu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                category TEXT NOT NULL,
                size TEXT NOT NULL,
                color TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 5,
                max_stock INTEGER DEFAULT 100,
                location TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                image_url TEXT
            )
        ''')
        
        # Stok hareketleri tablosu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                reason TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_name TEXT DEFAULT 'Sistem',
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # E-posta bildirimleri tablosu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                notification_type TEXT NOT NULL,
                email TEXT NOT NULL,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Kullanıcı ayarları tablosu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Varsayılan ayarları ekle
        default_settings = [
            ('email_notifications_enabled', 'true'),
            ('daily_report_enabled', 'true'),
            ('low_stock_threshold', '5'),
            ('critical_stock_threshold', '2')
        ]
        
        for setting in default_settings:
            conn.execute('''
                INSERT OR IGNORE INTO user_settings (setting_name, setting_value)
                VALUES (?, ?)
            ''', setting)
        
        # Örnek ürünler
        sample_products = [
            ('ZR001234', 'Oversized Blazer', 'ZARA', 'Ceket', 'M', 'Siyah', 299.95, 15, 5, 50, 'A1-R2-S3', None),
            ('ZR001235', 'Mom Fit Jean', 'ZARA', 'Pantolon', 'S', 'Mavi', 199.95, 3, 5, 30, 'A2-R1-S4', None),
            ('PB002001', 'Graphic Tee', 'PULL&BEAR', 'Tişört', 'L', 'Beyaz', 79.95, 25, 10, 60, 'B1-R3-S2', None),
            ('BS003001', 'Denim Jacket', 'BERSHKA', 'Ceket', 'M', 'Lacivert', 159.95, 2, 5, 40, 'A3-R2-S1', None),
            ('ST004001', 'Floral Dress', 'STRADIVARIUS', 'Elbise', 'S', 'Çiçekli', 129.95, 1, 3, 25, 'C1-R1-S5', None),
            ('MD005001', 'Wool Coat', 'MASSIMO DUTTI', 'Palto', 'L', 'Gri', 499.95, 8, 3, 20, 'D1-R1-S1', None),
            ('OY006001', 'Yoga Pants', 'OYSHO', 'Sporcu', 'M', 'Siyah', 89.95, 20, 8, 50, 'E1-R2-S3', None)
        ]
        
        for product in sample_products:
            conn.execute('''
                INSERT OR IGNORE INTO products 
                (product_code, name, brand, category, size, color, price, quantity, min_stock, max_stock, location, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', product)

def get_all_products():
    """Tüm aktif ürünleri getir"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute('''
            SELECT id, product_code, name, brand, category, size, color, price, 
                   quantity, min_stock, max_stock, location, last_updated, status, image_url
            FROM products WHERE status = 'active' ORDER BY brand, name
        ''')
        return cursor.fetchall()

def get_low_stock_products():
    """Düşük stoklu ürünleri getir"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute('''
            SELECT * FROM products 
            WHERE quantity <= min_stock AND status = 'active'
            ORDER BY quantity ASC
        ''')
        return cursor.fetchall()

def get_critical_stock_products():
    """Kritik stoklu ürünleri getir"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute('''
            SELECT * FROM products 
            WHERE quantity <= 2 AND status = 'active'
            ORDER BY quantity ASC
        ''')
        return cursor.fetchall()

def add_stock_movement(product_id, movement_type, quantity, reason, user_name='Sistem'):
    """Stok hareketi ekle"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT INTO stock_movements (product_id, movement_type, quantity, reason, user_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, movement_type, quantity, reason, user_name))

def update_product_timestamp(product_id):
    """Ürün güncelleme zamanını güncelleştir"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            UPDATE products SET last_updated = CURRENT_TIMESTAMP WHERE id = ?
        ''', (product_id,))

def send_email(subject, recipients, html_body):
    """E-posta gönder"""
    try:
        if not app.config['MAIL_USERNAME']:
            logger.warning("E-posta yapılandırması eksik")
            return False
            
        msg = Message(
            subject=subject,
            sender=app.config['MAIL_USERNAME'],
            recipients=recipients if isinstance(recipients, list) else [recipients]
        )
        msg.html = html_body
        
        with app.app_context():
            mail.send(msg)
        
        logger.info(f"E-posta gönderildi: {subject}")
        return True
    except Exception as e:
        logger.error(f"E-posta gönderme hatası: {str(e)}")
        return False

def send_low_stock_alert(product):
    """Düşük stok uyarısı e-postası gönder"""
    subject = f"⚠️ Düşük Stok Uyarısı - {product[2]} ({product[1]})"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #dc3545, #fd7e14); padding: 20px; text-align: center; color: white;">
            <h1>🚨 Düşük Stok Uyarısı</h1>
        </div>
        
        <div style="padding: 20px; background-color: #f8f9fa;">
            <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #dc3545; margin-top: 0;">Stok Seviyesi Kritik!</h2>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Ürün Kodu:</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{product[1]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Ürün Adı:</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{product[2]}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Marka:</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{product[3]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Beden/Renk:</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">{product[5]} / {product[6]}</td>
                    </tr>
                    <tr style="background-color: #fff3cd;">
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold; color: #856404;">Mevcut Stok:</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; color: #856404; font-weight: bold;">{product[8]} adet</td>
                    </tr>
                    <tr style="background-color: #f8d7da;">
                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold; color: #721c24;">Minimum Stok:</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; color: #721c24; font-weight: bold;">{product[9]} adet</td>
                    </tr>
                </table>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <strong>⚡ Acil Eylem Gerekli!</strong><br>
                    Bu ürünün stok seviyesi minimum eşiğin altına düşmüştür. Lütfen en kısa sürede yeni stok siparişi verin.
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <p style="color: #6c757d; font-size: 14px;">
                        Bu e-posta Inditex Stok Takip Sistemi tarafından otomatik olarak gönderilmiştir.<br>
                        Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}
                    </p>
                </div>
            </div>
        </div>
    </div>
    """
    
    return send_email(subject, ADMIN_EMAIL, html_body)

def check_stock_levels():
    """Stok seviyelerini kontrol et ve gerekirse uyarı gönder"""
    try:
        critical_products = get_critical_stock_products()
        
        for product in critical_products:
            # Son 24 saat içinde bu ürün için uyarı gönderilmiş mi kontrol et
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM email_notifications 
                    WHERE product_id = ? AND notification_type = 'low_stock' 
                    AND sent_date > datetime('now', '-24 hours')
                ''', (product[0],))
                
                if cursor.fetchone()[0] == 0:  # Son 24 saatte uyarı gönderilmemiş
                    if send_low_stock_alert(product):
                        # Gönderilen uyarıyı kaydet
                        conn.execute('''
                            INSERT INTO email_notifications (product_id, notification_type, email)
                            VALUES (?, 'low_stock', ?)
                        ''', (product[0], ADMIN_EMAIL))
        
        logger.info("Stok seviyeleri kontrol edildi")
    except Exception as e:
        logger.error(f"Stok kontrol hatası: {str(e)}")

def schedule_background_tasks():
    """Arka plan görevlerini planla"""
    schedule.every(30).minutes.do(check_stock_levels)  # Her 30 dakikada bir stok kontrol et
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1 dakika bekle

# Arka plan görevlerini başlat
def start_background_tasks():
    background_thread = threading.Thread(target=schedule_background_tasks, daemon=True)
    background_thread.start()

@app.route('/')
def index():
    """Ana sayfa"""
    products = get_all_products()
    low_stock = get_low_stock_products()
    critical_stock = get_critical_stock_products()
    
    # İstatistikler
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'active'")
        total_products = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT SUM(quantity) FROM products WHERE status = 'active'")
        total_stock = cursor.fetchone()[0] or 0
        
        cursor = conn.execute("SELECT COUNT(*) FROM products WHERE quantity <= min_stock AND status = 'active'")
        low_stock_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM products WHERE quantity <= 2 AND status = 'active'")
        critical_stock_count = cursor.fetchone()[0]
        
        # Marka bazında istatistikler
        cursor = conn.execute('''
            SELECT brand, COUNT(*), SUM(quantity), SUM(price * quantity) as total_value
            FROM products WHERE status = 'active' 
            GROUP BY brand ORDER BY total_value DESC
        ''')
        brand_stats = cursor.fetchall()
    
    stats = {
        'total_products': total_products,
        'total_stock': total_stock,
        'low_stock_count': low_stock_count,
        'critical_stock_count': critical_stock_count,
        'total_value': sum([p[7] * p[8] for p in products]),  # toplam değer
        'brand_stats': brand_stats
    }
    
    return render_template('index.html', 
                         products=products, 
                         low_stock=low_stock,
                         critical_stock=critical_stock,
                         stats=stats)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    """Ürün ekleme"""
    if request.method == 'POST':
        try:
            # Form verilerini al
            name = request.form['name'].strip()
            sku = request.form['sku'].strip().upper()
            url = request.form.get('url', '').strip()
            current_stock = int(request.form['current_stock'])
            min_stock = int(request.form['min_stock'])
            description = request.form.get('description', '').strip()
            email_notifications = 'email_notifications' in request.form
            color = request.form['color'].strip()
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            min_stock = int(request.form['min_stock'])
            max_stock = int(request.form['max_stock'])
            location = request.form['location'].strip()
            
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute('''
                    INSERT INTO products 
                    (product_code, name, brand, category, size, color, price, quantity, min_stock, max_stock, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product_code, name, brand, category, size, color, price, quantity, min_stock, max_stock, location))
                
                # Stok hareketi ekle
                product_id = conn.lastrowid
                add_stock_movement(product_id, 'giriş', quantity, 'İlk stok girişi', 'Admin')
            
            flash(f'✅ {name} başarıyla eklendi!', 'success')
            return redirect(url_for('index'))
            
        except sqlite3.IntegrityError:
            flash('❌ Bu ürün kodu zaten mevcut!', 'danger')
        except ValueError:
            flash('❌ Lütfen geçerli sayısal değerler girin!', 'danger')
        except Exception as e:
            flash(f'❌ Hata: {str(e)}', 'danger')
    
    return render_template('add_product.html')

@app.route('/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    """Stok güncelleme"""
    try:
        action = request.form['action']
        quantity = int(request.form['quantity'])
        reason = request.form.get('reason', '').strip()
        
        with sqlite3.connect(DB_NAME) as conn:
            # Mevcut stok miktarını al
            cursor = conn.execute("SELECT quantity, name, min_stock FROM products WHERE id = ?", (product_id,))
            result = cursor.fetchone()
            
            if not result:
                flash('❌ Ürün bulunamadı!', 'danger')
                return redirect(url_for('index'))
            
            current_stock, product_name, min_stock = result
            
            if action == 'add':
                new_quantity = current_stock + quantity
                movement_type = 'giriş'
                flash_message = f'✅ {product_name} için {quantity} adet stok eklendi!'
            else:  # remove
                if quantity > current_stock:
                    flash(f'❌ Yetersiz stok! Mevcut: {current_stock} adet', 'danger')
                    return redirect(url_for('index'))
                
                new_quantity = current_stock - quantity
                movement_type = 'çıkış'
                flash_message = f'✅ {product_name} için {quantity} adet stok çıkarıldı!'
            
            # Stok güncelle
            conn.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_quantity, product_id))
            
            # Hareket kaydı ekle
            add_stock_movement(product_id, movement_type, quantity, reason, 'Admin')
            update_product_timestamp(product_id)
            
            flash(flash_message, 'success')
            
            # Düşük stok kontrolü
            if new_quantity <= min_stock and movement_type == 'çıkış':
                flash(f'⚠️ Dikkat: {product_name} stoku minimum seviyeye düştü!', 'warning')
    
    except ValueError:
        flash('❌ Lütfen geçerli bir miktar girin!', 'danger')
    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    """Ürün silme (soft delete)"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute("SELECT name FROM products WHERE id = ?", (product_id,))
            result = cursor.fetchone()
            
            if result:
                product_name = result[0]
                conn.execute("UPDATE products SET status = 'deleted' WHERE id = ?", (product_id,))
                add_stock_movement(product_id, 'silme', 0, 'Ürün silindi', 'Admin')
                flash(f'✅ {product_name} başarıyla silindi!', 'success')
            else:
                flash('❌ Ürün bulunamadı!', 'danger')
    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/reports')
def reports():
    """Raporlar sayfası"""
    with sqlite3.connect(DB_NAME) as conn:
        # Son 30 günlük stok hareketleri
        cursor = conn.execute('''
            SELECT sm.date, p.name, p.brand, sm.movement_type, sm.quantity, sm.reason, sm.user_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            WHERE sm.date >= datetime('now', '-30 days')
            ORDER BY sm.date DESC
            LIMIT 100
        ''')
        recent_movements = cursor.fetchall()
        
        # Marka bazında stok dağılımı
        cursor = conn.execute('''
            SELECT brand, COUNT(*) as product_count, SUM(quantity) as total_stock,
                   AVG(price) as avg_price, SUM(price * quantity) as total_value
            FROM products WHERE status = 'active'
            GROUP BY brand
            ORDER BY total_value DESC
        ''')
        brand_analysis = cursor.fetchall()
        
        # Kategori bazında analiz
        cursor = conn.execute('''
            SELECT category, COUNT(*) as product_count, SUM(quantity) as total_stock,
                   AVG(price) as avg_price
            FROM products WHERE status = 'active'
            GROUP BY category
            ORDER BY total_stock DESC
        ''')
        category_analysis = cursor.fetchall()
    
    return render_template('reports.html',
                         recent_movements=recent_movements,
                         brand_analysis=brand_analysis,
                         category_analysis=category_analysis)

@app.route('/api/stock_chart')
def stock_chart_data():
    """Stok grafiği için JSON verisi"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute('''
            SELECT brand, SUM(quantity) as total_stock
            FROM products WHERE status = 'active'
            GROUP BY brand
            ORDER BY total_stock DESC
        ''')
        data = cursor.fetchall()
    
    return jsonify({
        'labels': [row[0] for row in data],
        'data': [row[1] for row in data]
    })

@app.route('/test_email')
def test_email():
    """E-posta test endpoint (sadece development için)"""
    if app.debug:
        test_product = ('TEST001', 'Test Ürün', 'ZARA', 'Test', 'M', 'Siyah', 99.99, 1, 5, 50, 'A1-R1-S1')
        if send_low_stock_alert(test_product):
            return "E-posta başarıyla gönderildi!"
        else:
            return "E-posta gönderilirken hata oluştu!"
    return "Bu endpoint sadece development modunda kullanılabilir."

if __name__ == '__main__':
    init_db()
    start_background_tasks()
    
    print("🚀 Inditex Stok Takip Sistemi başlatılıyor...")
    print("📧 E-posta bildirimleri aktif")
    print("🔄 Otomatik stok kontrolleri çalışıyor")
    print("🌐 Uygulama: http://127.0.0.1:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
