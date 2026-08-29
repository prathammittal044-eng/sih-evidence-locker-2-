// src/lib/auth.ts — JWT Auth Helper

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'sih_token';
const USER_KEY  = 'sih_user';

export interface SIHUser {
  id: number;
  name: string;
  role: 'Officer' | 'Reviewer' | 'Judge';
  badge: string;
  department: string;
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): SIHUser | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function saveSession(token: string, user: SIHUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  // Keep legacy key for any existing components
  localStorage.setItem('sih_user_id', user.id.toString());
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem('sih_user_id');
  window.location.href = '/login';
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Call on every protected page — redirects to /login if not authenticated. */
export function requireAuth(): SIHUser | null {
  const token = getToken();
  const user  = getUser();
  if (!token || !user) {
    if (typeof window !== 'undefined') window.location.href = '/login';
    return null;
  }
  return user;
}

export async function loginRequest(username: string, password: string) {
  const form = new FormData();
  form.append('username', username);
  form.append('password', password);
  const res = await fetch(`${API}/auth/login/`, { method: 'POST', body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Login failed');
  return data as { access_token: string; user: SIHUser };
}
