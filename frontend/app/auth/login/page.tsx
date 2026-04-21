'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { signIn } from 'next-auth/react'

function ShieldCheckIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3 5 6v5c0 4.2 2.54 8.1 7 10 4.46-1.9 7-5.8 7-10V6l-7-3Zm-2.1 9 1.5 1.5 3.2-3.7"
      />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" />
    </svg>
  )
}

function getErrorMessage(errorCode: string | null): string | null {
  if (!errorCode) return null
  if (errorCode === 'OAuthAccountNotLinked') {
    return 'This email is already associated with another account.'
  }
  if (errorCode === 'OAuthSignin' || errorCode === 'OAuthCallback') {
    return 'Google sign-in failed. Please try again.'
  }
  return 'Authentication failed. Please try again.'
}

function LoginCard() {
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(getErrorMessage(searchParams.get('error')))
  }, [searchParams])

  async function handleGoogleSignIn() {
    setLoading(true)
    setError(null)

    try {
      await signIn('google', { callbackUrl: '/dashboard' })
    } catch {
      setLoading(false)
      setError('Authentication failed. Please try again.')
    }
  }

  return (
    <div className="w-full max-w-sm rounded-2xl border border-[#2A2A26] bg-[#141412] p-8">
      <h1 className="text-center text-xl font-semibold text-[#F5F4F0]">
        Welcome to VerifyFlow
      </h1>
      <p className="mt-1.5 mb-8 text-center text-sm text-[#8A8880]">
        Sign in with your Google account to continue.
      </p>

      <button
        type="button"
        onClick={handleGoogleSignIn}
        disabled={loading}
        className="w-full flex items-center justify-center gap-3 rounded-xl border border-[#2A2A26] bg-[#1E1E1C] py-3 text-sm font-medium text-[#F5F4F0] transition-colors hover:bg-[#2A2A26] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? <SpinnerIcon /> : <GoogleIcon />}
        <span>{loading ? 'Signing in…' : 'Continue with Google'}</span>
      </button>

      {error ? (
        <div className="mt-4 rounded-xl border border-[#FCA5A5] bg-[#FEF2F2] p-3 text-center text-xs text-[#991B1B]">
          {error}
        </div>
      ) : null}

      <p className="mt-6 text-center font-mono text-xs text-[#8A8880]">
        Secured by NextAuth.js · JWT sessions
      </p>
    </div>
  )
}

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[#0A0A08] flex flex-col items-center justify-center px-4 text-[#F5F4F0]">
      <Link
        href="/"
        className="mb-10 flex items-center gap-2 text-sm font-semibold tracking-tight text-[#F5F4F0]"
      >
        <ShieldCheckIcon />
        <span>VerifyFlow</span>
      </Link>

      <Suspense fallback={<div className="w-full max-w-sm rounded-2xl border border-[#2A2A26] bg-[#141412] p-8" />}>
        <LoginCard />
      </Suspense>

      <p className="mt-8 text-center text-xs text-[#8A8880]">
        By signing in, you agree to use this application responsibly.
      </p>
    </div>
  )
}
