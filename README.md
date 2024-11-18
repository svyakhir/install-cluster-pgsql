### Подготовка хостов ###  
1. Выполнить apt update -y && apt upgrade -y
2. Установить *openssh-server*  
3. Права *root* у пользователя под которым осуществляется подключение  
4. Ключ должен быть добавлен в authorized_keys
5. В /etc/sudoers добавить "*user* ALL=(ALL) NOPASSWD:ALL"
6. На хостах не должен быть установлен Postgresql

### Установка ###
1. Создать файл config.py. В нем указать информацию для подключения к нодам  
```
#Версия ETCD  
ETCD_VER='v3.5.15'

#Список нод на которые подключаемся  
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
```
2. Для установки etcd - запустить install_etcd_debian.py
3. Для установки Postgresql 13 - запустить install_postgresql.py