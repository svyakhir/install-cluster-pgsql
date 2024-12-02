Создает кластер Postgres из трех нод.  
БД и пользователь БД по умолчанию postgres. Пароль указывается в config.py  

На каждую ноду устанавливается ETCD, Postgresql, Patroni, PgBouncer, HAproxy, KeepAlive

Протестировано на Debian 11. На Debian 12 не стартовал патрони в apt идет Postgres 15

### Подготовка хостов ###  
1. Выполнить apt update -y && apt upgrade -y
2. Установить *openssh-server*  
3. Права *root* у пользователя под которым осуществляется подключение  
4. Ключ должен быть добавлен в authorized_keys
5. В /etc/sudoers добавить "*user* ALL=(ALL) NOPASSWD:ALL"
6. На хостах не должен быть установлен Postgresql

### Установка ###
0. Создать файл config.py. В нем указать информацию для подключения к нодам  
```
#Версия ETCD  
ETCD_VER='v3.5.15'

#Список нод на которые подключаемся. Используем только ip адреса  
nodes = [
    '192.168.0.1',
    '192.168.0.2',
    '192.168.0.3'
]

#Параметры для подключения по ssh с логином и паролем  
username = "username"  
password = "password"

#Параметры для подключения по ssh с ключом  
path_pkey = "D:/home/username"  # Путь до приватного ключа

# Параметры Patroni
patroni_password = "password" # Используется при подключении к БД развернутьой с помощью Патрони. Пользователь postgres

# Параметры БД. Предварительно создаем их в БД руками. 
dbname = "dbname"
dbuser = "dbuser"
dbpassword = "dbpassword"

# Параметры PgBouncer
pgbouncer_user = "admin" # Пользователь для управления PgBouncer

# Доступ до веб интерфейса HAproxy
haproxyuser = "vyakhir"
haproxypassword = "vyakhir"

# Виртуальный IP адрес для Keepalived
virt_ip = '192.168.0.200' #  Должен быть в той же подсети и что и основные сервера
net_interface = 'ens33' #  Интерфейс сети к которой прикручиваем виртуальную сеть
```
1. Для установки etcd - запустить install_etcd_debian.py
2. Для установки Postgresql 13 - запустить install_postgresql.py
3. Для установки Patroni - запустить install_patroni.py  
  Если планируется использовать БД и пользователся не postgres,тогда создаем:  
  `CREATE ROLE dbuser LOGIN SUPERUSER PASSWORD 'dbpassword';`  
  `CREATE DATABASE dbname WITH OWNER dbuser;`  
  И в PgBouncer используем эти параметры.  
  Если БД и пользователь не создавались, используем postgres. Как п умолчанию. Пароль используем как в patroni
4. Для установки PgBouncer - запусить install_pgbouncer.py.  
  После установки PgBouncer нужно выставить необходимые значения: 
    - размер пула соединений
    - максимальное количество подключений к PgBouncer

    и выполнить перезагрузку сервиса `systemctl restart pgbouncer`
5. Для установки HAproxy - запустить install_haproxy.py
6. Для установки Keepalive - запустить install_keepalived.py