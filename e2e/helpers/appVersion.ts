import { readFileSync } from 'node:fs'
import path from 'node:path'

/** Read the repo VERSION file (same source as backend runtime). */
export function appVersion(): string {
  const versionFile = path.resolve(__dirname, '..', '..', 'VERSION')
  return readFileSync(versionFile, 'utf-8').trim()
}

/** Escape dots for use in a RegExp that matches the semver string. */
export function versionPattern(version: string): RegExp {
  return new RegExp(version.replace(/\./g, '\\.'))
}
