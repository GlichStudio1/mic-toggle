# Mic Toggle - APK'yı almak için (Windows, WSL/Ubuntu gerekmez)

1. https://github.com adresinde boş bir repo oluştur (ör. mic-toggle).
2. Bu klasörde PowerShell aç:

    git init
    git add .
    git commit -m "Mic Toggle"
    git branch -M main
    git remote add origin https://github.com/KULLANICI_ADIN/mic-toggle.git
    git push -u origin main

3. GitHub'da repo -> Actions sekmesi -> "Build APK" çalışır (ilk sefer 20-40 dk).
4. Bittiğinde çalıştırma sayfasındaki Artifacts -> mic-toggle-apk dosyasını indir,
   zip'ten çıkar, APK'yı telefona gönderip yükle.

Windows'ta arayüzü önizlemek için:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install kivy
    python main.py

(İsteğe bağlı) fonts\ klasörüne DejaVuSans.ttf koyarsan ⚙ simgesi görünür,
koymazsan buton "AYAR" yazar.

Telefonda: Başlat -> mikrofon/bildirim izni -> "Diğer uygulamaların üzerinde
göster" iznini aç -> geri dön -> yüzen daire çıkar.
