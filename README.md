# AllLove Logistics

Система отслеживания поставок одежды шоурума AllLove. Версия 1.0.0.

Два клиента к одному API:

- **веб** — сотрудник шоурума и администратор; на телефоне ставится как приложение («На экран Домой»);
- **десктоп / мобильный клиент валидатора** — очередь проверки, документы, сверка количеств. На компьютере: `python -m desktop`. На телефоне тот же веб ставится как PWA.

Стек: FastAPI + SQLAlchemy + PostgreSQL, React + TypeScript + Refine + Ant Design, JWT, tkinter.

После входа открывается рабочее место роли:

- **администратор** — люди, справочники, номенклатура, журнал, копии;
- **сотрудник шоурума** — сводка, поставки, архив, документы, предложения, отчёты, уведомления;
- **валидатор** — очередь проверки, сверка количеств, расхождения.

## Что нужно

- Python 3.10+
- Docker Desktop (PostgreSQL)
- Node.js 18+
- Git

## Запуск

### 1. База данных

```bash
docker compose up -d
```

Контейнер `postgres:16` слушает порт `5433`. Если схема уже создавалась по старой версии:

```bash
docker compose down
docker volume rm шоурумлогистика_postgres_data 2>/dev/null || true
docker compose up -d
```

### 2. Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Если порт 8000 занят: `uvicorn app.main:app --reload --port 8001`  
и в `frontend/.env` укажите `VITE_PROXY_TARGET=http://127.0.0.1:8001`.

При старте применяются миграции Alembic (`alembic upgrade head`). Старая sqlite-база без `alembic_version` помечается как актуальная и не ломается.

Swagger: http://127.0.0.1:8000/docs

HTTPS пилота (самоподписанный сертификат):

```bash
python scripts/make_certs.py
python scripts/run_https.py
```

API: https://127.0.0.1:8443  
Либо `docker compose --profile https up`, если Docker доступен. Браузер спросит доверие к учебному сертификату.

### 3. Начальные данные

```bash
python scripts/seed.py
```

| Роль | Email | Пароль |
|---|---|---|
| Администратор | admin@alllove.ru | admin123 |
| Клиент | client1@alllove.ru | client123 |
| Клиент | client2@alllove.ru | client123 |
| Клиент | client3@alllove.ru | client123 |
| Валидатор | validator@alllove.ru | validator123 |

`python scripts/seed.py` также создаёт 10 демо-поставок со статусами, накладными PDF и фото коробок. Повторный запуск их не дублирует.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Интерфейс: http://localhost:5173

На телефоне откройте тот же адрес в Chrome или Safari и добавьте на Домой — это мобильное приложение.

### 5. Десктоп валидатора

Из корня проекта, с активным venv:

```bash
python -m desktop
```

Вход: `validator@alllove.ru` / `validator123`. Адрес сервера по умолчанию `http://127.0.0.1:8001` (или `ALLLOVE_API_URL`). Сотрудник шоурума и администратор входят через веб.

## Тесты

```bash
pytest -q
```

Покрывают UC-01–UC-12, миграции, сертификат HTTPS и фильтры. Изолированная SQLite, Docker не нужен.

Нагрузка 5000 поставок / 20 сессий (НФТ-03):

```bash
python scripts/load_check.py
```

Протокол пишется в `docs/load_protocol.md`.

Дневная копия создаётся планировщиком API около 03:00 и скриптом `python scripts/backup.py`. Cron: `deploy/crontab.example`.

## Резервное копирование и восстановление

```bash
python scripts/backup.py
python scripts/restore.py            # последняя копия
python scripts/restore.py 2026-11-13 # конкретный день
```

Либо разделы **Копии** у администратора. Хранятся последние 7 дневных комплектов «база + файлы».

HTTPS для пилота: пример `deploy/nginx.conf.example`.

## Руководства

- `docs/guides.md` — сценарии трёх ролей
- `docs/process.md` — вехи, CR, откат, HTTPS
- `docs/acceptance.md` — бланк протокола приёмки

## Статусы поставки

`Создана` → `В пути` → `На проверке` → `Проверена` / `Есть расхождения` → `Завершена`.  
Отмена доступна до завершения. Просрочка — отдельный признак по плановой дате.

## Важно

`bcrypt==4.0.1` не обновляйте до 5.x.  
Не выполняйте `docker compose down -v`, если нужно сохранить данные.
