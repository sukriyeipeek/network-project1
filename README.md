# Ağ Tanılama Projesi

Bu projede makine bilgisi, Echo testi, SNTP saati, sohbet ve socket ayarlarını tek bir Python uygulamasında birleştirdim. Arayüz için Tkinter kullandım. Ek pip paketi gerekmiyor.

## Çalıştırma

Python 3.11 veya üzeri ve Tkinter gerekiyor. Proje klasöründe şu komutu çalıştırıyorum:

```powershell
python main.py
```

GitHub sürümünde runtime klasörü yok. Python ve Tkinter kurulu olmalı.

## Kullanım

- Makine sekmesinde bilgisayarın adını, IP adreslerini ve ağ arayüzlerini görüntülüyorum.
- Echo sekmesinde sunucuyu başlatıp mesaj gönderiyorum. Dönen mesajın gönderdiğim mesajla aynı olup olmadığını kontrol ediyorum. Varsayılan port 5000.
- SNTP sekmesinde sunucudan gelen saat bilgisini görüntülüyorum. İnternet ve UDP 123 erişimi gerekiyor.
- Sohbet için iki pencere açıyorum. Birinde sunucu, diğerinde istemci seçip aynı adres ve portla bağlanıyorum. Aynı bilgisayarda adres 127.0.0.1, varsayılan port 5001.
- Ayarlar sekmesinde timeout, gönderme/alma tamponları ve blocking modunu değiştiriyorum. Ayarlar yeni bağlantılarda uygulanıyor ve uygulama kapanınca sıfırlanıyor.
- Hata yönetimi sekmesinde bağlantı ve zaman aşımı hatalarını görüyorum.

Sohbet mesajlarını logs klasörüne kaydediyorum. Modüller netkit klasöründe. Echo ve sohbette tek satırlık metin mesajları kullanıyorum. Nonblocking modda henüz veri yoksa kısa süre bekleyip tekrar almayı deniyorum; gönderme hazır değilse hata gösteriliyor.
