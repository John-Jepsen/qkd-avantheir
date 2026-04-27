export default function StatusPanel({ status, generations, result }) {
  const latest = generations[generations.length - 1]

  const statusColor = {
    idle: 'var(--text-secondary)',
    training: 'var(--yellow)',
    evolving: 'var(--yellow)',
    complete: 'var(--green)',
    error: 'var(--red)',
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Status</span>
        <span className="data-value" style={{ color: statusColor[status] || 'var(--text-secondary)' }}>
          {status.toUpperCase()}
        </span>
      </div>

      <div className="status-item">
        <span className="status-label">Generations</span>
        <span className="status-value">{generations.length}</span>
      </div>

      {latest && (
        <>
          <div className="status-item">
            <span className="status-label">Best Evasion</span>
            <span className="status-value" style={{ color: 'var(--red)' }}>
              {(latest.evasion_rate * 100).toFixed(1)}%
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Avg Fitness</span>
            <span className="status-value">
              {latest.avg_fitness.toFixed(3)}
            </span>
          </div>
        </>
      )}

      {result && (
        <>
          <div className="status-item">
            <span className="status-label">Phylogeny Nodes</span>
            <span className="status-value">{result.phylogeny?.total_nodes || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Total Time</span>
            <span className="status-value">{result.total_elapsed_s}s</span>
          </div>
        </>
      )}
    </div>
  )
}
