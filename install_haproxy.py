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

def check_haproxy_installed(function_connect):
    stdin, stdout, stderr = function_connect.exec_command(f"sudo dpkg -l | grep haproxy")
    output = stdout.read().decode()
    if "haproxy" in output:
        return True
    return False

def install_haproxy_debian(function_connect):
    print(f"Copying haproxy.cfg to {host}, directory /tmp")
    sftp_copy(host, 'haproxy.cfg', '/tmp/haproxy.cfg')

    commands = [
        f'apt update -y',
        f'apt install haproxy -y',
        f'cp -a /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.orig',
        f'cp /tmp/haproxy.cfg /etc/haproxy/haproxy.cfg',
        f'haproxy -f /etc/haproxy/haproxy.cfg -c'
    ]

    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(2)

def systemctl_restart_haproxy(function_connect):
    commands = [
        f'systemctl restart haproxy',
        f'systemctl status haproxy | awk "/ etcd.service|Loaded:|Active:/"'
    ]
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(3)

if check_ssh_connect(hosts):
    print()
    for host in hosts:
        connect = connect_to_hosts(host)
        if check_haproxy_installed(connect):
            print(f"\033[43mHaproxy is already installed to host {host}. Necessary to check that the existing installation is correctly!\033[0m")
        else:
            print(f"\033[44mHaproxy is not installed to host {host}\033[0m\n\033[44mInstalling Haproxy to host {host}\033[0m")
            with open("haproxy.cfg", "w", encoding="utf-8") as file:
                print(f'global', file=file)
                print(f'    maxconn 1000', file=file)
                print(f'\ndefaults', file=file)
                print(f'    log global', file=file)
                print(f'    mode tcp', file=file)
                print(f'    retries 2', file=file)
                print(f'    timeout client 30m', file=file)
                print(f'    timeout connect 4s', file=file)
                print(f'    timeout server 30m', file=file)
                print(f'    timeout check 5s', file=file)
                print(f'\nlisten stats', file=file)
                print(f'    mode http', file=file)
                print(f'    bind *:7000', file=file)
                print(f'    stats enable', file=file)
                print(f'    stats uri /', file=file)
                print(f'    stats auth {haproxyuser}:{haproxypassword}', file=file)
                print(f'\nlisten postgres', file=file)
                print(f'    bind *:5000', file=file)
                print(f'    option httpchk', file=file)
                print(f'    http-check expect status 200', file=file)
                print(f'    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions', file=file)
                print(f'    server dbserver1 {host}:6432 maxconn 100 check port 8008', file=file)
                print(f'    server dbserver2 {host}:6432 maxconn 100 check port 8008', file=file)
                print(f'    server dbserver3 {host}:6432 maxconn 100 check port 8008', file=file)
            print(f"Файл haproxy.cfg подготовлен для ноды {host}!\n")
            install_haproxy_debian(connect)
        connect.close()

for host in hosts: #  Запустиь Pgbouncer
    print(f"\033[44mExecuting systemctl restart HAproxy to host {host}\033[0m")
    connect = connect_to_hosts(host)
    systemctl_restart_haproxy(connect)
    connect.close()

print(f"\033[42mFor check HAproxy execute:\033[0m")
for host in hosts:
    print(f"psql -h {host} -p 5000 -U {dbuser} -d {dbname}")