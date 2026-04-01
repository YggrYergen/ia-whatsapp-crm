import React from 'react'
import { TrendingUp, DollarSign, BarChart, Zap, CreditCard, ArrowUpRight, Activity } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart as ReBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const finopsData = [
    { month: 'Ene', ingresos: 4000, costos: 2400 },
    { month: 'Feb', ingresos: 3000, costos: 1398 },
    { month: 'Mar', ingresos: 2000, costos: 9800 },
    { month: 'Abr', ingresos: 2780, costos: 3908 },
    { month: 'May', ingresos: 1890, costos: 4800 },
    { month: 'Jun', ingresos: 2390, costos: 3800 },
];

interface FinopsViewProps {
    type: 'reportes' | 'finops';
}

export default function FinopsView({ type }: FinopsViewProps) {
    return (
        <div className="flex-1 overflow-y-auto bg-slate-50/30 p-4 md:p-8 space-y-8 pb-[100px] md:pb-10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-black text-slate-800 tracking-tight capitalize">
                        {type === 'finops' ? 'Análisis de Costos (FinOps)' : 'Reportes de Negocio'}
                    </h2>
                    <p className="text-slate-500 font-medium">Visualización en tiempo real de márgenes y consumo de API.</p>
                </div>
                <button className="bg-emerald-600 text-white font-bold py-2.5 px-6 rounded-xl shadow-lg shadow-emerald-600/20 flex items-center gap-2 hover:bg-emerald-700 transition-colors text-sm">
                    <Zap size={16} /> Mejorar a Pro+
                </button>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-slate-100 shadow-sm overflow-hidden group hover:shadow-md transition-shadow">
                    <CardContent className="p-5">
                        <div className="flex items-center gap-3 mb-3 text-emerald-600">
                            <div className="p-2 bg-emerald-50 rounded-lg group-hover:scale-110 transition-transform"><TrendingUp size={20} /></div>
                            <span className="text-[10px] font-black uppercase tracking-widest">Ingresos Brutos</span>
                        </div>
                        <div className="text-2xl font-black text-slate-800 tracking-tight">$4,250</div>
                        <div className="text-[10px] text-emerald-500 font-bold mt-1">+15.2% vs mes anterior</div>
                    </CardContent>
                </Card>
                <Card className="border-slate-100 shadow-sm overflow-hidden group hover:shadow-md transition-shadow">
                    <CardContent className="p-5">
                        <div className="flex items-center gap-3 mb-3 text-rose-600">
                            <div className="p-2 bg-rose-50 rounded-lg group-hover:scale-110 transition-transform"><Zap size={20} /></div>
                            <span className="text-[10px] font-black uppercase tracking-widest">Costos LLM (Tokens)</span>
                        </div>
                        <div className="text-2xl font-black text-slate-800 tracking-tight">$312</div>
                        <div className="text-[10px] text-rose-400 font-bold mt-1">Eficiencia: 92%</div>
                    </CardContent>
                </Card>
                <Card className="border-slate-100 shadow-sm overflow-hidden group hover:shadow-md transition-shadow">
                    <CardContent className="p-5">
                        <div className="flex items-center gap-3 mb-3 text-blue-600">
                            <div className="p-2 bg-blue-50 rounded-lg group-hover:scale-110 transition-transform"><ArrowUpRight size={20} /></div>
                            <span className="text-[10px] font-black uppercase tracking-widest">Margen Operativo</span>
                        </div>
                        <div className="text-2xl font-black text-slate-800 tracking-tight">85%</div>
                        <div className="text-[10px] text-blue-400 font-bold mt-1">Óptimo para SaaS B2B</div>
                    </CardContent>
                </Card>
                <Card className="border-slate-100 shadow-sm overflow-hidden group hover:shadow-md transition-shadow">
                    <CardContent className="p-5">
                        <div className="flex items-center gap-3 mb-3 text-amber-600">
                            <div className="p-2 bg-amber-50 rounded-lg group-hover:scale-110 transition-transform"><CreditCard size={20} /></div>
                            <span className="text-[10px] font-black uppercase tracking-widest">Citas Pendientes Cobro</span>
                        </div>
                        <div className="text-2xl font-black text-slate-800 tracking-tight">$850</div>
                        <div className="text-[10px] text-amber-500 font-bold mt-1">6 citas pendientes</div>
                    </CardContent>
                </Card>
            </div>

            <Card className="border-slate-100 shadow-xl overflow-hidden">
                <CardHeader className="bg-white border-b border-slate-50">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-xl font-black text-slate-800 flex items-center gap-3">
                                <Activity size={22} className="text-emerald-600" /> Rendimiento Mensual
                            </CardTitle>
                            <CardDescription className="font-medium">Comparativa de ingresos reales vs costos de infraestructura AI</CardDescription>
                        </div>
                        <div className="flex gap-2">
                             <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 rounded-lg">
                                 <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
                                 <span className="text-[10px] font-black text-emerald-700 uppercase">Ingresos</span>
                             </div>
                             <div className="flex items-center gap-1.5 px-3 py-1 bg-rose-50 rounded-lg">
                                 <div className="w-2.5 h-2.5 rounded-full bg-rose-500"></div>
                                 <span className="text-[10px] font-black text-rose-700 uppercase">Costos API</span>
                             </div>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="pt-8 h-[400px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <ReBarChart data={finopsData}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontStyle: 'bold', fontSize: 13}} dy={10} />
                            <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontStyle: 'bold', fontSize: 13}} />
                            <Tooltip 
                                cursor={{fill: '#f8fafc'}}
                                contentStyle={{backgroundColor: '#fff', borderRadius: '16px', border: 'none', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)', padding: '12px'}}
                                itemStyle={{fontWeight: 'bold', fontSize: '12px'}}
                            />
                            <Bar dataKey="ingresos" fill="#10b981" radius={[6, 6, 0, 0]} barSize={34} />
                            <Bar dataKey="costos" fill="#f43f5e" radius={[6, 6, 0, 0]} barSize={34} />
                        </ReBarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            <div className="bg-indigo-900 rounded-[2rem] p-8 text-white relative overflow-hidden shadow-2xl">
                <div className="relative z-10">
                    <Badge variant="secondary" className="bg-indigo-500/30 text-white border-indigo-400/30 mb-4 px-4 py-1">Tip Empresa</Badge>
                    <h3 className="text-3xl font-black mb-3">Maximiza tu ROI con Agendamiento Automático</h3>
                    <p className="text-indigo-200 max-w-xl font-medium text-lg leading-relaxed">
                        El 40% de los costos de tokens provienen de clientes que preguntan por horarios. Al optimizar tu Prompt, hemos reducido el desperdicio en un 12% este mes.
                    </p>
                    <button className="mt-8 bg-white text-indigo-900 font-black px-10 py-4 rounded-2xl hover:bg-slate-100 transition-all shadow-xl active:scale-95 text-lg">
                        Ver Auditoría de Tokens
                    </button>
                </div>
                <div className="absolute top-0 right-0 p-12 opacity-10">
                    <BarChart size={240} />
                </div>
                <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-emerald-500/20 blur-[100px] rounded-full"></div>
            </div>
        </div>
    )
}
