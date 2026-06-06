import { narrateResult } from '../narration'

export default function ResultBanner({ result, isSample }) {
  if (!result) return null
  const held = result.final_evasion_rate <= 0.15
  const narration = narrateResult(result)

  const cls = held ? 'result-banner result-win' : 'result-banner result-lose'
  const icon = held ? '✅' : '⚠️'
  const headline = held ? 'Defender held the line' : 'Defender was broken'
  const nextStep = held
    ? 'Try the Quick Robustness Test to stress-test at higher epsilon.'
    : 'Increase the Hardening Mix or run more generations.'

  return (
    <div className={cls}>
      <div className="result-banner-icon">{icon}</div>
      <div className="result-banner-body">
        <div className="result-banner-head">
          {isSample && <span className="sample-tag">SAMPLE</span>}
          <span className="result-banner-headline">{headline}</span>
        </div>
        <p className="result-banner-line">{narration}</p>
        <p className="result-banner-next"><strong>Next:</strong> {nextStep}</p>
      </div>
    </div>
  )
}
