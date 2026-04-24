import { type JWT } from 'next-auth/jwt'
import { SignJWT, jwtVerify } from 'jose'

function getSecretKey(secret: string) {
  return new TextEncoder().encode(secret)
}

export async function encodeAuthToken({
  secret,
  token,
  maxAge,
}: {
  secret: string
  token?: JWT | null
  maxAge?: number
}) {
  const secretKey = getSecretKey(secret)
  return new SignJWT((token ?? {}) as Record<string, unknown>)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(
      Math.floor(Date.now() / 1000) + (maxAge ?? 30 * 24 * 60 * 60)
    )
    .sign(secretKey)
}

export async function decodeAuthToken({
  secret,
  token,
}: {
  secret: string
  token?: string
}) {
  if (!token) return null

  const secretKey = getSecretKey(secret)

  try {
    const { payload } = await jwtVerify(token, secretKey)
    return payload as JWT
  } catch {
    return null
  }
}
