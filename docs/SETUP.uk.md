# Налаштування Token Tracker на іншому комп'ютері

[English](SETUP.md)

Усе нижче виконується на тій машині, чию статистику Claude Code ви хочете бачити. Token Tracker
читає логи з диска цієї машини, тому не може показати використання з іншого комп'ютера.

## 1. Вимоги

| Що | Версія | Перевірка | Для чого |
| --- | --- | --- | --- |
| Git | будь-яка | `git --version` | клонування |
| Python | 3.11 або новіший | `python3 --version` | бекенд |
| Node.js + npm | 22 (20.19+ теж підійде) | `node -v` | одноразова збірка дашборду |
| Claude Code | будь-яка, вже використовувався на цій машині | `ls ~/.claude/projects` | джерело даних |
| `claude` CLI у `PATH` | будь-яка | `claude --version` | необов'язково: ліміти підписки |

Працює на macOS і Linux. На Windows використовуйте WSL.

## 2. Встановлення

```bash
git clone https://github.com/YuriyTikhonoff/token-tracker.git
cd token-tracker

python3 -m venv .venv
.venv/bin/pip install -e backend

cd frontend
npm ci
npm run build:package      # збирає дашборд усередину Python-пакета
cd ..
```

Node.js потрібен лише для цього кроку збірки. Коли бандл існує, застосунок працює на самому Python.

## 3. Завантаження даних і відкриття дашборду

```bash
.venv/bin/token-tracker ingest     # читає ~/.claude/projects/**/*.jsonl у локальний SQLite-файл
.venv/bin/token-tracker serve      # потім відкрийте http://127.0.0.1:8765
```

Перший `ingest` може тривати довго, якщо історія велика. Наступні запуски читають лише нове.
Натисніть **Refresh** у дашборді або знову запустіть `ingest`, щоб підтягнути свіжу активність.

## 4. Щоденний запуск

```bash
.venv/bin/token-tracker run        # читає нову активність і запускає дашборд
```

Щоб запускати з будь-якої теки, додайте alias (змініть шлях на свій):

```bash
echo "alias token-tracker='$PWD/.venv/bin/token-tracker run'" >> ~/.zshrc
```

Або `source backend/aliases.sh` (див. розділ 6): він дає `tt-open` з тим самим ефектом.

## 5. Перевірка

```bash
.venv/bin/token-tracker doctor
```

Усі рядки мають бути `[ok]` або `[info]`. Рядок `[FAIL]` каже, чого бракує, а команда завершується
з ненульовим кодом. Типові виправлення:

| Повідомлення | Що робити |
| --- | --- |
| Claude Code transcripts: none found | Спочатку попрацюйте з Claude Code на цій машині або задайте `CLAUDE_CONFIG_DIR`, якщо конфіг не в `~/.claude` |
| claude CLI on PATH (показано як `FAIL`) | Встановіть Claude Code або проігноруйте: лише смужкам лімітів підписки потрібен CLI |
| web dashboard: not bundled in this checkout | Виконайте `npm run build:package` у `frontend/` |
| database ... does not exist yet | Виконайте `token-tracker ingest` |

## 6. Необов'язково

- **Кілька акаунтів на одній машині:** `.venv/bin/token-tracker install-hooks` (з `--dry-run` лише
  покаже зміни). Команда редагує `~/.claude/settings.json` і лишає резервну копію з часовою міткою.
- **Автоматичне оновлення:** `backend/watch.sh` для циклу в терміналі або macOS-агент у
  `backend/launchd/`.
- **Короткі команди в шеллі:** `echo "source $PWD/backend/aliases.sh" >> ~/.zshrc`.
- **Використання Codex CLI:** `.venv/bin/token-tracker codex`, див. [CODEX.md](../CODEX.md).
- **Віджет поверх усіх вікон (macOS):** [widgets/hammerspoon](../widgets/hammerspoon/README.md).

## 7. Конфігурація

Задайте змінну середовища або ключ у `~/.token-tracker/config.toml`.

| Що | Змінна середовища | Типово |
| --- | --- | --- |
| Каталог даних | `TOKEN_TRACKER_HOME` | `~/.token-tracker` |
| Каталог Claude Code | `CLAUDE_CONFIG_DIR` | `~/.claude` |
| Часовий пояс (назва IANA, напр. `Europe/Kyiv`) | `TOKEN_TRACKER_TZ` | системний пояс |
| Порт | `serve --port N` | 8765 |

Після змін перезапустіть `serve`. Якщо використовуєте власний `CLAUDE_CONFIG_DIR`, експортуйте те
саме значення в кожному шеллі, що запускає `ingest` або `serve`.

## 8. Безпека

- API не має авторизації. Лишайте типовий `127.0.0.1` і не передавайте `--host 0.0.0.0` у спільній
  чи публічній мережі.
- База містить кількості токенів, назви моделей, назви папок проєктів, часові мітки та перші 200
  символів кожного промпту. Вважайте `~/.token-tracker/token_tracker.db` приватним файлом.

## 9. Перенесення наявної історії на нову машину

Лише якщо потрібні старі цифри, а не тільки свіжі. Скопіюйте файл бази
(`~/.token-tracker/token_tracker.db`) у каталог даних нової машини до першого `ingest`. Без нього
нова машина почне з того, що є в її власному `~/.claude`.

## 10. Оновлення або видалення

```bash
git pull
.venv/bin/pip install -e backend
(cd frontend && npm ci && npm run build:package)
```

Щоб видалити: `.venv/bin/token-tracker uninstall-hooks`, якщо ставили хуки, потім видаліть
каталог із клоном і `~/.token-tracker`.

## Вирішення проблем

- **Порожня сторінка або «dashboard not built»:** немає бандла, виконайте `npm run build:package`.
- **Порт зайнятий:** `serve --port 8766`.
- **`npm ci` падає:** перевірте `node -v`; використовуйте Node 22 (npm 10).
- **Порожній дашборд:** запустіть `ingest`, потім перевірте рядок про транскрипти в `doctor`.
- **Неправильний час:** задайте `TOKEN_TRACKER_TZ`.
