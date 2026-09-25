import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

async function proxyRequest(request: NextRequest, pathSegments: string[]) {
  const backendBase = (process.env.BACKEND_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const subpath = pathSegments.join('/');
  const queryString = request.nextUrl.search;
  const targetUrl = backendBase + '/api/' + subpath + queryString;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower !== 'host' && lower !== 'content-length') {
      headers.set(key, value);
    }
  });

  const method = request.method;
  const isBodyAllowed = !['GET', 'HEAD'].includes(method);
  const body = isBodyAllowed ? await request.arrayBuffer() : undefined;

  try {
    const upstreamRes = await fetch(targetUrl, {
      method,
      headers,
      body: body && body.byteLength > 0 ? body : undefined,
      cache: 'no-store',
    });

    const responseHeaders = new Headers();
    upstreamRes.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    const responseBody = await upstreamRes.arrayBuffer();
    return new NextResponse(responseBody, {
      status: upstreamRes.status,
      statusText: upstreamRes.statusText,
      headers: responseHeaders,
    });
  } catch (err: any) {
    console.error('Proxy error to ' + targetUrl + ':', err);
    return NextResponse.json(
      { detail: 'Backend proxy connection failed: ' + (err.message || String(err)) },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path);
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path);
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(request, params.path);
}
