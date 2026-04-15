'use client'

/**
 * UIContext — Toasts, notifications, and mobile view state.
 *
 * ⚠️ TENANT ISOLATION: Alerts are filtered by currentTenantId to prevent
 *    cross-tenant data leaks. The Realtime subscription is re-created
 *    whenever the active tenant changes (superadmin switching).
 *
 * ⚠️ OBSERVABILITY: Every failure → console.error + Sentry.
 */

import React, { createContext, useContext, useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useTenant } from './TenantContext'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()

interface Toast {
    id: number;
    payload: { content: string; contact_id?: string; type?: string; created_at?: string };
}

export interface NotificationItem {
    id: string;
    message: string;
    type: string;
    contact_id: string | null;
    is_read: boolean;
    created_at: string;
}

interface UIContextType {
    mobileView: 'list' | 'chat' | 'info';
    setMobileView: (view: 'list' | 'chat' | 'info') => void;
    showDesktopInfo: boolean;
    setShowDesktopInfo: (show: boolean) => void;
    toasts: Toast[];
    setToasts: React.Dispatch<React.SetStateAction<Toast[]>>;
    notifications: NotificationItem[];
    setNotifications: React.Dispatch<React.SetStateAction<NotificationItem[]>>;
    unreadCount: number;
    markAsRead: (id: string) => void;
    markAllAsRead: () => void;
    isNotificationFeedOpen: boolean;
    setIsNotificationFeedOpen: (open: boolean) => void;
}

const UIContext = createContext<UIContextType | undefined>(undefined)

export function UIProvider({ children }: { children: React.ReactNode }) {
    const [mobileView, setMobileView] = useState<'list' | 'chat' | 'info'>('list')
    const [showDesktopInfo, setShowDesktopInfo] = useState(false)
    const [toasts, setToasts] = useState<Toast[]>([])
    const [notifications, setNotifications] = useState<NotificationItem[]>([])
    const [isNotificationFeedOpen, setIsNotificationFeedOpen] = useState(false)

    // ⚠️ TENANT ISOLATION: Get the active tenant to filter alerts
    const { currentTenantId } = useTenant()

    const unreadCount = notifications.filter(n => !n.is_read).length

    useEffect(() => {
        const _where = 'UIContext.alertsEffect'

        // Don't fetch alerts if no tenant selected yet
        if (!currentTenantId) {
            setNotifications([])
            return
        }

        // ── Initial fetch of alerts — FILTERED BY TENANT ──
        const fetchAlerts = async () => {
            try {
                const { data, error } = await supabase
                    .from('alerts')
                    .select('*')
                    .eq('tenant_id', currentTenantId)
                    .order('created_at', { ascending: false })
                    .limit(50)

                if (error) {
                    const errMsg = `[${_where}] Alerts fetch failed | tenant=${currentTenantId} | error=${error.message}`
                    console.error(errMsg)
                    Sentry.captureMessage(errMsg, 'error')
                    return
                }

                if (data) setNotifications(data as NotificationItem[])
            } catch (fetchErr: any) {
                const errMsg = `[${_where}] Alerts fetch CRASHED | tenant=${currentTenantId} | error=${String(fetchErr).slice(0, 300)}`
                console.error(errMsg, fetchErr)
                Sentry.captureException(fetchErr, {
                    extra: { where: _where, tenant_id: currentTenantId },
                })
            }
        }
        fetchAlerts()

        if (typeof window !== 'undefined' && 'Notification' in window) {
            Notification.requestPermission()
        }

        const playNotificationSound = () => {
            try {
                const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
                if (audioCtx.state === 'suspended') audioCtx.resume();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
                gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime);
                oscillator.start();
                gainNode.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + 0.3);
                oscillator.stop(audioCtx.currentTime + 0.3);
            } catch (e) {
                console.warn("Audio playback error", e);
            }
        }

        // ── Realtime sub — FILTERED BY TENANT ──
        // Ref: https://supabase.com/docs/guides/realtime/postgres-changes#filter-changes
        const channelName = `alerts-realtime-${currentTenantId.slice(0, 8)}`
        const alertsSub = supabase
            .channel(channelName)
            .on(
                'postgres_changes' as any,
                {
                    event: 'INSERT',
                    schema: 'public',
                    table: 'alerts',
                    filter: `tenant_id=eq.${currentTenantId}`,
                },
                (payload: any) => {
                    const newAlert = payload.new as any

                    // Add to history
                    setNotifications(prev => [newAlert, ...prev]);

                    // Toast
                    const toastId = Date.now() + Math.random();
                    setToasts((prev) => [...prev, { id: toastId, payload: { content: newAlert.message, contact_id: newAlert.contact_id, type: newAlert.type, created_at: newAlert.created_at } }]);
                    setTimeout(() => {
                        setToasts((prev) => prev.filter(t => t.id !== toastId));
                    }, 30000);

                    // Web Notification & Sound
                    playNotificationSound();
                    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
                        new Notification('Alerta del Sistema', {
                            body: newAlert.message,
                            icon: '/favicon.ico'
                        });
                    }
                }
            )
            .subscribe()

        // ── Cleanup: unsubscribe when tenant changes ──
        return () => {
            supabase.removeChannel(alertsSub)
        }
    }, [currentTenantId])  // ← Re-run when tenant switches

    const markAsRead = async (id: string) => {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
        try {
            await supabase.from('alerts').update({ is_read: true }).eq('id', id);
        } catch (err: any) {
            console.error(`[UIContext.markAsRead] Failed | id=${id} | error=${String(err).slice(0, 200)}`)
            Sentry.captureException(err, { extra: { alert_id: id } })
        }
    }

    const markAllAsRead = async () => {
        if (!currentTenantId) return
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        try {
            await supabase
                .from('alerts')
                .update({ is_read: true })
                .eq('is_read', false)
                .eq('tenant_id', currentTenantId)
        } catch (err: any) {
            console.error(`[UIContext.markAllAsRead] Failed | tenant=${currentTenantId} | error=${String(err).slice(0, 200)}`)
            Sentry.captureException(err, { extra: { tenant_id: currentTenantId } })
        }
    }

    return (
        <UIContext.Provider value={{
            mobileView, setMobileView,
            showDesktopInfo, setShowDesktopInfo,
            toasts, setToasts,
            notifications, setNotifications, unreadCount, markAsRead, markAllAsRead,
            isNotificationFeedOpen, setIsNotificationFeedOpen
        }}>
            {children}
        </UIContext.Provider>
    )
}

export function useUI() {
    const context = useContext(UIContext)
    if (context === undefined) {
        throw new Error('useUI must be used within a UIProvider')
    }
    return context
}
