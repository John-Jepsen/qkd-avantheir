import { useState, useRef, useEffect } from 'react'
import { GLOSSARY } from '../glossary'

export default function Tooltip({ term, children }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const entry = GLOSSARY[term]

  useEffect(() => {
    if (!open) return
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [open])

  if (!entry) return <>{children || term}</>

  return (
    <span className="tooltip-wrap" ref={ref}>
      <span
        className="tooltip-term"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={() => setOpen(o => !o)}
        tabIndex={0}
      >
        {children || entry.label}
      </span>
      {open && (
        <span className="tooltip-bubble" role="tooltip">
          <strong>{entry.label}</strong>
          <br />
          {entry.short}
        </span>
      )}
    </span>
  )
}
