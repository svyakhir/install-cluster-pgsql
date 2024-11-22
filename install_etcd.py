import paramiko
import time
from config import *


def connect_to_hosts(host):  # Подключение к нодам
    try:
        key = paramiko.RSAKey.from_private_key_file(
            path_pkey)  # Указываем что вместо пароля используем ключ и путь к приватному ключу
        ssh = paramiko.client.SSHClient()  # Создание ssh клиента
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Параметры удаленного сервера. Если подключение по паролю то вместо pkey=key вставить password=password
        ssh.connect(host, port=port, username=username, pkey=key)
        return ssh
    except Exception:
        return None


def check_ssh_connect(hosts):  # Проверка подключения
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


def execute_sudo_command(function_connect, command):  # Выполнения комманд под sudo
    # Подключаемся к root сессии и выполняем команды по root
    stdin, stdout, stderr = function_connect.exec_command(f"sudo {command}")
    # stdin.write(f'{password}\n') #  Используем если в /etc/sudoers не отключена проверка пароля
    # stdin.flush() #  Используем если в /etc/sudoers не отключена проверка пароля

    # Вывод результата выполнения команд
    output = stdout.read().decode()
    error = stderr.read().decode()
    if output:
        print(f"OUTPUT: {output}")
    if error:
        print(f"ERROR: {error}")
    return output


def check_etcd_installed(function_connect):
    stdin, stdout, stderr = function_connect.exec_command(f"command -v etcd")
    output = stdout.read().decode()
    if "etcd" in output:
        return True
    return False


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


def install_etcd_debian(function_connect):  # Установка etcd на дебиан
    # Копирование конфигурационных файлов
    print(f"Copying etcd.service to {host}")
    sftp_copy(host, 'etcd.service', '/tmp/etcd.service')
    print(f"Copying etcd.conf to {host}")
    sftp_copy(host, 'etcd.conf', '/tmp/etcd.conf')

    # Команд которые будут выполняться на удаленной ноде
    commands = [
        #  Загружает в хом пользователя под которым идет подключение ssh
        f'wget -P /tmp/ https://github.com/etcd-io/etcd/releases/download/{ETCD_VER}/etcd-{ETCD_VER}-linux-amd64.tar.gz',
        f'tar -xzvf /tmp/etcd-{ETCD_VER}-linux-amd64.tar.gz -C /tmp/',
        f'mv /tmp/etcd-{ETCD_VER}-linux-amd64/etcd* /usr/local/bin/',
        'groupadd --system etcd',  # Создание группы
        'useradd -s /sbin/nologin --system -g etcd etcd',  # Создание пользователя и добавление в группу etcd
        'mkdir /var/lib/etcd',  # Создание каталога с данными
        'mkdir /etc/etcd',  # Создание каталога с конфигом
        'chown -R etcd:etcd /var/lib/etcd',
        'chmod -R 700 /var/lib/etcd',
        f'rm -rf /tmp/etcd-{ETCD_VER}-linux-amd64*',
        'cp /tmp/etcd.service /etc/systemd/system/etcd.service',
        'cp /tmp/etcd.conf /etc/etcd/etcd.conf'
    ]
    # Выполнение команд
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(2)


def systemctl_demon_reload(function_connect):
    print(f"Executing as sudo systemctl daemon-reload")
    execute_sudo_command(function_connect, 'systemctl daemon-reload')
    time.sleep(2)


def systemctl_start_etcd(function_connect):  # Запуск служб etcd
    commands = ['systemctl enable etcd',
                'systemctl start etcd',
                'systemctl status etcd | awk "/ etcd.service|Loaded:|Active:/"'
                ]
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(3)


def check_leader(function_connect):
    print(f"Executing as sudo etcdctl endpoint status --cluster -w table")
    execute_sudo_command(function_connect, 'etcdctl endpoint status --cluster -w table')
    time.sleep(2)


if check_ssh_connect(hosts):
    num = 1
    for host in hosts:
        connect = connect_to_hosts(host)
        check_etcd = check_etcd_installed(connect)
        if check_etcd:
            print(
                f"\033[43m{host} ETCD is already installed. Necessary to check that the existing installation is correctly!\033[0m")
        else:
            print(f"\n\033[44m{host} ETCD is not installed\033[0m\n\033[44mInstalling ETCD to host {host}\033[0m")
            with open("etcd.conf", "w") as file:  # Создает файл конфигурации etcd
                print(f'ETCD_NAME="etcd{num}"', file=file)
                print(f'ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"', file=file)
                print(f'ETCD_ADVERTISE_CLIENT_URLS="http://{host}:2379"', file=file)
                print(f'ETCD_LISTEN_PEER_URLS="http://0.0.0.0:2380"', file=file)
                print(f'ETCD_INITIAL_ADVERTISE_PEER_URLS="http://{host}:2380"', file=file)
                print(f'ETCD_INITIAL_CLUSTER_TOKEN="etcd-postgres-cluster"', file=file)
                print(
                    f'ETCD_INITIAL_CLUSTER="etcd1=http://{hosts[0]}:2380,etcd2=http://{hosts[1]}:2380,etcd3=http://{hosts[2]}:2380"',
                    file=file)
                print(f'ETCD_INITIAL_CLUSTER_STATE="new"', file=file)
                print(f'ETCD_DATA_DIR="/var/lib/etcd"', file=file)
                print(f'ETCD_ELECTION_TIMEOUT="10000"', file=file)
                print(f'ETCD_HEARTBEAT_INTERVAL="2000"', file=file)
                print(f'ETCD_INITIAL_ELECTION_TICK_ADVANCE="false"', file=file)
                print(f'ETCD_ENABLE_V2="true"', file=file)
            print(f"\033[44mФайл etcd.conf подготовлен для ноды {num}!\033[0m\n")
            install_etcd_debian(connect)
        connect.close()
        num += 1
else:
    print("\033[41mOne or more connections failed. Exiting.\033[0m")

for host in hosts:  # Перезагрузка демона
    print(f"\033[44mExecuting systemctl daemon-reload to host {host}\033[0m")
    connect = connect_to_hosts(host)
    systemctl_demon_reload(connect)
    connect.close()

for host in hosts:  # Запуск ETCD
    print(f"\033[44mExecuting systemctl start etcd to host {host}\033[0m")
    connect = connect_to_hosts(host)
    systemctl_start_etcd(connect)
    connect.close()

for host in hosts:  # Проверка лидера ETCD
    print(f"\033[44mExecuting check_leader to host {host}\033[0m")
    connect = connect_to_hosts(host)
    check_leader(connect)
    connect.close()
