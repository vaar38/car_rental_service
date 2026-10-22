# Бэкенд Car Rental Service

FastAPI + SQLAlchemy + PostgreSQL + Alembic. Команды ниже выполняются из папки `backend`.

## Запуск

```
python -m venv .venv
.venv\Scripts\activate            # Windows; на Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Создайте `backend/.env` по образцу `.env.example` и укажите `DATABASE_URL` и `SECRET_KEY`.

```
alembic upgrade head              # создать/обновить таблицы
uvicorn app.main:app --reload     # API на http://127.0.0.1:8000, Swagger на /docs
```

## Первый сотрудник

Регистрация через API даёт роль `client`. Чтобы получить доступ к админ-части,
зарегистрируйтесь и назначьте себя сотрудником:

```
python -m app.make_staff you@example.com
```

## Тесты

```
pip install -r requirements-dev.txt
pytest
```

Тесты используют базу из `DATABASE_URL` (или `TEST_DATABASE_URL`, если задана),
миграции должны быть применены. Каждый тест выполняется в транзакции,
которая откатывается, поэтому данные в базе не остаются.

## Правила бронирования

- Аренда минимум на 1 день: `end_date > start_date`, дней = `end_date - start_date`.
- День возврата свободен для следующего клиента (бронь 10→12 не мешает брони 12→14).
  В базе это гарантирует ограничение `no_overlapping_bookings` с диапазоном `[)`.
- Пересечение проверяется только с бронями в статусах `pending`, `confirmed`, `active`.
- Цена считается на сервере: `price_per_day × дни`; `user_id` и `total_price` из запроса игнорируются.
- Клиент видит и отменяет только свои брони; чужая бронь отвечает 404, как несуществующая.
- Отмена (`DELETE /api/bookings/{id}`) возможна в статусах `pending` и `confirmed`, запись остаётся со статусом `cancelled`.
- Сотрудник меняет статус через `PATCH /api/bookings/{id}`:
  `pending → confirmed | cancelled`, `confirmed → active | cancelled`, `active → completed`.
  При `active` машина получает статус `rented`, при `completed` — `available` и переезжает в пункт возврата.

## Каталог

- `GET /api/cars?start_date=...&end_date=...` добавляет к каждой машине признак `available`
  (не на обслуживании и нет пересекающейся активной брони).
- Госномер уникален, пробелы убираются, буквы приводятся к верхнему регистру.
- Машину с бронями удалить нельзя (409) — переведите её в `maintenance` через `PATCH`.
- Категорию или пункт выдачи, которые используются, удалить нельзя (409).
