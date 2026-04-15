'use client'

/**
 * ChatContext — Contacts, messages, and Realtime subscriptions.
 *
 * ⚠️ TENANT ISOLATION: All queries and Realtime subs are filtered by
 *    currentTenantId to prevent cross-tenant data leaks.
 *
 * ⚠️ OBSERVABILITY: Every failure → console.error + Sentry.
 */

import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
import { createClient } from '@/lib/supabase'
import { useTenant } from './TenantContext'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()

interface ChatContextType {
    selectedContact: any;
    setSelectedContact: (contact: any) => void;
    contacts: any[];
    setContacts: (contacts: any[]) => void;
    messages: any[];
    setMessages: (messages: any[] | ((prev: any[]) => any[])) => void;
    newMessage: string;
    setNewMessage: (msg: string) => void;
    simulationMode: boolean;
    setSimulationMode: (mode: boolean) => void;
    isIAProcessing: boolean;
    setIsIAProcessing: (v: boolean) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function ChatProvider({ children }: { children: React.ReactNode }) {
    const [selectedContact, setSelectedContact] = useState<any>(null)
    const [contacts, setContacts] = useState<any[]>([])
    const [messages, setMessages] = useState<any[]>([])
    const [newMessage, setNewMessage] = useState('')
    const [simulationMode, setSimulationMode] = useState(false)
    const [isIAProcessing, setIsIAProcessing] = useState(false)

    // ⚠️ TENANT ISOLATION: Get the active tenant
    const { currentTenantId } = useTenant()
    // Track selected contact for Realtime callback (avoids stale closure)
    const selectedContactRef = useRef<any>(null)
    selectedContactRef.current = selectedContact

    // Fetch contacts — FILTERED BY TENANT
    const fetchContacts = async () => {
        if (!currentTenantId) return

        try {
            const { data, error } = await supabase
                .from('contacts')
                .select('*')
                .eq('tenant_id', currentTenantId)
                .order('last_message_at', { ascending: false })

            if (error) {
                console.error(`[ChatContext.fetchContacts] Query failed: ${error.message}`)
                Sentry.captureMessage(`contacts fetch failed: ${error.message}`, 'error')
                return
            }

            if (data) {
                setContacts(data)
                if (selectedContactRef.current) {
                    const updated = data.find((c: any) => c.id === selectedContactRef.current.id)
                    if (updated) setSelectedContact(updated)
                }
            }
        } catch (err: any) {
            console.error(`[ChatContext.fetchContacts] Crashed:`, err)
            Sentry.captureException(err, { extra: { tenant_id: currentTenantId } })
        }
    }

    useEffect(() => {
        if (!currentTenantId) {
            setContacts([])
            setMessages([])
            return
        }

        fetchContacts()

        // ── Realtime: contacts changes — FILTERED BY TENANT ──
        const contactsSub = supabase
            .channel(`contacts-${currentTenantId.slice(0, 8)}`)
            .on(
                'postgres_changes' as any,
                {
                    event: '*',
                    schema: 'public',
                    table: 'contacts',
                    filter: `tenant_id=eq.${currentTenantId}`,
                },
                () => {
                    fetchContacts()
                }
            )
            .subscribe()

        // ── Realtime: new messages — FILTERED BY TENANT ──
        const messagesSub = supabase
            .channel(`messages-${currentTenantId.slice(0, 8)}`)
            .on(
                'postgres_changes' as any,
                {
                    event: 'INSERT',
                    schema: 'public',
                    table: 'messages',
                    filter: `tenant_id=eq.${currentTenantId}`,
                },
                (payload: any) => {
                    const newMsg = payload.new as any
                    const current = selectedContactRef.current

                    if (current && newMsg.contact_id === current.id) {
                        setMessages(prev => {
                            // ⚠️ DEDUP by message ID — prevents Realtime delivering same msg twice
                            if (prev.some(m => m.id === newMsg.id)) return prev
                            // Remove optimistic temp messages matching this sender_role
                            // (temp-* IDs are added by handleSendMessage for instant UX)
                            const cleaned = prev.filter(m => {
                                if (typeof m.id === 'string' && m.id.startsWith('temp-') && m.sender_role === newMsg.sender_role) {
                                    return false  // Remove the optimistic temp message
                                }
                                return true
                            })
                            return [...cleaned, newMsg]
                        })
                    }

                    if (newMsg.sender_role === 'assistant') {
                        setIsIAProcessing(false)
                    }
                }
            )
            .subscribe()

        return () => {
            supabase.removeChannel(contactsSub)
            supabase.removeChannel(messagesSub)
        }
    }, [currentTenantId])  // Re-subscribe when tenant changes

    // When selected contact changes, clear messages (they'll be reloaded by the chat component)
    useEffect(() => {
        if (!selectedContact) {
            setMessages([])
        }
    }, [selectedContact?.id])

    return (
        <ChatContext.Provider value={{
            selectedContact, setSelectedContact,
            contacts, setContacts,
            messages, setMessages,
            newMessage, setNewMessage,
            simulationMode, setSimulationMode,
            isIAProcessing, setIsIAProcessing
        }}>
            {children}
        </ChatContext.Provider>
    )
}

export function useChat() {
    const context = useContext(ChatContext)
    if (context === undefined) {
        throw new Error('useChat must be used within a ChatProvider')
    }
    return context
}
