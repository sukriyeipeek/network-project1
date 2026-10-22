import socket


def machine_info():
    hostname=socket.gethostname()
    addresses=socket.gethostbyname_ex(hostname)[2]
    interfaces=[]
    try:
        for index,name in socket.if_nameindex():
            interfaces.append(name)
    except (OSError,AttributeError):
        pass
    return {'hostname': hostname,'addresses': addresses,'interfaces': interfaces}
