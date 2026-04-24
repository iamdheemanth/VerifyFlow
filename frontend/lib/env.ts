const PLACEHOLDER_VALUES = new Set([
  'your-key-here',
  'replace-me',
  'change-me',
  'changeme',
  'replace-with-api-url',
])

function requirePublicEnv(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) {
    throw new Error(`Missing required environment variable ${name}.`)
  }
  if (PLACEHOLDER_VALUES.has(value.toLowerCase())) {
    throw new Error(`Environment variable ${name} must not use an example placeholder.`)
  }
  return value
}

function requirePublicUrl(name: string): string {
  const value = requirePublicEnv(name)
  try {
    const parsed = new URL(value)
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      throw new Error('invalid protocol')
    }
  } catch {
    throw new Error(`Environment variable ${name} must be a valid http(s) URL.`)
  }
  return value.replace(/\/$/, '')
}

export const publicEnv = {
  apiUrl: requirePublicUrl('NEXT_PUBLIC_API_URL'),
}
