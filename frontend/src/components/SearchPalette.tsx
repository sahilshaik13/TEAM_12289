"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, ExternalLink, Clock, Globe, FileText, Code } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type SourceType = "web" | "pdf" | "code" | "text";

const SOURCE_ICONS: Record<SourceType, React.ComponentType<{ className?: string }>> = {
  web: Globe,
  pdf: FileText,
  code: Code,
  text: FileText,
};

interface SearchResult {
  memory_id: string;
  chunk_id: string;
  score: number;
  similarity: number;
  recency_score: number;
  title: string | null;
  url: string | null;
  file_path: string | null;
  source_type: SourceType;
  snippet: string;
  domain: string | null;
  captured_at: string;
}

export default function SearchPalette() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const stored = localStorage.getItem("echomemory_token");
    setToken(stored);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "E") {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const search = useCallback(async (q: string) => {
    if (!q.trim() || !token) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/search?q=${encodeURIComponent(q)}&limit=10`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    const timer = setTimeout(() => search(query), 300);
    return () => clearTimeout(timer);
  }, [query, search]);

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  if (!token) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm">
        <p className="text-gray-500 mb-4">Sign in to start searching your memories.</p>
        <button
          onClick={() => router.push("/api/auth/signin")}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition"
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  return (
    <>
      <div
        className="relative rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden"
        onClick={() => setIsOpen(true)}
      >
        <div className="flex items-center gap-3 px-4 py-3">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search your memories (e.g. 'that paper about sparse attention')..."
            className="flex-1 outline-none text-gray-700 placeholder-gray-400"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
          />
          {isLoading && <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />}
        </div>
      </div>

      {isOpen && results.length > 0 && (
        <div className="mt-2 rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden max-h-96 overflow-y-auto">
          {results.map((result) => {
            const Icon = SOURCE_ICONS[result.source_type] || Globe;
            return (
              <a
                key={result.chunk_id}
                href={result.url || result.file_path || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-3 px-4 py-3 hover:bg-indigo-50 transition border-b border-gray-100 last:border-0"
              >
                <Icon className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-medium text-gray-900 text-sm truncate">
                      {result.title || result.url || "Untitled"}
                    </span>
                    <span className="text-xs text-gray-400 flex-shrink-0 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(result.captured_at)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-2">{result.snippet}</p>
                  {result.url && (
                    <span className="text-xs text-gray-400 mt-1 block truncate">{result.domain}</span>
                  )}
                </div>
              </a>
            );
          })}
        </div>
      )}

      {isOpen && query && !isLoading && results.length === 0 && (
        <div className="mt-2 rounded-xl border border-gray-200 bg-white shadow-lg p-6 text-center text-gray-500 text-sm">
          No memories found for &ldquo;{query}&rdquo;
        </div>
      )}
    </>
  );
}
