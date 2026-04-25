import nextEnv from '@next/env'

const { loadEnvConfig } = nextEnv
loadEnvConfig(process.cwd())

const PLACEHOLDER_VALUES = new Set([
  'your-key-here',
  'your-google-client-id',
  'your-google-client-secret',
  'replace-me',
  'change-me',
  'changeme',
  'replace-with-api-url',
  'replace-with-at-least-32-random-characters',
  'replace-with-google-client-id',
  'replace-with-google-client-secret',
])

function requireEnv(name, { minLength, url } = {}) {
  const value = process.env[name]?.trim()
  if (!value) {
    throw new Error(`Missing required environment variable ${name}.`)
  }
  if (PLACEHOLDER_VALUES.has(value.toLowerCase())) {
    throw new Error(`Environment variable ${name} must not use an example placeholder.`)
  }
  if (minLength && value.length < minLength) {
    throw new Error(`Environment variable ${name} must be at least ${minLength} characters long.`)
  }
  if (url) {
    try {
      const parsed = new URL(value)
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        throw new Error('invalid protocol')
      }
    } catch {
      throw new Error(`Environment variable ${name} must be a valid http(s) URL.`)
    }
  }
  return value
}

const isLintCommand =
  process.env.npm_lifecycle_event === 'lint' || process.argv.includes('lint')

if (!isLintCommand) {
  requireEnv('NEXT_PUBLIC_API_URL', { url: true })
  requireEnv('NEXTAUTH_SECRET', { minLength: 32 })
  requireEnv('GOOGLE_CLIENT_ID')
  requireEnv('GOOGLE_CLIENT_SECRET')
}

const nextConfig = {};

export default nextConfig;
