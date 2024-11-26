import paramiko
import time
from config import *

def connect_to_hosts(host): #  Подключение к нодам
    try:
        key = paramiko.RSAKey.from_private_key_file(path_pkey) #  Указываем что вместо пароля используем ключ и путь к приватному ключу
        ssh = paramiko.client.SSHClient() #  Создание ssh клиента
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Параметры удаленного сервера. Если подключение по паролю то вместо pkey=key вставить password=password
        ssh.connect(host, port=port, username=username, pkey=key)
        return ssh
    except Exception:
        return None

def check_ssh_connect(hosts): # Проверка подключения
    print(f"Check connecting to hosts...")
    for host in hosts:
        connect = connect_to_hosts(host)
        if connect:
            print(f"\033[42mConnect to {host} is succesful!\033[0m")
        else:
            print(f"\033[41mError connecting to {host}\033[0m")
            return False
        connect.close()
    return True

def execute_sudo_command(function_connect, command): #  Выполнения комманд под sudo
    # Подключаемся к root сессии и выполняем команды по root
    stdin, stdout, stderr = function_connect.exec_command(f"sudo {command}")
    # stdin.write(f'{password}\n') #  Используем если в /etc/sudoers не отключена проверка пароля
    # stdin.flush() #  Используем если в /etc/sudoers не отключена проверка пароля

    # Построчно читаем вывод в реальном времени. Если вывода слишком много можно просто закомментить
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            output = stdout.channel.recv(1024).decode('utf-8')
            print(f"OUTPUT: {output}", end='')

    # Вывод результата выполнения команд
    output = stdout.read().decode()
    error = stderr.read().decode()
    if output:
        print(f"OUTPUT: {output}")
    if error:
        print(f"ERROR: {error}")
    return output

def sftp_copy(host, local_path, remote_path):  # копирование на ноды указанных в переменных файлов
    try:
        # Устанавливаем SSH-соединение
        key = paramiko.RSAKey.from_private_key_file(path_pkey)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, pkey=key)

        # Используем SFTP для передачи файла
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
    except Exception as error:
        print(f"Error connecting to {host}: {error}")
    finally:
        sftp.close()

def check_keepalived_installed(function_connect):
    stdin, stdout, stderr = function_connect.exec_command(f"sudo dpkg -l | grep keepalived")
    output = stdout.read().decode()
    if "keepalived" in output:
        return True
    return False

def install_keepalived_debian(function_connect):
    print(f"Copying keepalived.conf to {host}, directory /tmp")
    sftp_copy(host, 'keepalived.conf', '/tmp/keepalived.conf')

    commands = [
        f'apt update -y',
        f'apt install keepalived -y',
        f'cp -a /etc/sysctl.conf /etc/sysctl.conf.bckp',
        f'echo "net.ipv4.ip_nonlocal_bind=1" | sudo tee -a /etc/sysctl.conf',
        f'sysctl -p',
        f'cp -a /etc/keepalived/keepalived.conf /etc/keepalived/keepalived.conf.orig',
        f'mv /tmp/keepalived.conf /etc/keepalived/keepalived.conf'
    ]
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(2)

def systemctl_restart_keepalived(function_connect):
    commands = [
        f'systemctl restart keepalived',
        f'systemctl status keepalived | awk "/ etcd.service|Loaded:|Active:/"'
    ]
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(3)

if check_ssh_connect(hosts):
    print()
    for host in hosts:
        connect = connect_to_hosts(host)
        if check_keepalived_installed(connect):
            print(f"\033[43mKeepalived is already installed to host {host}. Necessary to check that the existing installation is correctly!\033[0m")
        else:
            print(f"\033[44mKeepalived is not installed to host {host}\033[0m\n\033[44mInstalling Keepalived to host {host}\033[0m")
            with open("keepalived.conf", "w", encoding="utf-8") as file:
                print(f'# Global definitions', file=file)
                print('global_defs {', file=file)
                print(f'  # Unique identifier for the Keepalived instance', file=file)
                print(f'  router_id haproxy_DH', file=file)
                print('}', file=file)
                print(f'\n# Script used to check if HAProxy is running', file=file)
                print('vrrp_script check_haproxy {', file=file)
                print(f'  script "/usr/bin/systemctl is-active haproxy"', file=file)
                print(f'  interval 2', file=file)
                print(f'  weight 2', file=file)
                print('}', file=file)
                print(f'\n# Virtual Router Redundancy Protocol (VRRP) instance', file=file)
                print('vrrp_instance VI_01 {', file=file)
                print(f'  state MASTER                # The initial state of this instance, MASTER or BACKUP', file=file)
                print(f'  interface {net_interface}              # The network interface to use', file=file)
                print(f'  virtual_router_id 51        # Identifier for the VRRP instance', file=file)
                print(f'  priority 111                # Priority of this instance (higher value means higher priority)', file=file)
                print(f'  advert_int 1                # Advertisement interval (in seconds)', file=file)
                print(f'\n  # The virtual IP address shared between the load balancers', file=file)
                print('  virtual_ipaddress {', file=file)
                print(f'    {virt_ip}/24', file=file)
                print('  }', file=file)
                print(f'\n  # Tracking script for HAProxy', file=file)
                print(f'    check_haproxy', file=file)
                print('  }', file=file)
                print('}', file=file)
            print(f"Файл keepalived.conf подготовлен для ноды {host}!\n")
            install_keepalived_debian(connect)
        connect.close()

for host in hosts: #  Запустиь Pgbouncer
    print(f"\033[44mExecuting systemctl restart Дeepalived to host {host}\033[0m")
    connect = connect_to_hosts(host)
    systemctl_restart_keepalived(connect)
    connect.close()

print(f"\033[42mFor check HAproxy execute:\033[0m")
print(f"psql -h {virt_ip} -p 5000 -U vyakhir -d vyakhir")