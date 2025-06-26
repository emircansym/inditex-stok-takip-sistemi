# Inditex Stok Takip Sistemi

Modern ve kullanıcı dostu Inditex markalarına özel stok takip uygulaması.

## 🌟 Özellikler

- **Multi-Marka Desteği**: ZARA, PULL&BEAR, BERSHKA, STRADIVARIUS, MASSIMO DUTTI, OYSHO
- **Otomatik E-posta Bildirimleri**: Düşük stok uyarıları
- **Gerçek Zamanlı Stok Takibi**: Anlık stok durumu güncellemeleri
- **Modern Responsive Tasarım**: Mobil ve masaüstü uyumlu
- **Gelişmiş Raporlama**: Detaylı stok analizleri

## 🚀 Kurulum

1. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

2. Çevre değişkenlerini ayarlayın (`.env` dosyası):
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_USE_TLS=True
ADMIN_EMAIL=admin@company.com
```

3. Uygulamayı çalıştırın:
```bash
python app.py
```

## 📧 E-posta Bildirimleri

Uygulama aşağıdaki durumlarda otomatik e-posta gönderir:
- Stok seviyesi minimum eşiğin altına düştüğünde
- Yeni ürün eklendiğinde
- Günlük stok raporları

## 🛠️ Kullanım

1. **Ürün Ekleme**: Ana sayfada "Yeni Ürün" butonuna tıklayın
2. **Stok Güncelleme**: Ürün satırındaki +/- butonları ile
3. **Raporlar**: Dashboard'da anlık istatistikleri görüntüleyin

## 📱 Responsive Tasarım

Uygulama tüm cihazlarda mükemmel çalışır:
- Masaüstü bilgisayarlar
- Tabletler
- Akıllı telefonlar
