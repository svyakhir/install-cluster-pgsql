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

def check_patroni_installed(function_connect):
    stdin, stdout, stderr = function_connect.exec_command(f"sudo dpkg -l | grep patroni")
    output = stdout.read().decode()
    if "patroni" in output:
        return True
    return False

def get_hostname(function_connect):
    stdin, stdout, stdoerr = function_connect.exec_command(f"hostname")
    output = stdout.read().decode()
    return output

def install_patroni_debian(function_connect):
    print(f"Copying etcd.conf to {host}")
    sftp_copy(host, 'config.yml', '/tmp/config.yml')

    commands = [
        f"apt update -y",
        f"apt upgrade -y",
        f"apt install -y patroni",
        f"mkdir -p /etc/patroni",
        f"chown -R postgres:postgres /etc/patroni",
        f"rm -rf /var/lib/postgresql/13/main/*"
        f"cp -ar /tmp/config.yml /etc/patroni/config.yml"
    ]

    for command in commands:
        print(f"Executing as sudo {command}")
        execute_sudo_command(function_connect, command)
        time.sleep(2)

if check_ssh_connect(hosts):
    print()
    for host in hosts:
        connect = connect_to_hosts(host)
        check_patroni = check_patroni_installed(connect)
        if check_patroni:
            print(f"\033[43mPatroni is already installed to host {host}. Necessary to check that the existing installation is correctly!\033[0m")
        else:
            hostname = get_hostname(connect)
            modified_host = ".".join(host.split(".")[:2]) + ".0.0"
            print(f"\033[44mPatroni is not installed to host {host}\033[0m\n\033[44mInstalling Patroni to host {host}\033[0m")
            with open("config.yml", "w") as file:
                print(f"scope: 13-pgsql", file=file)
                print(f"name: {hostname}", file=file)
                print(f"log:", file=file)
                print(f"  level: INFO", file=file)
                print(f"  format: '%(asctime)s %(levelname)s: %(message)s'", file=file)
                print(f"  max_queue_size: 1000", file=file)
                print(f"  dir: /var/log/postgresql", file=file)
                print(f"  file_num: 4", file=file)
                print(f"  file_size: 25000000", file=file)
                print(f"  loggers:", file=file)
                print(f"    postgres.postmaster: WARNING", file=file)
                print(f"    urllib3: DEBUG", file=file)
                print(f"\nrestapi:", file=file)
                print(f"  listen: {host}:8008", file=file)
                print(f"  connect_address: {host}:8008", file=file)
                print(f"\netcd3:", file=file)
                print(f"  hosts:", file=file)
                print(f"    - {hosts[0]}:2379", file=file)
                print(f"    - {hosts[1]}:2379", file=file)
                print(f"    - {hosts[2]}:2379", file=file)
                print(f"\npg_hba:", file=file)
                print(f"  - local all all trust", file=file)
                print(f"  - host replication replicator {modified_host}/24 md5", file=file)
                print(f"  - host replication replicator 127.0.0.1/32 trust", file=file)
                print(f"  - host all all 0.0.0.0/0 md5", file=file)
                print(f"  - host all all 127.0.0.1/32 md5", file=file)
                print(f"  - host all all {modified_host}/24 md5", file=file)
                print(f"\nbootstrap:", file=file)
                print(f"  dcs:", file=file)
                print(f"    ttl: 30", file=file)
                print(f"    loop_wait: 10", file=file)
                print(f"    retry_timeout: 10", file=file)
                print(f"    maximum_lag_on_failover: 0", file=file)
                print(f"    synchronous_mode: true", file=file)
                print(f"    synchronous_mode_strict: false", file=file)
                print(f"    postgresql:", file=file)
                print(f"      use_pg_rewind: true", file=file)
                print(f"      use_slots: true", file=file)
                print(f"      parameters:", file=file)
                print(f"        max_connections: 200", file=file)
                print(f"        shared_buffers: 2GB", file=file)
                print(f"        effective_cache_size: 6GB", file=file)
                print(f"        maintenance_work_mem: 512MB", file=file)
                print(f"        checkpoint_completion_target: 0.7", file=file)
                print(f"        wal_buffers: 16MB", file=file)
                print(f"        default_statistics_target: 100", file=file)
                print(f"        random_page_cost: 1.1", file=file)
                print(f"        effective_io_concurrency: 200", file=file)
                print(f"        work_mem: 2621kB", file=file)
                print(f"        min_wal_size: 1GB", file=file)
                print(f"        max_wal_size: 4GB", file=file)
                print(f"        max_worker_processes: 40", file=file)
                print(f"        max_parallel_workers_per_gather: 4", file=file)
                print(f"        max_parallel_workers: 40", file=file)
                print(f"        max_parallel_maintenance_workers: 4", file=file)
                print(f"        max_locks_per_transaction: 64", file=file)
                print(f"        max_prepared_transactions: 0", file=file)
                print(f"        wal_level: replica", file=file)
                print(f"        wal_log_hints: on", file=file)
                print(f"        track_commit_timestamp: off", file=file)
                print(f"        max_wal_senders: 10", file=file)
                print(f"        max_replication_slots: 10", file=file)
                print(f"        wal_keep_segments: 8", file=file)
                print(f"        logging_collector: on", file=file)
                print(f"        log_destination: csvlog", file=file)
                print(f"        log_directory: '/var/log/postgresql'", file=file)
                print(f"        log_min_messages: warning", file=file)
                print(f"        log_min_error_statement: error", file=file)
                print(f"        log_min_duration_statement: 1000", file=file)
                print(f"        log_statement: all", file=file)
                print(f"  initdb:", file=file)
                print(f"    - encoding: UTF8", file=file)
                print(f"    - data-checksums", file=file)
                print(f"  pg_hba:", file=file)
                print(f"    - local all all trust", file=file)
                print(f"    - host replication replicator {modified_host}/24 md5", file=file)
                print(f"    - host replication replicator 127.0.0.1/32 trust", file=file)
                print(f"    - host all all 0.0.0.0/0 md5", file=file)
                print(f"    - host all all 127.0.0.1/32 md5", file=file)
                print(f"    - host all all {modified_host}/24 md5", file=file)
                print(f"  users:", file=file)
                print(f"    postgres:", file=file)
                print(f"      password: {patroni_password}", file=file)
                print(f"      options:", file=file)
                print(f"        - createrole", file=file)
                print(f"        - createdb", file=file)
                print(f"    replicator:", file=file)
                print(f"      password: {patroni_password}", file=file)
                print(f"      options:", file=file)
                print(f"        - replication", file=file)
                print(f"\npostgresql:", file=file)
                print(f"  listen: {host}:5432", file=file)
                print(f"  connect_address: {host}:5432", file=file)
                print(f"  data_dir: /var/lib/postgresql/13/main", file=file)
                print(f"  bin_dir: /usr/lib/postgresql/13/bin", file=file)
                print(f"  config_dir: /etc/postgresql/13/main", file=file)
                print(f"  pgpass: /var/lib/postgresql/.pgpass", file=file)
                print(f"  pg_hba:", file=file)
                print(f"    - local all all trust", file=file)
                print(f"    - host replication replicator {modified_host}/24 md5", file=file)
                print(f"    - host replication replicator 127.0.0.1/32 trust", file=file)
                print(f"    - host all all 0.0.0.0/0 md5", file=file)
                print(f"    - host all all 127.0.0.1/32 md5", file=file)
                print(f"    - host all all {modified_host}/24 md5", file=file)
                print(f"  authentication:", file=file)
                print(f"    replication:", file=file)
                print(f"      username: replicator", file=file)
                print(f"      password: {patroni_password}", file=file)
                print(f"    superuser:", file=file)
                print(f"      username: postgres", file=file)
                print(f"      password: {patroni_password}", file=file)
                print(f"  parameters:", file=file)
                print(f"    unix_socket_directories: '/var/run/postgresql'", file=file)
                print(f"    port: 5432", file=file)
            print(f"Файл config.yml подготовлен для ноды {host}!\n")
            install_patroni_debian(connect)
        connect.close()
