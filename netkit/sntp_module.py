import datetime
import logging
import socket
import struct
import time

NTP_EPOCH=2208988800


def encode_stamp(unix):
    seconds=unix + NTP_EPOCH
    integer=int(seconds)
    return struct.pack('!II',integer & 0xffffffff,int((seconds - integer) * 2**32))


def decode_stamp(raw,reference):
    seconds,fraction=struct.unpack('!II',raw)

    era=round((reference + NTP_EPOCH - seconds) / 2**32)
    return seconds + era * 2**32 - NTP_EPOCH + fraction / 2**32


def query(host,settings,port=123):
    packet=bytearray(48)
    packet[0]=0x23
    address=socket.getaddrinfo(host,port,type=socket.SOCK_DGRAM)[0]
    with socket.socket(address[0],socket.SOCK_DGRAM) as sock:
        settings.apply(sock)

        sock.settimeout(settings.timeout)
        sock.connect(address[4])
        t1=time.time()
        packet[40:48]=encode_stamp(t1)
        sock.send(packet)
        reply=sock.recv(512)
        t4=time.time()
    if len(reply) < 48:
        raise ValueError('Eksik SNTP yanıtı.')
    leap,version,mode=reply[0] >> 6,(reply[0] >> 3) & 7,reply[0] & 7
    if leap == 3 or version not in (3,4) or mode != 4 or not 1 <= reply[1] <= 15:
        raise ValueError('SNTP sunucusu senkronize değil veya yanıt geçersiz (stratum/mode).')
    if reply[24:32] != packet[40:48]:
        raise ValueError('SNTP istek/yanıt zaman damgası eşleşmiyor.')
    if reply[32:40] == bytes(8) or reply[40:48] == bytes(8):
        raise ValueError('SNTP zaman damgası sıfır.')
    t2=decode_stamp(reply[32:40],t4)
    t3=decode_stamp(reply[40:48],t4)
    result={'server': host,'stratum': reply[1],'offset_seconds': ((t2 - t1) + (t3 - t4)) / 2,
              'delay_seconds': (t4 - t1) - (t3 - t2),
              'server_utc': datetime.datetime.fromtimestamp(t3,datetime.timezone.utc).isoformat(),
              'local_utc': datetime.datetime.fromtimestamp(t4,datetime.timezone.utc).isoformat()}
    logging.info('SNTP result: %s',result)
    return result
