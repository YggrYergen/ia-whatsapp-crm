'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'

const supabase = createClient()

interface AuthContextType {
    user: any;
    setUser: (user: any) => void;
    isLoadingAuth: boolean;
    dashboardRole: 'admin' | 'staff';
    setDashboardRole: (role: 'admin' | 'staff') => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<any>(null)
    const [isLoadingAuth, setIsLoadingAuth] = useState(true)
    const [dashboardRole, setDashboardRole] = useState<'admin' | 'staff'>('admin')

    useEffect(() => {
        const checkUser = async () => {
            const { data: { session } } = await supabase.auth.getSession()
            setUser(session?.user || null)
            setIsLoadingAuth(false)
        }

        checkUser()

        const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user || null)
        })

        return () => {
            authListener?.subscription?.unsubscribe()
        }
    }, [])

    return (
        <AuthContext.Provider value={{
            user, setUser,
            isLoadingAuth,
            dashboardRole, setDashboardRole
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
