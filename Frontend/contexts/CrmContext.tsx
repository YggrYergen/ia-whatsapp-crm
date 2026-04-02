'use client'

import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
import { createClient } from '@/lib/supabase'

const supabase = createClient()

interface CrmContextType {
    selectedContact: any;
    setSelectedContact: (contact: any) => void;
    contacts: any[];
    setContacts: (contacts: any[]) => void;
    messages: any[];
    setMessages: (messages: any[]) => void;
    newMessage: string;
    setNewMessage: (msg: string) => void;
    simulationMode: boolean;
    setSimulationMode: (mode: boolean) => void;
    mobileView: 'list' | 'chat' | 'info';
    setMobileView: (view: 'list' | 'chat' | 'info') => void;
    showDesktopInfo: boolean;
    setShowDesktopInfo: (show: boolean) => void;
    user: any;
    setUser: (user: any) => void;
    isLoadingAuth: boolean;
    isIAProcessing: boolean;
    setIsIAProcessing: (v: boolean) => void;
    dashboardRole: 'admin' | 'staff';
    setDashboardRole: (role: 'admin' | 'staff') => void;
    toasts: any[];
    setToasts: React.Dispatch<React.SetStateAction<any[]>>;
}

const CrmContext = createContext<CrmContextType | undefined>(undefined)

export function CrmProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<any>(null)
    const [isLoadingAuth, setIsLoadingAuth] = useState(true)
    const [selectedContact, setSelectedContact] = useState<any>(null)
    const [contacts, setContacts] = useState<any[]>([])
    const [messages, setMessages] = useState<any[]>([])
    const [newMessage, setNewMessage] = useState('')
    const [simulationMode, setSimulationMode] = useState(false)
    const [mobileView, setMobileView] = useState<'list' | 'chat' | 'info'>('list')
    const [showDesktopInfo, setShowDesktopInfo] = useState(false)
    const [isIAProcessing, setIsIAProcessing] = useState(false)
    const [dashboardRole, setDashboardRole] = useState<'admin' | 'staff'>('admin')
    const [toasts, setToasts] = useState<any[]>([])

    useEffect(() => {
        const checkUser = async () => {
            const { data: { session } } = await supabase.auth.getSession()
            setUser(session?.user || null)
            setIsLoadingAuth(false)
        }
        
        checkUser()

        const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
            setUser(session?.user || null)
        })

        return () => {
            authListener?.subscription?.unsubscribe()
        }
    }, [])

    // Initial Fetch
    const fetchContacts = async () => {
        const { data } = await supabase
            .from('contacts')
            .select('*')
            .order('last_message_at', { ascending: false })
        
        if (data) {
            setContacts(data)
            // If we have a selected contact, update it with fresh data
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
            .channel('crm_contacts_changes')
            .on('postgres_changes' as any, { event: '*', table: 'contacts' }, () => {
                fetchContacts()
            })
            .subscribe()

        const messagesSub = supabase
            .channel('crm_messages_changes')
            .on('postgres_changes' as any, { event: 'INSERT', table: 'messages' }, async (payload: any) => {
                const newMsg = payload.new as any
                
                // If the message is for the currently open contact, append it
                if (selectedContact && newMsg.contact_id === selectedContact.id) {
                    setMessages(prev => {
                        // Avoid duplicates if optimistic update already added it
                        if (prev.some(m => m.id === newMsg.id)) return prev;
                        return [...prev, newMsg];
                    });
                }

                if (newMsg.sender_role === 'assistant') {
                    setIsIAProcessing(false)
                }
            })
            .subscribe()

        const alertsSub = supabase
            .channel('alerts-realtime')
            .on('postgres_changes' as any, { event: 'INSERT', schema: 'public', table: 'alerts' }, (payload: any) => {
                const newAlert = payload.new as any
                const toastId = Date.now() + Math.random();
                setToasts((prev) => [...prev, { id: toastId, payload: { content: newAlert.message, contact_id: newAlert.contact_id } }]);
                // Auto hide
                setTimeout(() => {
                    setToasts((prev) => prev.filter(t => t.id !== toastId));
                }, 30000);
            })
            .subscribe()

        return () => {
            supabase.removeChannel(contactsSub)
            supabase.removeChannel(messagesSub)
            supabase.removeChannel(alertsSub)
        }
    }, [selectedContact?.id])

    return (
        <CrmContext.Provider value={{
            selectedContact, setSelectedContact,
            contacts, setContacts,
            messages, setMessages,
            newMessage, setNewMessage,
            simulationMode, setSimulationMode,
            mobileView, setMobileView,
            showDesktopInfo, setShowDesktopInfo,
            user, setUser,
            isLoadingAuth,
            isIAProcessing, setIsIAProcessing,
            dashboardRole, setDashboardRole,
            toasts, setToasts
        }}>
            {children}
        </CrmContext.Provider>
    )
}

export function useCrm() {
    const context = useContext(CrmContext)
    if (context === undefined) {
        throw new Error('useCrm must be used within a CrmProvider')
    }
    return context
}
