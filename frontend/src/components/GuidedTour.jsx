import { useEffect, useState, useRef } from 'react'

const DISMISS_KEY = 'qkd-tour-dismissed-v1'

const STEPS = [
  {
    selector: '[data-tour="controls"]',
    title: 'Step 1 — Set the rules',
    body: 'Population, generations, and how hard the attackers fight. Defaults are sane. Just hit Run the demo and watch.',
  },
  {
    selector: '[data-tour="battle"]',
    title: 'Step 2 — Watch the battle',
    body: 'Red dots are attackers trying to cross the blue defender line. Higher means closer to fooling the detector. Use the Pace controls if it moves too fast.',
  },
  {
    selector: '[data-tour="result"]',
    title: 'Step 3 — See who won',
    body: 'A green ✅ banner means the defender held the line. A yellow ⚠️ means the attackers broke through — tune up the hardening mix and try again.',
  },
]

export default function GuidedTour({ forceStart }) {
  const [step, setStep] = useState(-1)
  const [rect, setRect] = useState(null)
  const retryRef = useRef(null)

  // Auto-start logic. If forceStart prop changes (key bumped from parent's
  // Tour button), kick off the tour. Otherwise on first visit, wait for the
  // Welcome modal to be dismissed before starting.
  useEffect(() => {
    if (forceStart) {
      setStep(0)
      return
    }
    const tourDismissed = window.localStorage.getItem(DISMISS_KEY)
    if (tourDismissed) return

    const interval = setInterval(() => {
      const welcomeDismissed = window.localStorage.getItem('qkd-welcome-dismissed-v1')
      if (welcomeDismissed) {
        setStep(0)
        clearInterval(interval)
      }
    }, 400)
    return () => clearInterval(interval)
  }, [forceStart])

  // Resolve the target rect for the current step. Retry every 300ms until
  // we find it — the result panel only mounts once a run completes (or the
  // sample loads), so step 3 may not have a target right away.
  useEffect(() => {
    if (retryRef.current) {
      clearInterval(retryRef.current)
      retryRef.current = null
    }
    if (step < 0) return

    const tryResolve = () => {
      const target = document.querySelector(STEPS[step].selector)
      if (target) {
        const r = target.getBoundingClientRect()
        setRect({ top: r.top + window.scrollY, left: r.left, width: r.width, height: r.height })
        target.scrollIntoView({ behavior: 'smooth', block: 'center' })
        return true
      }
      return false
    }

    if (tryResolve()) return

    // Target missing — show centered fallback, but keep trying.
    setRect(null)
    retryRef.current = setInterval(() => {
      if (tryResolve()) {
        clearInterval(retryRef.current)
        retryRef.current = null
      }
    }, 300)
    return () => {
      if (retryRef.current) clearInterval(retryRef.current)
    }
  }, [step])

  const close = () => {
    setStep(-1)
    window.localStorage.setItem(DISMISS_KEY, '1')
  }

  if (step < 0) return null
  const current = STEPS[step]
  const isLast = step === STEPS.length - 1

  // Card placement: below the highlighted rect when found, centered on
  // screen otherwise. The centered fallback keeps step 3 readable even when
  // the result panel hasn't rendered yet.
  const cardStyle = rect
    ? { top: rect.top + rect.height + 12, left: Math.max(16, Math.min(window.innerWidth - 340, rect.left)) }
    : { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }

  return (
    <>
      <div className="tour-backdrop" onClick={close} />
      {rect && (
        <div
          className="tour-highlight"
          style={{ top: rect.top - 6, left: rect.left - 6, width: rect.width + 12, height: rect.height + 12 }}
        />
      )}
      <div className="tour-card" style={cardStyle}>
        <div className="tour-step-count">Step {step + 1} of {STEPS.length}</div>
        <h4>{current.title}</h4>
        <p>{current.body}</p>
        {!rect && (
          <p className="tour-card-hint">
            (Run a demo to see this part in action.)
          </p>
        )}
        <div className="tour-actions">
          <button className="tour-skip" onClick={close}>Skip tour</button>
          {step > 0 && (
            <button className="tour-skip" onClick={() => setStep(step - 1)}>← Back</button>
          )}
          {!isLast && (
            <button className="tour-next" onClick={() => setStep(step + 1)}>Next →</button>
          )}
          {isLast && (
            <button className="tour-next" onClick={close}>Got it</button>
          )}
        </div>
      </div>
    </>
  )
}
