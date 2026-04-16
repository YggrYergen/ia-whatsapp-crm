'use client'

/**
 * /chats/sandbox — Standalone sandbox chat for newcomers to test their AI assistant.
 *
 * Architecture:
 *   - Auto-creates a sandbox pseudo-contact on first visit.
 *   - Uses POST /api/sandbox/chat — 100% ISOLATED from the WhatsApp webhook pipeline.
 *   - The backend uses the OpenAI Responses API (NOT Chat Completions).
 *   - Messages are stored in `messages` table; Supabase Realtime delivers to UI.
 *   - Always accessible at `/chats/sandbox` regardless of onboarding state.
 *
 * ISOLATION:
 *   - /api/sandbox/chat does NOT import TenantContext, ProcessMessageUseCase,
 *     MetaGraphAPIClient, LLMFactory, or tool_registry.
 *   - Zero risk to the production WhatsApp webhook path.
 *
 * Feedback system:
 *   - Each message bubble has an inline comment input (appears on hover/tap).
 *   - "Enviar Prueba" saves the annotated chat to `test_feedback` (history + notes).
 *   - No new DB schema required — uses existing history/notes JSONB columns.
 *
 * Observability: All error paths → console.error + Sentry.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Bot, Send, ArrowLeft, Sparkles, RefreshCw, AlertCircle, MessageSquare, CheckCircle2, Loader2 } from 'lucide-react'
import { useTenant } from '@/contexts/TenantContext'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import * as Sentry from '@sentry/nextjs'
import { formatWhatsAppMessage, messageBubbleStyles } from '@/lib/whatsappFormatter'

// Virtual sandbox phone number — never collides with real contacts
const SANDBOX_PHONE = 'sandbox-test-000'

interface SandboxMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export default function SandboxPage() {
  const router = useRouter()
  const { currentTenantId, currentTenant, isLoadingTenant } = useTenant()
  const [messages, setMessages] = useState<SandboxMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sandboxContactId, setSandboxContactId] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const initRef = useRef<string | null>(null) // Track which tenantId was initialized (prevents StrictMode double-init)

  // ─── Feedback / annotation state ───
  // comments: { [messageId]: string } — draft comment per bubble
  // sentFeedback: true when submit succeeded
  const [comments, setComments] = useState<Record<string, string>>({})
  const [activeCommentId, setActiveCommentId] = useState<string | null>(null)
  const [isSendingFeedback, setIsSendingFeedback] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ─── Initialize sandbox contact (auto-provisioning) ───
  useEffect(() => {
    if (!currentTenantId || initRef.current === currentTenantId) return
    initRef.current = currentTenantId

    // Reset state for new tenant (superadmin tenant switch)
    setMessages([])
    setSandboxContactId(null)
    setComments({})
    setFeedbackSent(false)
    setError(null)

    const initSandbox = async () => {
      const _where = 'SandboxPage.initSandbox'
      const supabase = createClient()

      try {
        // Check if sandbox contact already exists for this tenant
        const { data: existing, error: fetchErr } = await supabase
          .from('contacts')
          .select('id')
          .eq('tenant_id', currentTenantId)
          .eq('phone_number', SANDBOX_PHONE)
          .maybeSingle()

        if (fetchErr) {
          console.error(`[${_where}] Failed to check sandbox contact: ${fetchErr.message}`)
          Sentry.captureMessage(`sandbox contact check failed: ${fetchErr.message}`, 'error')
        }

        if (existing) {
          setSandboxContactId(existing.id)
          console.info(`[${_where}] Sandbox contact found: ${existing.id}`)

          // Load existing messages
          const { data: msgs } = await supabase
            .from('messages')
            .select('id, sender_role, content, timestamp')
            .eq('contact_id', existing.id)
            .order('timestamp', { ascending: true })

          if (msgs && msgs.length > 0) {
            setMessages(msgs.map(m => ({
              id: m.id,
              role: m.sender_role === 'assistant' ? 'assistant' : 'user',
              content: m.content,
              timestamp: new Date(m.timestamp).getTime(),
            })))
          }
        } else {
          // Create sandbox contact — minimal row, no real phone
          const { data: newContact, error: createErr } = await supabase
            .from('contacts')
            .insert({
              tenant_id: currentTenantId,
              phone_number: SANDBOX_PHONE,
              name: '🧪 Chat de Pruebas',
              role: 'cliente',
              bot_active: true,
            })
            .select('id')
            .single()

          if (createErr) {
            console.error(`[${_where}] Failed to create sandbox contact: ${createErr.message}`)
            Sentry.captureMessage(`sandbox contact creation failed: ${createErr.message}`, 'error')
            setError('No se pudo crear el chat de pruebas. Intenta recargar.')
            return
          }

          setSandboxContactId(newContact.id)
          console.info(`[${_where}] Sandbox contact created: ${newContact.id}`)
        }
      } catch (err: any) {
        console.error(`[${_where}] Sandbox init crashed:`, err)
        Sentry.captureException(err, { extra: { where: _where, tenant_id: currentTenantId } })
        setError('Error inicializando el chat de pruebas.')
      }
    }

    initSandbox()
  }, [currentTenantId])

  // ─── Realtime subscription for sandbox messages ───
  useEffect(() => {
    if (!sandboxContactId) return

    const supabase = createClient()
    const channel = supabase
      .channel(`sandbox-${sandboxContactId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `contact_id=eq.${sandboxContactId}`,
        },
        (payload: any) => {
          const msg = payload.new
          if (!msg) return

          setMessages(prev => {
            // Dedup by ID
            if (prev.some(m => m.id === msg.id)) return prev
            return [...prev, {
              id: msg.id,
              role: msg.sender_role === 'assistant' ? 'assistant' : 'user',
              content: msg.content,
              timestamp: new Date(msg.timestamp).getTime(),
            }]
          })

          // Clear processing indicator when assistant responds
          if (msg.sender_role === 'assistant') {
            setIsProcessing(false)
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sandboxContactId])

  // ─── Send message ───
  const handleSend = useCallback(async () => {
    const trimmed = inputValue.trim()
    if (!trimmed || isProcessing || !sandboxContactId || !currentTenantId) return

    setInputValue('')
    setError(null)
    setIsProcessing(true)
    setFeedbackSent(false) // Reset feedback state on new message

    const supabase = createClient()
    const _where = 'SandboxPage.handleSend'

    try {
      // Insert user message — Realtime will add it to the UI
      const { error: insertErr } = await supabase.from('messages').insert({
        contact_id: sandboxContactId,
        tenant_id: currentTenantId,
        content: trimmed,
        sender_role: 'user',
      })

      if (insertErr) {
        console.error(`[${_where}] Message insert failed: ${insertErr.message}`)
        Sentry.captureMessage(`sandbox insert failed: ${insertErr.message}`, 'error')
        setError('Error enviando mensaje.')
        setIsProcessing(false)
        return
      }

      // Call the new isolated sandbox endpoint (uses Responses API, NOT ProcessMessageUseCase)
      const resp = await fetch('/api/sandbox/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: currentTenantId,
          contact_id: sandboxContactId,
          message: trimmed,
        }),
      })

      if (!resp.ok) {
        const errText = await resp.text().catch(() => 'Unknown')
        console.error(`[${_where}] Sandbox API failed: HTTP ${resp.status} — ${errText.slice(0, 200)}`)
        Sentry.captureMessage(`sandbox chat HTTP ${resp.status}: ${errText.slice(0, 100)}`, 'error')
        setError(`Error del asistente (HTTP ${resp.status}). Intenta de nuevo.`)
        setIsProcessing(false)
      }
    } catch (err: any) {
      console.error(`[${_where}] Send crashed:`, err)
      Sentry.captureException(err, { extra: { where: _where, tenant_id: currentTenantId } })
      setError('Error de conexión. Intenta de nuevo.')
      setIsProcessing(false)
    }

    // Safety timeout — clear processing after 30s
    setTimeout(() => setIsProcessing(false), 30_000)

    inputRef.current?.focus()
  }, [inputValue, isProcessing, sandboxContactId, currentTenantId])

  const handleReset = useCallback(async () => {
    if (!sandboxContactId || !currentTenantId) {
      console.warn('[SandboxPage.handleReset] No sandboxContactId or tenantId — aborting')
      return
    }
    if (!confirm('¿Borrar todos los mensajes de prueba?')) return

    const supabase = createClient()
    const _where = 'SandboxPage.handleReset'

    try {
      // Delete messages scoped to this contact AND this tenant (defense in depth)
      const { error: delErr, count } = await supabase
        .from('messages')
        .delete({ count: 'exact' })
        .eq('contact_id', sandboxContactId)
        .eq('tenant_id', currentTenantId)

      if (delErr) {
        const errMsg = `[${_where}] Delete failed | contact=${sandboxContactId} | tenant=${currentTenantId} | error=${delErr.message}`
        console.error(errMsg)
        Sentry.captureMessage(errMsg, 'error')
        setError('Error al reiniciar el chat. Intenta de nuevo.')
        return
      }

      setMessages([])
      setComments({})
      setFeedbackSent(false)
      setError(null)
      console.info(`[${_where}] Sandbox messages cleared | deleted=${count} | contact=${sandboxContactId}`)
    } catch (err: any) {
      const errMsg = `[${_where}] Reset crashed | error=${String(err).slice(0, 300)}`
      console.error(errMsg, err)
      Sentry.captureException(err, { extra: { where: _where, contact_id: sandboxContactId, tenant_id: currentTenantId } })
      setError('Error inesperado al reiniciar.')
    }
  }, [sandboxContactId, currentTenantId])

  // ─── Submit annotated test to admin-feedback ───
  const handleSubmitFeedback = useCallback(async () => {
    if (messages.length === 0 || isSendingFeedback) return

    setIsSendingFeedback(true)
    setError(null)
    const _where = 'SandboxPage.handleSubmitFeedback'

    try {
      const supabase = createClient()

      // Build history array (matches test_feedback.history schema)
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
      }))

      // Build notes array — only messages that have a comment
      const notes = messages
        .filter(m => comments[m.id]?.trim())
        .map(m => ({
          content: m.content,   // Used by admin-feedback page to match message
          note: comments[m.id].trim(),
        }))

      const { error: insertErr } = await supabase
        .from('test_feedback')
        .insert({
          tenant_id: currentTenantId,
          history,
          notes,
        })

      if (insertErr) {
        console.error(`[${_where}] test_feedback INSERT failed: ${insertErr.message}`)
        Sentry.captureMessage(`test_feedback insert failed: ${insertErr.message}`, 'error')
        setError('No se pudo enviar la prueba. Intenta de nuevo.')
        return
      }

      setFeedbackSent(true)
      setActiveCommentId(null)
      console.info(`[${_where}] Feedback submitted | messages=${messages.length} notes=${notes.length}`)
    } catch (err: any) {
      console.error(`[${_where}] Submit feedback crashed:`, err)
      Sentry.captureException(err, { extra: { where: _where, tenant_id: currentTenantId } })
      setError('Error enviando feedback.')
    } finally {
      setIsSendingFeedback(false)
    }
  }, [messages, comments, currentTenantId, isSendingFeedback])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ─── Loading state ───
  if (isLoadingTenant) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Cargando...</p>
        </div>
      </div>
    )
  }

  if (!currentTenantId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3 max-w-sm mx-4">
          <AlertCircle className="w-10 h-10 text-amber-400 mx-auto" />
          <p className="text-sm text-slate-500">No se encontró tu empresa. Completa el onboarding primero.</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm hover:bg-emerald-400 transition-colors"
          >
            Ir al panel
          </button>
        </div>
      </div>
    )
  }

  const hasAnnotations = Object.values(comments).some(c => c.trim())

  return (
    <div className="flex-1 flex flex-col h-full bg-[#efeae2] overflow-hidden">
      {/* ─── Header ─── */}
      <div className="h-[56px] bg-white border-b flex items-center px-3 md:px-6 justify-between shrink-0 z-10">
        <div className="flex items-center gap-2 md:gap-3">
          <button
            onClick={() => router.push('/chats')}
            className="p-2 hover:bg-slate-100 rounded-full text-slate-600"
            title="Volver a Chats"
          >
            <ArrowLeft size={20} />
          </button>

          <div className="w-9 h-9 md:w-10 md:h-10 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-full flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
            <Sparkles size={18} />
          </div>
          <div>
            <h3 className="font-bold text-slate-800 text-sm md:text-base whitespace-nowrap">
              🧪 Chat de Pruebas
            </h3>
            <div className="text-[9px] md:text-[10px] text-slate-400 font-bold uppercase tracking-tighter">
              {currentTenant?.name || 'Tu negocio'} — Sandbox
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 border border-slate-200 transition-colors"
            title="Limpiar conversación"
          >
            <RefreshCw size={14} />
            <span className="hidden sm:inline">Reiniciar</span>
          </button>

          {/* ─── Enviar Prueba ─── */}
          {messages.length > 0 && (
            <button
              onClick={handleSubmitFeedback}
              disabled={isSendingFeedback || feedbackSent}
              title={feedbackSent ? 'Prueba enviada' : 'Enviar chat anotado al equipo'}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border
                ${feedbackSent
                  ? 'bg-emerald-50 text-emerald-600 border-emerald-200 cursor-default'
                  : isSendingFeedback
                    ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-wait'
                    : hasAnnotations
                      ? 'bg-amber-500 text-white border-amber-400 hover:bg-amber-400 shadow-sm shadow-amber-500/20'
                      : 'bg-slate-800 text-white border-slate-700 hover:bg-slate-700'
                }`}
            >
              {feedbackSent ? (
                <><CheckCircle2 size={14} /><span className="hidden sm:inline">Enviado</span></>
              ) : isSendingFeedback ? (
                <><Loader2 size={14} className="animate-spin" /><span className="hidden sm:inline">Enviando...</span></>
              ) : (
                <><MessageSquare size={14} /><span className="hidden sm:inline">Enviar prueba</span></>
              )}
            </button>
          )}
        </div>
      </div>

      {/* ─── Welcome card (when empty) ─── */}
      {messages.length === 0 && !isProcessing && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 rounded-2xl flex items-center justify-center border border-emerald-500/20">
              <Bot className="w-8 h-8 text-emerald-500" />
            </div>
            <h2 className="text-lg font-bold text-slate-700">
              Prueba tu Asistente Virtual
            </h2>
            <p className="text-sm text-slate-500 leading-relaxed">
              Escribe un mensaje como si fueras un cliente de{' '}
              <strong className="text-slate-700">{currentTenant?.name || 'tu negocio'}</strong>.
              Tu asistente responderá usando la configuración que acabas de crear.
            </p>
            <div className="flex flex-wrap gap-2 justify-center pt-2">
              {['Hola, quisiera información', '¿Qué servicios ofrecen?', '¿Cuál es el horario?'].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInputValue(suggestion)
                    inputRef.current?.focus()
                  }}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs text-slate-600 hover:bg-emerald-50 hover:border-emerald-200 hover:text-emerald-700 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Messages area ─── */}
      {(messages.length > 0 || isProcessing) && (
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-2">
          {messages.map((msg) => {
            const isCommentOpen = activeCommentId === msg.id
            const commentText = comments[msg.id] || ''
            const hasComment = commentText.trim().length > 0

            return (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-0.5`}>
                {/* Message bubble */}
                <div
                  className={`group relative max-w-[80%] md:max-w-[70%] px-4 py-2.5 rounded-2xl shadow-sm text-[14px] cursor-pointer
                    ${msg.role === 'user' ? 'bg-[#d9fdd3] rounded-tr-none' : 'bg-white rounded-tl-none'}
                    ${hasComment ? 'ring-2 ring-amber-400/50' : ''}
                  `}
                  onClick={() => setActiveCommentId(isCommentOpen ? null : msg.id)}
                  title="Toca para añadir observación"
                >
                  <p className={messageBubbleStyles}>{formatWhatsAppMessage(msg.content)}</p>
                  <div className="text-[9px] text-slate-500/70 text-right mt-1 font-medium flex items-center justify-end gap-1.5">
                    {hasComment && <MessageSquare size={9} className="text-amber-500" />}
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>

                  {/* Hover hint — desktop only */}
                  <div className="absolute -top-5 left-1/2 -translate-x-1/2 hidden group-hover:flex items-center gap-1 bg-slate-800 text-white text-[9px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap pointer-events-none opacity-80">
                    <MessageSquare size={8} /> Añadir nota
                  </div>
                </div>

                {/* Inline comment input */}
                {isCommentOpen && (
                  <div className={`w-full max-w-[80%] md:max-w-[70%] ${msg.role === 'user' ? 'self-end' : 'self-start'}`}>
                    <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 flex items-start gap-2 shadow-sm mt-0.5">
                      <MessageSquare size={13} className="text-amber-500 shrink-0 mt-1.5" />
                      <textarea
                        autoFocus
                        rows={2}
                        value={commentText}
                        onChange={(e) => setComments(prev => ({ ...prev, [msg.id]: e.target.value }))}
                        onKeyDown={(e) => { if (e.key === 'Escape') setActiveCommentId(null) }}
                        placeholder="Observación sobre esta respuesta..."
                        className="flex-1 text-[11px] text-slate-700 bg-transparent resize-none outline-none placeholder-amber-400/70 leading-relaxed"
                      />
                      <button
                        onClick={(e) => { e.stopPropagation(); setActiveCommentId(null) }}
                        className="text-[9px] font-bold text-amber-600 hover:text-amber-700 shrink-0 mt-1 uppercase tracking-wide"
                      >
                        OK
                      </button>
                    </div>
                  </div>
                )}

                {/* Saved comment preview (collapsed) */}
                {!isCommentOpen && hasComment && (
                  <div
                    className={`text-[10px] text-amber-600 font-medium flex items-center gap-1 cursor-pointer hover:text-amber-700 max-w-[80%] truncate
                      ${msg.role === 'user' ? 'self-end' : 'self-start'}`}
                    onClick={() => setActiveCommentId(msg.id)}
                  >
                    <MessageSquare size={9} />
                    {commentText.slice(0, 60)}{commentText.length > 60 ? '…' : ''}
                  </div>
                )}
              </div>
            )
          })}

          {/* Processing indicator */}
          {isProcessing && (
            <div className="flex justify-start">
              <div className="bg-white px-4 py-3 rounded-2xl border flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  IA Generando...
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      )}

      {/* ─── Error display ─── */}
      {error && (
        <div className="mx-4 mb-2">
          <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span className="text-xs text-red-600">{error}</span>
          </div>
        </div>
      )}

      {/* ─── Input area ─── */}
      <div className="bg-[#f0f2f5] p-2.5 shrink-0 border-t z-20">
        <div className="flex gap-2 items-center">
          <div className="flex-1 bg-white rounded-full shadow-sm border focus-within:ring-2 ring-emerald-500 transition-all overflow-hidden">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing || !sandboxContactId}
              placeholder={isProcessing ? 'Esperando respuesta...' : 'Escribe como cliente...'}
              className="w-full px-4 py-2.5 text-sm outline-none disabled:opacity-50"
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isProcessing || !sandboxContactId}
            className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all active:scale-95 flex-shrink-0
              ${inputValue.trim() && !isProcessing && sandboxContactId
                ? 'bg-emerald-500 text-white hover:bg-emerald-400'
                : 'bg-slate-300 text-slate-500 cursor-not-allowed'
              }`}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
