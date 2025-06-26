# 🚀 Inditex Stok Takip Sistemi - Hızlı Başlangıç

## Kurulum Adımları

### 1. Otomatik Kurulum (Önerilen)
```bash
# Windows PowerShell'de
.\setup.bat
```

### 2. Manuel Kurulum

```bash
# 1. Virtual environment oluştur
python -m venv venv

# 2. Virtual environment'ı aktif et
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Paketleri yükle
pip install -r requirements.txt

# 4. Environment dosyasını oluştur
cp .env.example .env

# 5. .env dosyasını düzenle (önemli!)
# - FLASK_SECRET_KEY değiştir
# - E-posta ayarlarını yap
# - Diğer ayarları ihtiyacına göre düzenle

# 6. Veritabanını oluştur
python -c "from app import init_db; init_db()"

# 7. Uygulamayı çalıştır
python app.py
```

## E-posta Kurulumu

### Gmail için Ayarlar:
1. Gmail hesabında 2FA aktif olmalı
2. App Password oluştur: https://myaccount.google.com/apppasswords
3. `.env` dosyasında şu ayarları yap:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
NOTIFICATION_EMAILS=admin@company.com
```

### Outlook için Ayarlar:
```
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-password
```

## İlk Kullanım

1. **Tarayıcıda aç:** http://localhost:5000
2. **Ürün ekle:** "Ürün Ekle" butonuna tıkla
3. **Stok güncelle:** Ana sayfada ürünlerin yanındaki düzenle butonunu kullan
4. **Raporları görüntüle:** "Raporlar" sekmesini ziyaret et

## Özellikler

### ✅ Tamamlanan Özellikler:
- Modern responsive web arayüzü
- Ürün ekleme, düzenleme, silme
- Otomatik düşük stok uyarıları
- E-posta bildirimleri
- Detaylı raporlama ve grafikler
- API endpoint'leri
- Arama ve filtreleme
- Excel export
- Yazdırma desteği

### 🔧 Teknik Özellikler:
- **Backend:** Python Flask
- **Frontend:** Bootstrap 5, Chart.js
- **Veritabanı:** SQLite
- **E-posta:** Flask-Mail
- **Otomatik görevler:** Threading, Schedule

## API Kullanımı

### Temel Endpoint'ler:
```bash
# Tüm ürünleri getir
GET /api/products

# Ürün detayı
GET /api/product/{id}

# Stok güncelle
POST /api/update_stock/{id}
Content-Type: application/json
{
  "current_stock": 10,
  "min_stock": 5
}

# Ürün sil
DELETE /api/delete_product/{id}

# Stok durumu kontrolü
GET /api/check_stock
```

## Sorun Giderme

### Port zaten kullanımda hatası:
```bash
# Farklı port kullan
python app.py --port 5001
```

### E-posta gönderilmiyor:
1. `.env` dosyasındaki ayarları kontrol et
2. App password kullandığından emin ol
3. Firewall/antivirus kontrolü yap

### Veritabanı hatası:
```bash
# Veritabanını sıfırla
python -c "from app import init_db; init_db()"
```

## Geliştirme

### Debug Mode:
```bash
# .env dosyasında
FLASK_DEBUG=True
FLASK_ENV=development
```

### Log dosyaları:
- Uygulama logları: `logs/app.log`
- Hata logları: `logs/error.log`

## Güvenlik Notları

⚠️ **Önemli:** Üretim ortamında:
1. `FLASK_SECRET_KEY` değiştir
2. `FLASK_DEBUG=False` yap
3. Güçlü parolalar kullan
4. HTTPS kullan
5. Firewall kuralları yapılandır

## Destek

Sorun yaşıyorsan:
1. Log dosyalarını kontrol et
2. GitHub Issues'da ara
3. Dokümantasyonu incele

---
💡 **İpucu:** Development için VS Code kullanıyorsan, `Ctrl+Shift+P` > "Python: Select Interpreter" ile virtual environment'ı seç.
