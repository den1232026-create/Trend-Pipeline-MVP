import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listTrends, refreshTrends } from "../api/client";
import { formatApiError } from "../api/errors";
import ErrorBanner from "../components/ErrorBanner";
import LoadingBlock from "../components/LoadingBlock";
import { useLocale } from "../i18n/LocaleContext";
import type { Trend } from "../types/contracts";

function signalLine(
  t: Trend,
  labels: { vel: string; rank: string; score: string }
): string {
  const parts: string[] = [];
  if (t.signals.upvote_velocity != null) {
    parts.push(`${labels.vel} ${Number(t.signals.upvote_velocity).toFixed(0)}`);
  }
  if (t.signals.rising_rank != null) {
    parts.push(`${labels.rank} #${t.signals.rising_rank}`);
  }
  if (t.signals.score != null) {
    parts.push(`${labels.score} ${t.signals.score}`);
  }
  return parts.join(" · ") || t.source;
}

function stageLabel(stage: Trend["stage"], t: (k: "stage_emerging" | "stage_rising" | "stage_peak") => string) {
  if (stage === "emerging") return t("stage_emerging");
  if (stage === "rising") return t("stage_rising");
  return t("stage_peak");
}

function typeLabel(
  type: Trend["trend_type"],
  t: (
    k: "type_face_swap" | "type_template_meme" | "type_ai_visual" | "type_other"
  ) => string
) {
  if (type === "face-swap") return t("type_face_swap");
  if (type === "template-meme") return t("type_template_meme");
  if (type === "ai-visual") return t("type_ai_visual");
  return t("type_other");
}

export default function TrendsPage() {
  const { t } = useLocale();
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTrends(await listTrends());
    } catch (e) {
      setError(formatApiError(e, t("loadTrendsFailed"), t));
      setTrends([]);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      await refreshTrends();
      setTrends(await listTrends());
    } catch (e) {
      setError(formatApiError(e, t("refreshFailed"), t));
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <section>
      <div className="hero-row">
        <div>
          <p className="eyebrow">{t("eyebrowTrends")}</p>
          <h1>{t("trendsTitle")}</h1>
          <p className="lede">{t("trendsLede")}</p>
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void onRefresh()}
          disabled={refreshing || loading}
        >
          {refreshing ? t("refreshing") : t("refresh")}
        </button>
      </div>

      <ErrorBanner message={error} />
      {loading && <LoadingBlock label={t("loadingTrends")} />}

      {!loading && !error && trends.length === 0 && (
        <p className="state empty">{t("emptyTrends")}</p>
      )}

      {!loading && trends.length > 0 && (
        <ul className="trend-grid">
          {trends.map((trend) => (
            <li key={trend.id}>
              <Link
                to={`/trends/${encodeURIComponent(trend.id)}`}
                className={`trend-card stage-${trend.stage}`}
              >
                <div className="trend-card-top">
                  <span className={`chip stage-${trend.stage}`}>
                    {stageLabel(trend.stage, t)}
                  </span>
                  <span className="chip quiet">{typeLabel(trend.trend_type, t)}</span>
                </div>
                <strong className="trend-title">{trend.title}</strong>
                <p className="trend-summary">{trend.summary}</p>
                <div className="trend-card-foot muted small">
                  {signalLine(trend, {
                    vel: t("vel"),
                    rank: t("rank"),
                    score: t("score"),
                  })}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
