import json
import logging
import select
import socket
import struct
import time
from dataclasses import asdict,dataclass
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
LOGS=ROOT / 'logs'
MAX_MESSAGE_SIZE=1024 * 1024
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


def wait_ready(sock,write,deadline):
    remaining=deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('İşlem süresi doldu.')
    if write:
        readable,writable,_=select.select([],[sock],[],remaining)
    else:
        readable,writable,_=select.select([sock],[],[],remaining)
    if not (readable or writable):
        raise TimeoutError('Socket hazır olmadı.')


def send_frame(sock,payload,settings):
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError('Mesaj en fazla 1 MiB olabilir.')
    data=memoryview(struct.pack('!I',len(payload)) + payload)
    deadline=time.monotonic() + settings.timeout
    while data:
        wait_ready(sock,True,deadline)
        try:
            sent=sock.send(data)
        except (BlockingIOError,InterruptedError):
            continue
        if sent == 0:
            raise ConnectionError('Gönderim sırasında bağlantı kapandı.')
        data=data[sent:]


def recv_frame(sock,settings):
    deadline=time.monotonic() + settings.timeout
    data=bytearray()
    expected=4
    header_received=False
    while len(data) < expected:
        try:
            wait_ready(sock,False,deadline)
        except TimeoutError as exc:
            if data:
                raise ConnectionError('Yarım mesaj alınırken zaman aşımı oluştu.') from exc
            raise
        try:
            chunk=sock.recv(min(expected - len(data),settings.receive_buffer))
        except (BlockingIOError,InterruptedError):
            continue
        if not chunk:
            raise ConnectionError('Karşı taraf bağlantıyı kapattı.')
        data.extend(chunk)
        if not header_received and len(data) == 4:
            size=struct.unpack('!I',data)[0]
            if size > MAX_MESSAGE_SIZE:
                raise ValueError('Gelen mesaj boyutu sınırı aşıyor.')
            expected=4 + size
            header_received=True
    return bytes(data[4:])


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
    wait_ready(sock,False,time.monotonic() + settings.timeout)
    conn,address=sock.accept()
    try:
        settings.apply(conn)
    except Exception:
        conn.close()
        raise
    return conn,address
