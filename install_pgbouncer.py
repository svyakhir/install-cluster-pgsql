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

def check_pgbouncer_installed(function_connect):
    stdin, stdout, stderr = function_connect.exec_command(f"sudo dpkg -l | grep pgbouncer")
    output = stdout.read().decode()
    if "pgbouncer" in output:
        return True
    return False

def install_pgbouncer_debian(function_connect):
    print(f"Copying /etc/pgbouncer/pgbouncer.ini to {host}")
    sftp_copy(host, 'pgbouncer.ini', '/tmp/pgbouncer.ini')

    commands = [
        f'apt update -y',
        f'apt install pgbouncer -y',
        f'systemctl stop pgbouncer',
        f'cp -a /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini.orig',
        f'chmod 755 /var/log/postgresql',
        f'cp /tmp/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini',
        f'echo \'"{dbuser}" "{dbpassword}"\' | sudo tee -a /etc/pgbouncer/userlist.txt'
    ]

    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(2)

def systemctl_start_pgbouncer(function_connect):
    commands = [
        f'systemctl start pgbouncer',
        f'systemctl status pgbouncer | awk "/ etcd.service|Loaded:|Active:/"'
    ]
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(3)

if check_ssh_connect(hosts):
    print()
    for host in hosts:
        connect = connect_to_hosts(host)
        if check_pgbouncer_installed(connect):
            print(f"\033[43mPgbouncer is already installed to host {host}. Necessary to check that the existing installation is correctly!\033[0m")
        else:
            print(f"\033[44mPgbouncer is not installed to host {host}\033[0m\n\033[44mInstalling Pgbouncer to host {host}\033[0m")
            with open("pgbouncer.ini", "w", encoding="utf-8") as file:
                print(f'[databases]', file=file)
                print(f'# Подключения к базе данных. Определяет какие БД доступны через PgBouncer', file=file)
                print(f'{dbname} = host={host} port=5432 dbname={dbname} auth_user={dbuser}', file=file)
                print(f'* = host=127.0.0.1 port=5432', file=file)
                print(f'\n[pgbouncer]', file=file)
                print(f'# Пользователь для управления PgBouncer', file=file)
                print(f'admin_users = {pgbouncer_user}', file=file)
                print(f'auth_file = /etc/pgbouncer/userlist.txt', file=file)
                print(f'\n# Максимальное количество подключений к PgBouncer', file=file)
                print(f'max_client_conn = 100', file=file)
                print(f'\n# Размер пула соединений для каждой базы данных', file=file)
                print(f'default_pool_size = 20', file=file)
                print(f'\n# Минимальное количество соединений, которое будет поддерживаться', file=file)
                print(f'#min_pool_size = 5', file=file)
                print(f'\n# Максимальное количество "отложенных" соединений, которые ждут доступ к пулу', file=file)
                print(f'#reserve_pool_size = 5', file=file)
                print(f'#reserve_pool_timeout = 5.0', file=file)
                print(f'\n# Пользователь для управления PgBouncer', file=file)
                print(f'auth_type = md5', file=file)
                print(f'auth_file = /etc/pgbouncer/userlist.txt', file=file)
                print(f'admin_users = {pgbouncer_user}', file=file)
                print(f'\nlogfile = /var/log/postgresql/pgbouncer.log', file=file)
                print(f'pidfile = /var/run/postgresql/pgbouncer.pid', file=file)
                print(f'\n# Место, где будет работать PgBouncer (сокет или порт)', file=file)
                print(f'listen_addr = *', file=file)
                print(f'listen_port = 6432', file=file)
                print(f'\n# UNIX-сокет для взаимодействия с клиентами', file=file)
                print(f'unix_socket_dir = /var/run/postgresql', file=file)
                print(f'\n# Логирование', file=file)
                print(f'log_connections = 1', file=file)
                print(f'log_disconnections = 1', file=file)
                print(f'log_pooler_errors = 1', file=file)
                print(f'\n# Таймауты и время жизни соединений', file=file)
                print(f'idle_transaction_timeout = 60', file=file)
                print(f'server_idle_timeout = 300', file=file)
                print(f'query_timeout = 60', file=file)
                print(f'\n# Режим работы пула и параметры запуска', file=file)
                print(f'pool_mode = session', file=file)
                print(f'ignore_startup_parameters = extra_float_digits', file=file)
            print(f"Файл pgbouncer.ini подготовлен для ноды {host}!\n")
            install_pgbouncer_debian(connect)
        connect.close()

for host in hosts: #  Запустиь Pgbouncer
    print(f"\033[44mExecuting systemctl start Pgbouncer to host {host}\033[0m")
    connect = connect_to_hosts(host)
    systemctl_start_pgbouncer(connect)
    connect.close()

print(f"\033[42mFor check PgBouncer execute:\033[0m")
for host in hosts:
    print(f"psql -h {host} -p 6432 -U {dbuser} -d {dbname}")
