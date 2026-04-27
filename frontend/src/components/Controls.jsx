import { useState } from 'react'

export default function Controls({ status, onStart, onEval }) {
  const [config, setConfig] = useState({
    population_size: 30,
    n_generations: 10,
    epsilon: 0.15,
    hardening_mix: 0.3,
  })

  const isRunning = status === 'evolving' || status === 'training'

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Controls</span>
      </div>

      <div className="control-group">
        <label className="control-label">Population Size</label>
        <input className="control-input" type="number" min="10" max="200"
          value={config.population_size}
          onChange={e => setConfig({ ...config, population_size: parseInt(e.target.value) || 30 })}
          disabled={isRunning}
        />
      </div>

      <div className="control-group">
        <label className="control-label">Generations</label>
        <input className="control-input" type="number" min="1" max="200"
          value={config.n_generations}
          onChange={e => setConfig({ ...config, n_generations: parseInt(e.target.value) || 10 })}
          disabled={isRunning}
        />
      </div>

      <div className="control-group">
        <label className="control-label">Perturbation Strength (epsilon)</label>
        <input className="control-input" type="number" min="0.01" max="0.5" step="0.01"
          value={config.epsilon}
          onChange={e => setConfig({ ...config, epsilon: parseFloat(e.target.value) || 0.15 })}
          disabled={isRunning}
        />
      </div>

      <div className="control-group">
        <label className="control-label">Hardening Mix Ratio</label>
        <input className="control-input" type="number" min="0" max="0.8" step="0.05"
          value={config.hardening_mix}
          onChange={e => setConfig({ ...config, hardening_mix: parseFloat(e.target.value) || 0.3 })}
          disabled={isRunning}
        />
      </div>

      <button className="btn-primary" onClick={() => onStart(config)} disabled={isRunning}>
        {isRunning ? 'Running...' : 'Start Evolution'}
      </button>

      <div style={{ marginTop: 12 }}>
        <button className="btn-primary" style={{ background: 'var(--purple)' }}
          onClick={() => onEval(config.epsilon)} disabled={isRunning}>
          Run Quick Eval
        </button>
      </div>
    </div>
  )
}
