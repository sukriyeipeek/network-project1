import datetime
import logging
import socket
import struct
import time


def query(host,settings,port=123):
    request=b'\x1b' + 47 * b'\0'
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.settimeout(settings.timeout)
        sock.sendto(request,(host,port))
        data,address=sock.recvfrom(512)
    if len(data) < 48:
        raise ValueError('Eksik SNTP yanıtı.')
    values=struct.unpack('!12I',data[:48])
    server_time=values[10] - 2208988800
    local_time=time.time()
    result={
        'server': host,
        'server_utc': datetime.datetime.fromtimestamp(server_time,datetime.timezone.utc).isoformat(),
        'local_utc': datetime.datetime.fromtimestamp(local_time,datetime.timezone.utc).isoformat(),
        'difference_seconds': round(server_time - local_time,3)
    }
    logging.info('SNTP: %s',result)
    return result
