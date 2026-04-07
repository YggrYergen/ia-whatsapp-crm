'use client'

import React from 'react'
import { Sparkles, LayoutDashboard, MessageCircle, CalendarIcon, Users, BarChart3, Receipt, Settings, LogOut, Terminal, Bell } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useCrm } from '@/contexts/CrmContext'
import { useUI } from '@/contexts/UIContext'

export default function Sidebar() {
    const pathname = usePathname()
    const { setMobileView, user } = useCrm()
    const { unreadCount, isNotificationFeedOpen, setIsNotificationFeedOpen } = useUI()

    const handleLogout = () => {
        // Mock logout
        window.location.href = '/login'
    }

    const isActive = (path: string) => pathname === path

    const navItems = [
        { href: '/dashboard', icon: LayoutDashboard, title: 'Panel', label: 'Panel' },
        { href: '/chats', icon: MessageCircle, title: 'Chats', label: 'Chats', alert: true },
        { href: '/agenda', icon: CalendarIcon, title: 'Agenda', label: 'Agenda' },
        { href: '/pacientes', icon: Users, title: 'Pacientes', label: 'CRM' },
        { href: '/reportes', icon: BarChart3, title: 'Reportes', desktopOnly: true },
        { href: '/finops', icon: Receipt, title: 'FinOps', desktopOnly: true },
        ...(['tomasgemes@gmail.com', 'alejandra.tamar.rojas@gmail.com', 'instagramelectrimax@gmail.com'].includes(user?.email) ? [
            { href: '/admin-feedback', icon: Terminal, title: 'Auditoría Dev', label: 'Dev' }
        ] : [])
    ]

    return (
        <div className={`
            bg-slate-900 border-t md:border-t-0 md:border-r border-slate-800 flex-shrink-0 z-50
            fixed bottom-0 left-0 w-full h-[68px] flex flex-row items-center justify-around px-2
            md:relative md:w-20 md:h-full md:flex-col md:justify-start md:py-6 md:px-0 md:gap-6
            pb-safe md:pb-6
        `}>
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
                        {item.alert && (
                            <span className="absolute top-2 right-2 md:top-2 md:right-2 w-2.5 h-2.5 bg-rose-500 rounded-full border-2 border-slate-900 border-transparent shadow-sm"></span>
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
                        <span className="absolute top-2 right-2 md:top-2 md:right-2 w-2.5 h-2.5 bg-rose-500 rounded-full border-2 border-slate-900 shadow-sm"></span>
                    )}
                    <span className="text-[10px] mt-1 md:hidden">Alertas</span>
                </button>
            </div>
            
            <div className="hidden md:flex flex-col gap-4 w-full px-2 mt-auto">
                <button 
                    onClick={() => setIsNotificationFeedOpen(!isNotificationFeedOpen)}
                    className={`w-full justify-center p-3 rounded-xl flex transition-all relative ${isNotificationFeedOpen ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-500 hover:text-emerald-400 hover:bg-slate-800/50'}`} 
                    title="Notificaciones"
                >
                    <Bell size={22} />
                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2 w-3 h-3 bg-rose-500 rounded-full border-2 border-slate-900 shadow-sm"></span>
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
