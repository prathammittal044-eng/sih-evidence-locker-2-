'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ShieldCheck, UploadCloud, FileText, History, CheckCircle, RefreshCw,
  FileLock2, Download, CheckCircle2, Lock, AlertTriangle, FileDown, Shield
} from 'lucide-react';
import Navbar from '@/components/Navbar';

const USERS: Record<number, { name: string; role: string; badge: string }> = {
  1: { name: 'Sub-Inspector Sharma', role: 'Officer',  badge: '9482A' },
  2: { name: 'Chief Inspector Verma', role: 'Reviewer', badge: '1109X' },
  3: { name: 'Hon. Judge Patel',      role: 'Judge',    badge: 'JDG-01' },
};

export default function CaseDetails() {
  const { id } = useParams();
  const [caseData, setCaseData]       = useState<any>(null);
  const [loading, setLoading]         = useState(true);
  const [currentUserId, setCurrentUserId] = useState(1);
  const [sealing, setSealing]         = useState(false);
  const [docType, setDocType]         = useState('FIR');

  const currentUser = USERS[currentUserId] || USERS[1];
  const canUpload   = currentUser.role === 'Officer';
  const canSeal     = currentUser.role === 'Judge';

  const fetchCase = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/${id}`);
      setCaseData(await res.json());
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchCase();
    const stored = localStorage.getItem('sih_user_id');
    if (stored) setCurrentUserId(parseInt(stored));
    const handler = () => {
      const newId = localStorage.getItem('sih_user_id');
      if (newId) setCurrentUserId(parseInt(newId));
    };
    window.addEventListener('userChange', handler);
    return () => window.removeEventListener('userChange', handler);
  }, [id]);

  const handleUpload = async (e: any) => {
    e.preventDefault();
    if (!canUpload) return;
    const formData = new FormData(e.target);
    formData.append('user_id', currentUserId.toString());
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/${id}/documents/`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) { alert('Document securely uploaded and sealed!'); fetchCase(); e.target.reset(); }
      else        { alert(`Error: ${data.detail}`); }
    } catch { alert('Network error — is the backend running?'); }
  };

  const handleVerify = async (document_id: number) => {
    try {
      const res  = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/documents/${document_id}/verify/`);
      const data = await res.json();
      let msg = 'CRYPTOGRAPHIC INTEGRITY CHECK\n' + '─'.repeat(40) + '\n\n';
      data.integrity_checks.forEach((c: any) => {
        const icon = c.status === 'VERIFIED' ? '✅' : c.status === 'TAMPERED' ? '🚨' : c.status === 'MISSING' ? '❌' : '⚠️';
        msg += `${icon}  Version ${c.version}: [${c.status}]\n    ${c.message}\n\n`;
      });
      alert(msg);
    } catch { alert('Error contacting server.'); }
  };

  const handleSeal = async () => {
    if (!canSeal) return;
    const confirmed = confirm(
      `⚠️ WARNING: This action is PERMANENT and IRREVERSIBLE.\n\n` +
      `Sealing Case "${caseData?.title}" will:\n` +
      `• Prevent ALL future document uploads\n` +
      `• Prevent ALL new document versions\n` +
      `• Record your identity in the permanent audit log\n\n` +
      `Are you absolutely sure you want to seal this case for trial?`
    );
    if (!confirmed) return;
    setSealing(true);
    try {
      const formData = new FormData();
      formData.append('user_id', currentUserId.toString());
      const res  = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/${id}/seal/`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) { alert(`✅ ${data.message}`); fetchCase(); }
      else        { alert(`Error: ${data.detail}`); }
    } catch { alert('Network error.'); }
    finally { setSealing(false); }
  };

  const handleDownloadReport = () => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/${id}/report/`, '_blank');
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
    </div>
  );
  if (!caseData) return <div className="p-8 text-center text-red-500 font-bold">Case not found</div>;

  const isSealed     = caseData.is_sealed;
  const sealerInfo   = isSealed && caseData.sealed_by ? USERS[caseData.sealed_by] : null;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <Navbar showBack={true} title={`CASE: ${caseData.case_number}`} />

      <main className="p-6 max-w-7xl mx-auto">

        {/* SEALED BANNER */}
        {isSealed && (
          <div className="mb-6 bg-red-600 text-white rounded-xl p-4 flex items-center gap-4 shadow-lg border border-red-700">
            <Lock className="w-8 h-8 flex-shrink-0" />
            <div>
              <p className="font-black text-lg tracking-wide uppercase">⚖️ This Case Is Sealed for Trial</p>
              <p className="text-red-100 text-sm mt-0.5">
                Sealed by <strong>{sealerInfo?.name || 'a Judge'}</strong>
                {caseData.sealed_at ? ` on ${new Date(caseData.sealed_at).toLocaleString()}` : ''}.
                No further documents or versions can be added.
              </p>
            </div>
          </div>
        )}

        {/* ROLE RESTRICTION BANNER */}
        {!isSealed && !canUpload && (
          <div className="mb-6 bg-amber-50 border-2 border-amber-300 text-amber-800 rounded-xl p-4 flex items-center gap-4">
            <AlertTriangle className="w-7 h-7 flex-shrink-0 text-amber-500" />
            <div>
              <p className="font-bold">Read-Only Access — Role: {currentUser.role}</p>
              <p className="text-sm mt-0.5">
                {currentUser.role === 'Judge'
                  ? 'As a Judge, you have read-only access. You may verify integrity and seal cases. Only Officers can upload documents.'
                  : 'As a Reviewer, you have read-only access. Only Officers can upload or update documents.'}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* LEFT COLUMN */}
          <div className="lg:col-span-4 space-y-5">

            {/* Case Info */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-blue-600"></div>
              <h2 className="text-2xl font-bold mb-1 text-slate-800">{caseData.title}</h2>
              <p className="text-slate-500 mb-5 font-mono text-sm border-b border-slate-100 pb-4">{caseData.case_number}</p>
              <div className="flex flex-col gap-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-500">Status</span>
                  <span className={`text-xs font-bold px-3 py-1 rounded-md border flex items-center gap-1 ${isSealed ? 'bg-red-50 text-red-700 border-red-200' : 'bg-green-50 text-green-700 border-green-200'}`}>
                    {isSealed ? <Lock className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                    {caseData.status}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-500">Created On</span>
                  <span className="text-sm font-bold text-slate-800">{new Date(caseData.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-500">Your Access</span>
                  <span className={`text-xs font-bold px-2 py-1 rounded border ${canUpload ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                    {currentUser.role}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-5 pt-4 border-t border-slate-100 flex flex-col gap-2">
                <button onClick={handleDownloadReport}
                  className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm font-bold transition-all">
                  <FileDown className="w-4 h-4" /> Download Custody Report
                </button>
                {canSeal && !isSealed && (
                  <button onClick={handleSeal} disabled={sealing}
                    className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2.5 rounded-lg text-sm font-bold transition-all disabled:opacity-60">
                    <Lock className="w-4 h-4" /> {sealing ? 'Sealing...' : 'Seal Case for Trial'}
                  </button>
                )}
              </div>
            </div>

            {/* Upload Form */}
            {canUpload && !isSealed && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200">
                <div className="flex items-center gap-2 px-5 pt-5 pb-4 border-b border-slate-100">
                  <UploadCloud className="w-5 h-5 text-blue-600" />
                  <h3 className="text-base font-bold text-slate-800">Add New Document</h3>
                </div>
                <form onSubmit={handleUpload} className="p-5 space-y-4">

                  {/* Document Type selector — drives the fields below */}
                  <div>
                    <label className="block text-xs font-black text-slate-500 uppercase tracking-wider mb-1.5">Document Type <span className="text-red-500">*</span></label>
                    <select name="doc_type" value={docType} onChange={e => setDocType(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-blue-500 outline-none text-sm cursor-pointer font-bold">
                      <option value="FIR">FIR (First Information Report)</option>
                      <option value="Evidence">Physical Evidence</option>
                      <option value="Forensic">Forensic Report</option>
                      <option value="Statement">Witness / Accused Statement</option>
                      <option value="Court">Court Filing / Order</option>
                      <option value="Medical">Medical / Post-Mortem Report</option>
                    </select>
                  </div>

                  {/* FIR-specific fields */}
                  {docType === 'FIR' && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
                      <p className="text-xs font-black text-blue-700 uppercase tracking-wider">FIR Details</p>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1">FIR Title / Subject <span className="text-red-500">*</span></label>
                        <input required name="name" type="text" placeholder="e.g., FIR against theft at MG Road"
                          className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-bold text-slate-600 mb-1">Date of Filing</label>
                          <input name="fir_date" type="date" className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-slate-600 mb-1">Filing Officer</label>
                          <input name="fir_officer" type="text" defaultValue={currentUser.name} readOnly
                            className="w-full border border-slate-200 rounded-lg p-2 text-sm bg-slate-100 text-slate-600 cursor-not-allowed" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Evidence-specific fields */}
                  {docType === 'Evidence' && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-3">
                      <p className="text-xs font-black text-amber-700 uppercase tracking-wider">Evidence Details</p>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1">Evidence Label <span className="text-red-500">*</span></label>
                        <input required name="name" type="text" placeholder="e.g., Exhibit A — Mobile Phone seized from accused"
                          className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-bold text-slate-600 mb-1">Evidence Type</label>
                          <select name="evidence_type" className="w-full border border-slate-300 rounded-lg p-2 text-sm bg-white outline-none focus:ring-1 focus:ring-amber-400">
                            <option>Physical Object</option><option>Photograph</option>
                            <option>CCTV Footage</option><option>Digital Record</option><option>Document</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-slate-600 mb-1">Collection Date</label>
                          <input name="collection_date" type="date" className="w-full border border-slate-300 rounded-lg p-2 text-sm bg-white outline-none focus:ring-1 focus:ring-amber-400" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Forensic-specific fields */}
                  {docType === 'Forensic' && (
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 space-y-3">
                      <p className="text-xs font-black text-purple-700 uppercase tracking-wider">Forensic Report Details</p>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1">Report Title <span className="text-red-500">*</span></label>
                        <input required name="name" type="text" placeholder="e.g., DNA Analysis Report — Victim Sample"
                          className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1">Forensic Lab / Authority</label>
                        <input name="forensic_lab" type="text" placeholder="e.g., State Forensic Science Laboratory, Delhi"
                          className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                      </div>
                    </div>
                  )}

                  {/* Statement-specific fields */}
                  {docType === 'Statement' && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
                      <p className="text-xs font-black text-green-700 uppercase tracking-wider">Statement Details</p>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1">Statement Description <span className="text-red-500">*</span></label>
                        <input required name="name" type="text" placeholder="e.g., Statement of Witness Ramesh Kumar (u/s 161 CrPC)"
                          className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-bold text-slate-600 mb-1">Person's Role</label>
                          <select name="person_role" className="w-full border border-slate-300 rounded-lg p-2 text-sm bg-white outline-none focus:ring-1 focus:ring-green-400">
                            <option>Witness</option><option>Accused</option><option>Victim</option><option>Expert</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-slate-600 mb-1">Statement Date</label>
                          <input name="statement_date" type="date" className="w-full border border-slate-300 rounded-lg p-2 text-sm bg-white outline-none focus:ring-1 focus:ring-green-400" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Generic title for Court / Medical */}
                  {(docType === 'Court' || docType === 'Medical') && (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                      <label className="block text-xs font-bold text-slate-600 mb-1">Document Title <span className="text-red-500">*</span></label>
                      <input required name="name" type="text"
                        placeholder={docType === 'Court' ? 'e.g., Bail Application Order — Sessions Court' : 'e.g., Post-Mortem Report — Dr. A. Verma'}
                        className="w-full border border-slate-300 rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-blue-500 bg-white" />
                    </div>
                  )}

                  {/* File upload — always shown */}
                  <div>
                    <label className="block text-xs font-black text-slate-500 uppercase tracking-wider mb-1.5">Attach File <span className="text-red-500">*</span></label>
                    <input required name="file" type="file"
                      className="w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer border border-slate-200 rounded-lg bg-slate-50 p-1" />
                    <p className="text-xs text-slate-400 mt-1">SHA-256 hash will be computed and locked on upload.</p>
                  </div>

                  <button type="submit" className="w-full bg-slate-900 hover:bg-slate-800 text-white py-3 rounded-lg font-bold tracking-wide flex justify-center items-center gap-2">
                    <FileLock2 className="w-4 h-4" /> Upload & Cryptographically Seal
                  </button>
                </form>
              </div>
            )}

            {/* Locked upload notice */}
            {(!canUpload || isSealed) && (
              <div className="bg-white p-6 rounded-xl border-2 border-dashed border-slate-200 text-center">
                <Lock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-slate-500 font-bold text-sm">Upload Restricted</p>
                <p className="text-slate-400 text-xs mt-1">
                  {isSealed ? 'This case is sealed. No uploads allowed.' : `Role "${currentUser.role}" cannot upload documents.`}
                </p>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Document Chain of Custody */}
          <div className="lg:col-span-8">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200">
              <div className="p-5 border-b border-slate-200 bg-slate-50 rounded-t-xl flex justify-between items-center">
                <div>
                  <h3 className="text-xl font-bold flex items-center gap-2 text-slate-800">
                    <History className="w-5 h-5 text-blue-600" /> Document Chain of Custody
                  </h3>
                  <p className="text-sm text-slate-500 mt-1">Git-inspired immutable version control. <strong>No Hard Deletes.</strong></p>
                </div>
                <div className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-xs font-bold border border-blue-200">
                  {caseData.documents?.length || 0} Records
                </div>
              </div>

              <div className="p-6">
                {(!caseData.documents || caseData.documents.length === 0) ? (
                  <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50">
                    <FileLock2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500 font-medium">No documents secured yet.</p>
                    {canUpload && !isSealed && <p className="text-slate-400 text-sm mt-1">Use the form on the left to upload the first document.</p>}
                  </div>
                ) : (
                  <div className="space-y-10">
                    {Object.entries(
                      caseData.documents.reduce((acc: any, doc: any) => {
                        if (!acc[doc.doc_type]) acc[doc.doc_type] = [];
                        acc[doc.doc_type].push(doc);
                        return acc;
                      }, {})
                    ).map(([docType, docs]: [string, any]) => (
                      <div key={docType}>
                        <h4 className="text-sm font-black text-slate-600 uppercase tracking-widest border-b-2 border-slate-200 pb-2 mb-5 flex items-center gap-2">
                          <FileText className="w-4 h-4 text-blue-500" /> {docType} FILES
                        </h4>
                        <div className="space-y-5">
                          {docs.map((doc: any) => (
                            <div key={doc.id} className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                              {/* Document Header */}
                              <div className="bg-white p-4 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex items-center gap-3">
                                  <div className="bg-blue-50 p-2 rounded-lg border border-blue-100">
                                    <FileText className="w-5 h-5 text-blue-600" />
                                  </div>
                                  <div>
                                    <h4 className="font-bold text-slate-800">{doc.name}</h4>
                                    <span className="text-xs text-slate-400 font-mono">ID: #{doc.id}</span>
                                  </div>
                                </div>
                                <div className="flex gap-2 flex-wrap">
                                  <button onClick={() => handleVerify(doc.id)}
                                    className="flex items-center gap-1 bg-white border-2 border-green-200 text-green-700 hover:bg-green-50 px-3 py-1.5 rounded-lg text-xs font-bold transition-all">
                                    <CheckCircle2 className="w-3.5 h-3.5" /> Verify Integrity
                                  </button>
                                  {canUpload && !isSealed && (
                                    <Link href={`/document/${doc.id}`}>
                                      <button className="flex items-center gap-1 bg-white border-2 border-slate-200 hover:border-blue-400 hover:text-blue-600 px-3 py-1.5 rounded-lg text-xs font-bold transition-all">
                                        <RefreshCw className="w-3.5 h-3.5" /> Update Version
                                      </button>
                                    </Link>
                                  )}
                                </div>
                              </div>

                              {/* Version Timeline */}
                              <div className="p-5 bg-slate-50">
                                <div className="relative border-l-2 border-blue-200 ml-3 space-y-5">
                                  {doc.versions.sort((a: any, b: any) => b.version_number - a.version_number).map((v: any) => {
                                    const uInfo = USERS[v.uploaded_by] || { name: 'Unknown', role: '—', badge: '—' };
                                    return (
                                      <div key={v.id} className="relative pl-7">
                                        <div className={`absolute -left-2 top-1.5 w-4 h-4 rounded-full border-2 border-white shadow ${v.status === 'Active' ? 'bg-green-500' : 'bg-slate-400'}`} />
                                        <div className={`bg-white p-4 rounded-lg border shadow-sm ${v.status === 'Active' ? 'border-green-200 ring-1 ring-green-50' : 'border-slate-200 opacity-75'}`}>
                                          {/* Version header */}
                                          <div className="flex flex-wrap gap-2 justify-between items-start mb-3">
                                            <div className="flex items-center gap-2">
                                              <span className={`font-black text-base ${v.status === 'Active' ? 'text-green-700' : 'text-slate-500'}`}>
                                                v{v.version_number}.0
                                              </span>
                                              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${v.status === 'Active' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                                                {v.status}
                                              </span>
                                            </div>
                                            <div className="flex flex-col items-end gap-1.5">
                                              <span className="text-xs text-slate-400">{new Date(v.created_at).toLocaleString()}</span>
                                              <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/files/${v.file_path}?user_id=${currentUserId}&document_id=${doc.id}`}
                                                target="_blank" rel="noreferrer"
                                                className="flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-800 bg-blue-50 px-2 py-1 rounded border border-blue-100 hover:bg-blue-100 transition-colors">
                                                <Download className="w-3 h-3" /> VIEW FILE
                                              </a>
                                            </div>
                                          </div>
                                          {/* Uploader info */}
                                          <div className="flex items-center gap-2 mb-3 bg-slate-50 px-3 py-2 rounded-lg border border-slate-100 w-fit">
                                            <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-black text-white">
                                              {uInfo.name.charAt(0)}
                                            </div>
                                            <span className="text-sm font-semibold text-slate-800">{uInfo.name}</span>
                                            <span className="text-xs text-slate-400 border-l border-slate-300 pl-2">{uInfo.role}</span>
                                            <span className="text-xs font-mono text-blue-600 border-l border-slate-300 pl-2">Badge: {uInfo.badge}</span>
                                          </div>
                                          {/* Hash */}
                                          <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
                                            <div className="flex items-center gap-1.5 mb-1">
                                              <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
                                              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">SHA-256 Integrity Hash</span>
                                            </div>
                                            <p className="text-xs font-mono text-slate-700 break-all bg-white p-2 rounded border border-slate-100">{v.file_hash}</p>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
