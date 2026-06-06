import { useState } from 'react'
import Tooltip from './Tooltip'

const DEFAULTS = {
  population_size: 30,
  n_generations: 10,
  epsilon: 0.15,
  hardening_mix: 0.3,
}

export default function Controls({ status, onStart, onEval }) {
  const [config, setConfig] = useState(DEFAULTS)
  const [advanced, setAdvanced] = useState(false)

  const isRunning = status === 'evolving' || status === 'training'

  const upd = (k, v) => setConfig(c => ({ ...c, [k]: v }))

  return (
    <div className="panel" data-tour="controls">
      <div className="panel-header">
        <span className="panel-title">Run the battle</span>
      </div>

      <p className="control-blurb">
        One click runs <Tooltip term="generation">10 generations</Tooltip> of
        red-team attackers vs. our blue-team defender. About 30 seconds.
      </p>

      <button
        className="btn-cta btn-run-demo"
        onClick={() => onStart(config)}
        disabled={isRunning}
      >
        {isRunning ? 'Running…' : '▶ Run the demo'}
      </button>

      <button
        className="btn-secondary"
        onClick={() => onEval(config.epsilon)}
        disabled={isRunning}
        title="Single-shot adversarial sanity check — no learning loop."
      >
        Quick robustness test
      </button>

      <button
        className="advanced-toggle"
        onClick={() => setAdvanced(a => !a)}
        type="button"
      >
        {advanced ? '▼' : '▶'} Advanced settings
      </button>

      {advanced && (
        <div className="advanced-body">
          <div className="control-group">
            <label className="control-label">
              <Tooltip term="population">Population size</Tooltip>
            </label>
            <input className="control-input" type="number" min="10" max="200"
              value={config.population_size}
              onChange={e => upd('population_size', parseInt(e.target.value) || 30)}
              disabled={isRunning}
            />
            <span className="control-hint">How many attacker candidates per round. Bigger = more diverse search.</span>
          </div>

          <div className="control-group">
            <label className="control-label">
              <Tooltip term="generation">Generations</Tooltip>
            </label>
            <input className="control-input" type="number" min="1" max="200"
              value={config.n_generations}
              onChange={e => upd('n_generations', parseInt(e.target.value) || 10)}
              disabled={isRunning}
            />
            <span className="control-hint">How many rounds of attack-then-retrain to play.</span>
          </div>

          <div className="control-group">
            <label className="control-label">
              <Tooltip term="epsilon">How hard the attacker fights</Tooltip>
            </label>
            <input className="control-input" type="number" min="0.01" max="0.5" step="0.01"
              value={config.epsilon}
              onChange={e => upd('epsilon', parseFloat(e.target.value) || 0.15)}
              disabled={isRunning}
            />
            <span className="control-hint">0.01 = gentle. 0.5 = aggressive. Bounded by QKD physics either way.</span>
          </div>

          <div className="control-group">
            <label className="control-label">
              <Tooltip term="hardening_mix">Hardening mix</Tooltip>
            </label>
            <input className="control-input" type="number" min="0" max="0.8" step="0.05"
              value={config.hardening_mix}
              onChange={e => upd('hardening_mix', parseFloat(e.target.value) || 0.3)}
              disabled={isRunning}
            />
            <span className="control-hint">Fraction of fresh adversarial examples mixed into defender retraining.</span>
          </div>

          <button
            className="btn-link"
            onClick={() => setConfig(DEFAULTS)}
            disabled={isRunning}
            type="button"
          >
            Reset to defaults
          </button>
        </div>
      )}
    </div>
  )
}
