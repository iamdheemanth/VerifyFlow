import { getServerSession } from 'next-auth'
import { type JWT } from 'next-auth/jwt'
import { NextResponse } from 'next/server'

import { authOptions } from '@/lib/auth'
import { encodeAuthToken } from '@/lib/auth-token'
import { serverEnv } from '@/lib/server-env'

export async function GET() {
  const session = await getServerSession(authOptions)

  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  }

  const token = await encodeAuthToken({
    secret: serverEnv.nextauthSecret,
    token: {
      sub: session.user.id,
      id: session.user.id,
      email: session.user.email ?? undefined,
      name: session.user.name ?? undefined,
      picture: session.user.image ?? undefined,
    } as JWT,
  })

  return NextResponse.json({ token })
}
