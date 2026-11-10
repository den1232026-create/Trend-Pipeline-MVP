# STATUS — Trend → Meme Pipeline

Оркестратор обновляет шапку. Воркеры дописывают **свою** секцию в конце смены (5 строк).

## Orchestrator

- Сделал: этап 2 **проверен live** — probe OK; `flux-schnell` OK; `faceswap` OK при реальном лице; curl-fallback скачивания CDN; `MOCK_GENERATE=0`; pipeline job `mocked=false`
- Путь: `python/gptunnel/client.py`, artifacts `smoke_real_*`, `job_48bc6f277b82.png`
- Блокер: нет. Замечание: PNG без лица → faceswap `ERR_NO_FACE_FOUND` (нужно фото с видимым лицом)
- Следующее: сдача / демо Тимофею; `.env` и артефакты в git не коммитить

---

## Trends

- Сделал: этап 2 early-catch — rising-first + age≤48h, `early_score`/stage bias emerging→rising, replace `data/trends` на refresh; seed-fallback без REDDIT_*; `llm_brief` всегда null; API `refresh/list_trends/get_trend` без изменений контракта
- Путь: `python/trends/`, `data/trends/`
- Команда: `PYTHONPATH=python python -m trends refresh` (из корня) или `cd python && python -m trends refresh`
- Env: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, опц. `REDDIT_SUBREDDITS`, `DATA_DIR`
- Блокер: в `.env` пустые `REDDIT_CLIENT_ID`/`SECRET` → пока seed; живой rising после заполнения Reddit OAuth

## Pipeline

- Сделал: этап 2 — CreativeLab media (`/api/v2/media/tasks` + poll/download), chat-brief (`gpt-4o-mini`), image `faceswap` (+ scene `flux-1-dev`), `resolve_models` из каталога; preset с реальными model id; без ключа/ошибка API → mock (`mocked:true`)
- Путь: `python/app.py`, `python/pipeline/`, `python/gptunnel/`
- Команда: `cd python && uvicorn app:app --host 127.0.0.1 --port 8000`
- Env: `MOCK_GENERATE`, `GPTUNNEL_API_KEY`, `GPTUNNEL_BASE_URL`, `GPTUNNEL_MEDIA_BASE_URL`, `GPTUNNEL_CHAT_MODEL`, `GPTUNNEL_IMAGE_MODEL`, `GPTUNNEL_SCENE_MODEL`, `GPTUNNEL_USE_WALLET`, `DATA_DIR`
- Блокер: нет при заполненном `GPTUNNEL_API_KEY` + `MOCK_GENERATE=0`; без ключа — mock

## App

- Сделал: этап 2 — витрина-грид трендов (stage/signals), loading/spinner + ErrorBanner, disabled при running/building, MOCK badge только при `job.mocked===true` (+ LIVE если false), header chip API mock/live из `/health`, network/FastAPI error text, upload errors в BFF; Vite `envDir=..` → корневой `.env`, live E2E с `VITE_USE_FIXTURES=0`
- Путь: `node-api/`, `web/`
- Команды: `cd node-api && npm run dev` (:3001); `cd web && npm run dev` (:5173)
- Env: `PORT`, `PYTHON_BASE_URL`, `DATA_DIR`; web: `VITE_API_BASE_URL=/api`, `VITE_USE_FIXTURES=0`
- Блокер: нет на стороне App; real image зависит от Pipeline `MOCK_GENERATE=0` + ключ в корневом `.env`
