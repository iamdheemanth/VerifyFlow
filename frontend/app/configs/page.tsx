import Link from "next/link";

import { api } from "@/lib/api";
import type { ConfigurationComparison, ModelPromptConfig } from "@/types/run";

export const dynamic = "force-dynamic";

export default async function ConfigurationsPage() {
  let configs: ModelPromptConfig[] = [];
  let comparison: ConfigurationComparison[] = [];

  try {
    [configs, comparison] = await Promise.all([
      api.getConfigurations(),
      api.getConfigurationComparison(),
    ]);
  } catch {
    configs = [];
    comparison = [];
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f8efe4,transparent_40%),linear-gradient(180deg,#fcfaf6_0%,#f2ede2_100%)] px-6 py-10 text-slate-900 md:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Link href="/dashboard" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          ← Back to dashboard
        </Link>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
          <p className="text-sm uppercase tracking-[0.3em] text-amber-700">Configuration Comparison</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
            Compare prompts and models by verification quality.
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            VerifyFlow treats prompt and model variants as reliability configurations. The point is not playground experimentation, it is measurable improvement in what the system can actually prove.
          </p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-slate-950">Registered Configurations</h2>
              <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                {configs.length}
              </span>
            </div>
            <div className="mt-5 grid gap-3">
              {configs.map((config) => (
                <article key={config.id} className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-base font-semibold text-slate-950">{config.name}</h3>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                      {config.role}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{config.model_name}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-400">
                    Prompt version {config.prompt_version}
                  </p>
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-slate-950">Reliability Comparison</h2>
              <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                {comparison.length} rows
              </span>
            </div>

            <div className="mt-5 overflow-x-auto rounded-[1.5rem] border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Config</th>
                    <th className="px-4 py-3 font-medium">Role</th>
                    <th className="px-4 py-3 font-medium">Runs</th>
                    <th className="px-4 py-3 font-medium">Success</th>
                    <th className="px-4 py-3 font-medium">Escalation</th>
                    <th className="px-4 py-3 font-medium">Confidence</th>
                    <th className="px-4 py-3 font-medium">Avg cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
                  {comparison.map((row) => (
                    <tr key={row.config_id}>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-950">{row.name}</div>
                        <div className="text-xs text-slate-500">{row.model_name}</div>
                      </td>
                      <td className="px-4 py-3 uppercase tracking-wide text-slate-500">{row.role}</td>
                      <td className="px-4 py-3">{row.run_count}</td>
                      <td className="px-4 py-3">{formatPercent(row.success_rate)}</td>
                      <td className="px-4 py-3">{formatPercent(row.escalation_rate)}</td>
                      <td className="px-4 py-3">{formatPercent(row.average_confidence)}</td>
                      <td className="px-4 py-3">${row.average_cost_usd.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}
