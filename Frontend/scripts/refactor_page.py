import sys

file_path = "d:/WebDev/IA/Frontend/app/page.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_imports = """import Sidebar from '@/components/Layout/Sidebar'
import DashboardView from '@/components/Dashboard/DashboardView'
import ContactList from '@/components/Conversations/ContactList'
import ChatArea from '@/components/Conversations/ChatArea'
import ClientProfilePanel from '@/components/Conversations/ClientProfilePanel'
import PacientesView from '@/components/CRM/PacientesView'
import AgendaView from '@/components/Agenda/AgendaView'
import FinopsView from '@/components/CRM/FinopsView'
"""

# Insert imports at line 9
lines.insert(8, new_imports)

# Find the start of `return (`
return_index = -1
for i, line in enumerate(lines):
    if "return (" in line and "className=\"flex flex-col" in lines[i+1]:
        return_index = i
        break

if return_index == -1:
    print("Could not find return statement")
    sys.exit(1)

# Keep the first part of the file (state, effects)
keep_lines = lines[:return_index]

new_render = """    return (
        <div className="flex flex-col md:flex-row h-[100dvh] w-full bg-[#f4f7f6] overflow-hidden text-[#1e293b] font-sans antialiased relative">
            
            {/* Global Toasts */}
            <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 max-w-sm w-full px-4 md:px-0 pointer-events-none">
                {toasts.map(toast => (
                    <div key={toast.id} className="bg-white pointer-events-auto border-l-4 border-rose-500 shadow-2xl rounded-lg p-4 flex flex-col gap-2 animate-in slide-in-from-top-4 fade-in duration-300">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-2 text-rose-600 font-bold text-sm uppercase tracking-wide">
                                <AlertTriangle size={16} /> Alerta de Sistema
                            </div>
                            <button onClick={() => setToasts(t => t.filter(x => x.id !== toast.id))} className="text-slate-400 hover:text-slate-600">
                                <XCircle size={16} />
                            </button>
                        </div>
                        <p className="text-sm font-medium text-slate-700">{toast.payload?.content}</p>
                    </div>
                ))}
            </div>

            <Sidebar 
                activeNav={activeNav}
                setActiveNav={setActiveNav}
                setMobileView={setMobileView}
                handleLogout={handleLogout}
            />

            {/* MAIN CONTENT AREA */}
            <div className="flex flex-1 overflow-hidden relative">
                {activeNav === 'dashboard' && (
                    <DashboardView setActiveNav={setActiveNav} setMobileView={setMobileView} />
                )}

                {activeNav === 'chats' && (
                    <div className="flex w-full h-full relative">
                        <ContactList 
                            contacts={contacts}
                            setContacts={setContacts}
                            selectedContact={selectedContact}
                            setSelectedContact={setSelectedContact}
                            fetchMessages={fetchMessages}
                            simulationMode={simulationMode}
                            setSimulationMode={setSimulationMode}
                            mobileView={mobileView}
                            setMobileView={setMobileView}
                        />

                        <ChatArea 
                            selectedContact={selectedContact}
                            messages={messages}
                            mobileView={mobileView}
                            setMobileView={setMobileView}
                            showDesktopInfo={showDesktopInfo}
                            setShowDesktopInfo={setShowDesktopInfo}
                            toggleBot={toggleBot}
                            isTestContact={isTestContact}
                            messagesEndRef={messagesEndRef}
                            newMessage={newMessage}
                            setNewMessage={setNewMessage}
                            handleSendMessage={handleSendMessage}
                        />

                        <ClientProfilePanel 
                            selectedContact={selectedContact}
                            setSelectedContact={setSelectedContact}
                            contacts={contacts}
                            setContacts={setContacts}
                            mobileView={mobileView}
                            setMobileView={setMobileView}
                            showDesktopInfo={showDesktopInfo}
                            setShowDesktopInfo={setShowDesktopInfo}
                            isTestContact={isTestContact}
                        />
                    </div>
                )}

                {activeNav === 'pacientes' && <PacientesView />}
                
                {activeNav === 'agenda' && <AgendaView />}
                
                {['reportes', 'finops'].includes(activeNav) && (
                    <FinopsView type={activeNav as 'reportes' | 'finops'} />
                )}
            </div>
        </div>
    )
}
"""

keep_lines.append(new_render)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(keep_lines)

print("Successfully refactored page.tsx!")
