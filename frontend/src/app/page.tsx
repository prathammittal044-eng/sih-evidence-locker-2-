'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Search, Folder, ShieldCheck, FileText, Plus, MapPin, Calendar, Tag, Hash, AlignLeft, Lock } from 'lucide-react';
import Navbar from '@/components/Navbar';

const CRIME_TYPES = [
  'Theft / Robbery', 'Cyber Crime / Fraud', 'Murder / Attempt to Murder',
  'Assault / Battery', 'Kidnapping / Abduction', 'Drug Trafficking',
  'Sexual Offence', 'Domestic Violence', 'Corruption / Bribery',
  'Property Dispute', 'Arson', 'Forgery / Cheating', 'Other',
];

const IPC_SECTIONS = [
  '302 – Murder', '307 – Attempt to Murder', '376 – Rape',
  '420 – Cheating', '379 – Theft', '392 – Robbery',
  '354 – Assault on Woman', '498A – Cruelty by Husband',
  '406 – Criminal Breach of Trust', '120B – Criminal Conspiracy',
  '34 – Common Intention', 'IT Act 66C – Identity Theft',
  'IT Act 66D – Cheating by Personation', 'NDPS Act', 'Other',
];

export default function Dashboard() {
  const [cases, setCases]         = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedSections, setSelectedSections] = useState<string[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);

  const canCreateCase = currentUser?.role === 'Officer';

  useEffect(() => {
    // Auth guard
    const token = localStorage.getItem('sih_token');
    const userRaw = localStorage.getItem('sih_user');
    if (!token || !userRaw) { window.location.href = '/login'; return; }
    setCurrentUser(JSON.parse(userRaw));
    fetchCases();
  }, []);

  const getHeaders = () => {
    const token = localStorage.getItem('sih_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchCases = () => {
    const token = localStorage.getItem('sih_token');
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(res => res.json())
      .then(data => setCases(data))
      .catch(err => console.error('Error fetching cases', err));
  };

  const toggleSection = (s: string) => {
    setSelectedSections(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  };

  const handleCreateCase = async (e: any) => {
    e.preventDefault();
    const fd = new FormData(e.target);

    // Build an enriched title that encodes metadata
    const meta = {
      title:             fd.get('title') as string,
      crime_type:        fd.get('crime_type') as string,
      incident_date:     fd.get('incident_date') as string,
      location:          fd.get('location') as string,
      complainant_name:  fd.get('complainant_name') as string,
      complainant_phone: fd.get('complainant_phone') as string,
      accused_name:      fd.get('accused_name') as string,
      ipc_sections:      selectedSections,
      description:       fd.get('description') as string,
    };

    const payload = {
      case_number: fd.get('case_number') as string,
      title: meta.title,
    };

    // Store metadata as a separate call — we post a "metadata document" after creating the case
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/cases/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getHeaders() },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const created = await res.json();
        // Store extra metadata in localStorage (prototype approach — no extra DB table needed)
        const stored = JSON.parse(localStorage.getItem('case_metadata') || '{}');
        stored[created.id] = meta;
        localStorage.setItem('case_metadata', JSON.stringify(stored));

        setShowModal(false);
        setSelectedSections([]);
        fetchCases();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail}`);
      }
    } catch { alert('Network error.'); }
  };

  const getCaseMeta = (id: number) => {
    const stored = JSON.parse(localStorage.getItem('case_metadata') || '{}');
    return stored[id] || null;
  };

  const [fileSearchMatches, setFileSearchMatches] = useState<number[]>([]);

  useEffect(() => {
    if (!searchQuery || searchQuery.length < 3) {
      setFileSearchMatches([]);
      return;
    }
    const delayDebounce = setTimeout(() => {
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/search/?q=${encodeURIComponent(searchQuery)}`)
        .then(res => res.json())
        .then(data => setFileSearchMatches(data || []))
        .catch(err => console.error("Search error", err));
    }, 300); // 300ms debounce
    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  const STOP_WORDS = new Set(["i","me","my","we","our","you","your","he","him","his","she","her","it","its","they","them","their","what","which","who","whom","this","that","these","those","am","is","are","was","were","be","been","being","have","has","had","do","does","did","a","an","the","and","but","if","or","because","as","until","while","of","at","by","for","with","about","against","between","into","through","during","before","after","above","below","to","from","up","down","in","out","on","off","over","under","again","further","then","once","here","there","when","where","why","how","all","any","both","each","few","more","most","other","some","such","no","nor","not","only","own","same","so","than","too","very","can","will","just","don","should","now","find","case","cases","around","people","months","years","days","show","looking","search"]);

  // Deep search logic across all case data and metadata
  const sortedCases = [...cases].map((c: any) => {
    let score = 0;
    
    // 1. If there's no search query, everything has score 0 (will show all)
    if (!searchQuery) return { ...c, score: 1 };
    
    const queryWords = searchQuery.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/)
      .filter(w => !STOP_WORDS.has(w) && w.length > 2);
      
    if (queryWords.length === 0) return { ...c, score: 1 };

    const meta = getCaseMeta(c.id) || {};
    const searchableText = `
      ${c.case_number} ${c.title} ${c.status}
      ${meta.crime_type || ''} ${meta.location || ''} 
      ${meta.complainant_name || ''} ${meta.accused_name || ''}
      ${(meta.ipc_sections || []).join(' ')} 
      ${meta.description || ''}
    `.toLowerCase();

    // Score based on local metadata
    queryWords.forEach(kw => {
      if (searchableText.includes(kw)) score += 1;
    });

    // Score based on backend file contents (the earlier in the array, the higher the score)
    const backendRankIndex = fileSearchMatches.indexOf(c.id);
    if (backendRankIndex !== -1) {
       // Add points inversely proportional to its rank in backend results
       score += (fileSearchMatches.length - backendRankIndex) * 2;
    }

    return { ...c, score };
  })
  .filter(c => c.score > 0)
  .sort((a, b) => b.score - a.score);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <Navbar />

      <main className="p-6 max-w-[1400px] mx-auto w-full">
        <div className="flex flex-col lg:flex-row gap-6">
          
          {/* ===================== SIDEBAR ===================== */}
          <div className="w-full lg:w-72 flex-shrink-0 space-y-6">
            
            {/* Action Panel */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-100 pb-2">Quick Actions</h3>
              {canCreateCase ? (
                <button onClick={() => setShowModal(true)}
                  className="w-full bg-[#1a3a6b] hover:bg-[#132a4f] text-white py-3 rounded-lg font-bold shadow-md transition-colors flex items-center justify-center gap-2">
                  <Plus className="w-5 h-5" /> Register New Case
                </button>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center text-sm text-slate-500 font-medium">
                  <ShieldCheck className="w-6 h-6 mx-auto mb-2 text-slate-400" />
                  Your role ({currentUser?.role}) does not have permission to register new cases.
                </div>
              )}
            </div>

            {/* System Overview */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-100 pb-2">System Overview</h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-slate-500 font-semibold mb-1">Total Registered Cases</p>
                  <p className="text-3xl font-black text-[#1a3a6b]">{cases.length}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-green-50 border border-green-200 p-3 rounded-lg">
                    <p className="text-xs text-green-700 font-bold uppercase">Active</p>
                    <p className="text-xl font-black text-green-800">{cases.filter((c: any) => !c.is_sealed).length}</p>
                  </div>
                  <div className="bg-red-50 border border-red-200 p-3 rounded-lg">
                    <p className="text-xs text-red-700 font-bold uppercase">Sealed</p>
                    <p className="text-xl font-black text-red-800">{cases.filter((c: any) => c.is_sealed).length}</p>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* ===================== MAIN DOSSIER AREA ===================== */}
          <div className="flex-1 min-w-0 flex flex-col gap-5">
            
            {/* Search Bar */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-2">
              <div className="relative w-full">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-blue-600" />
                </div>
                <input type="text" placeholder="Natural AI Search: Try 'Cyber fraud in Delhi' or 'FIR-2026-104'..."
                  value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  className="block w-full pl-12 pr-4 py-3.5 bg-slate-50 border-0 rounded-lg text-slate-800 font-medium placeholder-slate-400 focus:ring-2 focus:ring-blue-600 sm:text-sm transition-all" />
              </div>
            </div>

            {/* Case List */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
                <h2 className="text-lg font-black text-[#1a3a6b] tracking-wide">CASE DOSSIERS</h2>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{sortedCases.length} Results</span>
              </div>
              
              <div className="divide-y divide-slate-100">
                {sortedCases.length === 0 ? (
                  <div className="py-16 text-center">
                    <Folder className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500 font-medium">No cases found matching your criteria.</p>
                  </div>
                ) : (
                  sortedCases.map((c: any) => {
                    const meta = getCaseMeta(c.id);
                    return (
                      <Link href={`/case/${c.id}`} key={c.id} className="block hover:bg-blue-50 transition-colors group">
                        <div className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          
                          <div className="flex items-start gap-4 flex-1 min-w-0">
                            {/* Case Number Badge */}
                            <div className={`w-28 flex-shrink-0 text-center py-1.5 rounded border font-mono text-xs font-bold ${c.is_sealed ? 'bg-red-50 text-red-700 border-red-200' : 'bg-slate-100 text-[#1a3a6b] border-slate-300'}`}>
                              {c.case_number}
                            </div>
                            
                            {/* Main Info */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="text-base font-black text-slate-800 group-hover:text-blue-700 truncate">{c.title}</h3>
                                {c.is_sealed && <span className="bg-red-100 text-red-700 text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider flex items-center gap-1"><Lock className="w-3 h-3"/> Sealed</span>}
                              </div>
                              {meta && (
                                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 font-medium">
                                  {meta.crime_type && <span className="flex items-center gap-1"><Tag className="w-3 h-3 text-slate-400" /> {meta.crime_type}</span>}
                                  {meta.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3 text-slate-400" /> {meta.location}</span>}
                                  {meta.incident_date && <span className="flex items-center gap-1"><Calendar className="w-3 h-3 text-slate-400" /> {meta.incident_date}</span>}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Right Stats & Action */}
                          <div className="flex items-center gap-6 sm:pl-4 sm:border-l border-slate-200">
                            <div className="text-center min-w-[70px]">
                              <p className="text-xl font-black text-slate-700 leading-none">{c.documents?.length || 0}</p>
                              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Docs</p>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-white border-2 border-slate-200 group-hover:border-blue-500 group-hover:bg-blue-600 flex items-center justify-center transition-all flex-shrink-0">
                              <span className="text-slate-400 group-hover:text-white font-bold leading-none translate-x-px">→</span>
                            </div>
                          </div>

                        </div>
                      </Link>
                    );
                  })
                )}
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* ===================== CREATE CASE MODAL ===================== */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900 bg-opacity-60 flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl my-4">

            {/* Modal Header */}
            <div className="bg-slate-900 text-white px-6 py-5 rounded-t-2xl">
              <h3 className="text-xl font-black tracking-wide flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" /> REGISTER NEW CASE
              </h3>
              <p className="text-slate-400 text-sm mt-1">Fill in all mandatory fields to officially register this case in the system.</p>
            </div>

            <form onSubmit={handleCreateCase} className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">

              {/* Section 1: Case Identification */}
              <div>
                <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Hash className="w-3.5 h-3.5" /> Case Identification
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">
                      Case / FIR Number <span className="text-red-500">*</span>
                    </label>
                    <input required name="case_number" type="text"
                      placeholder="e.g., FIR-2026-105"
                      className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm font-mono" />
                    <p className="text-xs text-slate-400 mt-1">Format: FIR-YYYY-NNN</p>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">
                      Case Title <span className="text-red-500">*</span>
                    </label>
                    <input required name="title" type="text"
                      placeholder="e.g., Cyber Fraud at Sector 14"
                      className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm" />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">
                      Type of Crime <span className="text-red-500">*</span>
                    </label>
                    <select required name="crime_type"
                      className="w-full border border-slate-300 rounded-lg p-2.5 bg-white focus:ring-1 focus:ring-blue-500 outline-none text-sm cursor-pointer">
                      <option value="">-- Select Type --</option>
                      {CRIME_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">
                      Date of Incident <span className="text-red-500">*</span>
                    </label>
                    <input required name="incident_date" type="date"
                      className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm" />
                  </div>
                </div>
              </div>

              {/* Section 2: Location */}
              <div>
                <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5" /> Incident Location
                </h4>
                <input required name="location" type="text"
                  placeholder="e.g., Plot No. 42, MG Road, Sector 14, New Delhi — 110001"
                  className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm" />
              </div>

              {/* Section 3: Parties Involved */}
              <div>
                <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5" /> Parties Involved
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">Complainant / Victim Name <span className="text-red-500">*</span></label>
                    <input required name="complainant_name" type="text"
                      placeholder="Full name of complainant"
                      className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm" />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">Complainant Phone</label>
                    <input name="complainant_phone" type="tel"
                      placeholder="+91 XXXXX XXXXX"
                      className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm" />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">Accused / Suspect Name(s)</label>
                    <input name="accused_name" type="text"
                      placeholder="Full name(s) of accused — leave blank if unknown"
                      className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm" />
                  </div>
                </div>
              </div>

              {/* Section 4: IPC Sections */}
              <div>
                <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Hash className="w-3.5 h-3.5" /> Applicable IPC / Legal Sections
                </h4>
                <div className="flex flex-wrap gap-2">
                  {IPC_SECTIONS.map(s => (
                    <button key={s} type="button" onClick={() => toggleSection(s)}
                      className={`text-xs px-3 py-1.5 rounded-full border font-bold transition-all ${selectedSections.includes(s)
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400'}`}>
                      {s}
                    </button>
                  ))}
                </div>
                {selectedSections.length > 0 && (
                  <p className="text-xs text-blue-600 mt-2 font-medium">
                    Selected: {selectedSections.join(' | ')}
                  </p>
                )}
              </div>

              {/* Section 5: Brief Description */}
              <div>
                <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <AlignLeft className="w-3.5 h-3.5" /> Brief Description of Incident
                </h4>
                <textarea name="description" rows={3}
                  placeholder="Briefly describe the incident, how it was reported, and initial findings..."
                  className="w-full border border-slate-300 rounded-lg p-2.5 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm resize-none" />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-2 border-t border-slate-100 sticky bottom-0 bg-white pb-1">
                <button type="button" onClick={() => { setShowModal(false); setSelectedSections([]); }}
                  className="flex-1 bg-slate-100 text-slate-700 font-bold py-3 rounded-lg hover:bg-slate-200 transition-colors">
                  Cancel
                </button>
                <button type="submit"
                  className="flex-1 bg-blue-600 text-white font-bold py-3 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2">
                  <ShieldCheck className="w-4 h-4" /> Register & Seal Case
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
