import { NextRequest, NextResponse } from "next/server";

// The backend redirects here after Google OAuth with:
//   ?access_token=...&user_id=...&email=...&display_name=...
//
// We forward those params to /auth/complete (a client page) which
// writes them into localStorage — you can't do localStorage from a
// Next.js Route Handler (server-side).

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const token = searchParams.get("access_token");
  const userId = searchParams.get("user_id");
  const email = searchParams.get("email");
  const displayName = searchParams.get("display_name");

  if (!token) {
    return NextResponse.redirect(new URL("/?error=auth_failed", request.url));
  }

  // Build redirect to the client-side completion page
  const completeUrl = new URL("/auth/complete", request.url);
  completeUrl.searchParams.set("access_token", token);
  if (userId) completeUrl.searchParams.set("user_id", userId);
  if (email) completeUrl.searchParams.set("email", email);
  if (displayName) completeUrl.searchParams.set("display_name", displayName);

  return NextResponse.redirect(completeUrl);
}
