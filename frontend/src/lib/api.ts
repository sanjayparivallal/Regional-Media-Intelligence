/**
 * API Client for Regional Media Intelligence Agent
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const signal = options?.signal || controller.signal;
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
      signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorMsg: string;
      try {
        const errorData = await res.clone().json();
        errorMsg = errorData.detail || errorData.message || JSON.stringify(errorData);
      } catch {
        errorMsg = await res.text();
      }
      throw new Error(`API Error ${res.status}: ${errorMsg || res.statusText}`);
    }
    return res.json();
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error(`Request timed out for ${endpoint}`);
    }
    if (err.message?.includes('Failed to fetch') || err.message?.includes('fetch failed')) {
      throw new Error(`Cannot reach API at ${url}. Ensure the backend server is running.`);
    }
    throw err;
  }
}

// Documents
export const api = {
  // Health
  health: () => fetchAPI<{ status: string; demo_mode: boolean }>('/health'),

  // Documents
  uploadDocument: async (file: File, metadata?: Record<string, string>) => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      Object.entries(metadata).forEach(([key, value]) => {
        if (value) formData.append(key, value);
      });
    }
    const res = await fetch(`${API_BASE}/documents/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },

  getDocuments: (status?: string) =>
    fetchAPI<any[]>(`/documents${status ? `?status=${status}` : ''}`),

  getDocument: (id: string) => fetchAPI<any>(`/documents/${id}`),

  processDocument: (id: string) =>
    fetchAPI<any>(`/documents/${id}/process`, { method: 'POST' }),

  getDocumentJobs: (id: string) => fetchAPI<any[]>(`/documents/${id}/jobs`),

  getDocumentPages: (id: string) => fetchAPI<any[]>(`/documents/${id}/pages`),

  cancelDocument: (id: string) =>
    fetchAPI<any>(`/documents/${id}/cancel`, { method: 'POST' }),

  deleteDocument: (id: string) =>
    fetchAPI<any>(`/documents/${id}`, { method: 'DELETE' }),

  // Articles
  getArticles: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchAPI<any[]>(`/articles${query}`);
  },

  getArticle: (id: string) => fetchAPI<any>(`/articles/${id}`),

  // Alerts
  getAlerts: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchAPI<any[]>(`/alerts${query}`);
  },

  getAlert: (id: string) => fetchAPI<any>(`/alerts/${id}`),

  getAlertEvidence: (id: string) => fetchAPI<any>(`/alerts/${id}/evidence`),

  // Reviews
  getReviews: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchAPI<any[]>(`/reviews${query}`);
  },

  updateReview: (id: string, data: any) =>
    fetchAPI<any>(`/reviews/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Brands
  getBrands: () => fetchAPI<any[]>('/brands'),
  createBrand: (data: any) =>
    fetchAPI<any>('/brands', { method: 'POST', body: JSON.stringify(data) }),
  updateBrand: (id: string, data: any) =>
    fetchAPI<any>(`/brands/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteBrand: (id: string) =>
    fetchAPI<any>(`/brands/${id}`, { method: 'DELETE' }),

  // Analytics
  getOverview: () => fetchAPI<any>('/analytics/overview'),
  getCoverage: () => fetchAPI<any>('/analytics/coverage'),

  // Audit
  getAuditTrail: (documentId: string) => fetchAPI<any[]>(`/audit/${documentId}`),

  // Publications
  getPublications: () => fetchAPI<any[]>('/publications'),

  // Search
  search: (query: string) => fetchAPI<any>(`/search?q=${encodeURIComponent(query)}`),

  // Mentions
  getMentions: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchAPI<any[]>(`/articles/mentions/all${query}`);
  },

  // Incidents
  getIncidents: (params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchAPI<any[]>(`/incidents${query}`);
  },

  // System
  getSystemInfo: () => fetchAPI<any>('/system/info'),
};
