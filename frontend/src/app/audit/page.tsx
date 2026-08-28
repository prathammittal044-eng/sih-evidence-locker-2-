'use client';
import { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import { ShieldAlert, Activity, FileText, Upload, RefreshCw, Eye } from 'lucide-react';

const USERS: Record<number, { name: string; role: string; badge: string }> = {
  1: { name: 'Sub-Inspector Sharma', role: 'Officer',  badge: '9482A' },
  2: { name: 'Chief Inspector Verma', role: 'Reviewer', badge: '1109X' },
  3: { name: 'Hon. Judge Patel',      role: 'Judge',    badge: 'JDG-01' },
};

export default function AuditLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/audit-logs/`)
      .then(res => res.json())
      .then(data => setLogs(data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const getIconForAction = (action: string) => {
    switch (action) {
      case 'UPLOAD_DOCUMENT': return <Upload className="w-5 h-5 text-green-500" />;
      case 'CREATE_VERSION': return <RefreshCw className="w-5 h-5 text-blue-500" />;
      case 'VIEW_FILE': return <Eye className="w-5 h-5 text-purple-500" />;
      case 'SEAL_CASE': return <ShieldAlert className="w-5 h-5 text-red-500" />;
      default: return <Activity className="w-5 h-5 text-slate-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <Navbar showBack={true} title="SYSTEM AUDIT LOG" />

      <main className="p-8 max-w-6xl mx-auto">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
            <ShieldAlert className="w-8 h-8 text-blue-600" /> Immutable Audit Trail
          </h2>
          <p className="text-slate-500 mt-2">Cryptographically verifiable log of all system actions. Every view, upload, and update is tracked permanently.</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
              <tr>
                <th className="p-4 w-48">Timestamp</th>
                <th className="p-4 w-64">Officer / Official</th>
                <th className="p-4 w-48">Action</th>
                <th className="p-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={4} className="p-8 text-center text-slate-500">Loading audit records...</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={4} className="p-8 text-center text-slate-500">No actions recorded yet.</td></tr>
              ) : (
                logs.map((log: any) => {
                  const u = USERS[log.user_id] || { name: 'Unknown User', role: '—', badge: '—' };
                  return (
                    <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                      <td className="p-4 font-mono text-slate-500 whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                            {u.name.charAt(0)}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-800">{u.name}</span>
                            <span className="text-xs text-slate-500">{u.role} (Badge: {u.badge})</span>
                          </div>
                        </div>
                      </td>
                    <td className="p-4 flex items-center gap-2 font-bold text-slate-700">
                      {getIconForAction(log.action)}
                      {log.action.replace('_', ' ')}
                    </td>
                    <td className="p-4 text-slate-600">
                      {log.details}
                    </td>
                  </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
