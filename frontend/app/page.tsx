'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'

function ShieldCheckIcon() {
  return (
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
  )
}

function SearchIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="#C8A882"
      strokeWidth="1.5"
    >
      <circle cx="11" cy="11" r="6" />
      <path strokeLinecap="round" d="m20 20-4.35-4.35" />
    </svg>
  )
}

function ScaleIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="#C8A882"
      strokeWidth="1.5"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16M6 7h12M8 7l-3 6h6l-3-6Zm8 0-3 6h6l-3-6ZM9 20h6" />
    </svg>
  )
}

function ListIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="#C8A882"
      strokeWidth="1.5"
    >
      <path strokeLinecap="round" d="M8 7h10M8 12h10M8 17h10M4 7h.01M4 12h.01M4 17h.01" />
    </svg>
  )
}

function UsersIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="#C8A882"
      strokeWidth="1.5"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16 19v-1a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v1M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 9v-1a3 3 0 0 0-2-2.82M15 4.13a3 3 0 0 1 0 5.74"
      />
    </svg>
  )
}

function BarChartIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="#C8A882"
      strokeWidth="1.5"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 19V9m7 10V5m7 14v-7M3 19h18" />
    </svg>
  )
}

function ZapIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="#C8A882"
      strokeWidth="1.5"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="currentColor"
      viewBox="0 0 24 24"
    >
      <path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.08 3.29 9.39 7.86 10.9.58.1.79-.25.79-.56 0-.28-.01-1.2-.02-2.17-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.71.08-.71 1.16.08 1.78 1.2 1.78 1.2 1.03 1.77 2.71 1.26 3.37.97.1-.75.4-1.26.72-1.55-2.55-.29-5.23-1.28-5.23-5.68 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.19 1.18a10.98 10.98 0 0 1 5.82 0c2.21-1.49 3.18-1.18 3.18-1.18.64 1.59.24 2.77.12 3.06.74.8 1.19 1.83 1.19 3.08 0 4.41-2.68 5.39-5.24 5.67.41.36.77 1.06.77 2.14 0 1.55-.01 2.79-.01 3.17 0 .31.21.67.8.56a11.53 11.53 0 0 0 7.85-10.9C23.5 5.66 18.35.5 12 .5Z" />
    </svg>
  )
}

function Wordmark() {
  return (
    <Link
      href="/"
      className="inline-flex items-center gap-3 text-[#F5F4F0] transition-opacity hover:opacity-90"
    >
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#2A2A26] bg-[#141412] shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset]">
        <ShieldCheckIcon />
      </span>
      <span className="text-base font-semibold tracking-[0.01em] text-[#F5F4F0] sm:text-lg">
        VerifyFlow
      </span>
    </Link>
  )
}

