import { useEffect, useRef, useState } from 'react'
import { narrateAll } from '../narration'

export default function Narrator({ generations, status }) {
  const [ttsOn, setTtsOn] = useState(false)
  const [lastSpokenIdx, setLastSpokenIdx] = useState(-1)
  const scrollRef = useRef(null)

  const lines = narrateAll(generations)

  // Auto-scroll to newest line
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [lines.length])

  // Speak any new line when TTS is on
  useEffect(() => {
    if (!ttsOn) return
    if (lines.length === 0) return
    if (!('speechSynthesis' in window)) return
    const idx = lines.length - 1
    if (idx <= lastSpokenIdx) return
    const u = new SpeechSynthesisUtterance(lines[idx].text)
    u.rate = 1.05
    u.pitch = 1
    window.speechSynthesis.speak(u)
    setLastSpokenIdx(idx)
  }, [lines, ttsOn, lastSpokenIdx])

  // Reset spoken index when a new run starts
  useEffect(() => {
    if (generations.length === 0) setLastSpokenIdx(-1)
  }, [generations.length])

  const toggleTts = () => {
    if (ttsOn) window.speechSynthesis?.cancel()
    setTtsOn(v => !v)
  }

  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

  return (
    <div className="panel narrator-panel">
      <div className="panel-header">
        <span className="panel-title">Live commentary</span>
        {ttsSupported && (
          <button
            className={`tts-toggle ${ttsOn ? 'tts-on' : ''}`}
            onClick={toggleTts}
            aria-label={ttsOn ? 'Mute narration' : 'Speak narration'}
            title={ttsOn ? 'Mute narration' : 'Read narration aloud'}
          >
            {ttsOn ? '🔊 On' : '🔈 Off'}
          </button>
        )}
      </div>
      {lines.length === 0 ? (
        <div className="empty-state">
          The play-by-play will appear here once a run starts.
        </div>
      ) : (
        <ol className="narrator-list" ref={scrollRef}>
          {lines.map(l => (
            <li key={l.idx} className="narrator-line">{l.text}</li>
          ))}
          {status === 'evolving' && (
            <li className="narrator-line narrator-pending">
              <span className="narrator-spinner" /> waiting for next generation…
            </li>
          )}
        </ol>
      )}
    </div>
  )
}
