import socket
import struct
import time
import logging


def query(host,settings,port=123):
    request=b'\x1b' + 47 * b'\0'
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.settimeout(settings.timeout)
        sock.sendto(request,(host,port))
        data,address=sock.recvfrom(512)
    if len(data) < 48:
        raise ValueError('Eksik SNTP yanıtı.')
    seconds=struct.unpack('!12I',data[:48])[10] - 2208988800
    result={'server': host,'time': time.ctime(seconds)}
    logging.info('SNTP saati: %s',result)
    return result
