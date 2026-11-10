# trend-meme-pipeline

Тестовое для GPTunneL: **рано ловим визуальный тренд → автопресет на моделях Тоннеля → пользователь загружает лицо → готовый мем**.

Ориентир продукта: [gptunnel.ru/trends](https://gptunnel.ru/trends) (витрина трендов/пресетов).  
Устное ТЗ: три «морды» — парсер, автопайплайн, упакованный результат (+ backend/frontend).

Контракты: [`shared/contracts.md`](shared/contracts.md) · черновик ТЗ: [`TZ.md`](TZ.md) · статус: [`STATUS.md`](STATUS.md)

---

## Клон с GitHub

```powershell
git clone <url-репозитория> trend-meme-pipeline
cd trend-meme-pipeline
copy .env.example .env
# вставь GPTUNNEL_API_KEY, для демо: MOCK_GENERATE=0
```

Секреты только в локальном `.env` (в репозиторий не попадают). Runtime-файлы (`data/jobs`, лица, PNG) тоже игнорируются.

---

## Быстрый старт (с нуля)

### 1. Env

```powershell
cd "путь\к\trend-meme-pipeline"
copy .env.example .env
```

В `.env` заполни минимум:

| Переменная | Зачем |
|------------|--------|
| `GPTUNNEL_API_KEY` | ключ от Тимофея |
| `MOCK_GENERATE=0` | живая генерация (для демо); `1` = mock без списаний |
| `VITE_USE_FIXTURES=0` | UI ходит в живой API |

Опционально Reddit (`REDDIT_CLIENT_ID` / `SECRET` / `USER_AGENT`) — нужен аккаунт 18+. **Без Reddit** работает **seed**-fallback (3 демо-тренда), цепочка E2E не ломается.

`.env` в git не коммитить.

### 2. Три терминала

```powershell
# 1) Python :8000
cd python
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000

# 2) Node BFF :3001
cd node-api
npm install
npm run dev

# 3) Web :5173
cd web
npm install
npm run dev
```

Открыть: **http://localhost:5173/**  
(на Windows Vite слушает `localhost`, не всегда `127.0.0.1`)

### 3. Демо в UI (2 минуты)

1. **Обновить** — список трендов (seed или Reddit).  
2. Открыть карточку — референсы, why, LLM-brief.  
3. **Собрать / пересобрать пресет**.  
4. Загрузить **фото с лицом** → **Сгенерировать**.  
5. Бейдж **LIVE** = реальный GPTunnel; **MOCK** только при `MOCK_GENERATE=1` или ошибке при mock-режиме.

Язык UI: **RU | EN** в шапке или **Настройки**.

### 4. Smoke без UI

```powershell
python scripts/probe_gptunnel.py
powershell -File scripts/smoke_e2e.ps1
```

---

## Что сделано vs три «морды» Тимофея

| Морда | Требование | В проекте |
|-------|------------|-----------|
| 1. Парсер | Соцсети, рано, референсы, почему растёт | Модуль Trends: Reddit rising/hot + early_score/stage; без Reddit — seed. Референсы и why в карточке |
| 2. Автопайплайн | Сам пресет из тренда, модели Тоннеля, LLM | Pipeline: brief (chat) → Preset JSON (`faceswap` + сцена `flux-schnell`) |
| 3. Результат | Упаковано, лицо → мем, back+front | React UI + Node BFF + FastAPI; generate → PNG LIVE |

**Сознательные упрощения MVP (честно сказать на сдаче):**

- Результат — **картинка**, не видео (дешевле/быстрее в лимите ~500 ₽).  
- Источник трендов — Reddit API / seed, не прямой TikTok/Reels (ToS и возраст API).  
- «Вовремя» = refresh + rising/early heuristics, не круглосуточный кросс-платформенный крон в проде GPTunnel.  
- Это **отдельный демо-сервис**, не встройка в монолит gptunnel.ru.

---

## Структура

| Путь | Назначение |
|------|------------|
| `shared/` | контракты Trend / Preset / Job |
| `python/trends/` | ingest трендов |
| `python/pipeline/`, `gptunnel/`, `app.py` | пресет, generate, API `:8000` |
| `node-api/` | BFF `:3001` |
| `web/` | UI `:5173` |
| `data/` | runtime JSON + артефакты |

---

## Env (кратко)

См. [`.env.example`](.env.example).

- Chat: `GPTUNNEL_CHAT_MODEL` (по умолч. `gpt-4o-mini`)  
- Image: `GPTUNNEL_IMAGE_MODEL=faceswap`, сцена `GPTUNNEL_SCENE_MODEL=flux-schnell`  
- Media API: `GPTUNNEL_MEDIA_BASE_URL=https://gptunnel.ru/api/v2`

---

## Для ревьюеру

После правок пресетов всегда жми **Пересобрать пресет** в UI (старые JSON могли содержать placeholder `gptunnel/budget-*`).  
Для faceswap нужно фото **с видимым лицом**; иначе API вернёт ошибку (в live-режиме она показывается в UI, без тихого MOCK).
