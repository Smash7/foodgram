# Foodgram

Foodgram - это веб-приложение для публикации рецептов. Пользователи могут добавлять рецепты, подписываться на любимых авторов, добавлять рецепты в избранное и список покупок, а также просматривать рецепты других пользователей.

## Автор

- **ФИО**: Мартынов Евгений Алексеевич
- [LinkedIn](https://www.linkedin.com/in/eugene-martynov/)

## Техно-стек

- Python 3
- Django 3.2
- Django REST Framework
- PostgreSQL
- Docker
- Nginx
- Gunicorn
- React

## Команды локального развертывания

### Клонирование репозитория

```bash
git clone https://github.com/Smash7/foodgram.git
cd foodgram
```

### Создание .env файла

Создайте файл `.env` в корне проекта и добавьте в него следующие переменные окружения:

```env
DJANGO_SECRET_KEY=your_secret_key
DB_ENGINE=sqlite # or postgres
DB_NAME=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
DB_HOST=db
DB_PORT=5432
```

### Запуск Docker Compose

Перейдите в папку `infra` и выполните команду для запуска контейнеров:

```bash
cd infra
docker-compose up -d --build
```

### Применение миграций и сбор статики

После запуска контейнеров, примените миграции и соберите статику:

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py collectstatic --noinput
```

### Создание суперпользователя

Создайте суперпользователя для доступа к админ панели:

```bash
docker-compose exec backend python manage.py createsuperuser
```

### Импорт данных из JSON файлов

Для импорта тегов и продуктов из JSON файлов выполните следующие команды:

```bash
docker-compose exec backend python manage.py loaddata tags.json
docker-compose exec backend python manage.py loaddata ingredients.json
```

## Команды запуска

### Запуск контейнеров

Для запуска всех контейнеров выполните команду:

```bash
docker-compose up -d
```

### Остановка контейнеров

Для остановки всех контейнеров выполните команду:

```bash
docker-compose down
```

## Доступ к Docker приложению

- **Фронтенд веб-приложения**: [http://localhost](http://localhost)
- **Спецификация API**: [http://localhost/api/docs/](http://localhost/api/docs/)

## Запуск без Docker

### Установка зависимостей

Перейдите в папку `backend` и установите зависимости:

```bash
cd backend
pip install -r requirements.txt
```

### Применение миграций и сбор статики

Примените миграции и соберите статику:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Создание суперпользователя

Создайте суперпользователя для доступа к админ панели:

```bash
python manage.py createsuperuser
```

### Запуск сервера

Запустите сервер командой:

```bash
python manage.py runserver
```

### Доступ к приложению

- **API**: [http://localhost:8000/api/](http://localhost:8000/api/)