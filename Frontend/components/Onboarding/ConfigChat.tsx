'use client'

/**
 * ConfigChat — Step 2: AI configuration chat interface with Matrix Thought Visualizer.
 *
 * Layout: Dark sci-fi themed chat with:
 *   - Top: ConfigProgress (field completion indicator)
 *   - Middle: Chat messages area (scrollable)
 *   - Bottom-float: Matrix Thought Visualizer (when thinking)
 *   - Bottom: Message input
 *
 * The Matrix Visualizer:
 *   - Dark bg, green monospace font (JetBrains Mono), subtle glow
 *   - Max 3 lines visible, oldest fades as new lines appear
 *   - Disappears with fade-out when first text_delta arrives
 *
 * Observability: Sentry on all error paths.
 *
 * Ref implementation_plan.md §"Streaming UX Spec — Matrix Thought Visualizer"
 */

import React, { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, AlertCircle } from 'lucide-react'
import { useOnboardingStream, type OnboardingMessage } from '@/hooks/useOnboardingStream'
import ConfigProgress from './ConfigProgress'
import * as Sentry from '@sentry/nextjs'

interface ConfigChatProps {
  tenantId: string
  onConfigComplete: () => void
}

export default function ConfigChat({ tenantId, onConfigComplete }: ConfigChatProps) {
  const [inputValue, setInputValue] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const greetingSentRef = useRef(false) // Guard against double-send in StrictMode

  const {
    messages,
    currentText,
    thinkingText,
    isThinking,
    isStreaming,
    fields,
    progress,
    isConfigComplete,
    error,
    historyLoaded,
    sendMessage,
  } = useOnboardingStream(tenantId)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentText, thinkingText])

  // ─── Provisioning progress animation ────────────────────────────────
  const [provisionStep, setProvisionStep] = useState(-1) // -1 = not started
  const PROVISION_STEPS = [
    { label: 'Guardando configuración...', icon: '💾' },
    { label: 'Generando personalidad de tu asistente...', icon: '🧠' },
    { label: 'Activando herramientas...', icon: '🔧' },
    { label: '¡Tu asistente está listo!', icon: '✅' },
  ]

  // When config is complete, animate through provisioning steps
  useEffect(() => {
    if (!isConfigComplete || provisionStep >= 0) return

    // Start provisioning animation
    setProvisionStep(0)
    const timers: ReturnType<typeof setTimeout>[] = []

    PROVISION_STEPS.forEach((_, i) => {
      if (i === 0) return // Already at step 0
      timers.push(setTimeout(() => setProvisionStep(i), (i) * 1500))
    })

    // After all steps, wait a beat then transition
    timers.push(setTimeout(() => {
      onConfigComplete()
    }, PROVISION_STEPS.length * 1500 + 800))

    return () => timers.forEach(clearTimeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConfigComplete, onConfigComplete])

  // Auto-send initial greeting — only after persisted history loads.
  // If history has messages (resumed session), skip the greeting.
  // greetingSentRef prevents double-send from React StrictMode double-invoke.
  useEffect(() => {
    if (!historyLoaded) return // Wait for DB history to load first
    if (messages.length > 0) return // Already have messages (resumed session)
    if (isStreaming) return // Already streaming
    if (greetingSentRef.current) return // Already sent (StrictMode guard)

    greetingSentRef.current = true
    sendMessage('').catch((err) => {
      greetingSentRef.current = false // Allow retry on failure
      console.error('[ConfigChat] Initial greeting failed:', err)
      Sentry.captureException(err, {
        extra: { where: 'ConfigChat.initialGreeting', tenant_id: tenantId },
      })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyLoaded])

  const handleSend = async () => {
    const trimmed = inputValue.trim()
    if (!trimmed || isStreaming) return

    setInputValue('')

    try {
      await sendMessage(trimmed)
    } catch (err: any) {
      console.error('[ConfigChat] sendMessage failed:', err)
      Sentry.captureException(err, {
        extra: { where: 'ConfigChat.handleSend', tenant_id: tenantId, message_length: trimmed.length },
      })
    }

    // Re-focus input after send
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="fixed inset-0 z-[100] bg-slate-950 flex flex-col animate-onboarding-in">
      {/* ─── Provisioning Progress Overlay ─── */}
      {provisionStep >= 0 && (
        <div className="absolute inset-0 z-[200] bg-slate-950/98 backdrop-blur-md flex items-center justify-center animate-fadeIn">
          <div className="flex flex-col items-center gap-8 p-8">
            {/* Spinning ring */}
            <div className="relative w-24 h-24">
              <div className={`absolute inset-0 rounded-full border-4 border-slate-800 ${provisionStep < PROVISION_STEPS.length - 1 ? 'animate-spin' : ''}`}
                style={{ borderTopColor: provisionStep < PROVISION_STEPS.length - 1 ? '#10b981' : '#10b981', animationDuration: '1.5s' }} />
              <div className={`absolute inset-2 rounded-full bg-slate-900/80 flex items-center justify-center transition-all duration-700
                ${provisionStep === PROVISION_STEPS.length - 1 ? 'scale-110 shadow-[0_0_40px_rgba(16,185,129,0.4)]' : ''}`}>
                <span className="text-3xl transition-all duration-500">{PROVISION_STEPS[provisionStep]?.icon}</span>
              </div>
              {/* Glow ring on completion */}
              {provisionStep === PROVISION_STEPS.length - 1 && (
                <div className="absolute -inset-2 rounded-full border-2 border-emerald-400/30 animate-ping" />
              )}
            </div>

            {/* Steps list */}
            <div className="flex flex-col gap-3 min-w-[280px]">
              {PROVISION_STEPS.map((s, i) => (
                <div key={i}
                  className={`flex items-center gap-3 transition-all duration-500
                    ${i <= provisionStep ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs transition-all duration-500
                    ${i < provisionStep ? 'bg-emerald-500/20 text-emerald-400' :
                      i === provisionStep ? 'bg-emerald-500/30 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]' :
                      'bg-slate-800 text-slate-600'}`}>
                    {i < provisionStep ? '✓' : i === provisionStep ? (
                      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                    ) : '·'}
                  </div>
                  <span className={`text-sm transition-colors duration-300
                    ${i < provisionStep ? 'text-emerald-400/70' :
                      i === provisionStep ? 'text-white font-medium' :
                      'text-slate-600'}`}>
                    {s.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {/* ─── Header ─── */}
      <div className="flex-shrink-0 border-b border-slate-800/80 bg-slate-950/95 backdrop-blur-sm px-4 py-3 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Asistente de Configuración</h2>
            <p className="text-[11px] text-slate-500">
              {isStreaming ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                  {isThinking ? 'Analizando...' : 'Escribiendo...'}
                </span>
              ) : (
                'Configuración guiada por IA'
              )}
            </p>
          </div>
        </div>

        {/* Progress indicator */}
        <ConfigProgress fields={fields} progress={progress} />
      </div>

      {/* ─── Chat messages area ─── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 dark-scrollbar">
        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} />
        ))}

        {/* Currently streaming response — show only while actively streaming */}
        {isStreaming && currentText ? (
          <div className="flex gap-2 items-start">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="bg-slate-900/70 border border-slate-800/50 rounded-xl rounded-tl-sm px-3 py-2 max-w-[85%]">
              <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">{currentText}</p>
              <span className="inline-block w-1.5 h-4 bg-emerald-400 rounded-sm animate-pulse ml-0.5" />
            </div>
          </div>
        ) : null}

        {/* Typing indicator when no text yet but is streaming */}
        {isStreaming && !currentText && !isThinking && messages.length > 0 && (
          <div className="flex gap-2 items-start">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="bg-slate-900/70 border border-slate-800/50 rounded-xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* ─── Matrix Thought Visualizer ─── */}
      {(isThinking || thinkingText) && (
        <div className={`
          flex-shrink-0 mx-4 mb-2 animate-matrix-glow
          ${!isThinking && thinkingText ? 'animate-matrix-exit' : ''}
        `}>
          <div className="bg-slate-950 border border-emerald-900/30 rounded-lg px-3 py-2 overflow-hidden">
            <div className="flex items-center gap-2 mb-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] font-mono text-emerald-700 uppercase tracking-widest">
                reasoning
              </span>
            </div>
            <pre className="font-mono text-[11px] text-emerald-500/70 leading-relaxed whitespace-pre-wrap break-words max-h-[4.5rem] overflow-hidden">
              {thinkingText || '█'}
            </pre>
          </div>
        </div>
      )}

      {/* ─── Error display ─── */}
      {error && (
        <div className="flex-shrink-0 mx-4 mb-2">
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span className="text-xs text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* ─── Config complete banner ─── */}
      {isConfigComplete && (
        <div className="flex-shrink-0 mx-4 mb-2">
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-4 py-3 text-center">
            <p className="text-sm font-semibold text-emerald-400">🎉 ¡Configuración completa!</p>
            <p className="text-xs text-emerald-500/70 mt-1">Preparando tu panel...</p>
          </div>
        </div>
      )}

      {/* ─── Input area ─── */}
      <div className="flex-shrink-0 border-t border-slate-800/80 bg-slate-950/95 backdrop-blur-sm p-3">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming || isConfigComplete}
            placeholder={
              isConfigComplete
                ? '✅ Configuración finalizada'
                : isStreaming
                  ? 'Esperando respuesta...'
                  : 'Escribe tu respuesta...'
            }
            className="flex-1 bg-slate-900/50 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isStreaming || isConfigComplete}
            className={`
              p-2.5 rounded-lg transition-all
              ${inputValue.trim() && !isStreaming && !isConfigComplete
                ? 'bg-emerald-500 text-white hover:bg-emerald-400 active:scale-95'
                : 'bg-slate-800 text-slate-600 cursor-not-allowed'
              }
            `}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Chat Bubble Component ────────────────────────────────────────────────────

function ChatBubble({ message }: { message: OnboardingMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-2 items-start ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`
        w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5
        ${isUser
          ? 'bg-slate-700'
          : 'bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20'
        }
      `}>
        {isUser ? (
          <User className="w-4 h-4 text-slate-400" />
        ) : (
          <Bot className="w-4 h-4 text-emerald-400" />
        )}
      </div>
      <div className={`
        rounded-xl px-3 py-2 max-w-[85%]
        ${isUser
          ? 'bg-emerald-500/15 border border-emerald-500/20 rounded-tr-sm'
          : 'bg-slate-900/70 border border-slate-800/50 rounded-tl-sm'
        }
      `}>
        <p className={`text-sm whitespace-pre-wrap leading-relaxed ${isUser ? 'text-emerald-100' : 'text-slate-200'}`}>
          {message.content}
        </p>
      </div>
    </div>
  )
}
