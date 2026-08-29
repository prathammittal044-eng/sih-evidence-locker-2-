'use client';
import { useParams, useRouter } from 'next/navigation';
import { FileLock2, AlertTriangle, X } from 'lucide-react';

import { useState, useEffect } from 'react';

export default function DocumentUpdate() {
  const { id } = useParams();
  const router = useRouter();
  const [currentUserId, setCurrentUserId] = useState(1);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const storedId = localStorage.getItem('sih_user_id');
    if (storedId) setCurrentUserId(parseInt(storedId));
  }, []);

  const handleUpdate = async (e: any) => {
    e.preventDefault();
    if (isUploading) return;
    setIsUploading(true);
    const formData = new FormData(e.target);
    formData.append('user_id', currentUserId.toString());

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/documents/${id}/versions/`, {
        method: 'POST',
        body: formData,
      });
      if(res.ok) {
        alert('Document version created securely!');
        router.back();
      } else {
        const err = await res.json().catch(() => null);
        const msg = err?.detail || `Server error: ${res.status}`;
        alert(`Failed to update document.\n\n${msg}`);
      }
    } catch (err) {
      alert('Error updating document');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-900 flex items-center justify-center p-4 font-sans backdrop-blur-sm bg-opacity-95">
      <div className="bg-white p-8 rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full relative">
        <div className="absolute top-0 left-0 w-full h-2 bg-blue-600 rounded-t-2xl"></div>
        
        <div className="flex justify-between items-start mb-6 pt-2">
          <div>
            <h2 className="text-2xl font-black text-slate-800 flex items-center gap-2">
              <FileLock2 className="w-6 h-6 text-blue-600" /> Update Document
            </h2>
            <p className="text-sm text-slate-500 mt-1">Create a new version for Document #{id}</p>
          </div>
          <button onClick={() => router.back()} className="text-slate-400 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 p-2 rounded-full transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-xl mb-8 flex gap-3 shadow-sm">
          <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <strong className="block mb-1 text-yellow-900">No Hard Delete Policy Enforced</strong>
            Updating this document will securely generate a new version. The previous version will be marked as <span className="bg-yellow-200 px-1 rounded font-mono text-xs">Superseded</span> but will remain in the case history forever to preserve the chain of custody.
          </div>
        </div>

        <form onSubmit={handleUpdate} className="space-y-6">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">Select New File Version</label>
            <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 bg-slate-50 hover:bg-blue-50 hover:border-blue-300 transition-colors text-center cursor-pointer">
              <input required name="file" type="file" className="w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-bold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer" />
            </div>
          </div>
          
          <button disabled={isUploading} type="submit" className={`w-full ${isUploading ? 'bg-slate-500' : 'bg-[#0f172a] hover:bg-slate-800'} text-white py-3.5 rounded-xl font-bold tracking-wide shadow-md hover:shadow-lg transition-all flex justify-center items-center gap-2`}>
            {isUploading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                Uploading & AI Scanning...
              </>
            ) : (
              <>
                <FileLock2 className="w-5 h-5" /> Generate Version & Seal
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
