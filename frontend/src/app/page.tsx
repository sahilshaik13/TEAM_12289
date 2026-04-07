import { Suspense } from "react";
import SearchPalette from "@/components/SearchPalette";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 to-white flex flex-col items-center justify-center p-8">
      <div className="max-w-2xl w-full text-center">
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-lg">
            E
          </div>
          <h1 className="text-4xl font-bold text-gray-900">EchoMemory</h1>
        </div>
        <p className="text-xl text-gray-600 mb-4">
          Your personal semantic memory layer
        </p>
        <p className="text-gray-500 mb-12">
          Everything you read — papers, docs, code, articles — automatically captured and searchable by meaning.
        </p>

        <Suspense fallback={<div className="text-gray-400">Loading...</div>}>
          <SearchPalette />
        </Suspense>

        <div className="mt-8 flex items-center justify-center gap-6 text-sm text-gray-400">
          <span>Press</span>
          <kbd className="px-2 py-1 bg-gray-100 border border-gray-200 rounded text-xs">Cmd+Shift+E</kbd>
          <span>to search from anywhere</span>
        </div>
      </div>
    </main>
  );
}
