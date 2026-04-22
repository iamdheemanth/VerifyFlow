import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'
import { decodeAuthToken } from '@/lib/auth'

export default withAuth(
  function middleware(req) {
    return NextResponse.next()
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
    jwt: {
      decode: ({ secret, token }) =>
        decodeAuthToken({
          secret: secret as string,
          token,
        }),
    },
    pages: {
      signIn: '/auth/login',
    },
  }
)

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/runs/:path*',
    '/review/:path*',
    '/benchmarks/:path*',
    '/configs/:path*',
  ],
}
