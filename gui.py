"""Tkinter desktop interface; network I/O never runs on the UI thread."""
import datetime
import json
import logging
import os
import queue
import socket
import sys
import threading
from pathlib import Path

# Extended Windows paths let the portable Tcl runtime resolve its script library
# consistently in redirected/sandboxed desktop folders.
if sys.platform == 'win32':
    for variable,folder in [('TCL_LIBRARY','tcl8.6'),('TK_LIBRARY','tk8.6')]:
        library=Path(sys.executable).parent / 'tcl' / folder
        if library.is_dir():
            os.environ.setdefault(variable,'\\\\?\\' + str(library.resolve()))

import tkinter as tk
from dataclasses import replace
from tkinter import ttk,scrolledtext

from netkit import echo_module,machine_module,sntp_module
from netkit.error_settings import LOGS,Settings,accept,connect,error_text,listener,recv_frame,send_frame


class NetworkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Network Toolkit • Ağ Tanılama Merkezi')
        self.geometry('1040x760')
        self.minsize(840,620)
        self.configure(background='#eef2f7')
        self.events=queue.Queue()
        self.closing=False
        self.echo_stop=threading.Event()
        self.chat_stop=threading.Event()
        self.chat_socket=None
        self.chat_busy=False
        self.echo_busy=False
        self.echo_socket=None
        self.send_lock=threading.Lock()
        self.chat_generation=0
        try:
            self.settings=Settings.load()
        except (OSError,ValueError,TypeError) as exc:
            self.settings=Settings()
            self.events.put(('error',f'Ayarlar yüklenemedi; varsayılanlar kullanılıyor. {exc}'))
        style=ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame',background='#eef2f7')
        style.configure('TLabel',background='#eef2f7',font=('Segoe UI',10))
        style.configure('TButton',font=('Segoe UI',10),padding=8)
        style.configure('TNotebook.Tab',padding=(14,9),font=('Segoe UI',10))
        style.configure('Title.TLabel',font=('Segoe UI',24,'bold'),foreground='#17355c')
        ttk.Label(self,text='Ağ Tanılama Merkezi',style='Title.TLabel').pack(anchor='w',padx=24,pady=(20,4))
        ttk.Label(self,text='Makine bilgileri  •  TCP Echo  •  SNTP  •  Canlı sohbet').pack(anchor='w',padx=25,pady=(0,18))
        self.tabs=ttk.Notebook(self)
        self.tabs.pack(fill='both',expand=True,padx=20)
        self.info_tab=self.page('Makine')
        self.echo_tab=self.page('Echo testi')
        self.time_tab=self.page('SNTP saati')
        self.chat_tab=self.page('Sohbet')
        self.settings_tab=self.page('Ayarlar')
        self.help_tab=self.page('Yardım')
        self.build_info()
        self.build_echo()
        self.build_time()
        self.build_chat()
        self.build_settings()
        self.build_help()
        ttk.Label(self,text='İşlem günlüğü',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=24,pady=(12,4))
        self.log=scrolledtext.ScrolledText(self,height=5,state='disabled',font=('Consolas',9),background='#132239',foreground='#d5e7fb')
        self.log.pack(fill='x',padx=20)
        self.status=tk.StringVar(master=self,value='Hazır')
        ttk.Label(self,textvariable=self.status).pack(anchor='w',padx=24,pady=10)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.poll_id=self.after(60,self.drain)

    def page(self,label):
        frame=ttk.Frame(self.tabs,padding=18)
        self.tabs.add(frame,text=label)
        return frame

    def field(self,parent,label,value,width=30):
        row=ttk.Frame(parent)
        row.pack(fill='x',pady=5)
        ttk.Label(row,text=label,width=23).pack(side='left')
        variable=tk.StringVar(master=self,value=str(value))
        ttk.Entry(row,textvariable=variable,width=width).pack(side='left',fill='x',expand=True)
        return variable

    def output(self,parent,height=12):
        text=scrolledtext.ScrolledText(parent,height=height,wrap='word',state='disabled',font=('Consolas',10))
        text.pack(fill='both',expand=True,pady=10)
        return text

    @staticmethod
    def write(widget,content,clear=False):
        widget.configure(state='normal')
        if clear:
            widget.delete('1.0','end')
        widget.insert('end',content + '\n')
        widget.see('end')
        widget.configure(state='disabled')

    def task(self,label,operation,result=None,button=None):
        self.status.set(label)
        if button:
            button.configure(state='disabled')
        def work():
            try:
                value=operation()
                if result:
                    self.events.put(('result',result,value))
                self.events.put(('log',label + ' tamamlandı.'))
            except (OSError,ValueError,TypeError) as exc:
                logging.exception('GUI operation: %s',label)
                self.events.put(('error',error_text(exc)))
            finally:
                if button:
                    self.events.put(('enable',button))
        threading.Thread(target=work,daemon=True).start()

    def drain(self):
        if self.closing:
            return
        for _ in range(100):
            try:
                item=self.events.get_nowait()
            except queue.Empty:
                break
            kind=item[0]
            if kind in ('log','error'):
                message=('HATA: ' if kind == 'error' else '') + item[1]
                if kind == 'error':
                    logging.error('%s',item[1])
                self.write(self.log,datetime.datetime.now().strftime('%H:%M:%S') + '  ' + message)
                self.status.set(message)
            elif kind == 'result':
                self.write(item[1],json.dumps(item[2],ensure_ascii=False,indent=2),True)
            elif kind == 'enable':
                item[1].configure(state='normal')
            elif kind == 'echo_done':
                self.echo_busy=False
                self.echo_start.configure(state='normal')
                self.echo_end.configure(state='disabled')
            elif kind == 'chat_message':
                self.write(self.chat_output,item[1])
            elif kind == 'chat_done' and item[1] == self.chat_generation:
                self.chat_busy=False
                self.chat_start.configure(state='normal')
                self.chat_end.configure(state='disabled')
        self.poll_id=self.after(60,self.drain)

    def build_info(self):
        ttk.Label(self.info_tab,text='Bu bilgisayarın ağ arayüzlerini ve IP adreslerini görüntüleyin.').pack(anchor='w')
        self.info_button=ttk.Button(self.info_tab,text='Bilgileri yenile',command=self.refresh_info)
        self.info_button.pack(anchor='w',pady=10)
        self.info_output=self.output(self.info_tab)

    def refresh_info(self):
        self.task('Makine bilgileri alınıyor',machine_module.machine_info,self.info_output,self.info_button)

    def address(self,host,port):
        value=int(port.get())
        if not host.get().strip() or not 1 <= value <= 65535:
            raise ValueError('Adres boş olamaz; port 1–65535 olmalı.')
        return host.get().strip(),value

    def checked(self,operation):
        try:
            operation()
        except (ValueError,OSError) as exc:
            self.events.put(('error',error_text(exc)))

    def build_echo(self):
        self.echo_host=self.field(self.echo_tab,'Sunucu / dinleme adresi','127.0.0.1')
        self.echo_port=self.field(self.echo_tab,'TCP portu',5000)
        self.echo_message=self.field(self.echo_tab,'Test mesajı','Merhaba ağ! Türkçe mesaj testi.')
        row=ttk.Frame(self.echo_tab)
        row.pack(fill='x',pady=12)
        self.echo_start=ttk.Button(row,text='Sunucuyu başlat',command=lambda: self.checked(self.start_echo))
        self.echo_start.pack(side='left',padx=3)
        self.echo_end=ttk.Button(row,text='Sunucuyu durdur',command=self.stop_echo,state='disabled')
        self.echo_end.pack(side='left',padx=3)
        self.echo_test=ttk.Button(row,text='Mesaj gönder ve karşılaştır',command=lambda: self.checked(self.test_echo))
        self.echo_test.pack(side='left',padx=3)
        self.echo_output=self.output(self.echo_tab)

    def start_echo(self):
        host,port=self.address(self.echo_host,self.echo_port)
        settings=replace(self.settings)
        self.echo_stop=stop=threading.Event()
        self.echo_busy=True
        self.echo_start.configure(state='disabled')
        self.echo_end.configure(state='normal')
        def run():
            try:
                with listener(host,port,settings) as server:
                    self.events.put(('log',f'Echo dinleniyor: {host}:{port}'))
                    while not stop.is_set():
                        try:
                            conn,address=accept(server,replace(settings,timeout=0.25))
                        except TimeoutError:
                            continue
                        try:
                            with conn:
                                self.echo_socket=conn
                                if stop.is_set():
                                    continue
                                settings.apply(conn)
                                data=recv_frame(conn,settings)
                                send_frame(conn,data,settings)
                            self.events.put(('log',f'Echo: {address}, {len(data)} bayt geri gönderildi.'))
                        except (OSError,ValueError) as exc:
                            if not stop.is_set():
                                self.events.put(('error',error_text(exc)))
                        finally:
                            self.echo_socket=None
            except (OSError,ValueError) as exc:
                self.events.put(('error',error_text(exc)))
            finally:
                self.events.put(('echo_done',))
                self.events.put(('log','Echo sunucusu kapandı.'))
        threading.Thread(target=run,daemon=True).start()

    def stop_echo(self):
        self.echo_stop.set()
        conn=self.echo_socket
        if conn:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        self.echo_end.configure(state='disabled')
        self.status.set('Echo sunucusu durduruluyor…')

    def test_echo(self):
        host,port=self.address(self.echo_host,self.echo_port)
        message,settings=self.echo_message.get(),replace(self.settings)
        self.task('Echo testi',lambda: echo_module.client(host,port,message,settings),self.echo_output,self.echo_test)

    def build_time(self):
        ttk.Label(self.time_tab,text='UTC saatini ve yerel saat farkını ölçer; sistem saatini değiştirmez.').pack(anchor='w')
        self.ntp_host=self.field(self.time_tab,'SNTP sunucusu','pool.ntp.org')
        self.time_button=ttk.Button(self.time_tab,text='Sunucu saatini kontrol et',command=self.check_time)
        self.time_button.pack(anchor='w',pady=10)
        self.time_output=self.output(self.time_tab)

    def check_time(self):
        host,settings=self.ntp_host.get().strip(),replace(self.settings)
        self.task('SNTP sorgusu',lambda: sntp_module.query(host,settings),self.time_output,self.time_button)

    def build_chat(self):
        self.chat_host=self.field(self.chat_tab,'Sunucu / dinleme adresi','127.0.0.1')
        self.chat_port=self.field(self.chat_tab,'TCP portu',5001)
        self.nickname=self.field(self.chat_tab,'Takma ad','Kullanıcı')
        row=ttk.Frame(self.chat_tab)
        row.pack(fill='x',pady=5)
        self.chat_mode=tk.StringVar(master=self,value='client')
        for label,mode in [('İstemci','client'),('Sunucu','server')]:
            ttk.Radiobutton(row,text=label,variable=self.chat_mode,value=mode).pack(side='left',padx=6)
        self.chat_start=ttk.Button(row,text='Bağlan / dinle',command=lambda: self.checked(self.start_chat))
        self.chat_start.pack(side='left',padx=10)
        self.chat_end=ttk.Button(row,text='Bağlantıyı kes',command=self.stop_chat,state='disabled')
        self.chat_end.pack(side='left')
        self.chat_output=self.output(self.chat_tab,8)
        row=ttk.Frame(self.chat_tab)
        row.pack(fill='x')
        self.message=tk.StringVar(master=self)
        entry=ttk.Entry(row,textvariable=self.message)
        entry.pack(side='left',fill='x',expand=True)
        entry.bind('<Return>',lambda event: self.send_chat())
        ttk.Button(row,text='Gönder',command=self.send_chat).pack(side='left',padx=8)

    def start_chat(self):
        host,port=self.address(self.chat_host,self.chat_port)
        mode,settings=self.chat_mode.get(),replace(self.settings)
        self.chat_stop=stop=threading.Event()
        self.chat_generation += 1
        generation=self.chat_generation
        self.chat_busy=True
        self.chat_start.configure(state='disabled')
        self.chat_end.configure(state='normal')
        self.chat_settings=settings
        self.chat_name=self.nickname.get().strip() or 'Kullanıcı'
        self.transcript=LOGS / ('gui-chat-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.txt')
        transcript=self.transcript
        def run():
            conn=None
            try:
                if mode == 'server':
                    with listener(host,port,settings) as server:
                        self.events.put(('log',f'Sohbet bağlantısı bekleniyor: {host}:{port}'))
                        while not stop.is_set():
                            try:
                                conn,_=accept(server,replace(settings,timeout=0.25))
                                settings.apply(conn)
                                break
                            except TimeoutError:
                                continue
                else:
                    conn=connect(host,port,settings)
                if conn is None or stop.is_set():
                    return
                self.chat_socket=conn
                self.events.put(('log','Sohbet bağlandı.'))
                while not stop.is_set():
                    try:
                        message=recv_frame(conn,settings).decode('utf-8')
                        self.record_chat('GELEN',message,transcript)
                    except TimeoutError:
                        continue
            except (OSError,ValueError) as exc:
                if not stop.is_set():
                    self.events.put(('error',error_text(exc)))
            finally:
                stop.set()
                if conn:
                    conn.close()
                self.chat_socket=None
                self.events.put(('chat_done',generation))
                self.events.put(('log','Sohbet bağlantısı kapandı.'))
        threading.Thread(target=run,daemon=True).start()

    def record_chat(self,direction,message,transcript=None):
        line=f'{datetime.datetime.now().isoformat(timespec="seconds")} {direction}: {message}'
        with (transcript or self.transcript).open('a',encoding='utf-8') as file:
            file.write(line + '\n')
        self.events.put(('chat_message',line))

    def send_chat(self):
        conn,text=self.chat_socket,self.message.get().strip()
        if conn is None or self.chat_stop.is_set():
            self.events.put(('error','Önce sohbet bağlantısını kurun.'))
            return
        if not text:
            return
        message=self.chat_name + ': ' + text
        if len(message.encode('utf-8')) > 1048576:
            self.events.put(('error','Mesaj en fazla 1 MiB olabilir.'))
            return
        self.message.set('')
        settings=self.chat_settings
        transcript=self.transcript
        def send():
            with self.send_lock:
                try:
                    send_frame(conn,message.encode('utf-8'),settings)
                except (OSError,ValueError):
                    try:
                        conn.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    raise
                self.record_chat('GİDEN',message,transcript)
        self.task('Sohbet mesajı gönderimi',send)

    def stop_chat(self):
        self.chat_stop.set()
        conn=self.chat_socket
        if conn:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        self.chat_end.configure(state='disabled')

    def build_settings(self):
        self.timeout=self.field(self.settings_tab,'Zaman aşımı (saniye)',self.settings.timeout)
        self.send_buffer=self.field(self.settings_tab,'Gönderme tamponu (bayt)',self.settings.send_buffer)
        self.receive_buffer=self.field(self.settings_tab,'Alma tamponu (bayt)',self.settings.receive_buffer)
        self.blocking=tk.BooleanVar(master=self,value=self.settings.blocking)
        ttk.Checkbutton(self.settings_tab,text='Blocking modu (kapalıysa nonblocking)',variable=self.blocking).pack(anchor='w',pady=12)
        ttk.Button(self.settings_tab,text='Ayarları kaydet',command=lambda: self.checked(self.save_settings)).pack(anchor='w')
        ttk.Label(self.settings_tab,text='Ayarlar yeni bağlantılarda uygulanır. Timeout: 0.1–120 saniye.\nTamponlar: 1024–4194304 bayt. SNTP ve bağlantı kurma sonlu timeout kullanır.',wraplength=700).pack(anchor='w',pady=16)

    def save_settings(self):
        settings=Settings(float(self.timeout.get()),int(self.send_buffer.get()),int(self.receive_buffer.get()),self.blocking.get())
        settings.save()
        self.settings=settings
        self.events.put(('log','Socket ayarları kaydedildi.'))

    def build_help(self):
        help_text=self.output(self.help_tab)
        self.write(help_text,'HIZLI BAŞLANGIÇ\n\n'
                   'Echo: Sunucuyu başlatın, ardından aynı pencerede mesaj gönderin.\n'
                   'Sohbet: Uygulamayı iki kez açın. Birinde Sunucu, diğerinde İstemci\n'
                   'seçin; adres ve port aynı olmalıdır. Varsayılan sohbet portu 5001.\n\n'
                   'İki bilgisayar: Sunucu 0.0.0.0 adresini dinler; istemci sunucunun\n'
                   'yerel ağ IP adresine bağlanır. Güvenlik duvarı izinleri gerekebilir.\n\n'
                   'SNTP: İnternet ve UDP 123 erişimi gerekir. Pozitif offset sunucu\n'
                   'saatinin ileride olduğunu gösterir. Sistem saati değiştirilmez.\n\n'
                   'Hatalar alttaki işlem günlüğünde gösterilir. Sohbetler logs/gui-chat-*.txt\n'
                   'dosyalarına kaydedilir. Sohbeti güvenilir ağda kullanın; şifreleme yoktur.\n\n'
                   'Çalıştırma: Proje klasöründe python gui.py komutunu kullanın.\n'
                   'Windows runtime ile: .\\runtime\\python.exe gui.py\n'
                   'Ayrıntılı kullanım: README.md.')

    def close(self):
        self.closing=True
        self.after_cancel(self.poll_id)
        self.stop_echo()
        self.stop_chat()
        self.destroy()


if __name__ == '__main__':
    NetworkApp().mainloop()
