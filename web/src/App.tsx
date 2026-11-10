import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { fixturesEnabled, getHealth } from "./api/client";
import { useLocale } from "./i18n/LocaleContext";
import type { Locale } from "./i18n/locales";
import SettingsPage from "./pages/SettingsPage";
import TrendDetailPage from "./pages/TrendDetailPage";
import TrendsPage from "./pages/TrendsPage";

export default function App() {
  const { t, locale, setLocale, locales } = useLocale();
  const [mockGenerate, setMockGenerate] = useState<boolean | null>(null);

  useEffect(() => {
    if (fixturesEnabled()) {
      setMockGenerate(true);
      return;
    }
    void getHealth()
      .then((h) => setMockGenerate(Boolean(h.mock_generate)))
      .catch(() => setMockGenerate(null));
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand-wrap">
          <Link to="/" className="brand">
            {t("brand")}
          </Link>
          <span className="muted small">{t("brandSub")}</span>
        </div>
        <div className="topbar-meta">
          <div className="lang-switch" role="group" aria-label={t("settingsLanguage")}>
            {locales.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={`lang-btn ${locale === opt.id ? "active" : ""}`}
                onClick={() => setLocale(opt.id as Locale)}
              >
                {opt.id.toUpperCase()}
              </button>
            ))}
          </div>
          <Link to="/settings" className="settings-link">
            {t("settings")}
          </Link>
          {fixturesEnabled() && <span className="badge badge-warn">{t("fixtures")}</span>}
          {mockGenerate === true && (
            <span className="badge badge-soft" title={t("apiMockTitle")}>
              {t("apiMock")}
            </span>
          )}
          {mockGenerate === false && (
            <span className="badge badge-live" title={t("apiLiveTitle")}>
              {t("apiLive")}
            </span>
          )}
        </div>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<TrendsPage />} />
          <Route path="/trends/:id" element={<TrendDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
