'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/Layout/Sidebar'
import GlobalNotifications from '@/components/Layout/GlobalNotifications'
import GlobalFeedbackButton from '@/components/Layout/GlobalFeedbackButton'
import { CrmProvider } from '@/contexts/CrmContext'
import { createClient } from '@/lib/supabase'

export default function PanelLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [isAuthed, setIsAuthed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const supabase = createClient()

    // Check initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.replace('/login')
      } else {
        setIsAuthed(true)
      }
      setIsLoading(false)
    })

    // Listen for auth changes (logout, token expiry)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session) {
          router.replace('/login')
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [router])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen w-full bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-slate-400">Verificando sesión...</p>
        </div>
      </div>
    )
  }

  if (!isAuthed) return null

  return (
    <CrmProvider>
      <GlobalNotifications />
      <GlobalFeedbackButton />
      <div className="flex flex-col md:flex-row h-screen w-full bg-slate-50 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 flex flex-col relative overflow-hidden h-full z-10 transition-all pb-sidebar md:pb-0">
          {children}
        </main>
      </div>
    </CrmProvider>
  )
}
