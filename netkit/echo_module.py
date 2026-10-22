import logging
from .error_settings import connect,receive_message,send_message


def reply(conn):
    data=receive_message(conn)
    send_message(conn,data)
    logging.info('Echo mesajı geri gönderildi.')


def client(host,port,message,settings):
    with connect(host,port,settings) as sock:
        send_message(sock,message.encode('utf-8'))
        received=receive_message(sock).decode('utf-8')
    result={'matches': message == received,'received': received}
    logging.info('Echo sonucu: %s',result)
    return result
