# Yandex Tracker MCP

Независимый MCP-сервер на Python для работы AI-ассистентов с REST API v3
Яндекс Трекера.

## Возможности

- получение и поиск задач;
- создание и обновление задач;
- чтение и добавление комментариев;
- получение очередей;
- просмотр и выполнение переходов статуса;
- полное управление пунктами чек-листа;
- чтение трудозатрат и отчёты по задаче, сотрудникам, очередям и периодам;
- OAuth- и IAM-аутентификация;
- поддержка организаций Яндекс 360 и Yandex Cloud.

Инструменты, изменяющие данные, явно требуют от MCP-клиента сначала показать
планируемое изменение и получить подтверждение пользователя.

## Быстрый запуск

Требуются Python 3.11+ и [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
# Заполните .env, затем:
uv sync
uv run yandex-tracker-mcp
```

Используйте ровно один способ аутентификации:

- `TRACKER_TOKEN` — OAuth-токен;
- `TRACKER_IAM_TOKEN` — IAM-токен.

И ровно один идентификатор организации:

- `TRACKER_ORG_ID` — организация Яндекс 360;
- `TRACKER_CLOUD_ORG_ID` — организация Yandex Cloud.

## Подключение к Cursor

Добавьте сервер в `.cursor/mcp.json` нужного проекта:

```json
{
  "mcpServers": {
    "yandex-tracker": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/Yandex-Tracker-MCP",
        "run",
        "yandex-tracker-mcp"
      ],
      "env": {
        "TRACKER_TOKEN": "${env:TRACKER_TOKEN}",
        "TRACKER_ORG_ID": "${env:TRACKER_ORG_ID}"
      }
    }
  }
}
```

Для Yandex Cloud замените `TRACKER_ORG_ID` на `TRACKER_CLOUD_ORG_ID`.
Не сохраняйте токены непосредственно в git.

## Инструменты

Read-only:

- `get_issue`
- `search_issues`
- `list_comments`
- `list_queues`
- `list_transitions`
- `get_checklist`
- `list_worklogs`
- `get_issue_time_report`
- `get_time_report`

Изменяющие данные:

- `create_issue`
- `update_issue`
- `add_comment`
- `execute_transition`
- `add_checklist_item`
- `update_checklist_item`
- `delete_checklist_item`

### Чек-листы

`get_checklist` возвращает идентификаторы пунктов, необходимые для изменения и
удаления. Пункты поддерживают текст, отметку выполнения, исполнителя и deadline.
Для снятия исполнителя или срока используйте `clear_assignee` или
`clear_deadline` в `update_checklist_item`.

### Анализ времени

`get_issue_time_report` строит отчёт по одной задаче: первоначальная и текущая
оценка, сумма worklog-записей, отклонение и разбивка по сотрудникам и дням.

`get_time_report` принимает запрос на языке Трекера и может ограничить отчёт
датами `date_from` / `date_to` в формате `YYYY-MM-DD`. Например:

```text
Покажи затраты команды по Queue: "BACKEND" с 2026-09-01 по 2026-09-30,
с разбивкой по сотрудникам и задачам.
```

Трекер хранит worklog в ISO 8601 (`PT1H30M`). Сервер приводит все длительности
к минутам, считая рабочий день равным 8 часам, а рабочую неделю — 40 часам.
Один отчёт обрабатывает не более 200 задач и 500 worklog-записей на задачу;
при достижении лимита ответ содержит `truncated: true`.

## Разработка

```bash
uv sync --group dev
uv run ruff check .
uv run mypy
uv run pytest
```

## Официальная документация

- [Общий формат REST API v3](https://yandex.ru/support/tracker/ru/api-ref/common-format)
- [Доступ и аутентификация](https://yandex.ru/support/tracker/ru/api-ref/access)
- [Создание задачи](https://yandex.ru/support/tracker/ru/api-ref/issues/create-issue)
- [Поиск задач](https://yandex.ru/support/tracker/ru/api-ref/issues/search-issues)
- [Поля задач](https://yandex.ru/support/tracker/ru/api-ref/issues/request-fields)
- [Комментарии](https://yandex.ru/support/tracker/ru/api-ref/comments/)
- [Переходы между статусами](https://yandex.ru/support/tracker/ru/api-ref/issues/get-transitions)
- [Получить чек-лист](https://yandex.ru/support/tracker/ru/api-ref/issues/get-checklist)
- [Добавить пункт чек-листа](https://yandex.ru/support/tracker/ru/api-ref/issues/add-checklist-item)
- [Трудозатраты задачи](https://yandex.ru/support/tracker/ru/api-ref/issues/issue-worklog)
- [Поиск трудозатрат](https://yandex.ru/support/tracker/ru/api-ref/issues/get-worklog)

API base URL: `https://api.tracker.yandex.net/v3`.

## Происхождение

Проект реализован с собственной историей и структурой на основе официальной
документации Яндекс Трекера и Model Context Protocol. В качестве архитектурного
референса изучался Apache-2.0 проект
[`aikts/yandex-tracker-mcp`](https://github.com/aikts/yandex-tracker-mcp);
его git-история и исходный код в этот репозиторий не переносились.

## Лицензия

[MIT](LICENSE)
