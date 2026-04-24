'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { signOut, useSession } from 'next-auth/react'
import { usePathname } from 'next/navigation'

const navItems = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/runs', label: 'Runs' },
  { href: '/review', label: 'Review Queue' },
  { href: '/benchmarks', label: 'Benchmarks' },
  { href: '/configs', label: 'Configurations' },
]

function VerifyFlowMark() {
  return (
    <Link href="/dashboard" className="inline-flex items-center gap-3 text-[#F5F4F0]">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#2A2A26] bg-[#141412] shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset]">
        <svg
          aria-hidden="true"
          className="h-5 w-5"
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
      </span>
      <span className="text-base font-semibold tracking-[0.01em] sm:text-lg">
        VerifyFlow
      </span>
    </Link>
  )
}

function isActivePath(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`)
}

function NavLink({
  href,
  label,
  pathname,
  onNavigate,
}: {
  href: string
  label: string
  pathname: string
  onNavigate?: () => void
}) {
  const isActive = isActivePath(pathname, href)

  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={
        isActive
          ? 'rounded-full border border-[#3A332B] bg-[#C8A882]/10 px-4 py-2 text-sm font-medium text-[#E8D5BF]'
          : 'rounded-full px-4 py-2 text-sm text-[#8A8880] transition-colors hover:bg-[#141412] hover:text-[#F5F4F0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8A882]/70'
      }
    >
      {label}
    </Link>
  )
}

function AccountInitials({ name, email }: { name?: string | null; email?: string | null }) {
  const label = name || email || 'Account'
  const initials = label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')

  return (
    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[#3A332B] bg-[#C8A882]/10 font-mono text-xs font-semibold text-[#E8D5BF]">
      {initials || 'VF'}
    </span>
  )
}

export default function SidebarShell() {
  const pathname = usePathname()
  const { data: session } = useSession()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const shouldRenderNav = !(pathname === '/' || pathname.startsWith('/auth/'))
  const userName = session?.user?.name
  const userEmail = session?.user?.email

  useEffect(() => {
    document.body.dataset.sidebar = shouldRenderNav ? 'visible' : 'hidden'

    return () => {
      delete document.body.dataset.sidebar
    }
  }, [shouldRenderNav])

  useEffect(() => {
    setAccountOpen(false)
    setMobileNavOpen(false)
  }, [pathname])

  async function handleLogout() {
    await signOut({ callbackUrl: '/' })
  }

  if (!shouldRenderNav) {
    return null
  }

  return (
    <header className="sticky top-0 z-50 border-b border-[#23231F] bg-[rgba(10,10,8,0.82)] shadow-[0_18px_60px_-45px_rgba(0,0,0,0.95)] backdrop-blur-xl">
      <div className="mx-auto grid h-[72px] max-w-7xl grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 justify-start">
          <VerifyFlowMark />
        </div>

        <nav className="hidden items-center gap-1 rounded-full border border-[#24241F] bg-[rgba(20,20,18,0.62)] px-2 py-1 shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset] md:flex">
          {navItems.map((item) => (
            <NavLink key={item.href} pathname={pathname} {...item} />
          ))}
        </nav>

        <div className="flex items-center justify-end gap-2">
          <div className="relative hidden md:block">
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={accountOpen}
              onClick={() => setAccountOpen((open) => !open)}
              className="inline-flex items-center gap-3 rounded-full border border-[#2A2A26] bg-[#141412] py-1.5 pl-1.5 pr-4 text-left transition-colors hover:border-[#3A332B] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8A882]/70"
            >
              <AccountInitials name={userName} email={userEmail} />
              <span className="min-w-0">
                <span className="block max-w-36 truncate text-sm font-medium text-[#F5F4F0]">
                  {userName || 'Account'}
                </span>
                {userEmail ? (
                  <span className="block max-w-36 truncate text-xs text-[#8A8880]">
                    {userEmail}
                  </span>
                ) : null}
              </span>
              <svg
                aria-hidden="true"
                className={`h-4 w-4 text-[#8A8880] transition-transform ${
                  accountOpen ? 'rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
              </svg>
            </button>

            {accountOpen ? (
              <div
                role="menu"
                className="absolute right-0 mt-3 w-72 rounded-2xl border border-[#2A2A26] bg-[#10100E] p-2 shadow-[0_24px_80px_-36px_rgba(0,0,0,0.95)]"
              >
                <div className="border-b border-[#23231F] px-3 py-3">
                  <p className="truncate text-sm font-medium text-[#F5F4F0]">
                    {userName || 'Signed in'}
                  </p>
                  {userEmail ? (
                    <p className="mt-1 truncate text-xs text-[#8A8880]">{userEmail}</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => void handleLogout()}
                  className="mt-2 flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300/40"
                >
                  Log out
                  <span aria-hidden="true">-&gt;</span>
                </button>
              </div>
            ) : null}
          </div>

          <button
            type="button"
            aria-label="Toggle navigation"
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen((open) => !open)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#2A2A26] bg-[#141412] text-[#F5F4F0] md:hidden"
          >
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              {mobileNavOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6 6 18" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {mobileNavOpen ? (
        <div className="border-t border-[#23231F] bg-[#0A0A08] px-4 pb-4 md:hidden">
          <nav className="flex flex-col gap-1 pt-3">
            {navItems.map((item) => (
              <NavLink
                key={item.href}
                pathname={pathname}
                onNavigate={() => setMobileNavOpen(false)}
                {...item}
              />
            ))}
          </nav>
          <div className="mt-4 border-t border-[#23231F] pt-4">
            <div className="flex items-center gap-3 rounded-2xl border border-[#2A2A26] bg-[#10100E] p-3">
              <AccountInitials name={userName} email={userEmail} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[#F5F4F0]">
                  {userName || 'Signed in'}
                </p>
                {userEmail ? (
                  <p className="mt-0.5 truncate text-xs text-[#8A8880]">{userEmail}</p>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="mt-3 w-full rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-2.5 text-left text-sm font-medium text-red-300 transition-colors hover:bg-red-500/15"
            >
              Log out
            </button>
          </div>
        </div>
      ) : null}
    </header>
  )
}
