1. Клонировать репозиторий

```bash
git clone https://github.com/dmitrysvd/test_task
cd test_task
```

2. Указать настройки в файле `.env`, скопировав файл `example.env`.

```bash
cp example.env .env
vim .env
```

3. Запустить докер-контейнер

```bash
docker-compose up --build
```

4. Докуменация API доступна по адресу http://localhost:8001/docs