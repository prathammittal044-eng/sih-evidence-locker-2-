'use client';
import { useState } from 'react';
import { loginRequest, saveSession } from '@/lib/auth';
import { Shield, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';

const ROLE_COLORS: Record<string, string> = {
  Officer:  'bg-blue-700',
  Reviewer: 'bg-emerald-700',
  Judge:    'bg-purple-800',
};

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { access_token, user } = await loginRequest(username, password);
      saveSession(access_token, user);
      window.location.href = '/';
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#f0f4f8' }}>

      {/* TOP SECURITY BANNER */}
      <div className="bg-red-700 text-white text-center py-1.5 text-xs font-bold tracking-widest uppercase">
        RESTRICTED ACCESS — AUTHORISED PERSONNEL ONLY — GOVERNMENT OF INDIA
      </div>

      {/* GOVERNMENT HEADER */}
      <header style={{ background: '#1a3a6b' }} className="text-white">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-5">
          {/* Emblem placeholder — Ashoka chakra text symbol */}
          <div className="flex-shrink-0 w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-lg">
            <span className="text-3xl">🔰</span>
          </div>
          <div>
            <p className="text-xs font-bold tracking-widest text-blue-200 uppercase">भारत सरकार — Government of India</p>
            <h1 className="text-xl font-black tracking-wide leading-tight">Ministry of Home Affairs</h1>
            <p className="text-sm text-blue-300 font-medium">Digital Evidence Management &amp; Secure Locker System</p>
          </div>
        </div>
        {/* Tricolour strip */}
        <div className="flex h-1.5">
          <div className="flex-1" style={{ background: '#FF9933' }} />
          <div className="flex-1 bg-white" />
          <div className="flex-1" style={{ background: '#138808' }} />
        </div>
      </header>

      {/* MAIN BODY */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">

          {/* Login Card */}
          <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200">

            {/* Card Header */}
            <div style={{ background: '#1a3a6b' }} className="px-8 py-6 text-white text-center">
              <div className="w-14 h-14 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-3 border-2 border-white/30">
                <Shield className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-xl font-black tracking-wide">SECURE OFFICER LOGIN</h2>
              <p className="text-blue-200 text-xs mt-1 tracking-widest uppercase">Evidence Locker Portal — v2.0</p>
            </div>

            {/* Classification notice */}
            <div className="bg-amber-50 border-b border-amber-200 px-6 py-2.5 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
              <p className="text-xs text-amber-800 font-semibold">
                This system is for official use only. Unauthorised access is a criminal offence under IT Act 2000.
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleLogin} className="px-8 py-7 space-y-5">
              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-semibold">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div>
                <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-1.5">
                  Officer ID / Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="e.g. sharma"
                  required
                  className="w-full border-2 border-slate-200 focus:border-blue-600 rounded-lg px-4 py-3 text-sm font-semibold text-slate-800 outline-none transition-colors bg-slate-50 focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••••"
                    required
                    className="w-full border-2 border-slate-200 focus:border-blue-600 rounded-lg px-4 py-3 pr-12 text-sm font-semibold text-slate-800 outline-none transition-colors bg-slate-50 focus:bg-white"
                  />
                  <button type="button" onClick={() => setShowPass(p => !p)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700">
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{ background: loading ? '#94a3b8' : '#1a3a6b' }}
                className="w-full text-white font-black py-3.5 rounded-lg tracking-widest text-sm uppercase transition-all hover:opacity-90 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <><span className="animate-spin border-2 border-white border-t-transparent rounded-full w-4 h-4 inline-block" /> Authenticating...</>
                ) : (
                  <><Shield className="w-4 h-4" /> Sign In Securely</>
                )}
              </button>
            </form>

            {/* Demo credentials box */}
            <div className="mx-8 mb-7 bg-slate-50 border border-slate-200 rounded-xl p-4">
              <p className="text-xs font-black text-slate-500 uppercase tracking-widest mb-3">Demo Credentials</p>
              <div className="space-y-2">
                {[
                  { username: 'sharma',  password: 'Officer@123',  role: 'Officer',  name: 'Sub-Inspector Sharma' },
                  { username: 'verma',   password: 'Reviewer@123', role: 'Reviewer', name: 'Chief Inspector Verma' },
                  { username: 'judge1',  password: 'Judge@123',    role: 'Judge',    name: 'Hon. Judge Patel' },
                ].map(cred => (
                  <button key={cred.username} type="button"
                    onClick={() => { setUsername(cred.username); setPassword(cred.password); }}
                    className="w-full flex items-center justify-between bg-white hover:bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 transition-colors text-left"
                  >
                    <div>
                      <p className="text-xs font-bold text-slate-700">{cred.name}</p>
                      <p className="text-xs text-slate-400 font-mono">{cred.username} / {cred.password}</p>
                    </div>
                    <span className={`text-xs text-white font-bold px-2 py-0.5 rounded ${ROLE_COLORS[cred.role]}`}>
                      {cred.role}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Footer note */}
          <p className="text-center text-xs text-slate-400 mt-5">
            NIC — National Informatics Centre &nbsp;|&nbsp; MHA Digital Infrastructure &nbsp;|&nbsp; Helpline: 1930
          </p>
        </div>
      </main>

      {/* PAGE FOOTER */}
      <footer style={{ background: '#1a3a6b' }} className="text-white text-center py-3 text-xs text-blue-300">
        © Government of India, Ministry of Home Affairs &nbsp;|&nbsp; All rights reserved &nbsp;|&nbsp; Built on NIC Infrastructure
      </footer>
    </div>
  );
}
