import { useState, useEffect, useRef, useCallback } from 'react'
import EvolutionChart from './components/EvolutionChart'
import PhylogenyTree from './components/PhylogenyTree'
import ModelConfidence from './components/ModelConfidence'
import HardeningComparison from './components/HardeningComparison'
import Controls from './components/Controls'
import StatusPanel from './components/StatusPanel'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/evolution'

function App() {
  const [status, setStatus] = useState('idle')
  const [generations, setGenerations] = useState([])
  const [phylogeny, setPhylogeny] = useState(null)
  const [result, setResult] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef(null)

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
        setGenerations(prev => [...prev, msg.data])
      } else if (msg.type === 'complete') {
        setResult(msg.data)
        setPhylogeny(msg.data.phylogeny)
        setStatus('complete')
      }
    }
    wsRef.current = ws
  }, [])

  useEffect(() => {
    connectWs()
    return () => wsRef.current?.close()
  }, [connectWs])

  const startEvolution = async (config) => {
    setStatus('evolving')
    setGenerations([])
    setResult(null)
    setPhylogeny(null)

    const res = await fetch(`${API_BASE}/evolution/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    if (!res.ok) {
      const err = await res.json()
      setStatus('error')
      console.error(err)
    }
  }

  const runEval = async (epsilon) => {
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
    const res = await fetch(`${API_BASE}/evolution/status`)
    if (res.ok) {
      const data = await res.json()
      setGenerations(data.generations || [])
      if (data.status === 'complete') {
        setResult(data.result)
        setPhylogeny(data.result?.phylogeny)
        setStatus('complete')
      }
    }
  }, [status])

  useEffect(() => {
    if (status !== 'evolving' || wsConnected) return
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [status, wsConnected, pollStatus])

  return (
    <div className="app">
      <header className="app-header">
        <h1>QKD Adversarial Benchmark</h1>
        <div className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
          {wsConnected ? 'Connected' : 'Reconnecting...'}
        </div>
      </header>

      <div className="dashboard">
        <div className="main-column">
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
          <ModelConfidence generations={generations} status={status} />
          <StatusPanel
            status={status}
            generations={generations}
            result={result}
          />
        </div>
      </div>
    </div>
  )
}

export default App
