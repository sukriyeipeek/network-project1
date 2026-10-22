import json
import logging
import socket
import time
from dataclasses import asdict,dataclass
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
LOGS=ROOT / 'logs'
LOGS.mkdir(exist_ok=True)
logging.basicConfig(filename=LOGS / 'application.log',level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')


@dataclass
class Settings:
    timeout: float=5.0
    send_buffer: int=65536
    receive_buffer: int=65536
    blocking: bool=True

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
        sock.settimeout(self.timeout if self.blocking else 0.0)
        logging.info('Socket settings: %s',asdict(self))

    def save(self):
        self.validate()
        (ROOT / 'settings.json').write_text(json.dumps(asdict(self),indent=2),encoding='utf-8')

    @classmethod
    def load(cls):
        path=ROOT / 'settings.json'
        if not path.exists():
            return cls()
        result=cls(**json.loads(path.read_text(encoding='utf-8')))
        result.validate()
        return result


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
    sock=socket.create_connection((host,port),timeout=settings.timeout)
    try:
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


def accept(sock,settings):
    sock.settimeout(settings.timeout)
    conn,address=sock.accept()
    try:
        settings.apply(conn)
    except Exception:
        conn.close()
        raise
    return conn,address
