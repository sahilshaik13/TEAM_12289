"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts";
import { Globe, FileText, Code, Clock, Trash2, Loader2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("echomemory_token");
    setToken(stored);
  }, []);

  useEffect(() => {
    if (!token) return;

    async function load() {
      try {
        const [statsRes, heatRes, memRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/dashboard/stats`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/v1/dashboard/heatmap`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/v1/memories?limit=20`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (statsRes.ok) setStats(await statsRes.json());
        if (heatRes.ok) setHeatmap(await heatRes.json());
        if (memRes.ok) setMemories(await memRes.json());
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [token]);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Sign in to view your dashboard.</p>
          <a href="/api/auth/signin" className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium">
            Sign in with Google
          </a>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">E</div>
            <h1 className="text-lg font-semibold text-gray-900">EchoMemory</h1>
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <a href="/" className="text-gray-500 hover:text-gray-900">Search</a>
            <a href="/dashboard" className="text-indigo-600 font-medium">Dashboard</a>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Your Memory Dashboard</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Total Memories", value: stats?.total_memories || 0, icon: Globe, color: "indigo" },
              { label: "Web Pages", value: stats?.web_count || 0, icon: Globe, color: "blue" },
              { label: "PDFs", value: stats?.pdf_count || 0, icon: FileText, color: "red" },
              { label: "Code Files", value: stats?.code_count || 0, icon: Code, color: "green" },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`w-4 h-4 text-${color}-500`} />
                  <span className="text-sm text-gray-500">{label}</span>
                </div>
                <div className="text-2xl font-bold text-gray-900">{value}</div>
              </div>
            ))}
          </div>

          {heatmap.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-8">
              <h3 className="text-sm font-medium text-gray-700 mb-4">Capture Activity (Last 30 Days)</h3>
              <div className="flex items-end gap-1 h-24">
                {heatmap.map((entry) => (
                  <div
                    key={entry.date}
                    className="flex-1 bg-indigo-100 rounded-sm hover:bg-indigo-300 transition"
                    style={{ height: `${Math.min(100, (entry.count / Math.max(...heatmap.map((e) => e.count))) * 100)}%` }}
                    title={`${entry.date}: ${entry.count} memories`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Memories</h3>
          <div className="space-y-2">
            {memories.map((memory) => (
              <div
                key={memory.id}
                className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex items-center gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                      {memory.source_type}
                    </span>
                    <span className="text-xs text-gray-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(memory.captured_at)} at {formatTime(memory.captured_at)}
                    </span>
                  </div>
                  <p className="font-medium text-gray-900 truncate">
                    {memory.title || memory.url || memory.file_path || "Untitled"}
                  </p>
                  {memory.domain && (
                    <p className="text-xs text-gray-400">{memory.domain}</p>
                  )}
                </div>
                <button className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {memories.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                No memories captured yet. Browse the web and your files to start building your memory.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
