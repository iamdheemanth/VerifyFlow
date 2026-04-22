import Link from "next/link";

import RecentRunsList from "@/components/RecentRunsList";
import { serverApi } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await serverApi.getRuns();

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-[#1A1410]">
            Runs
          </h1>
          <p className="text-sm text-[#9C948A] mt-1">
            All verification runs, newest first.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-xl bg-[#1A1410] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#2D2520]"
        >
          New Run
        </Link>
      </div>

      <div className="overflow-hidden rounded-2xl border border-[#E2DAD0] bg-white shadow-sm">
        {runs.length === 0 ? (
          <div className="py-16 text-center">
            <svg
              aria-hidden="true"
              className="mx-auto h-8 w-8 text-[#C8BEB2]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v9A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-9Zm1.5 0L12 12l6.5-4.5"
              />
            </svg>
            <p className="text-sm font-medium text-[#5C5248] mt-3">No runs yet</p>
            <Link
              href="/dashboard"
              className="inline-flex items-center rounded-xl bg-[#1A1410] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#2D2520] mt-5"
            >
              Start your first run →
            </Link>
          </div>
        ) : (
          <div className="p-6">
            <RecentRunsList initialRuns={runs} showViewAllLink={false} />
          </div>
        )}
      </div>
    </div>
  );
}
