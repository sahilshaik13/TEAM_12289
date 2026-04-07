import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("access_token");
  const userId = request.nextUrl.searchParams.get("user_id");
  const email = request.nextUrl.searchParams.get("email");
  const displayName = request.nextUrl.searchParams.get("display_name");

  if (token) {
    const response = NextResponse.redirect(
      new URL("/", request.url)
    );
    response.cookies.set("echomemory_token", token, {
      httpOnly: false,
      secure: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
      path: "/",
    });
    response.cookies.set("echomemory_user", JSON.stringify({ userId, email, displayName }), {
      httpOnly: false,
      secure: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
      path: "/",
    });
    return response;
  }

  return NextResponse.redirect(
    new URL("/?error=auth_failed", request.url)
  );
}
