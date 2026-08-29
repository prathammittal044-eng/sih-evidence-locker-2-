'use client';
import Link from 'next/link';
import { Shield, LogOut, ArrowLeft, ClipboardList, User, BadgeCheck } from 'lucide-react';
import { useState, useEffect } from 'react';
import { getUser, logout, SIHUser } from '@/lib/auth';

const ROLE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  Officer:  { bg: 'bg-blue-700',    text: 'text-blue-100',   border: 'border-blue-500' },
  Reviewer: { bg: 'bg-emerald-700', text: 'text-emerald-100', border: 'border-emerald-500' },
  Judge:    { bg: 'bg-purple-800',  text: 'text-purple-100',  border: 'border-purple-500' },
};

export default function Navbar({ showBack = false }: { showBack?: boolean }) {
  const [user, setUser] = useState<SIHUser | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  const roleStyle = user ? (ROLE_STYLES[user.role] || ROLE_STYLES.Officer) : ROLE_STYLES.Officer;

  return (
    <header>
      {/* ── TOP SECURITY STRIP ── */}
      <div className="bg-red-700 text-white text-center py-1 text-xs font-bold tracking-widest uppercase">
        RESTRICTED — OFFICIAL USE ONLY — AUTHORISED PERSONNEL — GOVERNMENT OF INDIA
      </div>

      {/* ── GOVERNMENT IDENTITY HEADER ── */}
      <div style={{ background: '#1a3a6b' }} className="text-white">
        <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          {/* Left: Emblem + Title */}
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-white rounded-full flex items-center justify-center flex-shrink-0 shadow">
              <span className="text-xl">🔰</span>
            </div>
            <div>
              <p className="text-[10px] font-bold tracking-widest text-blue-300 uppercase leading-none">
                भारत सरकार · Government of India
              </p>
              <p className="text-sm font-black tracking-wide leading-snug">Ministry of Home Affairs</p>
              <p className="text-[10px] text-blue-300 leading-none hidden sm:block">
                Digital Evidence Management &amp; Secure Locker System
              </p>
            </div>
          </div>

          {/* Right: NIC badge */}
          <div className="hidden md:flex items-center gap-2 text-blue-300 text-xs">
            <Shield className="w-4 h-4" />
            <span className="font-bold tracking-wider">NIC · ISO 27001 Certified</span>
          </div>
        </div>
        {/* Tricolour strip */}
        <div className="flex h-1">
          <div className="flex-1" style={{ background: '#FF9933' }} />
          <div className="flex-1 bg-white" />
          <div className="flex-1" style={{ background: '#138808' }} />
        </div>
      </div>

      {/* ── MAIN NAV BAR ── */}
      <nav className="bg-[#0f2744] text-white shadow-lg border-b-2 border-blue-700">
        <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">

          {/* Left side */}
          <div className="flex items-center gap-3">
            {showBack ? (
              <Link href="/"
                className="flex items-center gap-1.5 bg-blue-900 hover:bg-blue-800 border border-blue-700 px-3 py-1.5 rounded text-xs font-bold tracking-wider transition-colors">
                <ArrowLeft className="w-3.5 h-3.5" /> DASHBOARD
              </Link>
            ) : (
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-400" />
                <span className="text-sm font-black tracking-widest text-slate-100 hidden sm:block">
                  EVIDENCE LOCKER
                </span>
              </div>
            )}
          </div>

          {/* Right side: audit + user info + logout */}
          <div className="flex items-center gap-3">
            <Link href="/audit"
              className="hidden md:flex items-center gap-1.5 bg-blue-900 hover:bg-blue-800 border border-blue-700 px-3 py-1.5 rounded text-xs font-bold tracking-wider transition-colors">
              <ClipboardList className="w-3.5 h-3.5" /> Audit Log
            </Link>

            {user && (
              <div className={`flex items-center gap-2 ${roleStyle.bg} border ${roleStyle.border} rounded-lg px-3 py-1.5`}>
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                  <User className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="hidden sm:block">
                  <p className={`text-xs font-black ${roleStyle.text} leading-none`}>{user.name}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <BadgeCheck className={`w-3 h-3 ${roleStyle.text} opacity-80`} />
                    <span className={`text-[10px] ${roleStyle.text} opacity-80 font-mono`}>
                      {user.role} · Badge {user.badge}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <button onClick={logout}
              title="Sign Out"
              className="flex items-center gap-1.5 bg-red-800 hover:bg-red-700 border border-red-600 px-3 py-1.5 rounded text-xs font-bold tracking-wider transition-colors">
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">SIGN OUT</span>
            </button>
          </div>
        </div>
      </nav>
    </header>
  );
}
