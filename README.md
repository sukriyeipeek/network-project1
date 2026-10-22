# Ağ Tanılama Projesi

Bu projede Python ile makine bilgilerini görüntüleyen, Echo testi yapan, SNTP sunucusundan saat bilgisi alan ve mesajlaşmayı sağlayan bir uygulama hazırladım.Arayüz için Tkinter kullandım.Ek bir pip paketi gerekmiyor.

## Çalıştırma

Python 3.11 veya üzeri ve Tkinter gerekiyor.Proje klasöründe şu komutla arayüzü açıyorum:

```powershell
python gui.py
```

GitHub sürümünde runtime klasörü yok. Çalıştırmak için Python kurulu olmalı.

## Kullanım

- Makine sekmesinde bilgisayarın adını,IP adreslerini ve ağ arayüzlerini görüntülüyorum.
- Echo sekmesinde sunucuyu başlatıp mesaj gönderiyorum. Gönderilen ve dönen mesajın eşleşmesini kontrol ediyorum. Varsayılan port 5000.
- SNTP sekmesinde internet üzerinden saat bilgisini alıp yerel saatle karşılaştırıyorum.Sistem saatini değiştirmiyorum.
- Sohbet için uygulamayı iki kez açıyorum.Birinde sunucu, diğerinde istemci seçip aynı adres ve portla bağlanıyorum. Aynı bilgisayarda adres olarak 127.0.0.1,port olarak 5001 kullanıyorum.
- Ayarlar sekmesinden zaman aşımını, tampon boyutlarını ve blocking modunu değiştiriyorum. Yeni ayarlar sonraki bağlantıda uygulanıyor.

Modülleri netkit klasöründe ayrı dosyalarda tuttum. Sohbet kayıtları ve işlem çıktıları logs klasörüne kaydediliyor. Bağlantı hataları arayüzün alt kısmında gösteriliyor.SNTP için internet bağlantısı ve UDP 123 erişimi gerekiyor.

Echo ve sohbet için tek satırlık metin mesajları kullanıyorum. Mesajın sonunu satır sonu karakteriyle ayırıyorum. SNTP sonucunda sunucu saati ile yerel saatin basit farkını gösteriyorum; hassas saat senkronizasyonu yapmıyorum. Nonblocking modda veri henüz gelmediyse kısa süre bekleyip tekrar almayı deniyorum. Gönderme hazır değilse hata gösteriliyor.
