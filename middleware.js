export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

function unauthorized(message = 'Authentication required') {
  return new Response(message, {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="JobFlow Fabian", charset="UTF-8"',
      'Cache-Control': 'no-store',
    },
  });
}

export function middleware(request) {
  const user = process.env.AUTH_USER;
  const password = process.env.AUTH_PASSWORD;
  if (!user || !password) {
    return new Response('AUTH_USER y AUTH_PASSWORD no están configurados en Vercel.', { status: 503 });
  }
  const header = request.headers.get('authorization') || '';
  const [scheme, encoded] = header.split(' ');
  if (scheme !== 'Basic' || !encoded) return unauthorized();
  let decoded = '';
  try { decoded = atob(encoded); } catch (_) { return unauthorized(); }
  const separator = decoded.indexOf(':');
  const actualUser = decoded.slice(0, separator);
  const actualPassword = decoded.slice(separator + 1);
  if (actualUser !== user || actualPassword !== password) return unauthorized('Credenciales inválidas');
  return Response.next();
}
