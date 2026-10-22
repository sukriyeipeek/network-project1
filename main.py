import argparse
import json
from dataclasses import asdict
from netkit import chat_module,echo_module,machine_module,sntp_module
from netkit.error_settings import LOGS,Settings,error_text,report_error


def display(result):
    text=json.dumps(result,ensure_ascii=False,indent=2)
    print(text)
    (LOGS / 'last-result.json').write_text(text,encoding='utf-8')


def read_address():
    host=input('Adres [127.0.0.1]: ').strip() or '127.0.0.1'
    port=int(input('Port [5000]: ') or '5000')
    if not 1 <= port <= 65535:
        raise ValueError('Port 1–65535 olmalı.')
    return host,port


def menu(settings):
    while True:
        print('\n=== NETWORK DIAGNOSTIC TOOLKIT ===\n'
              '1 Makine bilgileri\n2 Echo sunucusu\n3 Echo istemcisi\n'
              '4 SNTP saat kontrolü\n5 Sohbet\n6 Socket ayarları\n'
              '7 Hata yönetimi örnekleri\n0 Çıkış')
        choice=input('Seçim: ').strip()
        try:
            if choice == '0':
                return
            if choice == '1':
                display(machine_module.machine_info())
            elif choice == '2':
                host,port=read_address()
                echo_module.server(host,port,settings)
            elif choice == '3':
                host,port=read_address()
                message=input('Mesaj: ')
                display(echo_module.client(host,port,message,settings))
            elif choice == '5':
                mode=input('server/client: ').strip()
                if mode not in ('server','client'):
                    raise ValueError('Mod server veya client olmalı.')
                host,port=read_address()
                nickname=input('Takma ad: ') or 'Kullanıcı'
                chat_module.run(mode,host,port,settings,nickname)
            elif choice == '4':
                display(sntp_module.query(input('SNTP sunucusu [pool.ntp.org]: ') or 'pool.ntp.org',settings))
            elif choice == '6':
                display(asdict(settings))
                updated=Settings(
                    timeout=float(input('Timeout saniye [5]: ') or 5),
                    send_buffer=int(input('Gönderme tamponu [65536]: ') or 65536),
                    receive_buffer=int(input('Alma tamponu [65536]: ') or 65536),
                    blocking=input('Blocking? [E/h]: ').strip().lower() != 'h',
                )
                updated.save()
                settings=updated
                print('Ayarlar kaydedildi; sonraki bağlantılarda uygulanacak.')
            elif choice == '7':
                for exc in (TimeoutError(),ConnectionRefusedError(),ValueError('Geçersiz ayar')):
                    print(type(exc).__name__ + ': ' + error_text(exc))
                print('Bağlantı hataları logs/application.log dosyasına kaydedilir.')
            else:
                print('Geçersiz seçim.')
        except KeyboardInterrupt:
            print('\nİşlem durduruldu; ana menüye dönülüyor.')
        except (OSError,ValueError,TypeError) as exc:
            report_error(exc)


def main():
    parser=argparse.ArgumentParser(description='Network Diagnostic and Tool Package')
    parser.add_argument('command',nargs='?',default='menu',
                        choices=['menu','info','echo-server','echo-client','sntp','chat-server','chat-client'])
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=5000)
    parser.add_argument('--message',default='Merhaba ağ!')
    parser.add_argument('--name',default='Kullanıcı')
    parser.add_argument('--ntp-host',default='pool.ntp.org')
    args=parser.parse_args()
    try:
        settings=Settings.load()
        if not 1 <= args.port <= 65535:
            raise ValueError('Port 1–65535 olmalı.')
        if args.command == 'menu':
            menu(settings)
        elif args.command == 'info':
            display(machine_module.machine_info())
        elif args.command == 'echo-server':
            echo_module.server(args.host,args.port,settings)
        elif args.command == 'echo-client':
            result=echo_module.client(args.host,args.port,args.message,settings)
            display(result)
            return 0 if result['matches'] else 1
        elif args.command == 'sntp':
            display(sntp_module.query(args.ntp_host,settings))
        else:
            chat_module.run(args.command.split('-')[1],args.host,args.port,settings,args.name)
        return 0
    except KeyboardInterrupt:
        print('\nProgram kapatıldı.')
        return 130
    except (OSError,ValueError,TypeError) as exc:
        report_error(exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
