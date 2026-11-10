export default function LoadingBlock({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading-block" aria-busy="true" aria-live="polite">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}
