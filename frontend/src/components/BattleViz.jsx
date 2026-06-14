import { useRef, useEffect, useMemo, useState } from 'react'
import * as d3 from 'd3'

// Visual metaphor:
//   Y-axis = how close attackers are to fooling the defender.
//   Blue line + energy field = the defender's decision boundary.
//   Red dots = 30 attacker candidates. They spawn from the bottom, jitter
//     continuously, and try to rise above the defender line. Trails fade
//     behind them so you can follow movement. The defender line pulses on
//     every new generation; particle bursts erupt at the crossing points.
//   Big HUD on top tells the viewer the score in plain English.

const ATTACKER_COUNT = 30
const HEIGHT = 460
const MARGIN = { top: 56, right: 90, bottom: 64, left: 60 }
const DOT_R = 7
// Fixed vertical position of the 11% QBER threshold (the blue band's lower
// edge). Visually 40% of the arena for legibility; it still represents the 11%
// threshold. Dots that reach the band got past; the green defender line moves
// in the zone below it, driven by accuracy.
const THRESHOLD_FRAC = 0.40

function seedRand(seed) {
  let s = seed || 1
  return () => {
    s = (s * 9301 + 49297) % 233280
    return s / 233280
  }
}

const TRANSITION_MS = {
  slow: 3200,
  normal: 2000,
  fast: 1100,
}

function statusFor(latest) {
  if (!latest) return { tag: 'idle', label: 'Idle' }
  const ev = latest.evasion_rate || 0
  if (ev <= 0.10) return { tag: 'crushing', label: 'Defender is crushing it' }
  if (ev <= 0.25) return { tag: 'leading', label: 'Defender is in the lead' }
  if (ev <= 0.45) return { tag: 'tight', label: 'It\'s a tight fight' }
  if (ev <= 0.70) return { tag: 'breaking', label: 'Attackers are breaking through' }
  return { tag: 'overrun', label: 'Defender is being overrun' }
}

