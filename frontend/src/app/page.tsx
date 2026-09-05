'use client';
import { useState, useEffect } from 'react';
import { login } from '../api';
import { useRouter } from 'next/navigation';
import { HeartPulse, Lock, User, ArrowRight, Loader2 } from 'lucide-react';

export default function Home() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const role = localStorage.getItem('role');
    if (role === 'patient') router.push('/patient');
    if (role === 'staff') router.push('/staff');
    if (role === 'admin') router.push('/admin');
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await login(username, password);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('role', res.role);
      localStorage.setItem('userId', res.user_id);
      
      if (res.role === 'patient') router.push('/patient');
      else if (res.role === 'staff') router.push('/staff');
      else router.push('/admin');
    } catch (err) {
      alert("Login failed. Please check your credentials.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-slate-100 to-blue-50 relative overflow-hidden text-slate-800">
      
      {/* Decorative Background Elements */}
      <div className="absolute top-[-15%] left-[-10%] w-[500px] h-[500px] bg-blue-200/50 rounded-full mix-blend-multiply filter blur-[80px] opacity-70 animate-pulse" style={{ animationDuration: '8s' }}></div>
      <div className="absolute bottom-[-10%] right-[-5%] w-[400px] h-[400px] bg-cyan-200/50 rounded-full mix-blend-multiply filter blur-[80px] opacity-70 animate-pulse" style={{ animationDuration: '10s' }}></div>
      
      {/* Login Card */}
      <div className="relative z-10 bg-white/80 backdrop-blur-xl p-10 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white/60 w-full max-w-[420px]">
        
        {/* Header */}
        <div className="flex flex-col items-center mb-10">
            <div className="bg-gradient-to-tr from-blue-600 to-cyan-400 p-4 rounded-2xl shadow-lg shadow-blue-500/20 mb-5 text-white">
                <HeartPulse size={40} strokeWidth={2} />
            </div>
            <h1 className="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-700 to-cyan-600 tracking-tight">
                PulsePredict
            </h1>
            <p className="text-sm text-slate-500 mt-2 font-medium">Smart Wait-Time Operations</p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-500 transition-colors">
              <User size={18} strokeWidth={2.5} />
            </div>
            <input 
                type="text" 
                placeholder="User ID (e.g. PAT_1)"
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                className="block w-full pl-11 pr-4 py-3.5 border border-slate-200 rounded-xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 bg-white/50 hover:bg-white transition-all text-slate-700 placeholder-slate-400 outline-none font-medium" 
                required
            />
          </div>
          
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-500 transition-colors">
              <Lock size={18} strokeWidth={2.5} />
            </div>
            <input 
                type="password" 
                placeholder="Password"
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                className="block w-full pl-11 pr-4 py-3.5 border border-slate-200 rounded-xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 bg-white/50 hover:bg-white transition-all text-slate-700 placeholder-slate-400 outline-none font-medium" 
                required
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            className="group w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold py-3.5 px-4 rounded-xl hover:from-blue-700 hover:to-cyan-600 transition-all shadow-md shadow-blue-500/25 active:scale-[0.98] disabled:opacity-70 disabled:active:scale-100 mt-2"
          >
            {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Authenticating...
                </>
            ) : (
                <>
                  Sign In
                  <ArrowRight size={18} strokeWidth={2.5} className="group-hover:translate-x-1 transition-transform" />
                </>
            )}
          </button>
        </form>

        {/* Demo Credentials Box */}
        <div className="mt-10 pt-6 border-t border-slate-100">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest text-center mb-4">Demo Access</p>
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-500">
                <div className="bg-slate-50 p-2.5 rounded-lg flex flex-col border border-slate-200/60 items-center justify-center text-center hover:border-blue-200 transition-colors">
                    <span className="font-bold text-blue-600 mb-1">Patient</span>
                    <div className="flex items-center gap-1 font-mono text-[10px]">
                        <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold shadow-sm">PAT_1</code>
                        <span className="text-slate-300">/</span>
                        <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold shadow-sm">pat</code>
                    </div>
                </div>
                <div className="bg-slate-50 p-2.5 rounded-lg flex flex-col border border-slate-200/60 items-center justify-center text-center hover:border-emerald-200 transition-colors">
                    <span className="font-bold text-emerald-600 mb-1">Staff</span>
                    <div className="flex items-center gap-1 font-mono text-[10px]">
                        <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold shadow-sm">DOC_CAR_1</code>
                        <span className="text-slate-300">/</span>
                        <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold shadow-sm">doc</code>
                    </div>
                </div>
                <div className="bg-slate-50 p-2.5 rounded-lg flex flex-col border border-slate-200/60 items-center justify-center col-span-2 hover:border-purple-200 transition-colors">
                    <span className="font-bold text-purple-600 mb-1">Admin</span>
                    <div className="flex items-center gap-1 font-mono text-[10px]">
                        <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold shadow-sm">admin1</code>
                        <span className="text-slate-300">/</span>
                        <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold shadow-sm">admin</code>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
