import { useRef, useEffect } from 'react'
import * as d3 from 'd3'

export default function EvolutionChart({ generations, status }) {
  const svgRef = useRef()

  useEffect(() => {
    if (!generations.length) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const margin = { top: 20, right: 60, bottom: 30, left: 50 }
    const width = svgRef.current.clientWidth - margin.left - margin.right
    const height = 220 - margin.top - margin.bottom

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    const x = d3.scaleLinear()
      .domain([0, Math.max(generations.length - 1, 1)])
      .range([0, width])

    const y = d3.scaleLinear().domain([0, 1]).range([height, 0])

    // Grid
    g.append('g').attr('class', 'grid')
      .selectAll('line').data(y.ticks(5)).join('line')
      .attr('x1', 0).attr('x2', width)
      .attr('y1', d => y(d)).attr('y2', d => y(d))
      .attr('stroke', '#30363d').attr('stroke-dasharray', '2,2')

    // Axes
    g.append('g').attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(Math.min(generations.length, 10)).tickFormat(d3.format('d')))
      .selectAll('text,line,path').attr('stroke', '#8b949e').attr('fill', '#8b949e')

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('.0%')))
      .selectAll('text,line,path').attr('stroke', '#8b949e').attr('fill', '#8b949e')

    // Evasion rate line (red team)
    const evasionLine = d3.line()
      .x((_, i) => x(i))
      .y(d => y(d.evasion_rate))
      .curve(d3.curveMonotoneX)

    g.append('path')
      .datum(generations)
      .attr('fill', 'none')
      .attr('stroke', '#f85149')
      .attr('stroke-width', 2)
      .attr('d', evasionLine)

    // Defender accuracy line (blue team)
    const accLine = d3.line()
      .x((_, i) => x(i))
      .y(d => y(d.defender_accuracy))
      .curve(d3.curveMonotoneX)

    g.append('path')
      .datum(generations)
      .attr('fill', 'none')
      .attr('stroke', '#58a6ff')
      .attr('stroke-width', 2)
      .attr('d', accLine)

    // Legend
    const legend = g.append('g').attr('transform', `translate(${width - 140}, 0)`)
    legend.append('line').attr('x1', 0).attr('x2', 16).attr('y1', 0).attr('y2', 0).attr('stroke', '#f85149').attr('stroke-width', 2)
    legend.append('text').attr('x', 20).attr('y', 4).text('Evasion Rate').attr('fill', '#8b949e').attr('font-size', 11)
    legend.append('line').attr('x1', 0).attr('x2', 16).attr('y1', 16).attr('y2', 16).attr('stroke', '#58a6ff').attr('stroke-width', 2)
    legend.append('text').attr('x', 20).attr('y', 20).text('Defender Acc').attr('fill', '#8b949e').attr('font-size', 11)

    // Axis labels
    g.append('text').attr('x', width / 2).attr('y', height + 28).attr('text-anchor', 'middle').attr('fill', '#8b949e').attr('font-size', 11).text('Generation')

  }, [generations])

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Evolution Progress</span>
        {generations.length > 0 && (
          <span className="data-value" style={{ color: status === 'evolving' ? 'var(--yellow)' : 'var(--green)' }}>
            Gen {generations.length} {status === 'evolving' ? '...' : ''}
          </span>
        )}
      </div>
      {generations.length === 0 ? (
        <div className="empty-state">No runs yet. Click Start Evolution.</div>
      ) : (
        <div className="chart-container">
          <svg ref={svgRef} width="100%" height="250" />
        </div>
      )}
    </div>
  )
}
