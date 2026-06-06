import { useEffect, useState } from 'react'

const DISMISS_KEY = 'qkd-welcome-dismissed-v1'

export default function WelcomeHero({ forceOpen, onClose, onRunDemo }) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (forceOpen) {
      setOpen(true)
      return
    }
    const dismissed = window.localStorage.getItem(DISMISS_KEY)
    if (!dismissed) setOpen(true)
  }, [forceOpen])

  const close = () => {
    setOpen(false)
    window.localStorage.setItem(DISMISS_KEY, '1')
    onClose && onClose()
  }

  if (!open) return null

  return (
    <div className="hero-backdrop" onClick={close}>
      <div className="hero-card" onClick={e => e.stopPropagation()}>
        <button className="hero-close" onClick={close} aria-label="Close">×</button>
        <div className="hero-eyebrow">QKD ADVERSARIAL BENCHMARK</div>
        <h2 className="hero-title">Can our defender catch a moving target?</h2>
        <p className="hero-body">
          <strong>Quantum Key Distribution</strong> promises perfect secrecy. We
          built an ML detector that watches for eavesdroppers. This dashboard
          pits <span className="team-red-text">red-team attackers</span> against
          our <span className="team-blue-text">blue-team defender</span> — the
          attackers evolve, the defender retrains, repeat.
        </p>
        <ul className="hero-bullets">
          <li><span className="hero-bullet-dot" /> Attackers try to slip past the eavesdrop detector.</li>
          <li><span className="hero-bullet-dot" /> Defender sees the new attacks and hardens.</li>
          <li><span className="hero-bullet-dot" /> You watch who's winning, generation by generation.</li>
        </ul>
        <button
          className="hero-cta"
          onClick={() => { close(); onRunDemo && onRunDemo() }}
        >
          Run the demo (~30 seconds)
        </button>
        <button className="hero-secondary" onClick={close}>
          Skip — show me the sample run first
        </button>
      </div>
    </div>
  )
}
