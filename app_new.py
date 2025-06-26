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
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'inditex-stok-takip-secret-key-2025')

# E-posta yapılandırması
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

# Veritabanı dosyası
DB_NAME = 'inditex_stok.db'

# Bildirim e-postaları
NOTIFICATION_EMAILS = os.environ.get('NOTIFICATION_EMAILS', 'admin@company.com').split(',')

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Veritabanını başlat ve örnek veriler ekle"""
    with sqlite3.connect(DB_NAME) as conn:
        # Ürünler tablosu - Basitleştirilmiş şema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                url TEXT,
                current_stock INTEGER NOT NULL DEFAULT 0,
                min_stock INTEGER NOT NULL DEFAULT 5,
                description TEXT,
                email_notifications BOOLEAN DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')

        # Stok hareketleri tablosu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                old_stock INTEGER,
                new_stock INTEGER,
                description TEXT,
                user_name TEXT DEFAULT 'Admin',
                movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        
        # Örnek ürünler - Basitleştirilmiş
        sample_products = [
            ('Oversized Blazer', 'ZR001234', 'https://www.zara.com/tr/blazer', 15, 5, 'ZARA marka oversized blazer, siyah renk, M beden'),
            ('Mom Fit Jean', 'ZR001235', 'https://www.zara.com/tr/jean', 3, 5, 'ZARA marka mom fit jean, mavi renk, S beden'),
            ('Graphic Tee', 'PB002001', 'https://www.pullandbear.com/tr/tee', 25, 10, 'Pull&Bear marka graphic tişört, beyaz renk, L beden'),
            ('Denim Jacket', 'BS003001', 'https://www.bershka.com/tr/jacket', 2, 5, 'Bershka marka denim ceket, lacivert renk, M beden'),
            ('Floral Dress', 'ST004001', 'https://www.stradivarius.com/tr/dress', 1, 3, 'Stradivarius marka çiçekli elbise, S beden'),
            ('Wool Coat', 'MD005001', 'https://www.massimodutti.com/tr/coat', 8, 3, 'Massimo Dutti marka yün palto, gri renk, L beden'),
            ('Yoga Pants', 'OY006001', 'https://www.oysho.com/tr/yoga', 20, 8, 'Oysho marka yoga pantolonu, siyah renk, M beden')
        ]
        
        for product in sample_products:
            conn.execute('''
                INSERT OR IGNORE INTO products 
                (name, sku, url, current_stock, min_stock, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', product)

        conn.commit()
        logger.info("Veritabanı başarıyla oluşturuldu.")

def get_db_connection():
    """Veritabanı bağlantısı al"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_products():
    """Tüm aktif ürünleri getir"""
    conn = get_db_connection()
    products = conn.execute('''
        SELECT * FROM products WHERE status = 'active' ORDER BY name
    ''').fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    """ID'ye göre ürün getir"""
    conn = get_db_connection()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ? AND status = "active"', (product_id,)
    ).fetchone()
    conn.close()
    return product

def get_low_stock_products():
    """Düşük stoklu ürünleri getir"""
    conn = get_db_connection()
    products = conn.execute('''
        SELECT * FROM products 
        WHERE current_stock <= min_stock AND status = 'active'
        ORDER BY current_stock ASC
    ''').fetchall()
    conn.close()
    return products

