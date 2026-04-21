'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  {
    href: '/',
    label: 'Dashboard',
    icon: (
      <svg
        aria-hidden="true"
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4h7v7H4V4Zm9 0h7v4h-7V4ZM4 13h7v7H4v-7Zm9-1h7v8h-7v-8Z" />
      </svg>
    ),
  },
  {
    href: '/runs',
    label: 'Runs',
    icon: (
      <svg
        aria-hidden="true"
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />
      </svg>
    ),
  },
  {
    href: '/review',
    label: 'Review Queue',
    icon: (
      <svg
        aria-hidden="true"
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="m12 4 8 14H4L12 4Zm0 5v4m0 3h.01" />
      </svg>
    ),
  },
  {
    href: '/benchmarks',
    label: 'Benchmarks',
    icon: (
      <svg
        aria-hidden="true"
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 19V9m7 10V5m7 14v-7" />
      </svg>
    ),
  },
  {
    href: '/configs',
    label: 'Configurations',
    icon: (
      <svg
        aria-hidden="true"
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6 7h12M6 17h12M9 7a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm10 10a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z"
        />
      </svg>
    ),
  },
]

function VerifyFlowMark() {
  return (
    <div className="flex items-center gap-2">
      <svg
        aria-hidden="true"
        className="h-5 w-5 text-[#1A1410]"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 3 5 6v5c0 4.2 2.54 8.1 7 10 4.46-1.9 7-5.8 7-10V6l-7-3Zm-2.1 9 1.5 1.5 3.2-3.7"
        />
      </svg>
      <span className="text-sm font-semibold tracking-tight text-[#1A1410]">
        VerifyFlow
      </span>
    </div>
  )
}

function Navigation({
  pathname,
  onNavigate,
}: {
  pathname: string
  onNavigate?: () => void
}) {
  return (
    <nav className="flex flex-col gap-1.5">
      {navItems.map((item) => {
        const isActive =
          item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={
              isActive
                ? 'flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm border-l-2 border-[#1A1410] bg-[#EEE9E1] text-[#1A1410] font-medium'
                : 'flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-[#5C5248] hover:bg-[#EEE9E1] transition-colors'
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}

export default function SidebarShell() {
  const pathname = usePathname()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const shouldRenderSidebar = !(pathname === '/' || pathname.startsWith('/auth/'))

  useEffect(() => {
    document.body.dataset.sidebar = shouldRenderSidebar ? 'visible' : 'hidden'

    return () => {
      delete document.body.dataset.sidebar
    }
  }, [shouldRenderSidebar])

  if (!shouldRenderSidebar) {
    return null
  }

  return (
    <>
      <aside className="hidden md:flex w-56 h-screen fixed top-0 left-0 flex-col bg-[#F7F3EE] border-r border-[#E2DAD0] z-20">
        <div className="px-5 py-5 border-b border-[#E2DAD0]">
          <VerifyFlowMark />
        </div>
        <div className="flex-1 overflow-y-auto py-4 px-3">
          <Navigation pathname={pathname} />
        </div>
        <div className="px-5 py-4 border-t border-[#E2DAD0]">
          <div className="text-[10px] text-[#9C948A] font-mono">v0.1.0</div>
        </div>
      </aside>

      <div className="flex md:hidden items-center justify-between px-4 py-3 bg-[#F7F3EE] border-b border-[#E2DAD0] sticky top-0 z-10">
        <VerifyFlowMark />
        <button
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={mobileNavOpen}
          onClick={() => setMobileNavOpen((open) => !open)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[#E2DAD0] text-[#1A1410]"
        >
          <svg
            aria-hidden="true"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
      </div>

      {mobileNavOpen ? (
        <div className="fixed inset-0 z-30 flex flex-col bg-[#F7F3EE] md:hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#E2DAD0]">
            <VerifyFlowMark />
            <button
              type="button"
              aria-label="Close navigation"
              onClick={() => setMobileNavOpen(false)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[#E2DAD0] text-[#1A1410]"
            >
              <svg
                aria-hidden="true"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-4">
            <Navigation pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
          </div>
          <div className="px-4 py-4 border-t border-[#E2DAD0]">
            <div className="text-[10px] text-[#9C948A] font-mono">v0.1.0</div>
          </div>
        </div>
      ) : null}
    </>
  )
}
