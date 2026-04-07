'use client'

/**
 * CrmContext — Backwards-compatible shim.
 * Re-exports from AuthContext, ChatContext, and UIContext so existing components
 * continue working without code changes while new components can import
 * the specific context they need.
 */
import React from 'react'
import { AuthProvider, useAuth } from './AuthContext'
import { ChatProvider, useChat } from './ChatContext'
import { UIProvider, useUI } from './UIContext'

export function CrmProvider({ children }: { children: React.ReactNode }) {
    return (
        <AuthProvider>
            <ChatProvider>
                <UIProvider>
                    {children}
                </UIProvider>
            </ChatProvider>
        </AuthProvider>
    )
}

export function useCrm() {
    const auth = useAuth()
    const chat = useChat()
    const ui = useUI()

    return {
        // Auth
        user: auth.user,
        setUser: auth.setUser,
        isLoadingAuth: auth.isLoadingAuth,
        dashboardRole: auth.dashboardRole,
        setDashboardRole: auth.setDashboardRole,
        // Chat
        selectedContact: chat.selectedContact,
        setSelectedContact: chat.setSelectedContact,
        contacts: chat.contacts,
        setContacts: chat.setContacts,
        messages: chat.messages,
        setMessages: chat.setMessages,
        newMessage: chat.newMessage,
        setNewMessage: chat.setNewMessage,
        simulationMode: chat.simulationMode,
        setSimulationMode: chat.setSimulationMode,
        isIAProcessing: chat.isIAProcessing,
        setIsIAProcessing: chat.setIsIAProcessing,
        // UI
        mobileView: ui.mobileView,
        setMobileView: ui.setMobileView,
        showDesktopInfo: ui.showDesktopInfo,
        setShowDesktopInfo: ui.setShowDesktopInfo,
        toasts: ui.toasts,
        setToasts: ui.setToasts,
    }
}
