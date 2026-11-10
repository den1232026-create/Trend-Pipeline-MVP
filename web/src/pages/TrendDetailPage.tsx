import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  buildPreset,
  jobResultImageUrl,
  findPresetForTrend,
  generate,
  getTrend,
  pollJob,
} from "../api/client";
import { formatApiError } from "../api/errors";
import ErrorBanner from "../components/ErrorBanner";
import LoadingBlock from "../components/LoadingBlock";
import { useLocale } from "../i18n/LocaleContext";
import type { Job, Preset, Trend } from "../types/contracts";

function stageLabel(
  stage: Trend["stage"],
  t: (k: "stage_emerging" | "stage_rising" | "stage_peak") => string
) {
  if (stage === "emerging") return t("stage_emerging");
  if (stage === "rising") return t("stage_rising");
  return t("stage_peak");
}

export default function TrendDetailPage() {
  const { t } = useLocale();
  const { id = "" } = useParams();
  const [trend, setTrend] = useState<Trend | null>(null);
  const [preset, setPreset] = useState<Preset | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [face, setFace] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [imgError, setImgError] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const jobBusy = job?.status === "queued" || job?.status === "running";
  const busy = building || generating || jobBusy;

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const next = await getTrend(id);
      setTrend(next);
      const existing = await findPresetForTrend(id);
      setPreset(existing);
    } catch (e) {
      setError(formatApiError(e, t("loadTrendFailed"), t));
      setTrend(null);
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  async function onBuildPreset() {
    if (!id || busy) return;
    setBuilding(true);
    setError(null);
    try {
      const p = await buildPreset(id);
      setPreset(p);
      const refreshed = await getTrend(id);
      setTrend(refreshed);
    } catch (e) {
      setError(formatApiError(e, t("buildPresetFailed"), t));
    } finally {
      setBuilding(false);
    }
  }

  async function onGenerate() {
    if (!preset || !face || busy) {
      if (!face) setError(t("chooseFaceFirst"));
      return;
    }
    setGenerating(true);
    setError(null);
    setJob(null);
    setImgError(false);
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      let current = await generate(preset.id, face);
      setJob(current);
      if (current.status !== "done" && current.status !== "error") {
        current = await pollJob(current.id, setJob, ac.signal);
      }
      setJob(current);
      if (current.status === "error") {
        setError(current.error || t("generationFailed"));
      }
    } catch (e) {
      if (e instanceof Error && e.message === "aborted") return;
      setError(formatApiError(e, t("generateFailed"), t));
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <section>
        <Link to="/" className="back">
          {t("backTrends")}
        </Link>
        <LoadingBlock label={t("loadingTrend")} />
      </section>
    );
  }

  if (!trend) {
    return (
      <div>
        <Link to="/" className="back">
          {t("backTrends")}
        </Link>
        <ErrorBanner message={error || t("trendNotFound")} />
      </div>
    );
  }

  const showMockBadge = job?.mocked === true;
  const showLiveBadge = job?.status === "done" && job.mocked === false;

  return (
    <section className="detail">
      <Link to="/" className="back">
        {t("backTrends")}
      </Link>
      <p className="eyebrow">
        {trend.source} · {trend.trend_type}
      </p>
      <h1>{trend.title}</h1>
      <p className="lede">{trend.summary}</p>
      <div className="meta">
        <span className={`chip stage-${trend.stage}`}>{stageLabel(trend.stage, t)}</span>
        {trend.signals.upvote_velocity != null && (
          <span className="chip quiet">
            {t("vel")} {Number(trend.signals.upvote_velocity).toFixed(0)}
          </span>
        )}
        {trend.signals.rising_rank != null && (
          <span className="chip quiet">
            {t("rank")} #{trend.signals.rising_rank}
          </span>
        )}
      </div>

      <ErrorBanner message={error} />

      <h2>{t("whyTrending")}</h2>
      <p>{trend.why_trending}</p>

      {trend.llm_brief && (
        <>
          <h2>{t("llmBrief")}</h2>
          <p>{trend.llm_brief}</p>
        </>
      )}

      <h2>{t("references")}</h2>
      {trend.references.length === 0 ? (
        <p className="state empty">{t("noReferences")}</p>
      ) : (
        <ul className="refs">
          {trend.references.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noreferrer">
                {r.title}
              </a>
              <span className="muted small">
                {" "}
                {t("score")} {r.score}
              </span>
            </li>
          ))}
        </ul>
      )}

      <h2>{t("signals")}</h2>
      <dl className="signal-grid">
        {Object.entries(trend.signals).map(([key, value]) =>
          value == null ? null : (
            <div key={key} className="signal-item">
              <dt>{key}</dt>
              <dd>{String(value)}</dd>
            </div>
          )
        )}
      </dl>

      <div className="row between block">
        <h2>{t("preset")}</h2>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void onBuildPreset()}
          disabled={busy}
        >
          {building ? t("building") : preset ? t("rebuildPreset") : t("buildPreset")}
        </button>
      </div>

      {!preset && !building && <p className="state empty">{t("noPreset")}</p>}
      {building && <LoadingBlock label={t("buildingPreset")} />}

      {preset && (
        <div className="preset">
          <h3>{preset.title}</h3>
          <p className="muted">{preset.pipeline_rationale}</p>
          <p className="small">
            {t("estCost")}: <strong>{preset.est_cost_rub} ₽</strong> · {t("output")}:{" "}
            {preset.output_type}
          </p>
          <h4>{t("steps")}</h4>
          <ol>
            {preset.steps.map((s, i) => (
              <li key={`${s.model}-${i}`}>
                <code>{s.model}</code>
                <div className="small">{s.prompt}</div>
              </li>
            ))}
          </ol>
          <h4>{t("userInputs")}</h4>
          <ul>
            {preset.user_inputs.map((u) => (
              <li key={u.name}>
                {u.name} ({u.type})
                {u.required ? " *" : ""}
              </li>
            ))}
          </ul>

          <h4>{t("generate")}</h4>
          <div className="generate">
            <label className={`file-pick ${busy ? "disabled" : ""}`}>
              <span>{face ? face.name : t("chooseFace")}</span>
              <input
                type="file"
                accept="image/*"
                disabled={busy}
                onChange={(e) => setFace(e.target.files?.[0] ?? null)}
              />
            </label>
            <button
              type="button"
              className="btn-primary"
              onClick={() => void onGenerate()}
              disabled={busy || !face}
            >
              {generating || jobBusy
                ? `${t("jobLabel")}: ${job?.status || t("starting")}…`
                : t("generate")}
            </button>
          </div>
          {jobBusy && <LoadingBlock label={t("waitingJob")} />}
        </div>
      )}

      {job && (
        <div className="result">
          <div className="row">
            <h2>{t("result")}</h2>
            {showMockBadge && <span className="badge badge-mock">{t("mock")}</span>}
            {showLiveBadge && <span className="badge badge-live">{t("live")}</span>}
            <span className="chip">{job.status}</span>
          </div>
          {job.error && <ErrorBanner message={job.error} />}
          {job.status === "done" && jobResultImageUrl(job) && !imgError && (
            <img
              className="result-img"
              src={jobResultImageUrl(job) || undefined}
              alt={t("generatedAlt")}
              onError={() => {
                setImgError(true);
                setError(
                  `${t("artifactNotFound")}: ${job.output_path || job.output_url || ""}`
                );
              }}
            />
          )}
        </div>
      )}
    </section>
  );
}
