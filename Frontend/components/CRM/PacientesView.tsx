import React from 'react'
import { Filter, Plus, Search, Sparkles, Pause } from 'lucide-react'

export default function PacientesView() {
    return (
        <div className="flex-1 overflow-y-auto bg-slate-50 p-6 lg:p-10 w-full transition-all pb-[100px] md:pb-10 fixed inset-0 md:static top-[72px] bottom-0 z-40 md:z-0">
            <div className="max-w-6xl mx-auto space-y-6">
                <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
                    <div>
                        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Base de Pacientes CRM</h2>
                        <p className="text-slate-500 mt-1">Directorio consolidado de leads y clientes gestionados por IA.</p>
                    </div>
                    <div className="flex gap-2">
                        <button className="bg-white border border-slate-200 text-slate-600 font-bold py-2 px-4 rounded-lg shadow-sm flex items-center gap-2 hover:bg-slate-50">
                            <Filter size={16} /> Filtrar
                        </button>
                        <button className="bg-emerald-600 text-white font-bold py-2 px-4 rounded-lg shadow-sm flex items-center gap-2 hover:bg-emerald-700">
                            <Plus size={16} /> Nuevo Contacto
                        </button>
                    </div>
                </div>

                {/* Search bar */}
                <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex gap-4">
                    <div className="relative flex-1">
                        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input type="text" placeholder="Buscar por nombre, teléfono o etiqueta..." className="w-full bg-slate-50 border-none rounded-xl pl-10 pr-4 py-3 outline-none focus:ring-2 focus:ring-emerald-500 text-sm font-medium" />
                    </div>
                </div>

                {/* Data Table */}
                <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                        <thead>
                            <tr className="bg-slate-50 text-slate-500 text-xs uppercase font-bold tracking-wider border-b border-slate-200">
                                <th className="p-4 pl-6">Paciente / Lead</th>
                                <th className="p-4">Contacto</th>
                                <th className="p-4">Etapa Pipeline</th>
                                <th className="p-4">LTV Aprox</th>
                                <th className="p-4">Agente</th>
                                <th className="p-4 text-center">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm font-medium text-slate-800">
                            {[
                                { name: 'Andrea Valenzuela', phone: '+56 9 8765 4321', status: 'Cliente Frecuente', ltv: '$450', ai: true },
                                { name: 'Roberto Díaz', phone: '+56 9 1122 3344', status: 'Lead Nuevo', ltv: '$0', ai: true },
                                { name: 'Camila Muñoz', phone: '+56 9 5555 6666', status: 'Cita Agendada', ltv: '$120', ai: false },
                                { name: 'Test User (Simulador)', phone: '56912345678', status: 'Demo', ltv: 'N/A', ai: true },
                            ].map((p, i) => (
                                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors cursor-pointer group">
                                    <td className="p-4 pl-6 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">{p.name.charAt(0)}</div>
                                        <span className="font-bold">{p.name}</span>
                                    </td>
                                    <td className="p-4 text-slate-500 font-mono text-xs">{p.phone}</td>
                                    <td className="p-4">
                                        <span className={`px-2.5 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider
                                            ${p.status.includes('Cliente') ? 'bg-blue-100 text-blue-700' : p.status.includes('Lead') ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'}`
                                        }>
                                            {p.status}
                                        </span>
                                    </td>
                                    <td className="p-4 text-emerald-600 font-bold">{p.ltv}</td>
                                    <td className="p-4">
                                        {p.ai ? <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-600"><Sparkles size={12} /> Activo</span> : <span className="flex items-center gap-1.5 text-xs font-bold text-slate-400"><Pause size={12} /> Pausado</span>}
                                    </td>
                                    <td className="p-4 text-center">
                                        <button className="text-slate-400 hover:text-emerald-600 opacity-0 group-hover:opacity-100 transition-all font-bold text-xs uppercase">Ver Ficha</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <div className="p-4 bg-slate-50 text-center border-t border-slate-100">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Mostrando 4 de 1,204 Contactos</span>
                    </div>
                </div>
            </div>
        </div>
    )
}
