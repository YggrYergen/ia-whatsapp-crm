'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'

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

    // Fetch contacts
    const fetchContacts = async () => {
        const { data } = await supabase
            .from('contacts')
            .select('*')
            .order('last_message_at', { ascending: false })

        if (data) {
            setContacts(data)
            if (selectedContact) {
                const updated = data.find((c: any) => c.id === selectedContact.id)
                if (updated) setSelectedContact(updated)
            }
        }
    }

    useEffect(() => {
        fetchContacts()

        // Realtime Subscriptions
        const contactsSub = supabase
            .channel('chat_contacts_changes')
            .on('postgres_changes' as any, { event: '*', table: 'contacts' }, () => {
                fetchContacts()
            })
            .subscribe()

        const messagesSub = supabase
            .channel('chat_messages_changes')
            .on('postgres_changes' as any, { event: 'INSERT', table: 'messages' }, async (payload: any) => {
                const newMsg = payload.new as any

                if (selectedContact && newMsg.contact_id === selectedContact.id) {
                    setMessages(prev => {
                        if (prev.some(m => m.id === newMsg.id)) return prev;
                        return [...prev, newMsg];
                    });
                }

                if (newMsg.sender_role === 'assistant') {
                    setIsIAProcessing(false)
                }
            })
            .subscribe()

        return () => {
            supabase.removeChannel(contactsSub)
            supabase.removeChannel(messagesSub)
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
