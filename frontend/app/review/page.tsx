import Link from "next/link";

import ReviewQueueBoard from "@/components/ReviewQueueBoard";
import { api } from "@/lib/api";
import type { Escalation } from "@/types/run";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  let escalations: Escalation[] = [];
  try {
    escalations = await api.getEscalationQueue();
  } catch {
    escalations = [];
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f8efe4,transparent_40%),linear-gradient(180deg,#fcfaf6_0%,#f2ede2_100%)] px-6 py-10 text-slate-900 md:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Link href="/dashboard" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          ← Back to dashboard
        </Link>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
          <p className="text-sm uppercase tracking-[0.3em] text-amber-700">Human Review</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
            Escalations are where VerifyFlow asks a human to break the tie.
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            The agent never certifies itself. Deterministic checks go first, the adversarial judge looks for failure second, and only then does a human reviewer step in for unresolved ambiguity.
          </p>
        </section>

        <ReviewQueueBoard initialEscalations={escalations} />
      </div>
    </main>
  );
}
