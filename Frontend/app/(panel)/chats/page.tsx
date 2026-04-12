'use client'

import ContactList from '@/components/Conversations/ContactList'
import ChatArea from '@/components/Conversations/ChatArea'
import TestChatArea from '@/components/Conversations/TestChatArea'
import ClientProfilePanel from '@/components/Conversations/ClientProfilePanel'
import TestConfigPanel from '@/components/Conversations/TestConfigPanel'
import { useCrm } from '@/contexts/CrmContext'

export default function ChatsPage() {
  const { selectedContact, mobileView } = useCrm()

  const isTestContact = selectedContact?.phone_number === '56912345678'

  return (
    <div className="flex-1 flex overflow-hidden relative">
      {/* Contact List: Visible in 'list' mode on mobile, always on desktop */}
      <div className={`
        ${mobileView === 'list' ? 'flex w-full' : 'hidden'} 
        lg:flex lg:w-[320px] xl:w-[380px] border-r border-slate-200
        flex-col h-full flex-shrink-0
      `}>
        <ContactList />
      </div>

      {/* Main Chat Area: Visible in 'chat' mode on mobile, always on desktop when contact selected */}
      <div className={`
        flex-1 flex flex-col min-w-0
        ${mobileView === 'chat' || mobileView === 'info' ? 'flex w-full' : 'hidden'} 
        lg:flex
      `}>
        {isTestContact ? <TestChatArea /> : <ChatArea />}
      </div>

      {/* Right Panel (Profile or Test Config): Only visible if explicitly opened */}
      {isTestContact ? <TestConfigPanel /> : <ClientProfilePanel />}
    </div>
  )
}
