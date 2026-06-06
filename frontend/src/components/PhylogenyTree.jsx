import { useRef, useEffect, useState, useMemo } from 'react'
import * as d3 from 'd3'
import { nodeQber, attackerCounts } from '../sample-data'

// Visual mapping:
//   x = generation, y = vertical fan inside the generation column
//   Color: red if this attacker's QBER ≥ 11% (the static rule would have
//          caught it), blue if QBER < 11% (the static rule misses; only
//          the ML defender can spot it).
//   Size: scales with fitness — bigger = sneakier (higher attacker fitness).
// This makes the "static rule vs ML defender" story visible in the tree
// itself: the more blue dots high in fitness, the more our ML defender
// is doing that the textbook rule can't.

export default function PhylogenyTree({ phylogeny, status, collapsedByDefault = true }) {
  const svgRef = useRef()
  const tooltipRef = useRef()
  const [open, setOpen] = useState(!collapsedByDefault)
  const counts = useMemo(() => attackerCounts(phylogeny), [phylogeny])

  useEffect(() => {
    if (!phylogeny || !phylogeny.nodes.length) return
    if (!open) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = svgRef.current.clientWidth
    const height = 330
    const g = svg.append('g')

    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (e) => g.attr('transform', e.transform))
    svg.call(zoom)

    const nodes = phylogeny.nodes
    const maxGen = d3.max(nodes, d => d.generation) || 1
    const genGroups = d3.group(nodes, d => d.generation)

    nodes.forEach(node => {
      const siblings = genGroups.get(node.generation)
      const idx = siblings.indexOf(node)
      const count = siblings.length
      node.x = (node.generation / maxGen) * (width - 100) + 50
      node.y = ((idx + 1) / (count + 1)) * (height - 40) + 20
    })

    const nodeMap = new Map(nodes.map(n => [n.id, n]))

    // Edges (parent → child)
    g.selectAll('line.edge')
      .data(nodes.filter(n => n.parent_id != null))
      .join('line')
      .attr('class', 'edge')
      .attr('x1', d => nodeMap.get(d.parent_id)?.x || d.x)
      .attr('y1', d => nodeMap.get(d.parent_id)?.y || d.y)
      .attr('x2', d => d.x)
      .attr('y2', d => d.y)
      .attr('stroke', '#30363d')
      .attr('stroke-width', 1)

    // Nodes — circle (uniform shape), colored by QBER vs 11% threshold,
    // sized by fitness.
    const fitnesses = nodes.map(n => n.fitness || 0)
    const rScale = d3.scaleLinear()
      .domain([d3.min(fitnesses) || 0, d3.max(fitnesses) || 1])
      .range([4, 9])

    g.selectAll('circle.node')
      .data(nodes)
      .join('circle')
      .attr('class', 'node')
      .attr('cx', d => d.x).attr('cy', d => d.y)
      .attr('r', d => rScale(d.fitness || 0))
      .attr('fill', d => {
        const q = nodeQber(d)
        if (q == null) return '#8b949e'         // unknown — grey
        return q >= 0.11 ? '#f85149' : '#58a6ff' // red: rule catches, blue: rule misses
      })
      .attr('stroke', '#0d1117')
      .attr('stroke-width', 1.2)
      .attr('opacity', 0.92)
      .attr('cursor', 'pointer')
      .on('mouseover', (e, d) => {
        const q = nodeQber(d)
        const verdict = q == null
          ? 'unknown QBER'
          : (q >= 0.11
              ? 'static 11% rule would catch this'
              : 'static rule misses this — only ML can spot it')
        const tip = d3.select(tooltipRef.current)
        tip.style('display', 'block')
          .style('left', `${e.offsetX + 10}px`)
          .style('top', `${e.offsetY - 10}px`)
          .html(`
            <strong>Gen ${d.generation}, attacker ${d.id}</strong><br/>
            Fitness: ${(d.fitness || 0).toFixed(3)}<br/>
            QBER: ${q != null ? (q * 100).toFixed(1) + '%' : '?'}<br/>
            <em>${verdict}</em>
          `)
      })
      .on('mouseout', () => {
        d3.select(tooltipRef.current).style('display', 'none')
      })

    svg.call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(0.9))

  }, [phylogeny, open])

  return (
    <div className="panel" style={{ position: 'relative' }}>
      <div className="panel-header">
        <button
          className="phylogeny-toggle"
          onClick={() => setOpen(o => !o)}
          aria-expanded={open}
          type="button"
        >
          {open ? '▼' : '▶'} Attack family tree
          <span className="phylogeny-hint">
            {' '}— optional, for the nerds
          </span>
        </button>
        {open && phylogeny && (
          <button className="panel-export" onClick={() => {
            const json = JSON.stringify(phylogeny, null, 2)
            const blob = new Blob([json], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url; a.download = 'phylogeny.json'; a.click()
          }}>Export JSON</button>
        )}
      </div>
      {!open ? null : !phylogeny ? (
        <div className="empty-state">Run an evolution to see attack lineage</div>
      ) : (
        <>
          <p className="phylogeny-lede">
            Each dot is one attacker the evolutionary gym produced. Lines connect
            parents to children across generations. <span className="phy-legend-dot phy-red" /> <strong>Red</strong> = QBER ≥ 11% (the static rule catches this).
            <span className="phy-legend-dot phy-blue" /> <strong>Blue</strong> = QBER &lt; 11% (the static rule misses; only ML catches it).
            Bigger circle = higher fitness, i.e. a sneakier attacker.
            Drag to pan, scroll to zoom; hover a node for details.
          </p>
          {counts.total > 0 && counts.aboveThreshold === 0 && (
            <div className="phylogeny-note">
              All blue — the gym evolved {counts.total} attackers that stayed
              under 11% QBER. That's the whole point: these are the attacks
              the static rule can't see, and our ML defender has to.
            </div>
          )}
          {counts.total > 0 && counts.belowThreshold === 0 && (
            <div className="phylogeny-note">
              All red — every attacker pushed QBER above 11%, so the textbook
              rule would catch all of them. The ML defender's lift here is small;
              try a higher epsilon to evolve subtler attacks.
            </div>
          )}
          <div className="tree-container">
            <svg ref={svgRef} width="100%" height="350" />
            <div ref={tooltipRef} style={{
              display: 'none', position: 'absolute', background: '#161b22',
              border: '1px solid #30363d', borderRadius: 4, padding: '6px 10px',
              fontSize: 12, fontFamily: 'var(--font-data)', color: '#e6edf3',
              pointerEvents: 'none', zIndex: 10,
            }} />
          </div>
        </>
      )}
    </div>
  )
}
