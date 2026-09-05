'use client';
import { useEffect, useState } from 'react';
import useSWR from 'swr';
import { fetcher } from '../../api';
import { useRouter } from 'next/navigation';
import { Calendar, Clock, Activity, Info, LogOut, HeartPulse, UserCircle, Stethoscope, Plus, Loader2, Sparkles, ChevronRight } from 'lucide-react';

export default function PatientDashboard() {
  const [userId, setUserId] = useState<string | null>(null);
  const router = useRouter();
  const [booking, setBooking] = useState(false);
  const [shapExpanded, setShapExpanded] = useState(false);
  const [bookDept, setBookDept] = useState('Cardiology');
  const [bookDoc, setBookDoc] = useState('DOC_CAR_1');
  const [bookType, setBookType] = useState('new');
  const [bookTime, setBookTime] = useState(() => {
      const now = new Date();
      now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
      return now.toISOString().slice(0, 16);
  });
  
  const DOCTORS: Record<string, string[]> = {
    'Cardiology': ['DOC_CAR_1', 'DOC_CAR_2'],
    'General Physician': ['DOC_GEN_1', 'DOC_GEN_2'],
    'Orthopedics': ['DOC_ORT_1', 'DOC_ORT_2'],
    'Pediatrics': ['DOC_PED_1', 'DOC_PED_2']
  };

  useEffect(() => {
    setUserId(localStorage.getItem('userId'));
  }, []);

  const { data: history, error, mutate } = useSWR(userId ? `/patients/${userId}` : null, fetcher, { refreshInterval: 5000 });
  
  const currentAppt = history?.visit_history?.[0];
  const isUpcoming = currentAppt && !currentAppt.actual_start_time;

  const { data: status } = useSWR(
    isUpcoming ? `/appointments/${currentAppt.appointment_id}/status` : null, 
    fetcher, 
    { refreshInterval: 5000 }
  );

  const handleLogout = () => {
    localStorage.clear();
    router.push('/');
  };

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault();
    setBooking(true);
    const token = localStorage.getItem('token');
    try {
      const res = await fetch('http://localhost:8000/api/appointments/', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ doctor_id: bookDoc, department: bookDept, appointment_type: bookType, scheduled_time: new Date(bookTime).toISOString() })
      });
      if (res.ok) {
        await mutate(); // Refresh history immediately
      } else {
        alert("Failed to book appointment");
      }
    } catch(err) {
      alert("Error booking");
    }
    setBooking(false);
  };

  if (!userId) return null;
  
  if (error) return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <div className="text-red-500 font-medium p-4 bg-red-50 rounded-xl border border-red-200 flex items-center gap-2">
              <Info size={20} /> Failed to load patient data. Please try logging in again.
          </div>
      </div>
  );
  
  if (!history) return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center flex-col gap-3">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-500 font-medium">Loading your health data...</p>
      </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans pb-20">
      
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
          <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
              <div className="flex items-center gap-2 text-blue-700">
                  <div className="bg-blue-600 p-1.5 rounded-lg text-white">
                      <HeartPulse size={20} strokeWidth={2.5} />
                  </div>
                  <span className="font-bold text-lg tracking-tight">PulsePredict</span>
              </div>
              <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                      <UserCircle size={18} className="text-slate-400" /> {userId}
                  </div>
                  <button onClick={handleLogout} className="text-slate-400 hover:text-red-500 transition-colors p-2 rounded-full hover:bg-red-50">
                      <LogOut size={20} />
                  </button>
              </div>
          </div>
      </header>

      <main className="p-6 max-w-5xl mx-auto py-10 space-y-8">
          <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Welcome Back</h1>
              <p className="text-slate-500 mt-1">Manage your health and track live wait times.</p>
          </div>
          
          {isUpcoming && status ? (
            <div className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="bg-gradient-to-r from-blue-600 to-cyan-500 p-6 sm:p-8 text-white relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white opacity-5 rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/4"></div>
                    <div className="relative z-10 flex flex-col md:flex-row justify-between gap-6">
                        
                        <div className="flex-1">
                            <div className="flex items-center gap-2 text-blue-100 font-semibold mb-1 uppercase tracking-wider text-xs">
                                <Activity size={16} /> Live Status
                            </div>
                            <h2 className="text-2xl font-bold mb-4">{currentAppt.department}</h2>
                            <div className="flex items-center gap-4 text-blue-50">
                                <div className="flex items-center gap-2 bg-black/10 px-3 py-1.5 rounded-lg text-sm font-medium">
                                    <Calendar size={16} />
                                    {new Date(currentAppt.scheduled_time).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
                                </div>
                                <div className="flex items-center gap-2 bg-black/10 px-3 py-1.5 rounded-lg text-sm font-medium">
                                    <Clock size={16} />
                                    {new Date(currentAppt.scheduled_time).toLocaleTimeString([], {timeStyle: 'short'})}
                                </div>
                            </div>
                        </div>

                        {/* Live Prediction Box */}
                        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-5 rounded-2xl md:min-w-[280px]">
                            <h3 className="text-blue-100 font-medium text-sm mb-1 flex items-center gap-2">
                                <Clock size={16} /> Expected Consultation Window
                            </h3>
                            <p className="text-3xl font-extrabold tracking-tight mt-1 mb-2 drop-shadow-md">
                                {new Date(status.predicted_p10).toLocaleTimeString([], {timeStyle: 'short'})} <span className="text-blue-200 text-xl font-normal mx-1">to</span> {new Date(status.predicted_p90).toLocaleTimeString([], {timeStyle: 'short'})}
                            </p>
                            <div className="mb-3 inline-block bg-emerald-500/20 border border-emerald-400/30 text-emerald-100 px-3 py-1.5 rounded-lg text-sm font-semibold">
                                🔔 Recommended Arrival: {new Date(new Date(status.predicted_p10).getTime() - 15 * 60000).toLocaleTimeString([], {timeStyle: 'short'})}
                            </div>
                            <div className="text-xs text-blue-100/80 leading-relaxed bg-black/10 p-2.5 rounded-lg border border-white/10">
                                <Info size={14} className="inline mr-1 mb-0.5" />
                                {status.explanation}
                            </div>
                            
                            {status.shap_explanation && (
                              <div className="mt-4 bg-white/5 rounded-xl border border-white/10 overflow-hidden">
                                <button
                                  onClick={() => setShapExpanded(v => !v)}
                                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/10 transition-colors"
                                >
                                  <div className="flex items-center gap-2">
                                    <Sparkles size={14} className="text-purple-300" />
                                    <span className="text-xs font-medium text-blue-50">Why this estimate?</span>
                                  </div>
                                  <ChevronRight size={14} className={`text-blue-200 transition-transform ${shapExpanded ? 'rotate-90' : ''}`} />
                                </button>
                                
                                {shapExpanded && (
                                  <div className="px-4 pb-4 space-y-2 border-t border-white/5 pt-3">
                                    <p className="text-[10px] text-blue-200 mb-2">Base estimate: {status.shap_explanation.base_value_minutes} min</p>
                                    {status.shap_explanation.factors.map((f: any, i: number) => (
                                      <div key={i} className="flex items-center justify-between gap-3">
                                        <span className="text-xs text-blue-100/90 flex-1">{f.feature}</span>
                                        <span className={`text-xs font-semibold ${
                                          f.direction === 'increases_wait' ? 'text-red-300' : 'text-emerald-300'
                                        }`}>
                                          {f.direction === 'increases_wait' ? '+' : ''}{f.impact_minutes} min
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                        </div>

                    </div>
                </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 md:p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 text-blue-50 transform translate-x-4 -translate-y-4 pointer-events-none">
                    <Stethoscope size={150} />
                </div>
                <div className="relative z-10 max-w-xl">
                    <h2 className="text-xl font-bold tracking-tight text-slate-800 mb-2">Book an Appointment</h2>
                    <p className="text-sm text-slate-500 mb-4">Need to see a doctor? Schedule a walk-in immediately and get a live wait-time estimate instantly.</p>
                    
                    {(() => {
                      const { data: congestion } = useSWR(
                        bookDept ? `/congestion/live/${bookDept}` : null,
                        fetcher, { refreshInterval: 30000 }
                      );
                      
                      if (!congestion) return null;
                      
                      return (
                        <div className={`mb-6 flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium border ${
                          congestion.current_state === 'HEALTHY' ? 'bg-green-50 border-green-200 text-green-700' :
                          congestion.current_state === 'MODERATE' ? 'bg-yellow-50 border-yellow-200 text-yellow-700' :
                          congestion.current_state === 'BUSY' ? 'bg-orange-50 border-orange-200 text-orange-700' :
                          'bg-red-50 border-red-200 text-red-700'
                        }`}>
                          <Activity size={16} />
                          <span>{congestion.department} is currently <strong>{congestion.current_state}</strong></span>
                          {congestion.current_state !== 'HEALTHY' && (
                            <span className="text-xs opacity-75 ml-1">- longer waits possible</span>
                          )}
                        </div>
                      );
                    })()}
                    
                    <form onSubmit={handleBook} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Department</label>
                                <select 
                                    value={bookDept} 
                                    onChange={(e) => {
                                        setBookDept(e.target.value); 
                                        setBookDoc(DOCTORS[e.target.value][0]);
                                    }}
                                    className="w-full bg-slate-50 border border-slate-200 text-slate-700 py-2.5 px-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium text-sm"
                                >
                                    {Object.keys(DOCTORS).map(d => <option key={d} value={d}>{d}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Doctor</label>
                                <select 
                                    value={bookDoc} 
                                    onChange={(e) => setBookDoc(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-200 text-slate-700 py-2.5 px-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium text-sm"
                                >
                                    {DOCTORS[bookDept].map(doc => <option key={doc} value={doc}>{doc}</option>)}
                                </select>
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Visit Type</label>
                                <select 
                                    value={bookType} 
                                    onChange={(e) => setBookType(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-200 text-slate-700 py-2.5 px-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium text-sm"
                                >
                                    <option value="new">New Consultation</option>
                                    <option value="follow_up">Follow Up</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Time</label>
                                <input 
                                    type="datetime-local" 
                                    value={bookTime} 
                                    onChange={(e) => setBookTime(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-200 text-slate-700 py-2.5 px-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium text-sm"
                                />
                            </div>
                        </div>
                        <button 
                            type="submit" 
                            disabled={booking}
                            className="flex items-center justify-center gap-2 w-full md:w-auto bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-6 rounded-lg transition-colors disabled:opacity-70 mt-4 shadow-sm shadow-blue-600/20"
                        >
                            {booking ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                            {booking ? 'Booking...' : 'Book Walk-in / Appointment'}
                        </button>
                    </form>
                </div>
            </div>
          )}

          <div className="space-y-4 pt-4">
              <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 text-slate-800">
                  <Calendar size={22} className="text-slate-400" /> Past Visits
              </h2>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <table className="min-w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Date</th>
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Department</th>
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {history.visit_history?.filter((v:any) => v.actual_start_time || v !== currentAppt).map((v: any, i: number) => (
                      <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                            {new Date(v.scheduled_time).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 flex items-center gap-2">
                            <Stethoscope size={16} className="text-slate-400" /> {v.department}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                            <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${v.appointment_type === 'new' ? 'bg-indigo-50 text-indigo-700 border-indigo-100' : 'bg-emerald-50 text-emerald-700 border-emerald-100'}`}>
                                {v.appointment_type.replace('_', ' ').toUpperCase()}
                            </span>
                        </td>
                      </tr>
                    ))}
                    {history.visit_history?.filter((v:any) => v.actual_start_time || v !== currentAppt).length === 0 && (
                        <tr>
                            <td colSpan={3} className="px-6 py-8 text-center text-slate-400 text-sm">
                                No past visits found.
                            </td>
                        </tr>
                    )}
                  </tbody>
                </table>
              </div>
          </div>
      </main>
    </div>
  );
}
