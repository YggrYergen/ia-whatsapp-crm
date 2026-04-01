'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function RootPage() {
  const router = useRouter()

  useEffect(() => {
    // Basic redirect to dashboard as starting point
    router.replace('/dashboard')
  }, [router])

  return (
    <div className="h-screen w-full flex items-center justify-center bg-slate-900 text-white">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="font-bold text-emerald-400">Iniciando Command Center...</p>
      </div>
    </div>
  )
}
