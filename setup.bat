@echo off
echo Inditex Stok Takip Sistemi - Kurulum Scripti
echo ==========================================

echo.
echo 1. Python virtual environment olusturuluyor...
python -m venv venv

echo.
echo 2. Virtual environment aktif ediliyor...
call venv\Scripts\activate

echo.
echo 3. Gerekli paketler yukleniyor...
pip install -r requirements.txt

echo.
echo 4. Ornek .env dosyasi olusturuluyor...
if not exist .env (
    copy .env.example .env
    echo .env dosyasi olusturuldu. Lutfen kendi ayarlarinizi yapin.
) else (
    echo .env dosyasi zaten mevcut.
)

echo.
echo 5. Logs klasoru olusturuluyor...
if not exist logs mkdir logs

echo.
echo 6. Veritabani baslangic kurulumu...
python -c "from app import init_db; init_db()"

echo.
echo ==========================================
echo Kurulum tamamlandi!
echo.
echo Uygulamayi calistirmak icin:
echo   venv\Scripts\activate
echo   python app.py
echo.
echo Tarayicinizda http://localhost:5000 adresini ziyaret edin.
echo ==========================================
pause
