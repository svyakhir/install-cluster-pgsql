Подготовка на серверах  
Должен быть установлен *openssh-server*  
Права *root* у пользователя под которым осуществляется подключение  
Ключ должен быть добавлен в authorized_keys
в /etc/sudoers добавить "*user* ALL=(ALL) NOPASSWD:ALL"