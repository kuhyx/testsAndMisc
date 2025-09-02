import { useBattery } from './useBattery'
import { useBeforeUnload } from './useBeforeUnload'

export function App() {
  const { supported, loading, level, charging, chargingTime, dischargingTime, error } = useBattery()
  // Ask for confirmation when leaving the page (custom message may be ignored by some browsers)
  useBeforeUnload(true, 'Are you sure you want to leave this page? Unsaved battery info will be lost.')

  if (!supported) {
    return (
      <div className="app">
        <h1>Battery Status</h1>
        <p>Battery Status API is not supported by this browser.</p>
        <p>Tip: On some desktop browsers, this API may be disabled for privacy reasons.</p>
      </div>
    )
  }

  return (
    <div className="app">
      <h1>Battery Status</h1>
      {loading ? (
        <p>Loading…</p>
      ) : error ? (
        <p className="error">{error}</p>
      ) : (
        <div className="card">
          <div className="row">
            <span className="label">Charging:</span>
            <span className="value" data-charging={charging}>{charging ? 'Yes' : 'No'}</span>
          </div>
          <div className="row">
            <span className="label">Level:</span>
            <span className="value">{Math.round(level * 100)}%</span>
          </div>
          {typeof chargingTime === 'number' && charging && (
            <div className="row">
              <span className="label">Time to full:</span>
              <span className="value">{formatTime(chargingTime)}</span>
            </div>
          )}
          {typeof dischargingTime === 'number' && !charging && (
            <div className="row">
              <span className="label">Time to empty:</span>
              <span className="value">{formatTime(dischargingTime)}</span>
            </div>
          )}
        </div>
      )}
      <footer>
        <small>Powered by the Battery Status API (where available)</small>
      </footer>
    </div>
  )
}

function formatTime(seconds: number) {
  if (!isFinite(seconds) || seconds < 0) return 'N/A'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h === 0) return `${m}m`
  return `${h}h ${m}m`
}
