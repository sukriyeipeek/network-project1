import json
import platform
import socket
import subprocess


def machine_info():
    hostname=socket.gethostname()
    addresses=sorted({item[4][0] for item in socket.getaddrinfo(hostname,None)})
    try:
        interfaces=[{'index': index,'name': name} for index,name in socket.if_nameindex()]
    except (OSError,AttributeError):
        interfaces=[]
    details=None
    if platform.system() == 'Windows':

        result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
            'Get-NetIPAddress | Select-Object InterfaceAlias,AddressFamily,IPAddress,PrefixLength | ConvertTo-Json'],
            capture_output=True,text=True,timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            details=json.loads(result.stdout)
    return {'hostname': hostname,'platform': platform.platform(),'addresses': addresses,
            'interfaces': interfaces,'interface_addresses': details}
