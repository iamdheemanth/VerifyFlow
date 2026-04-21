import { type NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { SignJWT, jwtVerify } from 'jose'

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
    encode: async ({ secret, token, maxAge }) => {
      const secretKey = new TextEncoder().encode(secret as string)
      return new SignJWT(token as Record<string, unknown>)
        .setProtectedHeader({ alg: 'HS256' })
        .setIssuedAt()
        .setExpirationTime(
          Math.floor(Date.now() / 1000) + (maxAge ?? 30 * 24 * 60 * 60)
        )
        .sign(secretKey)
    },
    decode: async ({ secret, token }) => {
      if (!token) return null
      const secretKey = new TextEncoder().encode(secret as string)
      try {
        const { payload } = await jwtVerify(token, secretKey)
        return payload as any
      } catch {
        return null
      }
    },
  },
  pages: {
    signIn: '/auth/login',
    error: '/auth/login',
  },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.id = profile.sub
        token.email = profile.email
        token.name = profile.name
        token.picture = profile.picture ?? null
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
