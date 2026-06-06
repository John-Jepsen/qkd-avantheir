import { useState, useMemo } from 'react'
import Tooltip from './Tooltip'
import { staticRuleCatchRate, averageQber, attackerCounts } from '../sample-data'

export default function ComparisonCard({ result }) {
  const [showMore, setShowMore] = useState(false)

  const data = useMemo(() => {
    if (!result) return null
    const counts = attackerCounts(result.phylogeny)
    const derivedStatic = result.phylogeny
      ? staticRuleCatchRate(result.phylogeny, result.static_threshold_catch_rate ?? 0.62)
      : (result.static_threshold_catch_rate ?? 0.62)
    const ml = result.ml_defender_catch_rate ?? result.final_defender_accuracy ?? 0
    const avgQ = result.phylogeny ? averageQber(result.phylogeny) : null
    return {
      counts,
      staticPct: Math.round(derivedStatic * 100),
      mlPct: Math.round(ml * 100),
      gap: Math.round((ml - derivedStatic) * 100),
      avgQberPct: avgQ != null ? +(avgQ * 100).toFixed(1) : null,
    }
  }, [result])

  if (!result || !data) return null
  const { counts, staticPct, mlPct, gap, avgQberPct } = data
  const allUnderThreshold = counts.total > 0 && counts.aboveThreshold === 0
  const allOverThreshold = counts.total > 0 && counts.belowThreshold === 0

  return (
    <div className="panel comparison-card">
      <div className="panel-header">
        <span className="panel-title">Why this matters</span>
      </div>

      <div className="comparison-takeaway">
        <span className="comparison-takeaway-num">
          {gap >= 0 ? '+' : ''}{gap}%
        </span>
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

      {avgQberPct != null && (
        <div className="qber-readout">
          <div className="qber-readout-row">
            <span className="qber-readout-label">Average QBER across {counts.total} attackers</span>
            <span className={`qber-readout-value ${avgQberPct >= 11 ? 'qber-high' : 'qber-low'}`}>
              {avgQberPct.toFixed(1)}%
            </span>
          </div>
          <div className="qber-readout-counts">
            <span className="qber-count qber-count-above">
              {counts.aboveThreshold} attackers had QBER ≥ 11% (caught by static rule)
            </span>
            <span className="qber-count qber-count-below">
              {counts.belowThreshold} attackers stayed under 11% (slip past static rule)
            </span>
          </div>
        </div>
      )}

      {allUnderThreshold && (
        <div className="comparison-callout comparison-callout-strong">
          <strong>The gym evolved {counts.total} attackers that all stayed under
          the 11% threshold.</strong> The static rule sees nothing wrong with
          any of them — it would have let every single one through. This is
          exactly the gap the ML defender is designed to fill.
        </div>
      )}
      {allOverThreshold && (
        <div className="comparison-callout">
          Every attacker on this run pushed QBER above 11%, so both detectors
          should catch most of them. Try a higher epsilon to evolve subtler
          attacks.
        </div>
      )}

      <div className="comparison-grid">
        <div className="comparison-cell comparison-cell-baseline">
          <div className="comparison-cell-eyebrow">Static 11% rule</div>
          <div className="comparison-cell-value">{staticPct}%</div>
          <div className="comparison-cell-foot">
            {counts.total > 0
              ? `${counts.aboveThreshold} of ${counts.total} caught`
              : 'of attackers caught'}
          </div>
        </div>
        <div className="comparison-cell comparison-cell-ml">
          <div className="comparison-cell-eyebrow">Our ML defender</div>
          <div className="comparison-cell-value">{mlPct}%</div>
          <div className="comparison-cell-foot">of attackers caught</div>
        </div>
      </div>

      <div className="comparison-delta">
        <span className="comparison-delta-arrow">{gap >= 0 ? '↑' : '↓'}</span>
        <strong>{gap >= 0 ? '+' : ''}{gap} percentage points</strong> the ML
        defender caught that the textbook rule missed.
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
          <p>
            The evolutionary gym uses the defender's confidence as its
            fitness signal — so over generations it learns to produce
            attackers that <em>specifically</em> stay under 11% QBER while
            still fooling the other features. That's why low-QBER blue dots
            in the family tree are the most important: they're the ones the
            textbook rule can never see.
          </p>
        </div>
      )}
    </div>
  )
}
