import { useState, useEffect, useRef, useCallback } from 'react'
import BattleViz from './components/BattleViz'
import EvolutionChart from './components/EvolutionChart'
import PhylogenyTree from './components/PhylogenyTree'
import ModelConfidence from './components/ModelConfidence'
import HardeningComparison from './components/HardeningComparison'
import Controls from './components/Controls'
import StatusPanel from './components/StatusPanel'
import WelcomeHero from './components/WelcomeHero'
import ResultBanner from './components/ResultBanner'
import ComparisonCard from './components/ComparisonCard'
import Narrator from './components/Narrator'
import ProgressSteps from './components/ProgressSteps'
import GuidedTour from './components/GuidedTour'
import Glossary from './components/Glossary'
import { SAMPLE_GENERATIONS, SAMPLE_RESULT } from './sample-data'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/evolution'

// Playback pacing — backend can finish 10 gens in ~15s, which is too fast
// for a viewer to read commentary and watch the battle. We buffer events
// and release them at a fixed cadence per the selected speed.
const SPEED_MS = {
  slow: 5500,
  normal: 3500,
  fast: 1500,
}

function App() {
  // status: idle | training | evolving | complete | error
  const [status, setStatus] = useState('idle')
  const [generations, setGenerations] = useState([])
  const [phylogeny, setPhylogeny] = useState(null)
  const [result, setResult] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [targetGenerations, setTargetGenerations] = useState(0)
  const [showWelcome, setShowWelcome] = useState(false)
  const [tourNonce, setTourNonce] = useState(0)
  const [isSampleMode, setIsSampleMode] = useState(true)
  const [speed, setSpeed] = useState('normal')
  const [queueSize, setQueueSize] = useState(0)

  const wsRef = useRef(null)
  const queueRef = useRef([])
  const pendingResultRef = useRef(null)
  const drainTimerRef = useRef(null)

  // Show sample run by default so the empty state isn't dead.
  useEffect(() => {
    if (isSampleMode && generations.length === 0) {
      setGenerations(SAMPLE_GENERATIONS)
      setResult(SAMPLE_RESULT)
      setPhylogeny(SAMPLE_RESULT.phylogeny)
    }
  }, [isSampleMode, generations.length])

  const clearSample = () => {
    if (isSampleMode) {
      setIsSampleMode(false)
    }
    setGenerations([])
    setResult(null)
    setPhylogeny(null)
    setEvalResult(null)
    queueRef.current = []
    pendingResultRef.current = null
    setQueueSize(0)
    if (drainTimerRef.current) {
      clearTimeout(drainTimerRef.current)
      drainTimerRef.current = null
    }
  }

  // Pop one event off the queue and apply it, then schedule the next drain.
  // The deferred result release lets the user finish reading the last
  // generation before the win/lose banner pops.
  const scheduleDrain = useCallback(() => {
    if (drainTimerRef.current) return
    const delay = SPEED_MS[speed]
    drainTimerRef.current = setTimeout(() => {
      drainTimerRef.current = null
      const queue = queueRef.current
      if (queue.length > 0) {
        const next = queue.shift()
        setGenerations(prev => [...prev, next])
        setQueueSize(queue.length)
      } else if (pendingResultRef.current) {
        const res = pendingResultRef.current
        pendingResultRef.current = null
        setResult(res)
        setPhylogeny(res.phylogeny)
        setStatus('complete')
        return
      }
      // Keep draining while there's something to show
      if (queueRef.current.length > 0 || pendingResultRef.current) {
        scheduleDrain()
      }
    }, delay)
  }, [speed])

  const connectWs = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    ws.onopen = () => setWsConnected(true)
    ws.onclose = () => {
      setWsConnected(false)
      setTimeout(connectWs, 3000)
    }
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'generation') {
        queueRef.current.push(msg.data)
        setQueueSize(queueRef.current.length)
        scheduleDrain()
      } else if (msg.type === 'complete') {
        pendingResultRef.current = msg.data
        scheduleDrain()
      }
    }
    wsRef.current = ws
  }, [scheduleDrain])

  useEffect(() => {
    connectWs()
    return () => wsRef.current?.close()
  }, [connectWs])

  const startEvolution = async (config) => {
    clearSample()
    setStatus('evolving')
    setTargetGenerations(config.n_generations)

    const res = await fetch(`${API_BASE}/evolution/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      setStatus('error')
      console.error(err)
    }
  }

  const runEval = async (epsilon) => {
    clearSample()
    const res = await fetch(`${API_BASE}/adversarial-eval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ epsilon }),
    })
    if (res.ok) {
      setEvalResult(await res.json())
    }
  }

  const pollStatus = useCallback(async () => {
    if (status !== 'evolving') return
    if (wsConnected) return
    // HTTP-polling fallback when WS is unavailable. Drop the whole batch
    // through the queue so pacing still applies.
    const res = await fetch(`${API_BASE}/evolution/status`)
    if (res.ok) {
      const data = await res.json()
      const known = generations.length + queueRef.current.length
      const fresh = (data.generations || []).slice(known)
      if (fresh.length) {
        queueRef.current.push(...fresh)
        setQueueSize(queueRef.current.length)
        scheduleDrain()
      }
      if (data.status === 'complete' && data.result && !pendingResultRef.current) {
        pendingResultRef.current = data.result
        scheduleDrain()
      }
    }
  }, [status, wsConnected, generations.length, scheduleDrain])

  useEffect(() => {
    if (status !== 'evolving' || wsConnected) return
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [status, wsConnected, pollStatus])

  const triggerTour = () => {
    // Clear all dismiss flags so the tour reruns from step 1.
    window.localStorage.removeItem('qkd-tour-dismissed-v1')
    window.localStorage.removeItem('qkd-tour-dismissed-v1-started')
    setTourNonce(n => n + 1)
  }

  const isSampleVisible = isSampleMode && result?.is_sample

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <h1>QKD Adversarial Benchmark</h1>
          <div className="brand-sub">
            <span className="team-red-text">🤖 Red-team attackers</span>
            <span className="brand-vs">vs</span>
            <span className="team-blue-text">🛡️ Blue-team defender</span>
            <span className="brand-sep">·</span>
            <span>does our ML detector beat a moving target?</span>
          </div>
        </div>
        <div className="header-controls">
          <div className="speed-picker" title="Playback speed">
            <span className="speed-label">Pace:</span>
            {['slow', 'normal', 'fast'].map(s => (
              <button
                key={s}
                className={`speed-btn ${speed === s ? 'active' : ''}`}
                onClick={() => setSpeed(s)}
              >
                {s}
              </button>
            ))}
          </div>
          <button
            className="header-btn"
            onClick={triggerTour}
            title="Restart the guided tour"
          >
            Tour
          </button>
          <button
            className="header-btn"
            onClick={() => setShowWelcome(true)}
            title="Show the intro again"
          >
            ?
          </button>
          <div className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
            <span className="ws-dot" />
            {wsConnected ? 'Live updates on' : 'Reconnecting…'}
          </div>
        </div>
      </header>

      <WelcomeHero
        forceOpen={showWelcome}
        onClose={() => setShowWelcome(false)}
        onRunDemo={() => startEvolution({
          population_size: 30, n_generations: 10, epsilon: 0.15, hardening_mix: 0.3,
        })}
      />
      <GuidedTour key={tourNonce} forceStart={tourNonce > 0} />

      <div className="dashboard">
        <div className="main-column">
          {result && (
            <div data-tour="result">
              <ResultBanner result={result} isSample={isSampleVisible} />
              <ComparisonCard result={result} />
            </div>
          )}
          {isSampleVisible && (
            <div className="sample-banner">
              <span>👇 Below is a sample run so you can see how the dashboard reads. Hit <strong>Run the demo</strong> to replace it with your own.</span>
            </div>
          )}
          <ProgressSteps
            status={status}
            generations={generations}
            total={targetGenerations}
            queueSize={queueSize}
          />
          <BattleViz generations={generations} status={status} speed={speed} />
          <EvolutionChart generations={generations} status={status} />
          <PhylogenyTree phylogeny={phylogeny} status={status} />
          <HardeningComparison result={result} evalResult={evalResult} status={status} />
        </div>

        <div className="side-column">
          <Controls
            status={status}
            onStart={startEvolution}
            onEval={runEval}
          />
          <Narrator generations={generations} status={status} />
          <StatusPanel
            status={status}
            generations={generations}
            result={result}
            target={targetGenerations}
            isSample={isSampleVisible}
          />
          <ModelConfidence generations={generations} status={status} />
        </div>
      </div>

      <Glossary />
    </div>
  )
}

export default App
