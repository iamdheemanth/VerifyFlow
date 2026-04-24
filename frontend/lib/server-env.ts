import 'server-only'

const PLACEHOLDER_VALUES = new Set([
  'your-key-here',
  'your-google-client-id',
  'your-google-client-secret',
  'replace-me',
  'change-me',
  'changeme',
  'replace-with-at-least-32-random-characters',
  'replace-with-google-client-id',
  'replace-with-google-client-secret',
])

function requireServerEnv(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) {
    throw new Error(`Missing required environment variable ${name}.`)
  }
  if (PLACEHOLDER_VALUES.has(value.toLowerCase())) {
    throw new Error(`Environment variable ${name} must not use an example placeholder.`)
  }
  return value
}

function requireSecret(name: string, minLength = 1): string {
  const value = requireServerEnv(name)
  if (value.length < minLength) {
    throw new Error(`Environment variable ${name} must be at least ${minLength} characters long.`)
  }
  return value
}

export const serverEnv = {
  nextauthSecret: requireSecret('NEXTAUTH_SECRET', 32),
  googleClientId: requireServerEnv('GOOGLE_CLIENT_ID'),
  googleClientSecret: requireServerEnv('GOOGLE_CLIENT_SECRET'),
}
