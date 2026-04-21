'use client'

import Link from 'next/link'

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

function Wordmark() {
  return (
    <Link href="/" className="inline-flex items-center gap-2 text-[#F5F4F0]">
      <ShieldCheckIcon />
      <span className="text-sm font-semibold tracking-tight text-[#F5F4F0]">
        VerifyFlow
      </span>
    </Link>
  )
}

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
  return (
    <div className="bg-[#0A0A08] min-h-screen text-[#F5F4F0]">
      <nav className="sticky top-0 z-50 border-b border-[#2A2A26] bg-[#0A0A08]/90 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <Wordmark />
          <div className="flex items-center gap-5">
            <Link
              href="/auth/login"
              className="text-sm text-[#8A8880] transition-colors hover:text-[#F5F4F0]"
            >
              Sign in
            </Link>
            <Link
              href="/auth/login"
              className="rounded-lg bg-[#C8A882] px-4 py-1.5 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592]"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <section
        className="relative flex min-h-[calc(100vh-56px)] flex-col items-center justify-center px-6 py-24 text-center"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(200,168,130,0.10), transparent)',
        }}
      >
        <div className="mx-auto max-w-3xl">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-[#2A2A26] bg-[#141412] px-3 py-1 text-xs font-mono text-[#8A8880]">
            AI Agent Verification Infrastructure
          </div>
          <h1 className="text-6xl font-semibold tracking-tight leading-[1.05] text-[#F5F4F0] md:text-7xl">
            Trust What Your Agents <span className="text-[#C8A882]">Actually</span> Do.
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg leading-7 text-[#8A8880]">
            VerifyFlow independently verifies whether AI agents completed their tasks — not just whether they claimed to. Every action becomes evidence.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/auth/login"
              className="rounded-xl bg-[#C8A882] px-6 py-3 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592]"
            >
              Start Verifying →
            </Link>
            <Link
              href="/auth/login"
              className="rounded-xl border border-[#2A2A26] px-6 py-3 text-sm text-[#F5F4F0] transition-colors hover:bg-[#141412]"
            >
              Sign in
            </Link>
          </div>
          <p className="mt-4 font-mono text-xs text-[#8A8880]">
            Free · No credit card · Google sign-in
          </p>
        </div>
      </section>

      <section className="border-t border-[#2A2A26] px-6 py-24">
        <div className="mx-auto max-w-4xl">
          <p className="mb-3 text-center font-mono text-xs uppercase tracking-widest text-[#C8A882]">
            How It Works
          </p>
          <h2 className="text-center text-3xl font-semibold text-[#F5F4F0]">
            Claim. Verify. Trust.
          </h2>
          <p className="mx-auto mb-14 mt-3 max-w-xl text-center text-sm leading-6 text-[#8A8880]">
            VerifyFlow introduces an independent verification layer between what your agent says it did and what it actually did.
          </p>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            {steps.map((step) => (
              <article
                key={step.number}
                className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-6"
              >
                <p className="mb-4 font-mono text-xs text-[#C8A882]">{step.number}</p>
                <h3 className="mb-2 text-base font-semibold text-[#F5F4F0]">{step.title}</h3>
                <p className="text-sm leading-6 text-[#8A8880]">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-[#2A2A26] px-6 py-24">
        <div className="mx-auto max-w-5xl">
          <p className="text-center font-mono text-xs uppercase tracking-widest text-[#C8A882]">
            Built for Production
          </p>
          <h2 className="mt-3 text-center text-3xl font-semibold text-[#F5F4F0]">
            Everything you need to trust AI output.
          </h2>
          <div className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5 transition-colors hover:border-[#3A3A34]"
              >
                <div className="mb-4 flex h-8 w-8 items-center justify-center rounded-lg bg-[rgba(200,168,130,0.12)]">
                  {feature.icon}
                </div>
                <h3 className="mb-1.5 text-sm font-semibold text-[#F5F4F0]">
                  {feature.title}
                </h3>
                <p className="text-sm leading-6 text-[#8A8880]">{feature.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-2xl border-t border-[#2A2A26] px-6 py-24 text-center">
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
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-3">
            <Wordmark />
            <span className="text-xs text-[#8A8880]">© 2025 VerifyFlow</span>
          </div>
          <p className="font-mono text-xs text-[#8A8880]">
            Built with FastAPI · LangGraph · Next.js
          </p>
        </div>
      </footer>
    </div>
  )
}
