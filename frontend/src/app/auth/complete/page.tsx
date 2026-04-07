"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

// This page is the landing point after the OAuth callback chain:
//   Google → Backend (/api/v1/auth/callback) → /api/auth/callback → HERE
//
// It writes the JWT and user info into localStorage (which Route Handlers
// can't access), then redirects to the dashboard.

export default function AuthCompletePage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("access_token");
    const userId = searchParams.get("user_id");
    const email = searchParams.get("email");
    const displayName = searchParams.get("display_name");

    if (token) {
      localStorage.setItem("echomemory_token", token);
      localStorage.setItem(
        "echomemory_user",
        JSON.stringify({ userId, email, displayName })
      );
      router.replace("/dashboard");
    } else {
      router.replace("/?error=auth_failed");
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-indigo-50 to-white gap-4">
      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      <p className="text-gray-500 text-sm">Completing sign-in…</p>
    </div>
  );
}
