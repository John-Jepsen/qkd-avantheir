import { useRef, useEffect } from 'react'
import * as d3 from 'd3'

const ATTACK_COLORS = {
  intercept_resend: '#f85149',
  beam_splitting: '#d29922',
  pns_attack: '#a371f7',
  trojan_horse: '#f0883e',
  clean: '#3fb950',
  evolved: '#58a6ff',
}

const ATTACK_SHAPES = {
  intercept_resend: d3.symbolCircle,
  beam_splitting: d3.symbolDiamond,
  pns_attack: d3.symbolTriangle,
  trojan_horse: d3.symbolSquare,
  clean: d3.symbolCircle,
  evolved: d3.symbolStar,
}

export default function PhylogenyTree({ phylogeny, status }) {
  const svgRef = useRef()
  const tooltipRef = useRef()

  useEffect(() => {
    if (!phylogeny || !phylogeny.nodes.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = svgRef.current.clientWidth
    const height = 330

    const g = svg.append('g')

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (e) => g.attr('transform', e.transform))
    svg.call(zoom)

    const nodes = phylogeny.nodes
    const maxGen = d3.max(nodes, d => d.generation) || 1

    // Layout: x = generation, y = spread within generation
    const genGroups = d3.group(nodes, d => d.generation)

    nodes.forEach(node => {
      const siblings = genGroups.get(node.generation)
      const idx = siblings.indexOf(node)
      const count = siblings.length
      node.x = (node.generation / maxGen) * (width - 100) + 50
      node.y = ((idx + 1) / (count + 1)) * (height - 40) + 20
    })

    const nodeMap = new Map(nodes.map(n => [n.id, n]))

    // Edges
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

    // Nodes
    const symbol = d3.symbol().size(80)

    g.selectAll('path.node')
      .data(nodes)
      .join('path')
      .attr('class', 'node')
      .attr('d', d => symbol.type(ATTACK_SHAPES[d.attack_type] || d3.symbolStar)())
      .attr('transform', d => `translate(${d.x},${d.y})`)
      .attr('fill', d => ATTACK_COLORS[d.attack_type] || '#58a6ff')
      .attr('stroke', '#0d1117')
      .attr('stroke-width', 1)
      .attr('cursor', 'pointer')
      .on('mouseover', (e, d) => {
        const tip = d3.select(tooltipRef.current)
        tip.style('display', 'block')
          .style('left', `${e.offsetX + 10}px`)
          .style('top', `${e.offsetY - 10}px`)
          .html(`
            <strong>Gen ${d.generation}</strong><br/>
            Type: ${d.attack_type}<br/>
            Fitness: ${d.fitness.toFixed(3)}<br/>
            QBER: ${d.features?.qber?.toFixed(4) || '?'}
          `)
      })
      .on('mouseout', () => {
        d3.select(tooltipRef.current).style('display', 'none')
      })

    // Initial zoom to fit
    svg.call(zoom.transform, d3.zoomIdentity.translate(0, 0).scale(0.9))

  }, [phylogeny])

  return (
    <div className="panel" style={{ position: 'relative' }}>
      <div className="panel-header">
        <span className="panel-title">Attack Phylogeny</span>
        {phylogeny && (
          <button className="panel-export" onClick={() => {
            const json = JSON.stringify(phylogeny, null, 2)
            const blob = new Blob([json], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url; a.download = 'phylogeny.json'; a.click()
          }}>Export JSON</button>
        )}
      </div>
      {!phylogeny ? (
        <div className="empty-state">Run an evolution to see attack lineage</div>
      ) : (
        <div className="tree-container">
          <svg ref={svgRef} width="100%" height="350" />
          <div ref={tooltipRef} style={{
            display: 'none', position: 'absolute', background: '#161b22',
            border: '1px solid #30363d', borderRadius: 4, padding: '6px 10px',
            fontSize: 12, fontFamily: 'var(--font-data)', color: '#e6edf3',
            pointerEvents: 'none', zIndex: 10,
          }} />
        </div>
      )}
    </div>
  )
}
