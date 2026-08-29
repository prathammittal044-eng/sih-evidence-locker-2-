'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { Shield, LogOut, ClipboardList, User, BadgeCheck, LayoutDashboard, FileText, Settings, FolderClosed } from 'lucide-react';
import { useState, useEffect } from 'react';
import { getUser, logout, SIHUser } from '@/lib/auth';

const ROLE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  Officer:  { bg: 'bg-blue-700',    text: 'text-blue-100',   border: 'border-blue-500' },
  Reviewer: { bg: 'bg-emerald-700', text: 'text-emerald-100', border: 'border-emerald-500' },
  Judge:    { bg: 'bg-purple-800',  text: 'text-purple-100',  border: 'border-purple-500' },
};

export default function SidebarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [user, setUser] = useState<SIHUser | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, [pathname]); // re-check on nav

  if (pathname === '/login') {
    return <>{children}</>;
  }

  const roleStyle = user ? (ROLE_STYLES[user.role] || ROLE_STYLES.Officer) : ROLE_STYLES.Officer;

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* --- LEFT SIDEBAR --- */}
      <aside className="w-64 bg-[#0a192f] text-slate-300 flex flex-col flex-shrink-0">
        
        {/* Logo Area */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700/50 bg-[#061020]">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center flex-shrink-0 shadow-lg p-1.5">
            <img src="/emblem.png" alt="Emblem of India" className="w-full h-full object-contain" />
          </div>
          <div>
            <p className="text-[9px] font-bold tracking-widest text-blue-300 uppercase leading-tight">भारत सरकार</p>
            <h1 className="text-white font-black tracking-wide text-xs leading-tight mt-0.5">EVIDENCE LOCKER</h1>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          <Link href="/" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${pathname === '/' ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'}`}>
            <LayoutDashboard className="w-5 h-5" /> Dashboard
          </Link>
          <Link href="/" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${pathname.includes('/case') && !pathname.includes('audit') ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'}`}>
            <FolderClosed className="w-5 h-5" /> Cases
          </Link>
          <Link href="/" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${pathname.includes('/document') ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'}`}>
            <FileText className="w-5 h-5" /> Documents
          </Link>
          <Link href="/audit" className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${pathname === '/audit' ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'}`}>
            <ClipboardList className="w-5 h-5" /> Audit Trail
          </Link>
        </nav>

        {/* User Profile Area at Bottom */}
        {user && (
          <div className="p-4 border-t border-slate-700/50 bg-[#061020]">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-black text-white ${roleStyle.bg} border-2 ${roleStyle.border} shadow-lg`}>
                {user.name.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-white truncate">{user.name}</p>
                <p className="text-[10px] text-slate-400 font-mono truncate uppercase tracking-wider">{user.role}</p>
              </div>
            </div>
            <button onClick={logout} className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-red-900/80 text-slate-300 hover:text-white py-2 rounded-lg text-xs font-bold transition-all border border-slate-700 hover:border-red-700/50">
              <LogOut className="w-4 h-4" /> SIGN OUT
            </button>
          </div>
        )}
      </aside>

      {/* --- RIGHT MAIN CONTENT --- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Top Header */}
        <header className="h-10 bg-[#061020] border-b border-slate-800 flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-orange-500 rounded-full" />
            <span className="text-white text-xs font-bold tracking-widest uppercase">Government of India</span>
            <span className="text-slate-500 mx-2">|</span>
            <span className="text-slate-300 text-xs font-semibold tracking-wider">Ministry of Home Affairs</span>
          </div>
          <div className="text-slate-400 text-[10px] font-black tracking-widest uppercase">
            SIH 2024 INTERNAL DEMO
          </div>
        </header>
        
        {/* Tricolor Strip */}
        <div className="flex h-1 flex-shrink-0">
          <div className="flex-1" style={{ background: '#FF9933' }} />
          <div className="flex-1 bg-white" />
          <div className="flex-1" style={{ background: '#138808' }} />
        </div>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-slate-50 relative">
          <div className="max-w-[1400px] mx-auto w-full p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
