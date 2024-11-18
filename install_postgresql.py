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

def check_postgresql_installed(function_connect): #  Проверка установлен ли Posgresql перед установкой

    stdin, stdout, stderr = function_connect.exec_command(f"sudo dpkg -l | grep postgresql")
    output = stdout.read().decode()
    if "postgresql" in output: # Если в выводе команды есть "postgresql", возвращаем True
        return True
    return False

def install_postgresql_debian(function_connect):
    commands = ['apt update -y',
                'apt install postgresql-client-13 postgresql-doc-13 postgresql-common postgresql postgresql-13 postgresql-doc -y',
                'apt reinstall postgresql-client-13 postgresql-doc-13 postgresql-common postgresql postgresql-13 postgresql-doc -y',
                'systemctl stop postgresql',
                'systemctl disable postgresql',
                'systemctl status postgresql | awk "/ etcd.service|Loaded:|Active:/"'
                ]

    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(2)

if check_ssh_connect(hosts):
    print()
    print(f"Сhecking an existing installation Postgresql...")
    for host in hosts:
        connect = connect_to_hosts(host)
        check_postgresql = check_postgresql_installed(connect)
        if check_postgresql:
            print(f"\033[43m{host} Postgresql is already installed. Necessary to check that the existing installation is correctly!\033[0m")
        else:
            print(f"\n{host} Postgresql is not installed\nInstalling Postgresql 13 to host {host}")
            install_postgresql_debian(connect)
        connect.close()
    print(f"\n\033[42mPostgresql has been successfully installed on all hosts {hosts}\033[0m")
else:
    print("\033[41mOne or more connections failed. Exiting.\033[0m")