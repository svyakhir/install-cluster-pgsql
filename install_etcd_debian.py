import paramiko
import time
from config import *

def connect_to_nodes(node): #  Подключение к ноде и установка etcd
    try:
        key = paramiko.RSAKey.from_private_key_file(path_pkey)
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(node, username=username, pkey=key)
        print(f"Connected to node {node}")
        # Установка etcd на удаленной машине
        install_etcd_debian(client)
    except Exception as error:
        print(f"Error connecting to {node}: {error}")
    finally:
        client.close()

def sftp_copy(node,local_path, remote_path):
    try:
        # Устанавливаем SSH-соединение
        key = paramiko.RSAKey.from_private_key_file(path_pkey)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(node, username=username, pkey=key)

        # Используем SFTP для передачи файла
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
    except Exception as error:
        print(f"Error connecting to {node}: {error}")
    finally:
        sftp.close()

def install_etcd_debian(client):
    # Копирование конфигурационных файлов
    print(f"Copying etcd.service to {node}")
    sftp_copy(node, 'etcd.service', '/tmp/etcd.service')
    print(f"Copying etcd.conf to {node}")
    sftp_copy(node, 'etcd.conf', '/tmp/etcd.conf')

    # Команд которые будут выполняться на удаленной ноде
    commands = [
        #  Загружает в хом пользователя под которым идет подключение ssh
        f'wget -P /tmp/ https://github.com/etcd-io/etcd/releases/download/{ETCD_VER}/etcd-{ETCD_VER}-linux-amd64.tar.gz',
        f'tar -xzvf /tmp/etcd-{ETCD_VER}-linux-amd64.tar.gz -C /tmp/',
        f'mv /tmp/etcd-{ETCD_VER}-linux-amd64/etcd* /usr/local/bin/',
        'groupadd --system etcd', #  Создание группы
        'useradd -s /sbin/nologin --system -g etcd etcd', #  Создание пользователя и добавление в группу etcd
        'mkdir /var/lib/etcd', #  Создание каталога с данными
        'mkdir /etc/etcd', #  Создание каталога с конфигом
        'chown -R etcd:etcd /var/lib/etcd',
        'chmod -R 700 /var/lib/etcd',
        f'rm -rf /tmp/etcd-{ETCD_VER}-linux-amd64*',
        'cp /tmp/etcd.service /etc/systemd/system/etcd.service',
        'cp /tmp/etcd.conf /etc/etcd/etcd.conf',
        'systemctl daemon-reload',
        'systemctl enable etcd',
        'systemctl start etcd',
        'systemctl status etcd'
    ]
    # Выполнение команд
    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(client, command)
        time.sleep(2)

def execute_sudo_command(client, command):
    # Подключаемся к root сессии и выполняем команды по root
    stdin, stdout, stderr = client.exec_command(f"sudo {command}")
    # stdin.write(f'{password}\n') #  Используем если в /etc/sudoers не отключена проверка пароля
    # stdin.flush() #  Используем если в /etc/sudoers не отключена проверка пароля

    # Вывод результата выполнения команд
    output = stdout.read().decode()
    error = stderr.read().decode()
    if output:
        print(f"OUTPUT: {output}")
    if error:
        print(f"ERROR: {error}")

num = 1
for node in nodes:
    with open("etcd.conf", "w") as file: #  Создает файл конфигурации etcd
        print(f'ETCD_NAME="etcd{num}"', file=file)
        print(f'ETCD_LISTEN_CLIENT_URLS="http://0.0.0.0:2379"', file=file)
        print(f'ETCD_ADVERTISE_CLIENT_URLS="http://{node}:2379"', file=file)
        print(f'ETCD_LISTEN_PEER_URLS="http://0.0.0.0:2380"', file=file)
        print(f'ETCD_INITIAL_ADVERTISE_PEER_URLS="http://{node}:2380"', file=file)
        print(f'ETCD_INITIAL_CLUSTER_TOKEN="etcd-postgres-cluster"', file=file)
        print(f'ETCD_INITIAL_CLUSTER="etcd1=http://{nodes[0]}:2380,etcd2=http://{nodes[1]}:2380,etcd3=http://{nodes[2]}:2380"', file=file)
        print(f'ETCD_INITIAL_CLUSTER_STATE="new"', file=file)
        print(f'ETCD_DATA_DIR="/var/lib/etcd"', file=file)
        print(f'ETCD_ELECTION_TIMEOUT="10000"', file=file)
        print(f'ETCD_HEARTBEAT_INTERVAL="2000"', file=file)
        print(f'ETCD_INITIAL_ELECTION_TICK_ADVANCE="false"', file=file)
        print(f'ETCD_ENABLE_V2="true"', file=file)
    print(f"Файл etcd.conf подготовлен для ноды {num}!")
    connect_to_nodes(node)
    num += 1