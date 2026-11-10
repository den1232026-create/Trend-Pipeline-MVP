# Shared contracts — Trend → Meme Pipeline

Источник правды для Trends / Pipeline / App. Менять только через оркестратора.

## Trend

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | e.g. `reddit_memes_abc123` |
| `title` | string | |
| `summary` | string | short format description |
| `source` | `"reddit"` | |
| `references` | Reference[] | at least 1 |
| `signals` | object | see below |
| `stage` | `"emerging"` \| `"rising"` \| `"peak"` | |
| `trend_type` | `"face-swap"` \| `"template-meme"` \| `"ai-visual"` \| `"other"` | |
| `why_trending` | string | heuristics OK from Trends |
| `llm_brief` | string \| null | **null from Trends**; Pipeline fills on build-preset |

### Reference

| Field | Type |
|-------|------|
| `url` | string |
| `title` | string |
| `score` | number |
| `created_utc` | number |

### signals (recommended keys)

`score`, `num_comments`, `upvote_ratio`, `rising_rank`, `upvote_velocity` (numbers; missing keys OK as null/omit).

---

## Preset

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | MVP: `preset_{trend_id}` |
| `trend_id` | string | |
| `title` | string | |
| `user_inputs` | UserInput[] | include `face_image` |
| `steps` | Step[] | 1–2 for MVP |
| `output_type` | `"image"` | |
| `est_cost_rub` | number | rough |
| `pipeline_rationale` | string | why these steps |

### UserInput

`name` (string), `type` (`"image"` \| `"text"`), `required` (boolean)

### Step

`model` (string, placeholder OK e.g. `gptunnel/budget-image-v1`), `prompt` (string), `params` (object)

---

## Job

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | uuid or `job_{ts}` |
| `preset_id` | string | |
| `status` | `"queued"` \| `"running"` \| `"done"` \| `"error"` | |
| `input_paths` | object | e.g. `{ "face_image": "..." }` |
| `output_path` | string \| null | relative under artifacts, e.g. `{job_id}.png` |
| `output_url` | string \| null | optional CDN URL if local download failed but generation succeeded |
| `error` | string \| null | |
| `mocked` | boolean | **true** if mock generate |

---

## Storage layout

```
data/trends/{id}.json      # one file per trend
data/presets/{id}.json
data/jobs/{id}.json
data/artifacts/{job_id}.png
```

---

## HTTP

### Python `:8000` (no `/api` prefix)

| Method | Path | Owner |
|--------|------|--------|
| GET | `/health` | Pipeline app |
| GET | `/trends` | → trends.list_trends |
| GET | `/trends/{id}` | → trends.get_trend |
| POST | `/trends/refresh` | → trends.refresh |
| POST | `/trends/{id}/build-preset` | Pipeline |
| GET | `/presets` | Pipeline |
| GET | `/presets/{id}` | Pipeline |
| POST | `/generate` | multipart: `face` file + `preset_id` form field |
| GET | `/jobs/{id}` | Pipeline |
| GET | `/artifacts/{name}` | Pipeline (optional; Node also serves) |

### Node BFF `:3001` prefix `/api`

Same paths with `/api` prefix; proxies to Python except `GET /api/artifacts/*` may be served from `DATA_DIR/artifacts` on disk.

### Env

See root `.env.example`. Stage 1: `MOCK_GENERATE=1`.

---

## Examples

See `shared/examples/trend.json`, `preset.json`, `job.json`.
