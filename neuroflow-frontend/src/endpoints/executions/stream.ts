import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getAccessToken } from '@/api'
import { env } from '@/config/env'
import type { ExecutionEvent } from '@/types/executions'
import { executionKeys } from './keys'

// Browsers' native EventSource cannot send an Authorization header, so
// this is a hand-rolled SSE reader over fetch()'s streaming body instead
// of a library dependency -- docs/12-execution-engine.md #12.10.
//
// The sequence number is what lets a reconnect detect a gap: rather than
// try to patch in-memory state from a partial stream, a gap invalidates
// the execution detail query so the UI refetches the authoritative state.
export function useExecutionStream(
  executionId: string | null,
  onEvent: (event: ExecutionEvent) => void,
): void {
  const queryClient = useQueryClient()
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    if (!executionId) return
    const id = executionId
    const controller = new AbortController()
    let lastSequence = 0

    async function run() {
      try {
        const token = getAccessToken()
        const response = await fetch(
          `${env.apiBaseUrl}/executions/${id}/stream`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
          },
        )
        if (!response.ok || !response.body) {
          throw new Error(`Stream request failed: ${response.status}`)
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const chunks = buffer.split('\n\n')
          buffer = chunks.pop() ?? ''
          for (const chunk of chunks) {
            const dataLine = chunk.split('\n').find((line) => line.startsWith('data: '))
            if (!dataLine) continue
            const payload = JSON.parse(dataLine.slice('data: '.length)) as ExecutionEvent
            if (lastSequence !== 0 && payload.sequence !== lastSequence + 1) {
              queryClient.invalidateQueries({
                queryKey: executionKeys.detail(executionId),
              })
            }
            lastSequence = payload.sequence
            onEventRef.current(payload)
          }
        }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          queryClient.invalidateQueries({ queryKey: executionKeys.detail(executionId) })
        }
      }
    }

    void run()
    return () => controller.abort()
  }, [executionId, queryClient])
}
