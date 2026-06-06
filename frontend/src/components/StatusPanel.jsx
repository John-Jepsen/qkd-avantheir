// Plain-language status. The old version showed UPPERCASE state machine
// names — useful for debugging, useless for noobs. This rewrites each
// state into a human sentence.

export default function StatusPanel({ status, generations, result, target, isSample }) {
  const latest = generations[generations.length - 1]

  let headline, sub, tone
  if (status === 'idle') {
    headline = isSample
      ? 'Showing a sample run'
      : 'Ready when you are'
    sub = isSample
      ? 'Click Run the demo on the left to replace this with your own results.'
      : 'Click Run the demo on the left to start.'
    tone = 'idle'
  } else if (status === 'evolving' || status === 'training') {
    headline = `Generation ${generations.length}${target ? ` of ${target}` : ''}`
    sub = 'Attackers searching for a way past the defender. Defender will retrain after.'
    tone = 'running'
  } else if (status === 'complete') {
    headline = 'Run complete'
    sub = result?.final_evasion_rate <= 0.15
      ? 'Defender held the line.'
      : 'Defender was broken — try tuning Advanced settings.'
    tone = result?.final_evasion_rate <= 0.15 ? 'win' : 'lose'
  } else if (status === 'error') {
    headline = 'Something went wrong'
    sub = 'Check the FastAPI logs at http://localhost:8000.'
    tone = 'error'
  }

  return (
    <div className="panel status-panel">
      <div className="panel-header">
        <span className="panel-title">What's happening</span>
      </div>

      <div className={`status-headline status-tone-${tone}`}>{headline}</div>
      <div className="status-sub">{sub}</div>

      {latest && (
        <div className="status-mini-grid">
          <div className="status-mini">
            <span className="status-mini-label">Caught by defender</span>
            <span className="status-mini-value team-blue-text">
              {Math.round((latest.defender_accuracy || 0) * 100)}%
            </span>
          </div>
          <div className="status-mini">
            <span className="status-mini-label">Slipped past</span>
            <span className="status-mini-value team-red-text">
              {Math.round((latest.evasion_rate || 0) * 100)}%
            </span>
          </div>
        </div>
      )}

      {result?.total_elapsed_s != null && status === 'complete' && (
        <div className="status-foot">Ran in {result.total_elapsed_s}s.</div>
      )}
    </div>
  )
}