def add_stock_movement(product_id, movement_type, quantity, old_stock, new_stock, description=''):
    """Stok hareketi ekle"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO stock_movements 
        (product_id, movement_type, quantity, old_stock, new_stock, description)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (product_id, movement_type, quantity, old_stock, new_stock, description))
    conn.commit()
    conn.close()

def send_low_stock_notification(product):
    """Düşük stok uyarısı e-postası gönder"""
    if not app.config['MAIL_USERNAME']:
        logger.warning("E-posta yapılandırması bulunamadı.")
        return False
    
    try:
        subject = f"⚠️ Düşük Stok Uyarısı - {product['name']} ({product['sku']})"
        
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
                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">SKU:</td>
                            <td style="padding: 10px; border: 1px solid #dee2e6;">{product['sku']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Ürün Adı:</td>
                            <td style="padding: 10px; border: 1px solid #dee2e6;">{product['name']}</td>
                        </tr>
                        <tr style="background-color: #fff3cd;">
                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold; color: #856404;">Mevcut Stok:</td>
                            <td style="padding: 10px; border: 1px solid #dee2e6; color: #856404; font-weight: bold;">{product['current_stock']} adet</td>
                        </tr>
                        <tr style="background-color: #f8d7da;">
                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold; color: #721c24;">Minimum Stok:</td>
                            <td style="padding: 10px; border: 1px solid #dee2e6; color: #721c24; font-weight: bold;">{product['min_stock']} adet</td>
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
        
        for email in NOTIFICATION_EMAILS:
            email = email.strip()
            if email:
                msg = Message(subject=subject, recipients=[email], html=html_body)
                mail.send(msg)
                
                # Bildirim kaydını veritabanına ekle
                conn = get_db_connection()
                conn.execute('''
                    INSERT INTO email_notifications (product_id, notification_type, email)
                    VALUES (?, ?, ?)
                ''', (product['id'], 'low_stock', email))
                conn.commit()
                conn.close()
        
        logger.info(f"Düşük stok bildirimi gönderildi: {product['name']}")
        return True
        
    except Exception as e:
        logger.error(f"E-posta gönderme hatası: {str(e)}")
        return False

def check_stock_levels():
    """Stok seviyelerini kontrol et ve gerekirse bildirim gönder"""
    low_stock_products = get_low_stock_products()
    
    for product in low_stock_products:
        if product['email_notifications']:
            # Son 24 saat içinde bildirim gönderildi mi kontrol et
            conn = get_db_connection()
            recent_notification = conn.execute('''
                SELECT * FROM email_notifications 
                WHERE product_id = ? AND notification_type = 'low_stock' 
                AND datetime(sent_date) > datetime('now', '-24 hours')
            ''', (product['id'],)).fetchone()
            conn.close()
            
            if not recent_notification:
                send_low_stock_notification(product)

# Routes
@app.route('/')
def index():
    """Ana sayfa"""
    products = get_all_products()
    
    # İstatistikler
    total_products = len(products)
    in_stock = len([p for p in products if p['current_stock'] > p['min_stock']])
    low_stock = len([p for p in products if 0 < p['current_stock'] <= p['min_stock']])
    out_of_stock = len([p for p in products if p['current_stock'] == 0])
    
    stats = {
        'total_products': total_products,
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock
    }
    
    return render_template('index.html', products=products, stats=stats)

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
            
            # Veritabanına ekle
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO products 
                (name, sku, url, current_stock, min_stock, description, email_notifications)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, sku, url, current_stock, min_stock, description, email_notifications))
            
            product_id = conn.lastrowid
            
            # Stok hareketi ekle
            add_stock_movement(product_id, 'giriş', current_stock, 0, current_stock, 'İlk stok girişi')
            
            conn.commit()
            conn.close()
            
            flash('✅ Ürün başarıyla eklendi!', 'success')
            return jsonify({'success': True, 'message': 'Ürün başarıyla eklendi!'})
            
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Bu SKU zaten mevcut!'})
        except ValueError:
            return jsonify({'success': False, 'message': 'Lütfen geçerli sayısal değerler girin!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Hata: {str(e)}'})
    
    return render_template('add_product.html')

@app.route('/reports')
def reports():
    """Raporlar sayfası"""
    products = get_all_products()
    
    total_products = len(products)
    total_value = sum([p['current_stock'] * 50 for p in products])  # Örnek fiyat
    low_stock_count = len([p for p in products if 0 < p['current_stock'] <= p['min_stock']])
    out_of_stock_count = len([p for p in products if p['current_stock'] == 0])
    
    return render_template('reports.html', 
                         products=products,
                         total_products=total_products,
                         total_value=total_value,
                         low_stock_count=low_stock_count,
                         out_of_stock_count=out_of_stock_count)

# API Routes
@app.route('/api/product/<int:product_id>')
def api_get_product(product_id):
    """API: Ürün detayı"""
    product = get_product_by_id(product_id)
    if product:
        return jsonify(dict(product))
    return jsonify({'error': 'Ürün bulunamadı'}), 404

@app.route('/api/update_stock/<int:product_id>', methods=['POST'])
def api_update_stock(product_id):
    """API: Stok güncelle"""
    try:
        data = request.get_json()
        current_stock = int(data['current_stock'])
        min_stock = int(data['min_stock'])
        
        # Mevcut ürünü al
        product = get_product_by_id(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Ürün bulunamadı'})
        
        old_stock = product['current_stock']
        
        # Stoku güncelle
        conn = get_db_connection()
        conn.execute('''
            UPDATE products 
            SET current_stock = ?, min_stock = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (current_stock, min_stock, product_id))
        conn.commit()
        conn.close()
        
        # Stok hareketi ekle
        if old_stock != current_stock:
            movement_type = 'giriş' if current_stock > old_stock else 'çıkış'
            quantity = abs(current_stock - old_stock)
            add_stock_movement(product_id, movement_type, quantity, old_stock, current_stock, 'Manuel güncelleme')
        
        return jsonify({'success': True, 'message': 'Stok başarıyla güncellendi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete_product/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """API: Ürün sil"""
    try:
        conn = get_db_connection()
        conn.execute('UPDATE products SET status = "deleted" WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Ürün başarıyla silindi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/check_stock')
def api_check_stock():
    """API: Stok durumu kontrolü"""
    low_stock_products = get_low_stock_products()
    alerts = []
    
    for product in low_stock_products:
        if product['current_stock'] == 0:
            alerts.append({
                'type': 'error',
                'message': f"{product['name']} stokta yok!"
            })
        else:
            alerts.append({
                'type': 'warning',
                'message': f"{product['name']} stoku düşük ({product['current_stock']} adet)"
            })
    
    return jsonify({'alerts': alerts})

# Arka plan görevleri
def start_background_tasks():
    """Arka plan görevlerini başlat"""
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Her dakika kontrol et
    
    # Her 5 dakikada stok kontrolü
    schedule.every(5).minutes.do(check_stock_levels)
    
    # Arka plan thread'ini başlat
    thread = threading.Thread(target=run_schedule, daemon=True)
    thread.start()
    logger.info("Arka plan görevleri başlatıldı.")

if __name__ == '__main__':
    # Veritabanını başlat
    init_db()
    
    # Arka plan görevlerini başlat
    start_background_tasks()
    
    # Uygulamayı çalıştır
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Inditex Stok Takip Sistemi başlatılıyor...")
    logger.info(f"📊 Port: {port}")
    logger.info(f"🔧 Debug: {debug}")
    logger.info(f"📧 E-posta bildirimleri: {bool(app.config['MAIL_USERNAME'])}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