export default function BattleViz({ generations, status, speed = 'normal' }) {
  const svgRef = useRef()
  const layersRef = useRef({})
  const prevGenCountRef = useRef(0)
  const prevDefAccRef = useRef(null)
  const prevEvRef = useRef(null)
  const [dims, setDims] = useState({ innerW: 0, innerH: HEIGHT - MARGIN.top - MARGIN.bottom })

  const latest = generations[generations.length - 1]

  // Stable attacker layout — fixed x lanes, persistent jitter phases. Each
  // dot is labeled "evaded" or "caught" so the layout effect can position
  // it relative to the defender line: evaded → above, caught → below.
  // This keeps the line and the dots telling the same story.
  const dots = useMemo(() => {
    const seed = generations.length === 0 ? 1 : (generations.length * 7919)
    const rand = seedRand(seed)
    const evRate = latest?.evasion_rate || 0
    const evadedCount = Math.round(evRate * ATTACKER_COUNT)
    return Array.from({ length: ATTACKER_COUNT }, (_, i) => {
      const evaded = i < evadedCount
      // Where in its zone the dot sits — random spread per dot, capped so
      // dots cluster near the line not at the extremes.
      const zoneFrac = 0.15 + rand() * 0.75
      return {
        id: i,
        x: (i + 1) / (ATTACKER_COUNT + 1),
        evaded,
        zoneFrac,
        phase: rand() * Math.PI * 2,
        speed: 0.4 + rand() * 0.6,
        amp: 0.012 + rand() * 0.022,
      }
    })
  }, [generations.length, latest])

  // ResizeObserver feeds dims so the skeleton rebuilds at the right width.
  useEffect(() => {
    if (!svgRef.current) return
    const update = () => {
      const w = svgRef.current.clientWidth
      if (!w) return
      const innerW = Math.max(160, w - MARGIN.left - MARGIN.right)
      setDims(d => (d.innerW === innerW ? d : { innerW, innerH: HEIGHT - MARGIN.top - MARGIN.bottom }))
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(svgRef.current)
    window.addEventListener('resize', update)
    return () => { ro.disconnect(); window.removeEventListener('resize', update) }
  }, [])

  // Build SVG skeleton when dims arrive (or change).
  useEffect(() => {
    if (!svgRef.current || !dims.innerW) return
    const { innerW, innerH } = dims
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // ---- defs: gradients, masks, filters ----
    const defs = svg.append('defs')

    // Vertical danger gradient (top = red, bottom = blue)
    const arenaGrad = defs.append('linearGradient')
      .attr('id', 'arena-grad').attr('x1', '0').attr('y1', '0').attr('x2', '0').attr('y2', '1')
    arenaGrad.append('stop').attr('offset', '0%').attr('stop-color', '#5b0a17').attr('stop-opacity', 0.85)
    arenaGrad.append('stop').attr('offset', '45%').attr('stop-color', '#1e1424').attr('stop-opacity', 0.6)
    arenaGrad.append('stop').attr('offset', '100%').attr('stop-color', '#08243d').attr('stop-opacity', 0.9)

    // Defender energy field gradient — bright at the line, fades out
    const fieldGrad = defs.append('linearGradient')
      .attr('id', 'field-grad').attr('x1', '0').attr('y1', '0').attr('x2', '0').attr('y2', '1')
    fieldGrad.append('stop').attr('offset', '0%').attr('stop-color', '#58a6ff').attr('stop-opacity', 0)
    fieldGrad.append('stop').attr('offset', '50%').attr('stop-color', '#58a6ff').attr('stop-opacity', 0.45)
    fieldGrad.append('stop').attr('offset', '100%').attr('stop-color', '#58a6ff').attr('stop-opacity', 0)

    // Glow filter for the defender line
    const lineGlow = defs.append('filter').attr('id', 'line-glow')
      .attr('x', '-20%').attr('y', '-200%').attr('width', '140%').attr('height', '500%')
    lineGlow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'b')
    const lm = lineGlow.append('feMerge')
    lm.append('feMergeNode').attr('in', 'b')
    lm.append('feMergeNode').attr('in', 'SourceGraphic')

    // Glow filter for HUD text
    const textGlow = defs.append('filter').attr('id', 'text-glow')
      .attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%')
    textGlow.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'b')
    const tm = textGlow.append('feMerge')
    tm.append('feMergeNode').attr('in', 'b')
    tm.append('feMergeNode').attr('in', 'SourceGraphic')

    // Master group with margin
    const g = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`)

    // Arena background
    g.append('rect')
      .attr('width', innerW).attr('height', innerH)
      .attr('fill', 'url(#arena-grad)').attr('rx', 12)
      .attr('stroke', '#30363d').attr('stroke-width', 1)

    // 11% QBER threshold band — fixed reference at the top of the arena.
    // Marks the BB84 abort threshold (QBER > 11% = compromised). Drawn taller
    // than 11% purely for legibility; it still represents the 11% threshold.
    const qberBand = g.append('g').attr('class', 'qber-band')
    const qberH = innerH * THRESHOLD_FRAC
    qberBand.append('rect')
      .attr('x', 0).attr('y', 0)
      .attr('width', innerW).attr('height', qberH)
      .attr('fill', '#58a6ff').attr('opacity', 0.16)
    qberBand.append('text')
      .attr('x', 10).attr('y', 18)
      .attr('fill', '#58a6ff').attr('font-size', 13).attr('font-weight', 800)
      .attr('opacity', 0.95)
      .text('⚠ 11% QBER abort threshold — attacker is past if a dot enters this band')

    // Lane grid — subtle vertical lines so eye reads x positions as lanes
    const grid = g.append('g').attr('class', 'arena-grid')
    for (let i = 0; i < 6; i++) {
      grid.append('line')
        .attr('x1', (i / 5) * innerW).attr('x2', (i / 5) * innerW)
        .attr('y1', 0).attr('y2', innerH)
        .attr('stroke', '#ffffff').attr('stroke-width', 0.5).attr('opacity', 0.06)
    }

    // Zone labels — small pill-style badges in the corners so they never
    // collide with the defender line or its glow.
    const labelPad = 10
    const attackerBadge = g.append('g').attr('transform', `translate(${innerW - 200}, 8)`)
    attackerBadge.append('rect').attr('width', 190).attr('height', 24).attr('rx', 12)
      .attr('fill', '#3a0a14').attr('stroke', '#f85149').attr('stroke-width', 1).attr('opacity', 0.85)
    attackerBadge.append('text').attr('x', 95).attr('y', 16).attr('text-anchor', 'middle')
      .attr('fill', '#f85149').attr('font-size', 11).attr('font-weight', 700)
      .text('↑ ATTACKER WINS ZONE')

    const defenderBadge = g.append('g').attr('transform', `translate(${innerW - 200}, ${innerH - 32})`)
    defenderBadge.append('rect').attr('width', 190).attr('height', 24).attr('rx', 12)
      .attr('fill', '#0a2a18').attr('stroke', '#3fb950').attr('stroke-width', 1).attr('opacity', 0.85)
    defenderBadge.append('text').attr('x', 95).attr('y', 16).attr('text-anchor', 'middle')
      .attr('fill', '#3fb950').attr('font-size', 11).attr('font-weight', 700)
      .text('↓ DEFENDER WINS ZONE')

    // ---- Defender layer ----
    const defLayer = g.append('g').attr('class', 'defender-layer')

    // Glow line behind sharp line — single bright stroke, no wide band.
    defLayer.append('line').attr('class', 'def-line-halo')
      .attr('x1', 0).attr('x2', innerW)
      .attr('stroke', '#3fb950').attr('stroke-width', 14).attr('opacity', 0.3)
      .attr('stroke-linecap', 'round')

    defLayer.append('line').attr('class', 'def-line')
      .attr('x1', 0).attr('x2', innerW)
      .attr('stroke', '#3fb950').attr('stroke-width', 4)
      .attr('stroke-linecap', 'round')
      .style('filter', 'url(#line-glow)')

    // Big shield emoji at the right edge
    defLayer.append('text').attr('class', 'def-shield')
      .attr('font-size', 32).text('🛡️')

    // ---- HUD bar at top (outside main group, fixed in margin) ----
    const hud = svg.append('g').attr('transform', `translate(${MARGIN.left}, 8)`)
    hud.append('rect').attr('class', 'hud-bg')
      .attr('width', innerW).attr('height', 38)
      .attr('rx', 8).attr('fill', '#0d1117').attr('stroke', '#30363d')
    hud.append('text').attr('class', 'hud-gen')
      .attr('x', 14).attr('y', 25)
      .attr('fill', '#8b949e').attr('font-size', 12).attr('font-weight', 600)
      .text('GEN 0')
    hud.append('text').attr('class', 'hud-status')
      .attr('x', innerW / 2).attr('y', 25)
      .attr('text-anchor', 'middle')
      .attr('fill', '#e6edf3').attr('font-size', 15).attr('font-weight', 700)
      .style('filter', 'url(#text-glow)')
      .text('Awaiting first generation…')
    hud.append('text').attr('class', 'hud-score')
      .attr('x', innerW - 14).attr('y', 25)
      .attr('text-anchor', 'end')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', 13)
      .text('—')

    // Bottom-of-arena legend strip
    const legend = svg.append('g').attr('transform', `translate(${MARGIN.left}, ${HEIGHT - 46})`)
    legend.append('rect')
      .attr('width', innerW).attr('height', 36).attr('rx', 8)
      .attr('fill', '#0d1117').attr('stroke', '#30363d')

    const legendItems = [
      { x: 12, color: '#f85149', label: '🤖 each red dot = one attacker' },
      { x: 250, color: '#3fb950', label: '🛡️ green line = defender decision boundary' },
      { x: 580, color: '#fff',    label: '⚡ white flash = attacker crossed' },
    ]
    legendItems.forEach(item => {
      legend.append('circle')
        .attr('cx', item.x + 8).attr('cy', 18).attr('r', 5)
        .attr('fill', item.color).attr('opacity', 0.9)
      legend.append('text')
        .attr('x', item.x + 20).attr('y', 22)
        .attr('fill', '#8b949e').attr('font-size', 11)
        .text(item.label)
    })

    // ---- Attacker layers (trail, dots, flashes, deltas) ----
    g.append('g').attr('class', 'trails')
    g.append('g').attr('class', 'attackers')
    g.append('g').attr('class', 'flashes')
    g.append('g').attr('class', 'deltas')

    layersRef.current = { g, defLayer, hud }
    prevGenCountRef.current = 0
  }, [dims])

  // Update on new generation: animate dots, pulse defender, score popups.
  useEffect(() => {
    if (!dims.innerW || !latest) return
    const { g, defLayer, hud } = layersRef.current
    if (!g) return
    const { innerW, innerH } = dims
    const dur = TRANSITION_MS[speed] || TRANSITION_MS.normal

    // Blue band (top THRESHOLD_FRAC) is the fixed 11% threshold. The green
    // defender line moves within the zone BELOW it, driven by accuracy: the
    // better the defender, the higher (closer to the threshold) it holds the
    // line, leaving a wide "caught" zone beneath it.
    const bandBottom = innerH * THRESHOLD_FRAC
    const lineTop = bandBottom + 24
    const lineBot = innerH - 28
    const acc = latest.defender_accuracy || 0
    const defenderY = lineBot - (lineBot - lineTop) * acc

    defLayer.select('.def-line')
      .transition().duration(dur).ease(d3.easeCubicInOut)
      .attr('y1', defenderY).attr('y2', defenderY)
    defLayer.select('.def-line-halo')
      .transition().duration(dur).ease(d3.easeCubicInOut)
      .attr('y1', defenderY).attr('y2', defenderY)
    defLayer.select('.def-shield')
      .transition().duration(dur).ease(d3.easeCubicInOut)
      .attr('x', innerW + 8).attr('y', defenderY + 10)

    // HUD updates
    const s = statusFor(latest)
    hud.select('.hud-gen').text(`GEN ${generations.length}`)
    hud.select('.hud-status').text(s.label).attr('fill', {
      crushing: '#3fb950', leading: '#58a6ff', tight: '#d29922',
      breaking: '#f0883e', overrun: '#f85149',
    }[s.tag] || '#e6edf3')
    const evPct = Math.round((latest.evasion_rate || 0) * 100)
    const dfPct = Math.round((latest.defender_accuracy || 0) * 100)
    hud.select('.hud-score').html('')
    hud.select('.hud-score')
      .append('tspan').attr('fill', '#f85149').text(`🤖 ${evPct}% past`)
    hud.select('.hud-score')
      .append('tspan').attr('fill', '#8b949e').text('   ·   ')
    hud.select('.hud-score')
      .append('tspan').attr('fill', '#3fb950').text(`🛡️ ${dfPct}% caught`)

    // Generation-change pulse + delta popup
    const isNewGen = generations.length !== prevGenCountRef.current
    if (isNewGen) {
      defLayer.select('.def-line-halo')
        .interrupt()
        .attr('opacity', 0.95).attr('stroke-width', 32)
        .transition().duration(950).ease(d3.easeCubicOut)
        .attr('opacity', 0.3).attr('stroke-width', 14)

      // Score-delta popup (e.g., "+4% caught this round")
      if (prevDefAccRef.current != null) {
        const deltaAcc = Math.round((latest.defender_accuracy - prevDefAccRef.current) * 100)
        const deltaEv = Math.round((latest.evasion_rate - prevEvRef.current) * 100)
        const popups = []
        if (deltaAcc !== 0) {
          popups.push({
            text: `${deltaAcc > 0 ? '+' : ''}${deltaAcc}% caught`,
            color: deltaAcc > 0 ? '#3fb950' : '#f85149',
            xFrac: 0.32,
          })
        }
        if (deltaEv !== 0) {
          popups.push({
            text: `${deltaEv > 0 ? '+' : ''}${deltaEv}% slipped`,
            color: deltaEv < 0 ? '#3fb950' : '#f85149',
            xFrac: 0.68,
          })
        }
        const deltas = g.select('.deltas')
        popups.forEach(p => {
          const t = deltas.append('text')
            .attr('x', p.xFrac * innerW)
            .attr('y', defenderY + 8)
            .attr('text-anchor', 'middle')
            .attr('fill', p.color)
            .attr('font-size', 18).attr('font-weight', 800)
            .attr('opacity', 0)
            .text(p.text)
          t.transition().duration(400).attr('opacity', 1)
            .transition().duration(1500).ease(d3.easeCubicIn)
            .attr('y', defenderY - 50).attr('opacity', 0).remove()
        })
      }

      prevDefAccRef.current = latest.defender_accuracy
      prevEvRef.current = latest.evasion_rate
      prevGenCountRef.current = generations.length
    }

    // Attacker dots — the data join only manages existence and static style.
    // All vertical motion (the per-generation assault on the line) is driven
    // by the battle-timeline timer below, so we don't set cy here.
    const attackerSel = g.select('.attackers').selectAll('circle.attacker')
      .data(dots, d => d.id)

    attackerSel.exit().remove()

    attackerSel.enter().append('circle')
      .attr('class', 'attacker')
      .attr('cx', d => d.x * innerW)
      .attr('cy', innerH - 14)
      .attr('r', DOT_R)
      .attr('opacity', 0.95)
      .attr('stroke', '#3a0a14').attr('stroke-width', 1.2)
      .merge(attackerSel)
      .attr('fill', d => d.evaded ? '#f85149' : '#f0883e')

    // Clear the crossing-flash layer; the timer re-fires a flash as each
    // attacker actually punches through the line this generation.
    if (isNewGen) g.select('.flashes').selectAll('*').remove()
  }, [dims, dots, latest, generations.length, speed])

  // Battle-timeline timer: every generation replays the assault. Each attacker
  // launches from the bottom, charges the threshold line, then resolves —
  // evaded dots break UP through the line into the band; caught dots reach the
  // line and get pushed back DOWN into the defender's zone. Settle-jitter and
  // motion trails ride on top once a dot has resolved.
  useEffect(() => {
    if (!dims.innerW || !latest) return
    const { g } = layersRef.current
    if (!g) return
    const { innerW, innerH } = dims
    const dur = TRANSITION_MS[speed] || TRANSITION_MS.normal

    const bandBottom = innerH * THRESHOLD_FRAC
    const lineTop = bandBottom + 24
    const lineBot = innerH - 28
    const acc = latest.defender_accuracy || 0
    const defenderY = lineBot - (lineBot - lineTop) * acc

    // Final resting spot once the dot has resolved: in the band if it got past,
    // spread through the defender's zone below the line if it got caught.
    const restY = (d) => {
      if (d.evaded) {
        const top = 32
        const bot = bandBottom - 8
        return top + (bot - top) * d.zoneFrac
      }
      const top = defenderY + 14
      const bot = innerH - 12
      return top + (bot - top) * d.zoneFrac
    }

    const launchY = innerH - 14        // staging line at the bottom
    const lineApproach = defenderY + 6 // pressed right up against the line
    const chargeDur = dur              // wall time for one dot's full run
    const staggerMs = (dur * 0.4) / ATTACKER_COUNT
    const recoil = d3.easeBackOut.overshoot(2.6) // caught-dot pushback bounce

    // Vertical position for local progress p (0..1), in three beats:
    //   charge (0→0.40)  — rise from the bottom up to the line
    //   press  (0.40→0.66) — strain against the line, quivering, the fight
    //   resolve(0.66→1)  — evaded dots punch UP into the band; caught dots get
    //                      shoved back DOWN past their rest spot, then settle
    const dotY = (d, p) => {
      if (p <= 0) return launchY
      const rest = restY(d)
      if (p < 0.40) {
        return launchY + (lineApproach - launchY) * d3.easeCubicOut(p / 0.40)
      }
      if (p < 0.66) {
        const q = (p - 0.40) / 0.26
        const quiver = Math.sin(q * Math.PI * 3) * 3 // ±3px struggle at the line
        return lineApproach + quiver
      }
      const q = (p - 0.66) / 0.34
      if (d.evaded) {
        return lineApproach + (rest - lineApproach) * d3.easeCubicOut(q)
      }
      return lineApproach + (rest - lineApproach) * recoil(q)
    }

    const flashed = new Set()
    const spawnFlash = (x, y) => {
      const flashLayer = g.select('.flashes')
      for (let k = 0; k < 4; k++) {
        const angle = (k / 4) * Math.PI * 2 + Math.random() * 0.4
        flashLayer.append('circle')
          .attr('cx', x).attr('cy', y).attr('r', 2)
          .attr('fill', '#ffffff').attr('opacity', 1)
          .transition().duration(900).ease(d3.easeCubicOut)
          .attr('cx', x + Math.cos(angle) * 28)
          .attr('cy', y + Math.sin(angle) * 28)
          .attr('opacity', 0).remove()
      }
      flashLayer.append('circle')
        .attr('cx', x).attr('cy', y).attr('r', 4)
        .attr('fill', 'none').attr('stroke', '#ffffff').attr('stroke-width', 2)
        .attr('opacity', 0.9)
        .transition().duration(800).ease(d3.easeCubicOut)
        .attr('r', 28).attr('opacity', 0).remove()
    }

    const start = Date.now()
    let lastTrail = 0

    const t = d3.timer(() => {
      const tMs = Date.now() - start
      const tSec = tMs / 1000

      g.select('.attackers').selectAll('circle.attacker')
        .each(function (d) {
          const local = Math.max(0, Math.min(1, (tMs - d.id * staggerMs) / chargeDur))
          let y = dotY(d, local)
          // Settle wobble ramps in over the last 20% of the run.
          const settle = Math.max(0, Math.min(1, (local - 0.8) / 0.2))
          y += Math.sin(tSec * d.speed + d.phase) * (innerH * d.amp) * settle
          const dx = Math.cos(tSec * (d.speed * 0.6) + d.phase) * (innerW * 0.006) * settle
          d3.select(this).attr('cy', y).attr('cx', d.x * innerW + dx)

          // Fire a crossing flash the moment an evaded dot punches the line.
          if (d.evaded && local >= 0.70 && !flashed.has(d.id)) {
            flashed.add(d.id)
            spawnFlash(d.x * innerW, defenderY)
          }
        })

      // Faint motion trails behind moving dots; fade fast.
      if (tMs - lastTrail > 90) {
        lastTrail = tMs
        const trails = g.select('.trails')
        g.select('.attackers').selectAll('circle.attacker').each(function (d) {
          const cx = +d3.select(this).attr('cx')
          const cy = +d3.select(this).attr('cy')
          trails.append('circle')
            .attr('cx', cx).attr('cy', cy).attr('r', 3)
            .attr('fill', d.evaded ? '#f85149' : '#f0883e').attr('opacity', 0.3)
            .transition().duration(700).ease(d3.easeCubicOut)
            .attr('r', 1).attr('opacity', 0).remove()
        })
      }
    })
    return () => t.stop()
  }, [dims, latest, dots, speed])

  const s = statusFor(latest)

  return (
    <div className="panel battle-panel" data-tour="battle">
      <div className="panel-header">
        <span className="panel-title">Live battle</span>
        {latest && (
          <span className={`battle-status-pill pill-${s.tag}`}>
            {s.label}
          </span>
        )}
      </div>

      <p className="battle-howto">
        How to read this: each <span className="team-red-text">🤖 red dot</span> is one
        attacker. Their height = how close they got to fooling the detector.
        The <span style={{ color: '#3fb950', fontWeight: 600 }}>🛡️ green line</span> is
        where the defender draws the line. Above the line means the attack worked.
        Below means it got caught. The <span style={{ color: '#58a6ff', fontWeight: 600 }}>
        blue band</span> at the top marks the fixed 11% QBER abort threshold.
      </p>

      <div className="battle-stage">
        <svg ref={svgRef} width="100%" height={HEIGHT} />
        {!latest && (
          <div className="battle-empty-overlay">
            <div style={{ fontSize: 40 }}>🤖 ⚔️ 🛡️</div>
            <div style={{ marginTop: 12, fontSize: 14 }}>
              Hit <strong>Run the demo</strong> to watch the fight.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
