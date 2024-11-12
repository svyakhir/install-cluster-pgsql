import paramiko
import time
from config import *

def connect_to_nodes(node, execute_function): #  Подключение к ноде
    try:
        key = paramiko.RSAKey.from_private_key_file(path_pkey)
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(node, username=username, pkey=key)
        print(f"Connected to node {node}")
        execute_function(client) # Выполняемая функция
    except Exception as error:
        print(f"Error connecting to {node}: {error}")
    finally:
        client.close()

def execute_sudo_command(client, command):
    # Подключаемся к root сессии и выполняем команды по root
    stdin, stdout, stderr = client.exec_command(f"sudo {command}")
    # stdin.write(f'{password}\n') #  Используем если в /etc/sudoers не отключена проверка пароля
    # stdin.flush() #  Используем если в /etc/sudoers не отключена проверка пароля

    # Построчно читаем вывод в реальном времени
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

def install_postgresql_debian(client):
    commands = ['apt install postgresql-client-13 postgresql-doc-13 postgresql-common postgresql postgresql-13 postgresql-doc -y',
               'apt reinstall postgresql-client-13 postgresql-doc-13 postgresql-common postgresql postgresql-13 postgresql-doc -y',
               'systemctl stop postgresql',
               'systemctl disable postgresql',
               'systemctl status postgresql | awk "/ etcd.service|Loaded:|Active:/"'
               ]

    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(client, command)
        time.sleep(2)

for node in nodes:
    connect_to_nodes(node, install_postgresql_debian)