function ProductMockup() {
  return (
    <div
      id="demo"
      className="landing-float relative mx-auto w-full max-w-[360px] rounded-[24px] border border-[#2A2A26] bg-[linear-gradient(180deg,rgba(20,20,18,0.98),rgba(12,12,11,0.98))] p-2.5 shadow-[0_40px_120px_-60px_rgba(0,0,0,0.95),0_0_0_1px_rgba(255,255,255,0.03)_inset] transition-transform duration-500 hover:-translate-y-1 sm:max-w-[390px] lg:max-w-[400px] xl:max-w-[430px]"
    >
      <div className="absolute inset-x-10 top-0 h-32 rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.22),transparent_72%)] blur-3xl" />
      <div className="relative overflow-hidden rounded-[20px] border border-[#2A2A26] bg-[#0F0F0D]">
        <div className="flex items-center justify-between border-b border-[#23231F] px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#C8A882]/80" />
            <span className="h-2 w-2 rounded-full bg-[#3A3A34]" />
            <span className="h-2 w-2 rounded-full bg-[#3A3A34]" />
          </div>
          <div className="rounded-full border border-[#2A2A26] bg-[#141412] px-2.5 py-1 font-mono text-[10px] text-[#8A8880]">
            reliability dashboard
          </div>
        </div>

        <div className="grid gap-3 p-3 lg:grid-cols-[1.45fr_0.95fr]">
          <div className="space-y-3">
            <div className="rounded-[18px] border border-[#2A2A26] bg-[#141412] p-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8A8880]">
                    Run Snapshot
                  </p>
                  <h3 className="mt-1.5 text-[13px] font-semibold text-[#F5F4F0]">
                    Claimed vs verified workflow
                  </h3>
                </div>
                <div className="rounded-full border border-[#3A332B] bg-[#C8A882]/10 px-2 py-1 font-mono text-[10px] text-[#C8A882]">
                  confidence 0.94
                </div>
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div className="rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                  <p className="font-mono text-[10px] text-[#8A8880]">Claimed</p>
                  <p className="mt-1.5 text-base font-semibold text-[#F5F4F0]">12</p>
                  <p className="mt-1 text-[11px] text-[#8A8880]">tasks attempted</p>
                </div>
                <div className="rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                  <p className="font-mono text-[10px] text-[#8A8880]">Verified</p>
                  <p className="mt-1.5 text-base font-semibold text-[#E9E4DA]">9</p>
                  <p className="mt-1 text-[11px] text-[#8A8880]">evidence-backed</p>
                </div>
                <div className="rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                  <p className="font-mono text-[10px] text-[#8A8880]">Escalated</p>
                  <p className="mt-1.5 text-base font-semibold text-[#F5F4F0]">3</p>
                  <p className="mt-1 text-[11px] text-[#8A8880]">needs review</p>
                </div>
              </div>
            </div>

            <div className="rounded-[18px] border border-[#2A2A26] bg-[#141412] p-3">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8A8880]">
                    Verification Timeline
                  </p>
                  <p className="mt-1.5 text-[13px] text-[#8A8880]">
                    Independent checks evaluate each action before the run can be trusted.
                  </p>
                </div>
                <div className="rounded-full border border-[#2A2A26] px-2 py-1 font-mono text-[10px] text-[#8A8880]">
                  run vf_2048
                </div>
              </div>

              <div className="mt-3 space-y-2.5">
                <div className="flex items-start gap-2.5 rounded-xl border border-[#2A2A26] bg-[#10100E] px-3 py-2.5">
                  <span className="mt-1 h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_16px_rgba(74,222,128,0.55)]" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-[13px] font-medium text-[#F5F4F0]">Open repository settings</p>
                      <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-300">
                        verified
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] leading-5 text-[#8A8880]">
                      Deterministic browser verifier confirmed the expected settings panel.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 rounded-xl border border-[#2A2A26] bg-[#10100E] px-3 py-2.5">
                  <span className="mt-1 h-2 w-2 rounded-full bg-amber-300 shadow-[0_0_16px_rgba(252,211,77,0.4)]" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-[13px] font-medium text-[#F5F4F0]">Commit policy update</p>
                      <span className="rounded-full bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] text-amber-200">
                        retry
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] leading-5 text-[#8A8880]">
                      Judge requested another pass after low-confidence evidence from the executor.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 rounded-xl border border-[#2A2A26] bg-[#10100E] px-3 py-2.5">
                  <span className="mt-1 h-2 w-2 rounded-full bg-[#C8A882] shadow-[0_0_18px_rgba(200,168,130,0.5)] animate-pulse" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-[13px] font-medium text-[#F5F4F0]">Update billing notification</p>
                      <span className="rounded-full bg-[#C8A882]/10 px-2 py-0.5 font-mono text-[10px] text-[#E8D5BF]">
                        escalated
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] leading-5 text-[#8A8880]">
                      Human reviewer sees the full action log, screenshots, and ledger trail before approval.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-[18px] border border-[#2A2A26] bg-[#141412] p-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8A8880]">
                Evidence Panel
              </p>
              <div className="mt-3 rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[13px] font-medium text-[#F5F4F0]">DOM assertions</p>
                  <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-300">
                    pass
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] leading-5 text-[#8A8880]">
                  Selector matched expected text and role attributes after navigation settled.
                </p>
              </div>
              <div className="mt-2.5 rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[13px] font-medium text-[#F5F4F0]">Judge rationale</p>
                  <span className="rounded-full bg-[#C8A882]/10 px-2 py-0.5 font-mono text-[10px] text-[#E8D5BF]">
                    hybrid
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] leading-5 text-[#8A8880]">
                  Claimed success conflicts with screenshot state. Escalating with evidence bundle attached.
                </p>
              </div>
            </div>

            <div className="rounded-[18px] border border-[#2A2A26] bg-[#141412] p-3">
              <div className="flex items-center justify-between gap-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8A8880]">
                  Reliability Score
                </p>
                <span className="text-[13px] font-semibold text-[#F5F4F0]">94%</span>
              </div>
              <div className="mt-3 h-2 rounded-full bg-[#1B1B18]">
                <div className="h-2 rounded-full bg-[linear-gradient(90deg,#C8A882,#E6D2BA)] shadow-[0_0_20px_rgba(200,168,130,0.28)]" style={{ width: '94%' }} />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2.5">
                <div className="rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                  <p className="font-mono text-[10px] text-[#8A8880]">false positives</p>
                  <p className="mt-1.5 text-[13px] font-semibold text-[#F5F4F0]">1.8%</p>
                </div>
                <div className="rounded-xl border border-[#2A2A26] bg-[#10100E] p-2.5">
                  <p className="font-mono text-[10px] text-[#8A8880]">review queue</p>
                  <p className="mt-1.5 text-[13px] font-semibold text-[#F5F4F0]">3 tasks</p>
                </div>
              </div>
            </div>

            <div className="rounded-[18px] border border-[#2A2A26] bg-[#141412] p-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8A8880]">
                Ledger Trace
              </p>
              <div className="mt-3 space-y-2 font-mono text-[10px] text-[#8A8880]">
                <div className="flex items-center justify-between rounded-lg border border-[#2A2A26] bg-[#10100E] px-3 py-2">
                  <span>task.created</span>
                  <span className="text-[#F5F4F0]">09:12:04</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-[#2A2A26] bg-[#10100E] px-3 py-2">
                  <span>verification.pass</span>
                  <span className="text-[#F5F4F0]">09:12:18</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-[#2A2A26] bg-[#10100E] px-3 py-2">
                  <span>escalation.created</span>
                  <span className="text-[#F5F4F0]">09:13:42</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const navLinks = [
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Features', href: '#features' },
  { label: 'Demo', href: '#demo' },
  { label: 'Use Cases', href: '#use-cases' },
]

const steps = [
  {
    number: '01',
    title: 'Plan',
    body: 'VerifyFlow breaks your goal into discrete, verifiable tasks — each with explicit success criteria and a defined tool.',
  },
  {
    number: '02',
    title: 'Execute & Judge',
    body: 'An executor agent attempts each task. An independent judge verifies the result using deterministic checks, LLM reasoning, or both.',
  },
  {
    number: '03',
    title: 'Escalate',
    body: 'When confidence is low, the task routes to a human reviewer with full evidence attached. Nothing slips through unchecked.',
  },
]

const features = [
  {
    title: 'Domain-Agnostic Verification',
    body: 'Works with any agent and any task type. Browser actions, file operations, GitHub commits — all verifiable.',
    icon: <SearchIcon />,
  },
  {
    title: 'Hybrid Judge Engine',
    body: 'Combines deterministic rules with LLM reasoning. Confidence scores on every verification decision.',
    icon: <ScaleIcon />,
  },
  {
    title: 'Immutable Ledger',
    body: 'Every claim and verification is recorded permanently. Full audit trail from task creation to final outcome.',
    icon: <ListIcon />,
  },
  {
    title: 'Human Escalation',
    body: 'Low-confidence tasks route to a human review queue with full evidence. Approve, reject, or send back for retry.',
    icon: <UsersIcon />,
  },
  {
    title: 'Benchmark Suites',
    body: 'Run structured test suites to measure false positive and negative rates across agent configurations.',
    icon: <BarChartIcon />,
  },
  {
    title: 'Real-time Streaming',
    body: 'Watch task execution live via SSE. Status updates pushed to the dashboard as they happen.',
    icon: <ZapIcon />,
  },
]

export default function HomePage() {
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10)
    }

    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className="min-h-screen bg-[#0A0A08] text-[#F5F4F0] selection:bg-[#C8A882]/30 selection:text-[#F5F4F0]">
      <nav
        className={`sticky top-0 z-50 transition-all duration-300 ${
          isScrolled
            ? 'border-b border-white/10 bg-[rgba(10,10,8,0.78)] shadow-[0_18px_60px_-40px_rgba(0,0,0,0.9)] backdrop-blur-xl'
            : 'border-b border-transparent bg-transparent'
        }`}
      >
        <div className="w-full px-3 sm:px-5 lg:px-6 xl:px-8">
          <div className="grid h-[72px] grid-cols-[auto_1fr_auto] items-center gap-4">
            <Wordmark />

            <div className="hidden justify-center lg:flex">
              <div className="flex items-center gap-1 rounded-full border border-[#24241F] bg-[rgba(20,20,18,0.62)] px-2 py-1 shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset] backdrop-blur-md">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-full px-4 py-2 text-sm text-[#8A8880] transition-all hover:bg-[#171714] hover:text-[#F5F4F0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8A882]/70"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 sm:gap-3">
              <Link
                href="/auth/login"
                className="rounded-full border border-transparent px-4 py-2 text-sm font-medium text-[#B1AEA4] transition-all hover:border-[#2A2A26] hover:bg-[#141412] hover:text-[#F5F4F0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8A882]/70"
              >
                Sign in
              </Link>
              <Link
                href="/auth/login"
                className="rounded-full bg-[#C8A882] px-5 py-2.5 text-sm font-semibold text-[#0A0A08] shadow-[0_12px_30px_-18px_rgba(200,168,130,0.7)] transition-all hover:bg-[#D4B592] hover:shadow-[0_18px_38px_-18px_rgba(200,168,130,0.8)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F0DCC6]"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <section
        className="relative overflow-hidden"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(200,168,130,0.14), transparent)',
        }}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(200,168,130,0.35),transparent)]" />
        <div className="absolute inset-x-0 bottom-0 h-28 bg-[linear-gradient(180deg,transparent,rgba(10,10,8,0.78))]" />
        <div className="mx-auto grid min-h-[calc(100svh-72px)] max-w-7xl items-center gap-5 px-6 py-5 sm:py-6 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)] lg:gap-6 lg:px-8 xl:gap-8">
          <div className="max-w-2xl text-left lg:self-center">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#2A2A26] bg-[rgba(20,20,18,0.78)] px-3 py-1.5 text-xs font-mono text-[#8A8880] shadow-[0_0_0_1px_rgba(255,255,255,0.02)_inset]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#C8A882]" />
              AI Agent Verification Infrastructure
            </div>

            <h1 className="max-w-[12ch] text-[clamp(3.5rem,6vw,5.75rem)] font-semibold leading-[0.96] tracking-[-0.04em] text-[#F5F4F0]">
              Trust What Your Agents <span className="text-[#C8A882]">Actually</span> Do.
            </h1>

            <p className="mt-4 max-w-xl text-[17px] leading-7 text-[#9A988F] sm:text-[18px]">
              VerifyFlow independently verifies whether AI agents completed their tasks, not just whether they claimed to. Every action becomes evidence.
            </p>

            <div className="mt-6 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
              <Link
                href="/auth/login"
                className="inline-flex items-center justify-center rounded-2xl bg-[#C8A882] px-6 py-3 text-sm font-semibold text-[#0A0A08] shadow-[0_18px_50px_-24px_rgba(200,168,130,0.8)] transition-all hover:-translate-y-0.5 hover:bg-[#D4B592] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F0DCC6]"
              >
                Start Verifying →
              </Link>
              <p className="font-mono text-xs text-[#8A8880]">
                Free · No credit card · Google sign-in
              </p>
            </div>

            <div className="mt-6 grid max-w-xl gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-[#2A2A26] bg-[rgba(20,20,18,0.72)] p-3.5 shadow-[0_18px_60px_-50px_rgba(0,0,0,0.9)]">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#8A8880]">
                  verify
                </p>
                <p className="mt-2 text-sm font-medium text-[#F5F4F0]">Independent checks</p>
              </div>
              <div className="rounded-2xl border border-[#2A2A26] bg-[rgba(20,20,18,0.72)] p-3.5 shadow-[0_18px_60px_-50px_rgba(0,0,0,0.9)]">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#8A8880]">
                  audit
                </p>
                <p className="mt-2 text-sm font-medium text-[#F5F4F0]">Immutable evidence trail</p>
              </div>
              <div className="rounded-2xl border border-[#2A2A26] bg-[rgba(20,20,18,0.72)] p-3.5 shadow-[0_18px_60px_-50px_rgba(0,0,0,0.9)]">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#8A8880]">
                  recover
                </p>
                <p className="mt-2 text-sm font-medium text-[#F5F4F0]">Retry or escalate safely</p>
              </div>
            </div>
          </div>

          <div className="relative flex items-center justify-center lg:justify-end">
            <div className="absolute -right-10 top-8 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.18),transparent_68%)] blur-3xl" />
            <div className="absolute -left-10 bottom-8 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(80,80,75,0.22),transparent_70%)] blur-3xl" />
            <div className="w-full max-w-[288px] sm:max-w-[316px] lg:max-w-[324px] xl:max-w-[348px]">
              <ProductMockup />
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="scroll-mt-28 border-t border-[#2A2A26] bg-[linear-gradient(180deg,rgba(14,14,13,0.96),rgba(10,10,8,1))] px-6 py-24 sm:py-28">
        <div className="mx-auto max-w-4xl">
          <p className="mb-3 text-center font-mono text-xs uppercase tracking-widest text-[#C8A882]">
            How It Works
          </p>
          <h2 className="text-center text-3xl font-semibold tracking-tight text-[#F5F4F0] sm:text-4xl">
            Claim. Verify. Trust.
          </h2>
          <p className="mx-auto mb-14 mt-4 max-w-xl text-center text-sm leading-7 text-[#8A8880] sm:text-[15px]">
            VerifyFlow introduces an independent verification layer between what your agent says it did and what it actually did.
          </p>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            {steps.map((step) => (
              <article
                key={step.number}
                className="rounded-2xl border border-[#2A2A26] bg-[linear-gradient(180deg,rgba(22,22,20,0.96),rgba(16,16,15,0.98))] p-6 shadow-[0_20px_70px_-56px_rgba(0,0,0,0.95)] transition-colors hover:border-[#38342E]"
              >
                <p className="mb-4 font-mono text-xs text-[#C8A882]">{step.number}</p>
                <h3 className="mb-2 text-base font-semibold tracking-tight text-[#F5F4F0]">{step.title}</h3>
                <p className="text-sm leading-6 text-[#8A8880]">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <div id="use-cases" className="scroll-mt-28" />
      <section id="features" className="scroll-mt-28 border-t border-[#2A2A26] px-6 py-24 sm:py-28">
        <div className="mx-auto max-w-6xl">
          <p className="text-center font-mono text-xs uppercase tracking-[0.22em] text-[#C8A882]">
            Built for Production
          </p>
          <h2 className="mt-4 text-center text-4xl font-semibold tracking-tight text-[#F5F4F0] sm:text-5xl">
            Everything you need to trust AI output.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-center text-base leading-7 text-[#9A988F] sm:text-lg">
            Verification, judgment, escalation, and auditability in one reliability layer for agentic workflows.
          </p>
          <div className="mt-16 grid grid-cols-1 gap-5 md:gap-6 xl:grid-cols-3">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="group rounded-[24px] border border-[#2E2E29] bg-[linear-gradient(180deg,rgba(24,24,22,0.98),rgba(18,18,17,0.98))] p-6 shadow-[0_24px_80px_-56px_rgba(0,0,0,0.95),0_0_0_1px_rgba(255,255,255,0.02)_inset] transition-all duration-300 hover:-translate-y-1 hover:border-[#4A4338] hover:shadow-[0_28px_90px_-52px_rgba(0,0,0,0.95),0_0_0_1px_rgba(255,255,255,0.03)_inset] sm:p-7"
              >
                <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl border border-[#3A332B] bg-[rgba(200,168,130,0.12)] shadow-[0_0_30px_rgba(200,168,130,0.08)] transition-colors duration-300 group-hover:bg-[rgba(200,168,130,0.16)]">
                  {feature.icon}
                </div>
                <h3 className="mb-3 text-lg font-semibold tracking-tight text-[#F5F4F0]">
                  {feature.title}
                </h3>
                <p className="text-[15px] leading-7 text-[#9A988F]">{feature.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="scroll-mt-28 border-t border-[#2A2A26] bg-[linear-gradient(180deg,rgba(10,10,8,1),rgba(14,14,13,0.96))] px-6 py-24 sm:py-28">
        <div className="mx-auto max-w-4xl rounded-[28px] border border-[#2A2A26] bg-[linear-gradient(180deg,rgba(20,20,18,0.96),rgba(14,14,13,0.96))] p-8 shadow-[0_30px_90px_-60px_rgba(0,0,0,0.9)] md:p-10">
          <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-start">
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-[#C8A882]">
                Pricing
              </p>
              <h2 className="mt-3 text-3xl font-semibold text-[#F5F4F0]">
                Start free while you prove the workflow.
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-[#8A8880]">
                Begin with Google sign-in, run your first verification flows, and evaluate claimed-vs-verified reliability before you expand usage.
              </p>
            </div>
            <div className="rounded-2xl border border-[#2A2A26] bg-[#10100E] p-5 shadow-[0_22px_70px_-56px_rgba(0,0,0,0.95)]">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#8A8880]">
                Launch offer
              </p>
              <p className="mt-3 text-3xl font-semibold text-[#F5F4F0]">Free</p>
              <p className="mt-1 text-sm text-[#8A8880]">
                No credit card required to get your first dashboard live.
              </p>
              <Link
                href="/auth/login"
                className="mt-6 inline-flex rounded-xl bg-[#C8A882] px-5 py-3 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592]"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-2xl border-t border-[#2A2A26] px-6 py-24 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-[#C8A882]">Launch</p>
        <h2 className="text-4xl font-semibold tracking-tight text-[#F5F4F0]">
          Ready to verify your agents?
        </h2>
        <p className="mt-4 text-base text-[#8A8880]">
          Sign in with Google and launch your first verification run in minutes.
        </p>
        <Link
          href="/auth/login"
          className="mt-8 inline-flex rounded-xl bg-[#C8A882] px-6 py-3 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592]"
        >
          Get Started Free →
        </Link>
      </section>

      <footer className="border-t border-[#2A2A26] px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col gap-8 rounded-[28px] border border-[#23231F] bg-[linear-gradient(180deg,rgba(18,18,16,0.94),rgba(12,12,11,0.98))] px-6 py-8 shadow-[0_24px_80px_-56px_rgba(0,0,0,0.95),0_0_0_1px_rgba(255,255,255,0.02)_inset] sm:px-8">
            <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-md">
                <Wordmark />
                <p className="mt-4 text-sm leading-7 text-[#9A988F]">
                  Independent verification for AI agent execution. Evidence over claims.
                </p>
              </div>

              <div className="grid gap-6 sm:grid-cols-[auto_auto] sm:items-start sm:gap-10">
                <nav
                  aria-label="Footer"
                  className="flex flex-col gap-3 text-sm text-[#8A8880] sm:items-end"
                >
                  {navLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="transition-colors hover:text-[#F5F4F0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8A882]/70"
                    >
                      {link.label}
                    </Link>
                  ))}
                </nav>

                <div className="sm:text-right">
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#8A8880]">
                    Follow
                  </p>
                  <a
                    href="https://github.com/your-org/verifyflow"
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-2 rounded-full border border-[#2A2A26] bg-[#141412] px-4 py-2 text-sm text-[#F5F4F0] transition-all hover:-translate-y-0.5 hover:border-[#3A332B] hover:bg-[#191916] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C8A882]/70"
                  >
                    <GitHubIcon />
                    GitHub
                  </a>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-[#23231F] pt-5 text-xs text-[#7F7D75] sm:flex-row sm:items-center sm:justify-between">
              <p>© 2025 VerifyFlow. Trust what your agents actually do.</p>
              <p className="font-mono">GitHub link ready for your production repository URL.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
