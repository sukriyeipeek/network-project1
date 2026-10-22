import json
import logging
import socket
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
LOGS=ROOT / 'logs'
LOGS.mkdir(exist_ok=True)
logging.basicConfig(filename=LOGS / 'application.log',level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')


class Settings:
    def __init__(self,timeout=5.0,send_buffer=65536,receive_buffer=65536,blocking=True):
        self.timeout=timeout
        self.send_buffer=send_buffer
        self.receive_buffer=receive_buffer
        self.blocking=blocking

    def validate(self):
        if not 0.1 <= self.timeout <= 120:
            raise ValueError('Timeout 0.1–120 saniye olmalı.')
        if not 1024 <= self.send_buffer <= 4194304:
            raise ValueError('Tampon boyutları 1024–4194304 aralığında olmalı.')
        if not 1024 <= self.receive_buffer <= 4194304:
            raise ValueError('Tampon boyutları 1024–4194304 aralığında olmalı.')

    def apply(self,sock):
        self.validate()
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,self.send_buffer)
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,self.receive_buffer)
        if self.blocking:
            sock.settimeout(self.timeout)
        else:
            sock.setblocking(False)
        logging.info('Socket settings: %s',vars(self))

    def save(self):
        self.validate()
        (ROOT / 'settings.json').write_text(json.dumps(vars(self),indent=2),encoding='utf-8')

def load_settings():
    path=ROOT / 'settings.json'
    if not path.exists():
        return Settings()
    data=json.loads(path.read_text(encoding='utf-8'))
    settings=Settings(data['timeout'],data['send_buffer'],data['receive_buffer'],data['blocking'])
    settings.validate()
    return settings


def error_text(exc):
    if isinstance(exc,TimeoutError):
        return 'Zaman aşımı: hedefe erişimi ve güvenlik duvarını kontrol edin.'
    if isinstance(exc,ConnectionRefusedError):
        return 'Bağlantı reddedildi: sunucunun ve portun açık olduğunu kontrol edin.'
    if isinstance(exc,socket.gaierror):
        return 'Adres çözümlenemedi: sunucu adını ve DNS bağlantısını kontrol edin.'
    if isinstance(exc,ConnectionError):
        return 'Bağlantı kapandı veya veri aktarımı kesildi: ' + str(exc)
    return str(exc)


def report_error(exc):
    logging.exception('Operation failed: %s',exc)
    print('HATA:',error_text(exc))


def send_message(sock,payload):
    if b'\n' in payload:
        raise ValueError('Mesaj tek satır olmalı.')
    sock.sendall(payload + b'\n')


def receive_message(sock):
    message=bytearray()
    while True:
        try:
            data=sock.recv(1)
        except BlockingIOError:
            time.sleep(0.05)
            continue
        if not data:
            raise ConnectionError('Karşı taraf bağlantıyı kapattı.')
        if data == b'\n':
            return bytes(message)
        message.extend(data)


def connect(host,port,settings):
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sock.settimeout(settings.timeout)
        sock.connect((host,port))
        settings.apply(sock)
        return sock
    except Exception:
        sock.close()
        raise


def listener(host,port,settings):
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        sock.bind((host,port))
        sock.listen(5)
        settings.apply(sock)
        return sock
    except Exception:
        sock.close()
        raise


def accept(sock,settings,timeout=None):
    if timeout is None:
        timeout=settings.timeout
    sock.settimeout(timeout)
    conn,address=sock.accept()
    try:
        settings.apply(conn)
    except Exception:
        conn.close()
        raise
    return conn,address
