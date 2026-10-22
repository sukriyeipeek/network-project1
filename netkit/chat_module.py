import datetime
import socket
import threading
from .error_settings import LOGS,accept,connect,listener,receive_message,send_message


class Chat:
    def __init__(self,settings):
        self.settings=settings
        self.socket=None
        self.running=True
        self.lock=threading.Lock()
        name=datetime.datetime.now().strftime('chat-%Y%m%d-%H%M%S-%f.txt')
        self.log_file=LOGS / name

    def connect(self,mode,host,port):
        if mode == 'server':
            with listener(host,port,self.settings) as server:
                while self.running:
                    try:
                        self.socket,address=accept(server,self.settings,0.25)
                        break
                    except TimeoutError:
                        continue
        else:
            self.socket=connect(host,port,self.settings)
        if not self.running:
            self.close()
        return self.socket is not None and self.running

    def record(self,direction,message):
        line=f'{datetime.datetime.now().isoformat(timespec="seconds")} {direction}: {message}\n'
        with self.lock,self.log_file.open('a',encoding='utf-8') as file:
            file.write(line)

    def send(self,message):
        send_message(self.socket,message.encode('utf-8'))
        self.record('GİDEN',message)

    def receive(self):
        message=receive_message(self.socket).decode('utf-8')
        self.record('GELEN',message)
        return message

    def close(self):
        self.running=False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
