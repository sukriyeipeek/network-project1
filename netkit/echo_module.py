import logging
import time
from .error_settings import accept,connect,listener,receive_message,send_message


def serve_once(server,settings):
    conn,address=accept(server,settings)
    with conn:
        payload=receive_message(conn)
        send_message(conn,payload)
    logging.info('Echo served %s bytes to %s',len(payload),address)
    return len(payload)


def server(host,port,settings):
    with listener(host,port,settings) as sock:
        print(f'Echo sunucusu {sock.getsockname()} adresinde bekliyor...')
        print('İstemci bağlanana kadar her zaman aşımında bekleme sürer. Ctrl+C: durdur.')
        while True:
            try:
                serve_once(sock,settings)
            except TimeoutError:
                logging.info('Echo wait timeout')
            except (OSError,ValueError) as exc:
                logging.warning('Echo client error: %s',exc)
                print('İstemci hatası:',exc)


def client(host,port,message,settings):
    payload=message.encode('utf-8')
    start=time.perf_counter()
    with connect(host,port,settings) as sock:
        send_message(sock,payload)
        response=receive_message(sock)
    result={'matches': response == payload,'bytes': len(payload),
              'round_trip_ms': round((time.perf_counter() - start) * 1000,3),
              'received': response.decode('utf-8')}
    logging.info('Echo result: %s',result)
    return result
