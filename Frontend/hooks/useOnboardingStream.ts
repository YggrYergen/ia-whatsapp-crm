'use client'

/**
 * useOnboardingStream — SSE streaming hook for the onboarding config agent.
 *
 * Connects to POST /api/onboarding/chat and parses Server-Sent Events:
 *   - thinking     → Matrix visualizer text (reasoning summaries)
 *   - text_delta   → Chat bubble text (response deltas)
 *   - field_update → A configuration field was confirmed (turns green)
 *   - progress     → Overall completion progress
 *   - done         → Stream complete
 *   - config_complete → All fields done, system prompt generated
 *   - error        → Error occurred
 *
 * Observability: Every failure path → console.error + Sentry.
 *
 * Ref: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
 * Ref: https://platform.openai.com/docs/api-reference/responses/streaming
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import * as Sentry from '@sentry/nextjs'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface OnboardingMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface FieldStatus {
  [fieldName: string]: {
    complete: boolean
    value: string
    confidence: 'confirmed' | 'inferred'
  }
}

export interface StreamProgress {
  fields_complete: number
  fields_total: number
  percentage: number
}

interface UseOnboardingStreamReturn {
  /** All chat messages (user + assistant) */
  messages: OnboardingMessage[]
  /** Currently streaming response text (not yet finalized) */
  currentText: string
  /** Current reasoning/thinking text for Matrix visualizer */
  thinkingText: string
  /** Whether the model is currently in "thinking" mode */
  isThinking: boolean
  /** Whether we're streaming a response */
  isStreaming: boolean
  /** Field completion status */
  fields: FieldStatus
  /** Overall progress */
  progress: StreamProgress
  /** Whether configuration is complete */
  isConfigComplete: boolean
  /** Generated system prompt (when complete) */
  generatedPrompt: string
  /** Error message if something went wrong */
  error: string | null
  /** Whether persisted history has been loaded (true = ready for initial greeting) */
  historyLoaded: boolean
  /** Send a message to the config agent */
  sendMessage: (message: string) => Promise<void>
  /** Reset all state */
  reset: () => void
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ONBOARDING_FIELDS = [
  'business_name', 'business_type', 'business_description',
  'target_audience', 'services_offered', 'business_hours',
  'tone_of_voice', 'special_instructions', 'greeting_message',
  'escalation_rules', 'phone_number',
] as const

