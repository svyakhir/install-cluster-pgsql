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
    except Exception as e:
        print(f"Error connecting to {node}: {e}")
    finally:
        if client:
            client.close()

def install_etcd_debian(client):
    # Команд которые будут выполняться на удаленной ноде
    commands = [
        #  Загружает в хом пользователя под которым идет подключение ssh
        f'wget -P /tmp/ https://github.com/etcd-io/etcd/releases/download/{ETCD_VER}/etcd-{ETCD_VER}-linux-amd64.tar.gz',
        f'tar -xzvf /tmp/etcd-{ETCD_VER}-linux-amd64.tar.gz',
        f'mv /tmp/etcd-{ETCD_VER}-linux-amd64/etcd* /usr/local/bin/',
        'groupadd --system etcd',
        'useradd -s /sbin/nologin --system -g etcd etcd',
        'mkdir /var/lib/etcd && mkdir /etc/etcd',
        'chown -R etcd:etcd /var/lib/etcd && chmod -R 700 /var/lib/etcd',
        'rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz'

        # Создаем конфигурацию systemd
        'cat << EOF > /etc/systemd/system/etcd.service'
    ]
    # Выполнение команд под sudo
    for command in commands:
        print(f"Executing as sudo: {command}")
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

for node in nodes:
    connect_to_nodes(node)