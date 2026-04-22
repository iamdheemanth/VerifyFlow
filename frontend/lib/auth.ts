import { type NextAuthOptions } from 'next-auth'
import { type JWT } from 'next-auth/jwt'
import GoogleProvider from 'next-auth/providers/google'
import { SignJWT, jwtVerify } from 'jose'

type GoogleProfile = {
  picture?: string | null
}

const DEFAULT_AUTH_REDIRECT_PATH = '/dashboard'

function getSecretKey(secret: string) {
  return new TextEncoder().encode(secret)
}

function getSafeRedirectPath(url: string, baseUrl?: string) {
  if (url.startsWith('/') && !url.startsWith('//')) {
    return url
  }

  if (baseUrl) {
    try {
      const parsedUrl = new URL(url)
      const parsedBaseUrl = new URL(baseUrl)

      if (parsedUrl.origin === parsedBaseUrl.origin) {
        return `${parsedUrl.pathname}${parsedUrl.search}${parsedUrl.hash}`
      }
    } catch {
      return DEFAULT_AUTH_REDIRECT_PATH
    }
  }

  return DEFAULT_AUTH_REDIRECT_PATH
}

export async function encodeAuthToken({
  secret,
  token,
  maxAge,
}: {
  secret: string
  token?: JWT | null
  maxAge?: number
}) {
  const secretKey = getSecretKey(secret)
  return new SignJWT((token ?? {}) as Record<string, unknown>)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(
      Math.floor(Date.now() / 1000) + (maxAge ?? 30 * 24 * 60 * 60)
    )
    .sign(secretKey)
}

export async function decodeAuthToken({
  secret,
  token,
}: {
  secret: string
  token?: string
}) {
  if (!token) return null

  const secretKey = getSecretKey(secret)

  try {
    const { payload } = await jwtVerify(token, secretKey)
    return payload as JWT
  } catch {
    return null
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: {
    strategy: 'jwt',
  },
  jwt: {
    // Produce a standard HS256 JWT instead of NextAuth's default
    // encrypted JWE — this lets FastAPI verify it with PyJWT.
    encode: async ({ secret, token, maxAge }) =>
      encodeAuthToken({
        secret: secret as string,
        token: token as JWT | null | undefined,
        maxAge,
      }),
    decode: async ({ secret, token }) =>
      decodeAuthToken({
        secret: secret as string,
        token,
      }),
  },
  pages: {
    signIn: '/auth/login',
    error: '/auth/login',
  },
  callbacks: {
    async redirect({ url, baseUrl }) {
      return `${baseUrl}${getSafeRedirectPath(url, baseUrl)}`
    },
    async jwt({ token, account, profile }) {
      if (account && profile) {
        const googleProfile = profile as typeof profile & GoogleProfile

        token.id = token.sub ?? account.providerAccountId
        token.email = profile.email ?? token.email
        token.name = profile.name ?? token.name
        token.picture = googleProfile.picture ?? token.picture ?? null
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
      }
      return session
    },
  },
}
