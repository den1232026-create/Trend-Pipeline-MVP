import { Link } from "react-router-dom";
import { useLocale } from "../i18n/LocaleContext";
import type { Locale } from "../i18n/locales";

export default function SettingsPage() {
  const { locale, setLocale, t, locales } = useLocale();

  return (
    <section className="settings">
      <Link to="/" className="back">
        {t("backHome")}
      </Link>
      <h1>{t("settingsTitle")}</h1>

      <div className="settings-card">
        <h2>{t("settingsLanguage")}</h2>
        <p className="muted lede">{t("settingsLanguageHint")}</p>
        <div className="lang-options" role="radiogroup" aria-label={t("settingsLanguage")}>
          {locales.map((opt) => (
            <label key={opt.id} className={`lang-option ${locale === opt.id ? "active" : ""}`}>
              <input
                type="radio"
                name="locale"
                value={opt.id}
                checked={locale === opt.id}
                onChange={() => setLocale(opt.id as Locale)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}
