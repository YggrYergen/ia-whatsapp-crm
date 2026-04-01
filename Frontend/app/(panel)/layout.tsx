import Sidebar from '@/components/Layout/Sidebar'
import GlobalNotifications from '@/components/Layout/GlobalNotifications'
import GlobalFeedbackButton from '@/components/Layout/GlobalFeedbackButton'
import { CrmProvider } from '@/contexts/CrmContext'

export default function PanelLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <CrmProvider>
      <GlobalNotifications />
      <GlobalFeedbackButton />
      <div className="flex flex-col md:flex-row h-screen w-full bg-slate-50 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 flex flex-col relative overflow-hidden h-full z-10 transition-all">
          {children}
        </main>
      </div>
    </CrmProvider>
  )
}
