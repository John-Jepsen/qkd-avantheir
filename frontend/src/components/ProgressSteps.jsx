// Reflects the orchestration of one Run Demo invocation.
// We don't get explicit step events from the backend yet, so this infers
// the current step from the high-level status + generation count.

const STEPS = [
  { key: 'training', label: 'Training models' },
  { key: 'spawn', label: 'Spawning attackers' },
  { key: 'evaluate', label: 'Evaluating' },
  { key: 'harden', label: 'Hardening defender' },
  { key: 'done', label: 'Done' },
]

export default function ProgressSteps({ status, generations, total, queueSize = 0 }) {
  if (status === 'idle' || status === 'error') return null

  let activeKey
  if (status === 'complete') activeKey = 'done'
  else if (generations.length === 0) activeKey = 'training'
  else if (generations.length < total) activeKey = generations.length % 2 === 1 ? 'evaluate' : 'harden'
  else activeKey = 'harden'

  const activeIdx = STEPS.findIndex(s => s.key === activeKey)

  return (
    <div className="progress-steps">
      {STEPS.map((s, i) => (
        <div
          key={s.key}
          className={`progress-step ${i < activeIdx ? 'done' : ''} ${i === activeIdx ? 'active' : ''}`}
        >
          <span className="progress-step-dot">{i < activeIdx ? '✓' : i + 1}</span>
          <span className="progress-step-label">{s.label}</span>
        </div>
      ))}
      {status === 'evolving' && total > 0 && (
        <div className="progress-counter">
          Generation {generations.length} of {total}
          {queueSize > 0 && (
            <span className="progress-queue">+{queueSize} queued for replay</span>
          )}
        </div>
      )}
    </div>
  )
}
