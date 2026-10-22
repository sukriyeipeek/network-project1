import datetime
import socket
import threading
from .error_settings import LOGS,accept,connect,listener,recv_frame,send_frame


def session(sock,settings,nickname='Kullanıcı'):
    stop=threading.Event()
    lock=threading.Lock()
    transcript=LOGS / ('chat-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.txt')

    def record(direction,message):
        line=f'{datetime.datetime.now().isoformat()} {direction}: {message}\n'
        with lock,transcript.open('a',encoding='utf-8') as file:
            file.write(line)

    def receive():
        while not stop.is_set():
            try:
                message=recv_frame(sock,settings).decode('utf-8')
                record('GELEN',message)
                print('\n' + message + '\n> ',end='',flush=True)
            except TimeoutError:
                continue
            except (OSError,ValueError) as exc:
                if not stop.is_set():
                    print('\nBağlantı sona erdi:',exc,'\nÇıkmak için Enter tuşuna basın.')
                stop.set()
    worker=threading.Thread(target=receive,daemon=True)
    worker.start()
    print(f'Sohbet başladı. /quit: çıkış. Kayıt: {transcript}')
    try:
        while not stop.is_set():
            text=input('> ')
            if text == '/quit' or stop.is_set():
                break
            if text:
                message=nickname + ': ' + text
                send_frame(sock,message.encode('utf-8'),settings)
                record('GİDEN',message)
    finally:
        stop.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
        worker.join(timeout=settings.timeout + 1)


def run(mode,host,port,settings,nickname):
    if mode == 'server':
        with listener(host,port,settings) as server:
            print('Sohbet bağlantısı bekleniyor; Ctrl+C: iptal.')
            while True:
                try:
                    conn,address=accept(server,settings)
                    print('Bağlanan:',address)
                    break
                except TimeoutError:
                    continue
    else:
        conn=connect(host,port,settings)
    with conn:
        session(conn,settings,nickname)
