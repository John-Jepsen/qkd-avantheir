export default function ModelConfidence({ generations, status }) {
  const latest = generations[generations.length - 1]

  const models = [
    { name: 'RF Eavesdrop', key: 'defender_accuracy', color: 'var(--blue)' },
  ]

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Model Confidence</span>
      </div>
      {!latest ? (
        <div className="empty-state" style={{ padding: '16px' }}>Models not loaded</div>
      ) : (
        <div>
          <div className="confidence-bar">
            <span className="confidence-bar-label">Defender Acc</span>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{
                width: `${(latest.defender_accuracy || 0) * 100}%`,
                backgroundColor: 'var(--blue)',
              }} />
            </div>
            <span className="confidence-bar-value">{((latest.defender_accuracy || 0) * 100).toFixed(0)}%</span>
          </div>
          <div className="confidence-bar">
            <span className="confidence-bar-label">Evasion Rate</span>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{
                width: `${(latest.evasion_rate || 0) * 100}%`,
                backgroundColor: 'var(--red)',
              }} />
            </div>
            <span className="confidence-bar-value">{((latest.evasion_rate || 0) * 100).toFixed(0)}%</span>
          </div>
          <div className="confidence-bar">
            <span className="confidence-bar-label">Best Fitness</span>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{
                width: `${(latest.best_fitness || 0) * 100}%`,
                backgroundColor: 'var(--yellow)',
              }} />
            </div>
            <span className="confidence-bar-value">{((latest.best_fitness || 0) * 100).toFixed(0)}%</span>
          </div>
          <div className="confidence-bar">
            <span className="confidence-bar-label">Avg Fitness</span>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{
                width: `${(latest.avg_fitness || 0) * 100}%`,
                backgroundColor: 'var(--purple)',
              }} />
            </div>
            <span className="confidence-bar-value">{((latest.avg_fitness || 0) * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </div>
  )
}
