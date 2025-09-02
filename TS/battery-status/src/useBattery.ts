import { useEffect, useState } from 'react'

type BatteryManagerLike = {
  charging: boolean
  chargingTime: number
  dischargingTime: number
  level: number
  addEventListener?: (type: string, listener: () => void) => void
  removeEventListener?: (type: string, listener: () => void) => void
  onchargingchange?: (() => void) | null
  onlevelchange?: (() => void) | null
  onchargingtimechange?: (() => void) | null
  ondischargingtimechange?: (() => void) | null
}

declare global {
  interface Navigator {
    getBattery?: () => Promise<BatteryManagerLike>
  }
}

export function useBattery() {
  const [supported, setSupported] = useState<boolean>(true)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [state, setState] = useState<Omit<BatteryManagerLike, 'addEventListener' | 'removeEventListener'>>({
    charging: false,
    chargingTime: Infinity,
    dischargingTime: Infinity,
    level: 1
  })

  useEffect(() => {
    let battery: BatteryManagerLike | null = null
    let unsub: (() => void) | undefined

    const init = async () => {
      if (!navigator.getBattery) {
        setSupported(false)
        setLoading(false)
        return
      }
      try {
        battery = await navigator.getBattery!()
        if (!battery) return
        const sync = () =>
          setState({
            charging: battery!.charging,
            chargingTime: battery!.chargingTime,
            dischargingTime: battery!.dischargingTime,
            level: battery!.level
          })
        sync()

        const onChange = () => sync()

        battery.addEventListener?.('chargingchange', onChange)
        battery.addEventListener?.('levelchange', onChange)
        battery.addEventListener?.('chargingtimechange', onChange)
        battery.addEventListener?.('dischargingtimechange', onChange)

        // Fallback for browsers without addEventListener on BatteryManager
        if (!battery.addEventListener && 'onlevelchange' in battery) {
          battery.onchargingchange = onChange
          battery.onlevelchange = onChange
          battery.onchargingtimechange = onChange
          battery.ondischargingtimechange = onChange
        }

        unsub = () => {
          battery?.removeEventListener?.('chargingchange', onChange)
          battery?.removeEventListener?.('levelchange', onChange)
          battery?.removeEventListener?.('chargingtimechange', onChange)
          battery?.removeEventListener?.('dischargingtimechange', onChange)
          if (!battery?.removeEventListener) {
            if (battery) {
              battery.onchargingchange = null
              battery.onlevelchange = null
              battery.onchargingtimechange = null
              battery.ondischargingtimechange = null
            }
          }
        }

        setLoading(false)
      } catch (e: any) {
        setError(e?.message ?? 'Failed to read battery status')
        setLoading(false)
      }
    }

    init()
    return () => {
      unsub?.()
    }
  }, [])

  return {
    supported,
    loading,
    error,
    ...state
  }
}
