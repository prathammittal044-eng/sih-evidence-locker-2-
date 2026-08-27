'use client';
import Link from 'next/link';
import { ShieldCheck, UserCircle, ArrowLeft } from 'lucide-react';
import { useState, useEffect } from 'react';

const USERS = [
  { id: 1, name: 'Sub-Inspector Sharma', role: 'Officer', badge: '9482A' },
  { id: 2, name: 'Chief Inspector Verma', role: 'Reviewer', badge: '1109X' },
  { id: 3, name: 'Hon. Judge Patel', role: 'Judge', badge: 'JDG-01' },
];

export default function Navbar({ showBack = false, title = "SIH SECURE EVIDENCE LOCKER" }) {
  const [currentUser, setCurrentUser] = useState(USERS[0]);

  useEffect(() => {
    const savedId = localStorage.getItem('sih_user_id');
    if (savedId) {
      const user = USERS.find(u => u.id === parseInt(savedId)) || USERS[0];
      setCurrentUser(user);
    }
  }, []);

  const handleUserChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const user = USERS.find(u => u.id === parseInt(e.target.value)) || USERS[0];
    setCurrentUser(user);
    localStorage.setItem('sih_user_id', user.id.toString());
    // Dispatch event so other components know user changed
    window.dispatchEvent(new Event('userChange'));
  };

  return (
    <nav className="bg-[#0f172a] text-white p-4 shadow-lg flex justify-between items-center border-b-4 border-blue-600">
      <div className="flex items-center gap-3">
        {showBack ? (
          <Link href="/" className="flex items-center gap-1 text-slate-300 hover:text-white transition-colors bg-slate-800 px-3 py-1.5 rounded-md text-sm font-bold tracking-wide mr-2">
            <ArrowLeft className="w-4 h-4" /> DASHBOARD
          </Link>
        ) : (
          <ShieldCheck className="w-8 h-8 text-blue-400" />
        )}
        <h1 className="text-xl font-bold tracking-widest text-slate-100 hidden sm:block">{title}</h1>
      </div>
      
      <div className="flex gap-4 items-center">
        <Link href="/audit" className="hidden md:flex items-center gap-1 bg-blue-800 hover:bg-blue-700 border border-blue-600 px-3 py-1.5 rounded text-sm font-bold transition-colors mr-2">
          System Audit Log
        </Link>
        <div className="flex flex-col items-end">
          <select 
            value={currentUser.id} 
            onChange={handleUserChange}
            className="bg-slate-800 text-white text-sm font-bold p-1 rounded border border-slate-600 outline-none cursor-pointer"
          >
            {USERS.map(u => (
              <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
            ))}
          </select>
          <span className="text-xs text-blue-400 font-mono mt-1">Badge: {currentUser.badge}</span>
        </div>
        <UserCircle className="w-10 h-10 text-slate-300 hidden sm:block" />
      </div>
    </nav>
  );
}
