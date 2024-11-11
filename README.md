### Подготовка хостов ###  
1. Установить *openssh-server*  
2. Права *root* у пользователя под которым осуществляется подключение  
3. Ключ должен быть добавлен в authorized_keys
4. В /etc/sudoers добавить "*user* ALL=(ALL) NOPASSWD:ALL"

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