const SSE_ACTIVITY_TIMEOUT_MS = 90_000 // 90s inactivity timeout — resets on each received event

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useOnboardingStream(tenantId: string | null): UseOnboardingStreamReturn {
  const [messages, setMessages] = useState<OnboardingMessage[]>([])
  const [currentText, setCurrentText] = useState('')
  const [thinkingText, setThinkingText] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [fields, setFields] = useState<FieldStatus>({})
  const [progress, setProgress] = useState<StreamProgress>({
    fields_complete: 0,
    fields_total: ONBOARDING_FIELDS.length,
    percentage: 0,
  })
  const [isConfigComplete, setIsConfigComplete] = useState(false)
  const [generatedPrompt, setGeneratedPrompt] = useState('')
  const [error, setError] = useState<string | null>(null)
  
  // Abort controller for cancelling in-flight requests
  const abortRef = useRef<AbortController | null>(null)
  // Conversation history ref (avoids stale closure in sendMessage)
  const historyRef = useRef<Array<{ role: string; content: string }>>([])
  // Whether persisted history has been loaded from server
  const [historyLoaded, setHistoryLoaded] = useState(false)

  // ─── Load persisted history on mount ──────────────────────────────
  // Enables: session resumability + superadmin debugging.
  // If the DB has messages, we populate state from them instead of starting fresh.
  // Also restores field completion status and progress bar.
  useEffect(() => {
    if (!tenantId || historyLoaded) return

    const loadPersistedHistory = async () => {
      const _where = 'useOnboardingStream.loadPersistedHistory'
      try {
        console.debug(`[${_where}] Loading persisted history | tenant=${tenantId}`)
        Sentry.addBreadcrumb({ category: 'onboarding', message: 'Loading persisted history', data: { tenantId } })

        const response = await fetch(`/api/onboarding/chat/history?tenant_id=${tenantId}`)
        if (!response.ok) {
          console.warn(`[${_where}] History fetch failed: HTTP ${response.status}`)
          setHistoryLoaded(true) // Don't block — proceed without history
          return
        }

        const data = await response.json()
        const persisted = data.messages || []

        if (persisted.length > 0) {
          console.info(`[${_where}] Resuming session with ${persisted.length} persisted messages | tenant=${tenantId}`)
          Sentry.addBreadcrumb({ category: 'onboarding', message: `Resumed with ${persisted.length} messages` })

          // Rebuild messages array and history ref from persisted data
          const restoredMessages: OnboardingMessage[] = persisted
            .filter((m: any) => m.role === 'user' || m.role === 'assistant')
            .map((m: any) => ({
              role: m.role as 'user' | 'assistant',
              content: m.content,
              timestamp: new Date(m.created_at).getTime(),
            }))

          setMessages(restoredMessages)
          historyRef.current = persisted
            .filter((m: any) => m.role === 'user' || m.role === 'assistant')
            .map((m: any) => ({ role: m.role, content: m.content }))
        } else {
          console.debug(`[${_where}] No persisted messages — fresh session | tenant=${tenantId}`)
        }

        // Restore field completion status if available (enables progress bar survival on refresh)
        if (data.fields_status && Object.keys(data.fields_status).length > 0) {
          console.info(`[${_where}] Restoring field status: ${data.fields_complete}/${data.fields_total} complete`)
          setFields(data.fields_status)
          setProgress({
            fields_complete: data.fields_complete ?? 0,
            fields_total: data.fields_total ?? ONBOARDING_FIELDS.length,
            percentage: data.fields_total ? Math.round((data.fields_complete / data.fields_total) * 100) : 0,
          })
        }

        // Restore configuration_complete flag if the onboarding was already finalized
        if (data.configuration_complete) {
          console.info(`[${_where}] Configuration already complete — skipping to completion state`)
          setIsConfigComplete(true)
        }
      } catch (loadErr: any) {
        console.error(`[${_where}] Failed to load history:`, loadErr)
        Sentry.captureException(loadErr, {
          extra: { where: _where, tenant_id: tenantId },
        })
        // Non-fatal: proceed with empty state
      } finally {
        setHistoryLoaded(true)
      }
    }

    loadPersistedHistory()
  }, [tenantId, historyLoaded])

  const reset = useCallback(() => {
    setMessages([])
    setCurrentText('')
    setThinkingText('')
    setIsThinking(false)
    setIsStreaming(false)
    setFields({})
    setProgress({ fields_complete: 0, fields_total: ONBOARDING_FIELDS.length, percentage: 0 })
    setIsConfigComplete(false)
    setGeneratedPrompt('')
    setError(null)
    historyRef.current = []
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
  }, [])

  const sendMessage = useCallback(async (message: string) => {
    const _where = 'useOnboardingStream.sendMessage'

    if (!tenantId) {
      const errMsg = `[${_where}] Cannot send — tenantId is null`
      console.error(errMsg)
      Sentry.captureMessage(errMsg, 'error')
      setError('No se encontró el tenant. Recarga la página.')
      return
    }

    if (isStreaming) {
      console.warn(`[${_where}] Already streaming — ignoring duplicate send`)
      return
    }

    // Cancel any previous request
    if (abortRef.current) {
      abortRef.current.abort()
    }
    abortRef.current = new AbortController()

    // Add user message (skip for greeting — empty messages shouldn't appear in UI)
    if (message.trim()) {
      const userMsg: OnboardingMessage = {
        role: 'user',
        content: message,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, userMsg])
    }
    historyRef.current.push({ role: 'user', content: message })

    // Clear state for new response
    setCurrentText('')
    setThinkingText('')
    setIsThinking(false)
    setIsStreaming(true)
    setError(null)

    // Build fields_status map for the backend
    const fieldsStatusMap: Record<string, boolean> = {}
    for (const f of ONBOARDING_FIELDS) {
      fieldsStatusMap[f] = fields[f]?.complete ?? false
    }

    try {
      // POST with streaming response
      const response = await fetch('/api/onboarding/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          tenant_id: tenantId,
          conversation_history: historyRef.current.slice(0, -1), // Exclude current msg (backend adds it)
          fields_status: fieldsStatusMap,
        }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        const errText = await response.text().catch(() => 'Unknown error')
        const errMsg = `[${_where}] HTTP ${response.status}: ${errText.slice(0, 300)}`
        console.error(errMsg)
        Sentry.captureMessage(errMsg, 'error')
        setError(`Error del servidor (${response.status}). Intenta de nuevo.`)
        setIsStreaming(false)
        return
      }

      if (!response.body) {
        const errMsg = `[${_where}] Response body is null — SSE not supported`
        console.error(errMsg)
        Sentry.captureMessage(errMsg, 'error')
        setError('Tu navegador no soporta streaming. Actualiza tu navegador.')
        setIsStreaming(false)
        return
      }

      // Parse SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedResponse = ''
      let buffer = ''
      let thinkingLines: string[] = []
      // Local mutable flag — NOT React state. React state (isThinking) is a
      // stale closure inside this async loop and can't be used for logic.
      // This flag correctly tracks whether we're in the thinking phase.
      let thinkingActive = false
      let configCompleteReceived = false
      let autoCompleteTimer: ReturnType<typeof setTimeout> | null = null

      // Activity-based timeout: resets every time we receive data.
      // This prevents false timeouts on long sessions (10+ tool calls)
      // while still catching genuinely stalled streams.
      let timeoutId: ReturnType<typeof setTimeout>
      const resetTimeout = () => {
        clearTimeout(timeoutId)
        timeoutId = setTimeout(() => {
          const errMsg = `[${_where}] Stream inactivity timeout after ${SSE_ACTIVITY_TIMEOUT_MS}ms | tenant=${tenantId}`
          console.error(errMsg)
          Sentry.captureMessage(errMsg, 'warning')
          abortRef.current?.abort()
          setError('La respuesta tardó demasiado. Intenta de nuevo.')
          setIsStreaming(false)
        }, SSE_ACTIVITY_TIMEOUT_MS)
      }
      resetTimeout() // Start initial timeout

      // SSE parser state — MUST persist across reader.read() calls!
      // When TCP splits an SSE event across two chunks, the 'event:' line
      // arrives in chunk N and the 'data:' line in chunk N+1. If these
      // variables are re-initialized per read(), the event type from chunk N
      // is lost and the data line is silently dropped.
      // ROOT CAUSE of message disappearance bug (discovered 2026-04-15).
      let currentEventType = ''
      let currentEventData = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          // Reset activity timeout — stream is alive
          resetTimeout()

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE events from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              currentEventData = line.slice(6)

              if (!currentEventType || !currentEventData) continue

              try {
                const data = JSON.parse(currentEventData)

                // ── SSE Observability ──────────────────────────────────
                // Log every event so streaming bugs are VISIBLE in DevTools.
                // Without this, text disappearance bugs are completely invisible.
                if (currentEventType !== 'text_delta' && currentEventType !== 'thinking') {
                  // Don't spam on high-frequency events, but log all discrete ones
                  console.debug(
                    `[SSE:${currentEventType}]`,
                    currentEventType === 'done'
                      ? { content_len: (data.content || '').length, accumulated_len: accumulatedResponse.length }
                      : data
                  )
                }
                Sentry.addBreadcrumb({
                  category: 'onboarding.sse',
                  message: `SSE event: ${currentEventType}`,
                  level: 'info',
                  data: { type: currentEventType, content_preview: JSON.stringify(data).slice(0, 200) },
                })

                switch (currentEventType) {
                  case 'thinking': {
                    thinkingActive = true
                    setIsThinking(true)
                    const newText = data.text || ''
                    // Accumulate thinking text, keep max 3 lines
                    thinkingLines.push(newText)
                    // Split by actual newlines within each chunk too
                    const allLines = thinkingLines.join('').split('\n')
                    // Keep last 3 lines
                    const visible = allLines.slice(-3).join('\n')
                    setThinkingText(visible)
                    break
                  }

                  case 'text_delta': {
                    // First text_delta → thinking phase ends. Must use local
                    // mutable flag (not React state) because isThinking from
                    // the closure is stale.
                    if (thinkingActive) {
                      thinkingActive = false
                      setIsThinking(false)
                      setThinkingText('')
                      thinkingLines = []
                    }
                    const delta = data.delta || ''
                    accumulatedResponse += delta
                    setCurrentText(accumulatedResponse)
                    console.warn(`[${_where}] text_delta received | len=${accumulatedResponse.length} | preview="${accumulatedResponse.slice(0,60)}…"`)
                    break
                  }

                  case 'field_update': {
                    const fieldName = data.field
                    if (fieldName) {
                      setFields(prev => ({
                        ...prev,
                        [fieldName]: {
                          complete: true,
                          value: data.value || '',
                          confidence: data.confidence || 'confirmed',
                        },
                      }))
                    }
                    break
                  }

                  case 'progress': {
                    setProgress({
                      fields_complete: data.fields_complete ?? 0,
                      fields_total: data.fields_total ?? ONBOARDING_FIELDS.length,
                      percentage: data.percentage ?? 0,
                    })
                    break
                  }

                  case 'config_complete': {
                    setIsConfigComplete(true)
                    setGeneratedPrompt(data.system_prompt || '')
                    configCompleteReceived = true
                    if (autoCompleteTimer) {
                      clearTimeout(autoCompleteTimer)
                      autoCompleteTimer = null
                    }
                    break
                  }

                  case 'done': {
                    // Finalize the assistant message
                    const finalContent = data.content || accumulatedResponse
                    console.warn(
                      `[${_where}] DONE event | finalContent.len=${finalContent.length} | ` +
                      `preview="${finalContent.slice(0,80)}…" | all_complete=${data.all_complete}`
                    )

                    // FIX 2026-04-15 v3: DEDUP ARCHITECTURE — never clear currentText here.
                    // Instead, add the message to the array and let currentText stay.
                    // ConfigChat's rendering deduplicates: if the last message content
                    // matches currentText, the streaming bubble is hidden automatically.
                    // This guarantees zero gap frames — text is ALWAYS visible somewhere.
                    if (finalContent.trim()) {
                      setMessages(prev => {
                        const updated = [
                          ...prev,
                          {
                            role: 'assistant' as const,
                            content: finalContent,
                            timestamp: Date.now(),
                          },
                        ]
                        console.warn(`[${_where}] DONE → setMessages | count=${updated.length}`)
                        return updated
                      })
                      historyRef.current.push({ role: 'assistant', content: finalContent })
                    }
                    // Clear thinking state (NOT currentText — that stays for dedup)
                    setIsThinking(false)
                    setThinkingText('')
                    // Reset local accumulators for next turn
                    accumulatedResponse = ''
                    thinkingLines = []

                    // ── Auto-complete fallback ────────────────────────────
                    // If the backend says all fields are done but config_complete
                    // hasn't arrived, start a 10s fallback timer. This handles
                    // edge cases where the model never calls mark_configuration_complete.
                    // FIX 2026-04-15: added as client-side safety net.
                    if (data.all_complete && !configCompleteReceived) {
                      if (autoCompleteTimer) clearTimeout(autoCompleteTimer)
                      autoCompleteTimer = setTimeout(() => {
                        if (!configCompleteReceived) {
                          console.warn(
                            `[${_where}] Auto-completing: all fields done but config_complete never received | tenant=${tenantId}`
                          )
                          Sentry.captureMessage(
                            'Onboarding auto-complete fallback triggered (frontend)',
                            'warning'
                          )
                          setIsConfigComplete(true)
                        }
                      }, 10_000)
                    }
                    break
                  }

                  case 'error': {
                    const errMsg = data.message || 'Error desconocido del servidor'
                    console.error(`[${_where}] SSE error event | tenant=${tenantId} | msg: ${errMsg}`)
                    Sentry.captureMessage(`Config agent SSE error: ${errMsg}`, 'error')
                    setError(errMsg)
                    break
                  }

                  default:
                    console.warn(`[${_where}] Unknown SSE event type: ${currentEventType}`)
                    break
                }
              } catch (parseErr) {
                console.error(
                  `[${_where}] SSE data JSON parse failed | event=${currentEventType} | ` +
                  `data_preview=${currentEventData.slice(0, 200)} | tenant=${tenantId}`,
                  parseErr
                )
                Sentry.captureException(parseErr, {
                  extra: {
                    where: _where,
                    event_type: currentEventType,
                    data_preview: currentEventData.slice(0, 500),
                    tenant_id: tenantId,
                  },
                })
              }

              // Reset for next event
              currentEventType = ''
              currentEventData = ''
            }
          }
        }
      } finally {
        clearTimeout(timeoutId)
        if (autoCompleteTimer) {
          clearTimeout(autoCompleteTimer)
          autoCompleteTimer = null
        }
      }
    } catch (fetchErr: any) {
      if (fetchErr.name === 'AbortError') {
        console.info(`[${_where}] Stream aborted (expected) | tenant=${tenantId}`)
        return
      }

      const errMsg = `[${_where}] Fetch failed | tenant=${tenantId} | error=${String(fetchErr).slice(0, 300)}`
      console.error(errMsg, fetchErr)
      Sentry.captureException(fetchErr, {
        extra: {
          where: _where,
          tenant_id: tenantId,
          message_length: message.length,
          history_length: historyRef.current.length,
        },
      })
      setError('Error de conexión. Verifica tu internet e intenta de nuevo.')
    } finally {
      console.warn(`[${_where}] Stream ended (finally) | tenant=${tenantId}`)
      setIsStreaming(false)
      setCurrentText('') // Safe to clear now — stream is truly done
      setIsThinking(false)
      setThinkingText('')
      abortRef.current = null
    }
  }, [tenantId, isStreaming, fields])

  return {
    messages,
    currentText,
    thinkingText,
    isThinking,
    isStreaming,
    fields,
    progress,
    isConfigComplete,
    generatedPrompt,
    error,
    historyLoaded,
    sendMessage,
    reset,
  }
}
