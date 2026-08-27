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
  const [currentUserId, setCurrentUserId] = useState(1);

  const USERS: Record<number, { role: string }> = {
    1: { role: 'Officer' },
    2: { role: 'Reviewer' },
    3: { role: 'Judge' },
  };
  const canCreateCase = USERS[currentUserId]?.role === 'Officer';

  useEffect(() => {
    fetchCases();
    const stored = localStorage.getItem('sih_user_id');
    if (stored) setCurrentUserId(parseInt(stored));
    const handler = () => {
      const newId = localStorage.getItem('sih_user_id');
      if (newId) setCurrentUserId(parseInt(newId));
    };
    window.addEventListener('userChange', handler);
    return () => window.removeEventListener('userChange', handler);
  }, []);

  const fetchCases = () => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || '${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}'}/cases/`)
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
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || '${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}'}/cases/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

      <main className="p-8 max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Active Cases</h2>
            <p className="text-slate-500 mt-1">Manage and securely upload evidence to your assigned cases.</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
            <div className="relative w-full sm:w-[500px]">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400" />
              </div>
              <input type="text" placeholder="Natural AI Search: Describe what you're looking for..."
                value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg bg-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm shadow-sm" />
            </div>
            {canCreateCase && (
              <button onClick={() => setShowModal(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-bold shadow-md transition-colors whitespace-nowrap flex items-center gap-2">
                <Plus className="w-4 h-4" /> Register New Case
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedCases.map((c: any) => {
            const meta = getCaseMeta(c.id);
            return (
              <Link href={`/case/${c.id}`} key={c.id}>
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-blue-400 transition-all cursor-pointer group relative overflow-hidden h-full flex flex-col">
                  <div className={`absolute top-0 left-0 w-1 h-full ${c.is_sealed ? 'bg-red-500' : 'bg-blue-600'} group-hover:opacity-80 transition-all`} />
                  <div className="flex justify-between items-start mb-3">
                    <span className="bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold px-2.5 py-1 rounded-md">
                      {c.case_number}
                    </span>
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-md border flex items-center gap-1 ${c.is_sealed ? 'bg-red-50 text-red-700 border-red-200' : c.status === 'Open' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                      {c.is_sealed && <Lock className="w-3 h-3" />} {c.status}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-800 group-hover:text-blue-700 transition-colors mb-2 flex items-center gap-2">
                    <Folder className="w-5 h-5 text-slate-400 group-hover:text-blue-500 flex-shrink-0" />
                    {c.title}
                  </h3>
                  {meta && (
                    <div className="space-y-1 mb-3">
                      {meta.crime_type && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <Tag className="w-3 h-3" /> {meta.crime_type}
                        </div>
                      )}
                      {meta.location && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <MapPin className="w-3 h-3" /> {meta.location}
                        </div>
                      )}
                      {meta.incident_date && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <Calendar className="w-3 h-3" /> Incident: {meta.incident_date}
                        </div>
                      )}
                      {meta.ipc_sections?.length > 0 && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <Hash className="w-3 h-3" /> IPC: {meta.ipc_sections.slice(0, 2).join(', ')}{meta.ipc_sections.length > 2 ? ` +${meta.ipc_sections.length - 2} more` : ''}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-sm text-slate-500 flex items-center gap-1.5">
                      <FileText className="w-4 h-4" /> {c.documents?.length || 0} Documents
                    </span>
                    <span className="text-sm font-bold text-blue-600 group-hover:translate-x-1 transition-transform">Open →</span>
                  </div>
                </div>
              </Link>
            );
          })}
          {sortedCases.length === 0 && (
            <div className="col-span-full text-center py-16 bg-white rounded-xl border border-dashed border-slate-300">
              <ShieldCheck className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500 font-medium">No cases found matching your description.</p>
              {canCreateCase && <p className="text-slate-400 text-sm mt-1">Click "Register New Case" to create your first case.</p>}
            </div>
          )}
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
