"use client";

type WarningItem = {
  protocolId: string;
  label: string;
  warning: string;
  code?: string | null;
};

type Props = {
  warnings: WarningItem[];
};

export function BlackBoxWarning({ warnings }: Props) {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <section className="blackbox-shell" aria-live="polite" aria-label="Protocol rejection safety warnings">
      <h2>Black Box Warning</h2>
      <div className="blackbox-list">
        {warnings.map((item) => (
          <article key={item.protocolId} className="blackbox-item">
            <strong>{item.warning}</strong>
            <p>Protocol: {item.label}</p>
            {item.code ? <small>Code: {item.code}</small> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
