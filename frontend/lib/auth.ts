import { type NextAuthOptions } from 'next-auth'
import { type JWT } from 'next-auth/jwt'
import GoogleProvider from 'next-auth/providers/google'

import { encodeAuthToken, decodeAuthToken } from '@/lib/auth-token'
import { serverEnv } from '@/lib/server-env'

type GoogleProfile = {
  picture?: string | null
}

const DEFAULT_AUTH_REDIRECT_PATH = '/dashboard'

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

export const authOptions: NextAuthOptions = {
  secret: serverEnv.nextauthSecret,
  providers: [
    GoogleProvider({
      clientId: serverEnv.googleClientId,
      clientSecret: serverEnv.googleClientSecret,
    }),
  ],
  session: {
    strategy: 'jwt',
  },
  jwt: {
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
