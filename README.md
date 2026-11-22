# Werewolf

## Установка

```bash
wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py
python3 /tmp/get-pip.py --user --break-system-packages
python3 -m pip install --user --break-system-packages Django Pillow
```

## Запуск

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

- <http://127.0.0.1:8000/>
- <http://127.0.0.1:8000/admin/> - `admin` / `admin`

## Запуск

```bash
docker compose up -d
```
