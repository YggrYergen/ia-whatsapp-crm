'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, LayoutDashboard, MessageCircle, CalendarIcon, Users, BarChart3, Receipt, Settings, LogOut, Terminal, Bell, AlertTriangle, ChevronDown, Building2, Shield, Package, Layers, MoreHorizontal, X as XIcon } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useCrm } from '@/contexts/CrmContext'
import { useUI } from '@/contexts/UIContext'
// Block R: Tenant switching for superadmins
import { useTenant } from '@/contexts/TenantContext'
import * as Sentry from '@sentry/nextjs'

export default function Sidebar() {
    const pathname = usePathname()
    const { setMobileView, user, contacts } = useCrm()
    const { unreadCount, isNotificationFeedOpen, setIsNotificationFeedOpen } = useUI()
    // Block R: Tenant context for superadmin switching
    const { isSuperadmin, allTenants, currentTenant, switchTenant } = useTenant()
    const [isTenantDropdownOpen, setIsTenantDropdownOpen] = useState(false)
    const [isMobileMoreOpen, setIsMobileMoreOpen] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)
    const mobileMoreRef = useRef<HTMLDivElement>(null)

    // Count escalated contacts (bot_active=false, excluding test contact)
    const escalatedCount = contacts.filter((c: any) => !c.bot_active && c.phone_number !== '56912345678').length

    const handleLogout = async () => {
        const { createClient } = await import('@/lib/supabase')
        const supabase = createClient()
        await supabase.auth.signOut()
        window.location.href = '/login'
    }

    const isActive = (path: string) => pathname === path

    // Close dropdown on click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setIsTenantDropdownOpen(false)
            }
        }
        if (isTenantDropdownOpen) {
            document.addEventListener('mousedown', handleClickOutside)
            return () => document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [isTenantDropdownOpen])

    // Close mobile more menu on click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (mobileMoreRef.current && !mobileMoreRef.current.contains(e.target as Node)) {
                setIsMobileMoreOpen(false)
            }
        }
        if (isMobileMoreOpen) {
            document.addEventListener('mousedown', handleClickOutside)
            return () => document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [isMobileMoreOpen])

    const handleTenantSwitch = (tenantId: string) => {
        const _where = 'Sidebar.handleTenantSwitch'
        console.info(`[${_where}] Switching to tenant: ${tenantId}`)
        Sentry.addBreadcrumb({
            category: 'superadmin',
            message: `Tenant switch: ${tenantId}`,
            level: 'info',
        })
        switchTenant(tenantId)
        setIsTenantDropdownOpen(false)
        // FIX 2026-04-16: Removed window.location.reload() — it destroyed the
        // switchTenant() state update by re-running resolveTenant() from scratch,
        // which always returned the first tenant_users row (CasaVitaCure).
        // React's useEffect hooks on currentTenantId already handle data re-fetching
        // in ChatContext, AgendaView, RecursosView, ServiciosView, etc.
    }

    const navItems = [
        { href: '/dashboard', icon: LayoutDashboard, title: 'Panel', label: 'Panel' },
        { href: '/chats', icon: MessageCircle, title: 'Chats', label: 'Chats', escalationBadge: true },
        { href: '/chats/sandbox', icon: Sparkles, title: 'Chat de Pruebas', label: 'Pruebas' },
        { href: '/agenda', icon: CalendarIcon, title: 'Agenda', label: 'Agenda' },
        { href: '/pacientes', icon: Users, title: 'Clientes', label: 'CRM' },
        { href: '/servicios', icon: Package, title: 'Servicios', label: 'Servicios' },
        { href: '/recursos', icon: Layers, title: 'Recursos', label: 'Recursos' },
        { href: '/reportes', icon: BarChart3, title: 'Reportes', desktopOnly: true },
        { href: '/finops', icon: Receipt, title: 'FinOps', desktopOnly: true },
        // Block R: Use isSuperadmin instead of hardcoded email list for dev tools
        ...(isSuperadmin ? [
            { href: '/admin-feedback', icon: Terminal, title: 'Auditoría Dev', label: 'Dev' }
        ] : [])
    ]

    return (
        <div className={`
            bg-slate-900 border-t md:border-t-0 md:border-r border-slate-800 flex-shrink-0 z-50
            fixed bottom-0 left-0 w-full h-[60px] flex flex-row items-center justify-around px-2
            md:relative md:w-20 md:h-full md:flex-col md:justify-between md:py-6 md:px-0
            pb-safe md:pb-6
        `}>
            {/* ─── Superadmin Tenant Switcher (desktop only) ─── */}
            {isSuperadmin && allTenants.length > 1 && (
                <div ref={dropdownRef} className="hidden md:block w-full px-2 relative mb-2">
                    <button
                        onClick={() => setIsTenantDropdownOpen(!isTenantDropdownOpen)}
                        className={`
                            w-full flex items-center justify-center gap-1 p-2 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all
                            ${isTenantDropdownOpen
                                ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                                : 'bg-slate-800/60 text-slate-500 hover:text-violet-300 hover:bg-violet-500/10 border border-transparent'
                            }
                        `}
                        title={`Tenant: ${currentTenant?.name || 'Sin asignar'}`}
                    >
                        <Shield className="w-3 h-3 flex-shrink-0" />
                        <ChevronDown className={`w-3 h-3 transition-transform ${isTenantDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {/* Dropdown */}
                    {isTenantDropdownOpen && (
                        <div className="absolute left-full top-0 ml-2 w-56 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl shadow-black/50 py-2 z-[60] animate-slide-in-right">
                            <div className="px-3 py-1.5 border-b border-slate-800">
                                <p className="text-[10px] text-violet-400 font-bold uppercase tracking-widest flex items-center gap-1">
                                    <Shield className="w-3 h-3" />
                                    Superadmin
                                </p>
                            </div>
                            <div className="max-h-64 overflow-y-auto dark-scrollbar py-1">
                                {allTenants.map((tenant) => (
                                    <button
                                        key={tenant.id}
                                        onClick={() => handleTenantSwitch(tenant.id)}
                                        className={`
                                            w-full text-left px-3 py-2 flex items-center gap-2 transition-all text-xs
                                            ${tenant.id === currentTenant?.id
                                                ? 'bg-emerald-500/10 text-emerald-400'
                                                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                                            }
                                        `}
                                    >
                                        <Building2 className="w-3.5 h-3.5 flex-shrink-0" />
                                        <div className="min-w-0 flex-1">
                                            <p className="font-medium truncate">{tenant.name}</p>
                                            <p className="text-[9px] text-slate-600 font-mono truncate">{tenant.id.slice(0, 8)}...</p>
                                        </div>
                                        {tenant.id === currentTenant?.id && (
                                            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full flex-shrink-0" />
                                        )}
                                        {!tenant.is_setup_complete && (
                                            <span className="text-[8px] bg-amber-500/20 text-amber-400 px-1 py-0.5 rounded font-bold">
                                                SETUP
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
            {/* ─── Top section: logo + nav (flex-1 so bottom stays pinned) ─── */}
            <div className="contents md:!flex md:flex-col md:items-center md:gap-6 md:w-full md:flex-1 md:min-h-0">
            <div className="hidden md:flex w-10 h-10 bg-emerald-500 rounded-xl items-center justify-center shadow-lg flex-shrink-0 ring-4 ring-emerald-500/20">
                <Sparkles className="text-white w-6 h-6" />
            </div>
            
            <div className="flex flex-row md:flex-col w-full justify-around md:justify-start md:gap-4 md:px-2">
                {navItems.map((item) => (
                    <Link 
                        key={item.href} 
                        href={item.href}
                        onClick={() => setMobileView('list')}
                        className={`
                            p-2.5 md:p-3 rounded-xl flex flex-col items-center justify-center transition-all relative
                            ${item.desktopOnly ? 'hidden md:flex' : 'flex'}
                            ${isActive(item.href) 
                                ? 'bg-emerald-500/10 text-emerald-400 font-bold md:bg-emerald-500 md:text-white md:shadow-md' 
                                : 'text-slate-500 hover:text-slate-300 md:hover:bg-slate-800/50'}
                        `} 
                        title={item.title}
                    >
                        <item.icon className="w-[20px] h-[20px] md:w-[22px] md:h-[22px]" />
                        {/* Escalation badge on Chats */}
                        {item.escalationBadge && escalatedCount > 0 && (
                            <span className="absolute top-1 right-1 md:top-1.5 md:right-1.5 min-w-[18px] h-[18px] bg-rose-500 rounded-full border-2 border-slate-900 text-[9px] text-white font-black flex items-center justify-center animate-badge-pop shadow-sm">
                                {escalatedCount}
                            </span>
                        )}
                        {item.label && <span className="text-[10px] mt-1 md:hidden">{item.label}</span>}
                    </Link>
                ))}
                
                {/* Mobile Notification Button */}
                <button 
                    onClick={() => setIsNotificationFeedOpen(true)}
                    className={`
                        p-2.5 md:p-3 rounded-xl flex-col items-center justify-center transition-all relative
                        flex md:hidden
                        ${isNotificationFeedOpen ? 'text-emerald-400 font-bold' : 'text-slate-500 hover:text-slate-300'}
                    `} 
                    title="Notificaciones"
                >
                    <Bell className="w-[20px] h-[20px] md:w-[22px] md:h-[22px]" />
                    {unreadCount > 0 && (
                        <span className="absolute top-1 right-1 min-w-[18px] h-[18px] bg-emerald-500 rounded-full border-2 border-slate-900 text-[9px] text-white font-black flex items-center justify-center shadow-sm">
                            {unreadCount}
                        </span>
                    )}
                    <span className="text-[10px] mt-1 md:hidden">Alertas</span>
                </button>

                {/* Mobile More Menu (Logout, Settings, etc.) */}
                <div ref={mobileMoreRef} className="relative flex md:hidden">
                    <button 
                        onClick={() => setIsMobileMoreOpen(!isMobileMoreOpen)}
                        className={`
                            p-2.5 rounded-xl flex flex-col items-center justify-center transition-all
                            ${isMobileMoreOpen ? 'text-emerald-400 font-bold' : 'text-slate-500 hover:text-slate-300'}
                        `} 
                        title="Más opciones"
                    >
                        <MoreHorizontal className="w-[20px] h-[20px]" />
                        <span className="text-[10px] mt-1">Más</span>
                    </button>

                    {isMobileMoreOpen && (
                        <div className="absolute bottom-full mb-2 right-0 w-52 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl shadow-black/60 py-2 z-[70]" 
                            style={{ animation: 'slideUp 0.15s ease-out' }}>
                            <Link href="/reportes" onClick={() => setIsMobileMoreOpen(false)}
                                className="flex items-center gap-3 px-4 py-3 text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                                <BarChart3 size={16} /> Reportes
                            </Link>
                            <Link href="/finops" onClick={() => setIsMobileMoreOpen(false)}
                                className="flex items-center gap-3 px-4 py-3 text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                                <Receipt size={16} /> FinOps
                            </Link>
                            <div className="border-t border-slate-800 my-1" />
                            <button onClick={() => { setIsMobileMoreOpen(false); handleLogout() }}
                                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors">
                                <LogOut size={16} /> Cerrar Sesión
                            </button>
                        </div>
                    )}
                </div>
            </div>
            </div>
            
            <div className="hidden md:flex flex-col gap-4 w-full px-2 flex-shrink-0">
                <button 
                    onClick={() => setIsNotificationFeedOpen(!isNotificationFeedOpen)}
                    className={`w-full justify-center p-3 rounded-xl flex transition-all relative ${isNotificationFeedOpen ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-500 hover:text-emerald-400 hover:bg-slate-800/50'}`} 
                    title="Notificaciones"
                >
                    <Bell size={22} />
                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2 min-w-[18px] h-[18px] bg-emerald-500 rounded-full border-2 border-slate-900 text-[9px] text-white font-black flex items-center justify-center shadow-sm">
                            {unreadCount}
                        </span>
                    )}
                </button>
                <Link href="/config">
                    <div className={`w-full justify-center p-3 rounded-xl flex transition-all ${isActive('/config') ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-500 hover:text-emerald-400 hover:bg-slate-800/50'}`} title="Configuración">
                        <Settings size={22} />
                    </div>
                </Link>
                <button onClick={handleLogout} className="w-full justify-center p-3 rounded-xl flex transition-all text-slate-500 hover:text-rose-400 hover:bg-slate-800/50" title="Cerrar sesión">
                    <LogOut size={22} />
                </button>
            </div>
        </div>
    )
}
