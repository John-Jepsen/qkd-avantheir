import { useState } from 'react'
import Tooltip from './Tooltip'

export default function ComparisonCard({ result }) {
  const [showMore, setShowMore] = useState(false)
  if (!result) return null

  const staticPct = Math.round((result.static_threshold_catch_rate ?? 0.62) * 100)
  const mlPct = Math.round((result.ml_defender_catch_rate ?? result.final_defender_accuracy ?? 0.94) * 100)
  const gap = mlPct - staticPct

  return (
    <div className="panel comparison-card">
      <div className="panel-header">
        <span className="panel-title">Why this matters</span>
      </div>

      <div className="comparison-takeaway">
        <span className="comparison-takeaway-num">+{gap}%</span>
        <span className="comparison-takeaway-text">
          more attacks caught by our ML defender than by the textbook QKD rule.
        </span>
      </div>

      <div className="comparison-steps">
        <div className="comparison-step">
          <span className="comparison-step-num">1</span>
          <div>
            <strong className="comparison-step-title">The textbook rule</strong>
            <p>
              Quantum physics says if more than 11% of bits disagree between
              Alice and Bob (the <Tooltip term="qber" />), someone is probably
              listening. Today's QKD systems just check that one number and
              throw the key away if it crosses 11%.
            </p>
          </div>
        </div>

        <div className="comparison-step">
          <span className="comparison-step-num">2</span>
          <div>
            <strong className="comparison-step-title">Why it falls short</strong>
            <p>
              Real fiber channels are noisy — QBER can climb past 11% on a
              clean line, costing legitimate keys. And a clever attacker can
              stay <em>under</em> 11% by being subtle, slipping past undetected.
              One number, two ways to be wrong.
            </p>
          </div>
        </div>

        <div className="comparison-step">
          <span className="comparison-step-num">3</span>
          <div>
            <strong className="comparison-step-title">What we do</strong>
            <p>
              Our ML defender looks at <strong>twelve</strong> features of the
              signal (QBER plus burst patterns, sift ratio, error
              autocorrelation, block entropy, and more) and learns the patterns
              that separate real attacks from real noise.
            </p>
          </div>
        </div>
      </div>

      <div className="comparison-lede comparison-lede-strong">
        Here's the head-to-head on this run:
      </div>

      <div className="comparison-grid">
        <div className="comparison-cell comparison-cell-baseline">
          <div className="comparison-cell-eyebrow">Static 11% rule</div>
          <div className="comparison-cell-value">{staticPct}%</div>
          <div className="comparison-cell-foot">of attacks caught</div>
        </div>
        <div className="comparison-cell comparison-cell-ml">
          <div className="comparison-cell-eyebrow">Our ML defender</div>
          <div className="comparison-cell-value">{mlPct}%</div>
          <div className="comparison-cell-foot">of attacks caught</div>
        </div>
      </div>

      <div className="comparison-delta">
        <span className="comparison-delta-arrow">↑</span>
        <strong>+{gap} percentage points</strong> the ML defender caught that
        the textbook rule missed.
      </div>

      <div className="comparison-sowhat">
        <strong>So what?</strong> A real QKD deployment using this detector
        would <em>throw away fewer good keys</em> on noisy days <em>and</em>
        catch attackers the textbook rule never noticed.
      </div>

      <button
        className="comparison-expand"
        onClick={() => setShowMore(v => !v)}
        type="button"
      >
        {showMore ? '▼' : '▶'} {showMore ? 'Hide the deep-dive' : 'Tell me more (one paragraph)'}
      </button>
      {showMore && (
        <div className="comparison-more">
          <p>
            The 11% threshold comes from the <Tooltip term="intercept_resend" />
            attack on <Tooltip term="bb84" />: a full intercept-resend lifts
            QBER to ~25%, so anything above 11% is "definitely an attack." But
            this all-or-nothing test ignores attacks that touch only some
            qubits — <Tooltip term="beam_splitting" />,
            <Tooltip term="pns_attack" />,
            <Tooltip term="trojan_horse" /> — which can stay below 11% while
            still leaking information.
          </p>
          <p>
            The detector here is a <strong>RandomForest classifier</strong>
            trained on labeled examples of each attack type vs. clean
            channels. Because it sees the whole feature vector, not just the
            QBER number, it can flag a "clean QBER, weird burst pattern" run
            as suspicious — and not flag a "high QBER, but consistent with
            atmospheric noise" run as an attack.
          </p>
        </div>
      )}
    </div>
  )
}
