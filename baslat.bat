@echo off
:: Varsayılan tarayıcıyı aç
start http://127.0.0.1:5000

:: Sunucuyu başlat
python app.py

:: Hata durumunda veya sunucu durdurulduğunda pencereyi açık tut
pause
