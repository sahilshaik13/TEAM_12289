"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

const EXTENSION_ID = process.env.NEXT_PUBLIC_EXTENSION_ID || "";

function AuthCompleteInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "done" | "error">("loading");

  useEffect(() => {
    const token = searchParams.get("access_token");
    const userId = searchParams.get("user_id");
    const email = searchParams.get("email");
    const displayName = searchParams.get("display_name");

    if (!token) {
      setStatus("error");
      setTimeout(() => router.replace("/?error=auth_failed"), 2000);
      return;
    }

    // 1️⃣ Write to localStorage for the web app
    localStorage.setItem("echomemory_token", token);
    localStorage.setItem(
      "echomemory_user",
      JSON.stringify({ userId, email, displayName })
    );

    // 2️⃣ Send token to Chrome extension (if this page was opened by it)
    try {
      const runtime = (window as any).chrome?.runtime;
      if (runtime) {
        runtime.sendMessage(
          EXTENSION_ID || undefined,
          { type: "AUTH_TOKEN", token },
          () => { void runtime.lastError; }
        );
      }
    } catch {
      // Extension not installed — that's fine
    }

    setStatus("done");
    setTimeout(() => router.replace("/dashboard"), 800);
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-indigo-50 to-white gap-4">
      {status === "loading" && (
        <>
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-gray-500 text-sm">Completing sign-in…</p>
        </>
      )}
      {status === "done" && (
        <>
          <CheckCircle2 className="w-8 h-8 text-green-500" />
          <p className="text-gray-700 font-medium">Signed in! Redirecting…</p>
        </>
      )}
      {status === "error" && (
        <>
          <AlertCircle className="w-8 h-8 text-red-500" />
          <p className="text-gray-700 font-medium">Sign-in failed. Redirecting…</p>
        </>
      )}
    </div>
  );
}

// useSearchParams() requires Suspense in Next.js 14 app router
export default function AuthCompletePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-indigo-50 to-white gap-4">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-gray-500 text-sm">Loading…</p>
        </div>
      }
    >
      <AuthCompleteInner />
    </Suspense>
  );
}
