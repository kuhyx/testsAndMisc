import { useEffect } from 'react'

/**
 * Prompts the user with a confirmation dialog when attempting to close/refresh the page.
 * Note: Most modern browsers ignore custom text and display a generic message.
 */
export function useBeforeUnload(when: boolean = true, message: string = '') {
  useEffect(() => {
    if (!when) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      // Setting returnValue is required for some browsers to trigger the prompt
      e.returnValue = message
      return message
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [when, message])
}
