import { getToken } from 'next-auth/jwt'
import { type NextRequest, NextResponse } from 'next/server'

import { serverEnv } from '@/lib/server-env'

export async function GET(req: NextRequest) {
  const token = await getToken({
    req,
    raw: true,
    secret: serverEnv.nextauthSecret,
  })
  if (!token) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  }
  return NextResponse.json({ token })
}
