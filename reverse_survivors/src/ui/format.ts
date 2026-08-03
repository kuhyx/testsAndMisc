export const fmtTime = (seconds: number): string => {
  const whole = Math.floor(seconds)
  const m = Math.floor(whole / 60)
  const s = whole % 60
  return `${String(m)}:${String(s).padStart(2, '0')}`
}
