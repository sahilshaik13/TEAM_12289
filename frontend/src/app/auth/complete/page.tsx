"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

// Extension ID — update if you use a different build.
// In production you'd read this from an env var or a well-known endpoint.
// The manifest's externally_connectable allows this page to message the extension.
const EXTENSION_ID = process.env.NEXT_PUBLIC_EXTENSION_ID || "";

export default function AuthCompletePage() {
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

    // 1️⃣  Always write to localStorage for the web app
    localStorage.setItem("echomemory_token", token);
    localStorage.setItem(
      "echomemory_user",
      JSON.stringify({ userId, email, displayName })
    );

    // 2️⃣  If the page was opened by the Chrome extension, send the token back
    //     The extension background.js listens for { type: 'AUTH_TOKEN', token }
    const sendToExtension = () => {
      // chrome.runtime is injected by Chrome when externally_connectable matches
      const runtime = (window as any).chrome?.runtime;
      if (!runtime) return false;

      const targetId = EXTENSION_ID || undefined; // undefined = any connected extension
      try {
        runtime.sendMessage(targetId, { type: "AUTH_TOKEN", token }, () => {
          // Ignore chrome.runtime.lastError — extension may not be installed
          void runtime.lastError;
        });
        return true;
      } catch {
        return false;
      }
    };

    sendToExtension();
    setStatus("done");

    // 3️⃣  Redirect to dashboard after a short delay (gives time for extension to receive msg)
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
