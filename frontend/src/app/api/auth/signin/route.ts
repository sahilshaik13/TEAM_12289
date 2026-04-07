import { NextResponse } from "next/server";

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const googleAuthUrl = `${apiUrl}/api/v1/auth/google`;
  return NextResponse.redirect(googleAuthUrl);
}
