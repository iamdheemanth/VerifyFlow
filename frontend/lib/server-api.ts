import 'server-only'

import { getServerSession } from 'next-auth'
import { type JWT } from 'next-auth/jwt'

import { authOptions, encodeAuthToken } from '@/lib/auth'
import type {
  BenchmarkOverview,
  ConfigurationComparison,
  ReliabilityOverview,
  Run,
  RunSummary,
} from '@/types/run'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api'

async function getServerAuthHeaders(): Promise<HeadersInit> {
  const session = await getServerSession(authOptions)
  const secret = process.env.NEXTAUTH_SECRET

  if (!session?.user?.id || !secret) {
    return {}
  }

  const token = await encodeAuthToken({
    secret,
    token: {
      sub: session.user.id,
      id: session.user.id,
      email: session.user.email ?? undefined,
      name: session.user.name ?? undefined,
      picture: session.user.image ?? undefined,
    } as JWT,
  })

  return { Authorization: `Bearer ${token}` }
}

async function serverRequest<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: await getServerAuthHeaders(),
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export const serverApi = {
  getRuns() {
    return serverRequest<RunSummary[]>('/runs')
  },

  getOverview() {
    return serverRequest<ReliabilityOverview>('/runs/overview')
  },

  getRun(id: string) {
    return serverRequest<Run>(`/runs/${id}`)
  },

  getBenchmarkOverview() {
    return serverRequest<BenchmarkOverview[]>('/benchmarks/overview')
  },

  getConfigurationComparison() {
    return serverRequest<ConfigurationComparison[]>('/configurations/comparison')
  },
}
