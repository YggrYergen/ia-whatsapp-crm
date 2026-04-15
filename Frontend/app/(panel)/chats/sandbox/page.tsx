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
 * Observability: All error paths → console.error + Sentry.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Bot, Send, ArrowLeft, Sparkles, RefreshCw, AlertCircle } from 'lucide-react'
import { useTenant } from '@/contexts/TenantContext'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import * as Sentry from '@sentry/nextjs'

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
  const initRef = useRef(false) // Prevent double init in StrictMode

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ─── Initialize sandbox contact (auto-provisioning) ───
  useEffect(() => {
    if (!currentTenantId || initRef.current) return
    initRef.current = true

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

  // ─── Reset sandbox ───
  const handleReset = useCallback(async () => {
    if (!sandboxContactId || !confirm('¿Borrar todos los mensajes de prueba?')) return

    const supabase = createClient()
    const _where = 'SandboxPage.handleReset'

    try {
      const { error: delErr } = await supabase
        .from('messages')
        .delete()
        .eq('contact_id', sandboxContactId)

      if (delErr) {
        console.error(`[${_where}] Delete failed: ${delErr.message}`)
        Sentry.captureMessage(`sandbox reset failed: ${delErr.message}`, 'error')
        return
      }

      setMessages([])
      console.info(`[${_where}] Sandbox messages cleared`)
    } catch (err: any) {
      console.error(`[${_where}] Reset crashed:`, err)
      Sentry.captureException(err, { extra: { where: _where } })
    }
  }, [sandboxContactId])

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
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-3">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`relative max-w-[80%] md:max-w-[70%] px-4 py-2.5 rounded-2xl shadow-sm text-[14px]
                ${msg.role === 'user'
                  ? 'bg-[#d9fdd3] rounded-tr-none'
                  : 'bg-white rounded-tl-none'
                }`}
              >
                <p className="break-words whitespace-pre-wrap">{msg.content}</p>
                <div className="text-[9px] text-slate-500/70 text-right mt-1 font-medium">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}

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
