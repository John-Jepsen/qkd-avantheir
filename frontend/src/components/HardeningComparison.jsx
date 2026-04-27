export default function HardeningComparison({ result, evalResult, status }) {
  const data = evalResult || (result ? {
    before: { evasion_rate: result.initial_evasion_rate, accuracy: null },
    after: { evasion_rate: result.final_evasion_rate, accuracy: result.final_defender_accuracy },
    improvement: result.initial_evasion_rate - result.final_evasion_rate,
    hardening_effective: result.final_evasion_rate < result.initial_evasion_rate,
  } : null)

  if (!data) {
    return (
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Hardening Comparison</span>
        </div>
        <div className="empty-state">Complete an evolution first</div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Hardening Comparison</span>
        <span className="data-value" style={{
          color: data.hardening_effective ? 'var(--green)' : 'var(--red)',
        }}>
          {data.hardening_effective ? 'EFFECTIVE' : 'INEFFECTIVE'}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 8 }}>BEFORE</div>
          <div className="status-item">
            <span className="status-label">Evasion</span>
            <span className="status-value" style={{ color: 'var(--red)' }}>
              {(data.before.evasion_rate * 100).toFixed(1)}%
            </span>
          </div>
          {data.before.accuracy != null && (
            <div className="status-item">
              <span className="status-label">Accuracy</span>
              <span className="status-value">{(data.before.accuracy * 100).toFixed(1)}%</span>
            </div>
          )}
        </div>
        <div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 8 }}>AFTER</div>
          <div className="status-item">
            <span className="status-label">Evasion</span>
            <span className="status-value" style={{ color: 'var(--green)' }}>
              {(data.after.evasion_rate * 100).toFixed(1)}%
            </span>
          </div>
          {data.after.accuracy != null && (
            <div className="status-item">
              <span className="status-label">Accuracy</span>
              <span className="status-value">{(data.after.accuracy * 100).toFixed(1)}%</span>
            </div>
          )}
        </div>
      </div>
      <div style={{ marginTop: 12, textAlign: 'center' }}>
        <span className="data-value" style={{ color: 'var(--blue)', fontSize: 16 }}>
          {data.improvement > 0 ? '-' : '+'}{(Math.abs(data.improvement) * 100).toFixed(1)}% evasion
        </span>
      </div>
    </div>
  )
}
