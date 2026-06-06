import { useState } from 'react'
import { GLOSSARY, GLOSSARY_ORDER } from '../glossary'

export default function Glossary() {
  const [open, setOpen] = useState(false)

  return (
    <div className="glossary">
      <button
        className="glossary-toggle"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        {open ? '▼' : '▶'} Glossary — {GLOSSARY_ORDER.length} terms in plain English
      </button>
      {open && (
        <div className="glossary-grid">
          {GLOSSARY_ORDER.map(key => {
            const entry = GLOSSARY[key]
            return (
              <div key={key} className="glossary-entry">
                <strong className="glossary-term">{entry.label}</strong>
                <span className="glossary-def">{entry.short}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
