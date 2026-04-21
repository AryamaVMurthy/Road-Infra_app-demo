import { execSync } from 'child_process'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const DB_NAME = 'app'
const DB_USER = 'postgres'

let cachedRuntimeContext = null

export const buildDockerHostCandidates = ({
  env = process.env,
  uid = process.getuid?.(),
  pathExists = fs.existsSync,
} = {}) => {
  const candidates = []
  const seen = new Set()

  const addHost = (host) => {
    if (!host || seen.has(host)) return
    seen.add(host)
    candidates.push(host)
  }

  addHost(env.E2E_DOCKER_HOST)
  addHost(env.DOCKER_HOST)

  if (typeof uid === 'number') {
    const rootlessSocketPath = `/run/user/${uid}/docker.sock`
    if (pathExists(rootlessSocketPath)) {
      addHost(`unix://${rootlessSocketPath}`)
    }
  }

  if (pathExists('/var/run/docker.sock')) {
    addHost('unix:///var/run/docker.sock')
  }

  if (candidates.length === 0) {
    throw new Error(
      'Could not resolve a usable Docker host. Set E2E_DOCKER_HOST explicitly or make /var/run/docker.sock available.'
    )
  }

  return candidates
}

export const resolveDockerHost = ({
  env = process.env,
  uid = process.getuid?.(),
  pathExists = fs.existsSync,
  probeDockerHost = (host) => {
    execSync('docker ps --format "{{.Names}}"', {
      env: { ...process.env, ...env, DOCKER_HOST: host },
      stdio: 'pipe',
    })
  },
} = {}) => {
  const failures = []

  for (const host of buildDockerHostCandidates({ env, uid, pathExists })) {
    try {
      probeDockerHost(host)
      return host
    } catch (error) {
      failures.push(`${host}: ${error.message}`)
    }
  }

  throw new Error(
    `Failed to connect to any Docker host for Playwright DB access. Attempts: ${failures.join(' | ')}`
  )
}

const findRepoRoot = () => {
  const fromHelpers = path.resolve(__dirname, '..', '..', '..')
  if (fs.existsSync(path.join(fromHelpers, 'backend', 'reset_db.py'))) return fromHelpers
  const fromCwd = process.cwd()
  if (fs.existsSync(path.join(fromCwd, 'backend', 'reset_db.py'))) return fromCwd
  return path.resolve(fromCwd, '..')
}

const listContainers = (dockerHost, env = process.env) => {
  return execSync('docker ps --format "{{.Names}}"', {
    env: { ...process.env, ...env, DOCKER_HOST: dockerHost },
    stdio: 'pipe',
  })
    .toString()
    .split('\n')
    .map((container) => container.trim())
    .filter(Boolean)
}

export const getDbContainer = ({
  env = process.env,
  dockerHost,
} = {}) => {
  if (env.E2E_DB_CONTAINER) {
    return env.E2E_DB_CONTAINER
  }

  const resolvedDockerHost = dockerHost || resolveDockerHost({ env })
  const containers = listContainers(resolvedDockerHost, env)
  const matchedContainer = containers.find((container) => container.includes('-db-'))
  if (matchedContainer) {
    return matchedContainer
  }

  throw new Error(
    'Could not find a running Docker container matching "*-db-*". Set E2E_DB_CONTAINER explicitly if needed.'
  )
}

const getRuntimeContext = () => {
  if (cachedRuntimeContext) {
    return cachedRuntimeContext
  }

  const dockerHost = resolveDockerHost()
  const repoRoot = process.env.E2E_REPO_ROOT || findRepoRoot()
  const pythonBin = process.env.E2E_PYTHON || path.join(repoRoot, '.venv/bin/python')

  cachedRuntimeContext = {
    dockerHost,
    dbContainer: getDbContainer({ dockerHost }),
    repoRoot,
    pythonBin,
  }
  return cachedRuntimeContext
}

export const runSql = (sql) => {
  const { dockerHost, dbContainer } = getRuntimeContext()
  return execSync(
    `docker exec -i ${dbContainer} psql -v ON_ERROR_STOP=1 -U ${DB_USER} -d ${DB_NAME} -qAt`,
    { input: sql, env: { ...process.env, DOCKER_HOST: dockerHost } }
  )
    .toString()
    .trim()
}

export const resetDatabase = () => {
  const { repoRoot, pythonBin } = getRuntimeContext()
  execSync(
    `cd ${repoRoot} && PYTHONPATH=backend ${pythonBin} backend/reset_db.py`,
    { stdio: 'inherit' }
  )
}

export const getLatestOtp = (email) => {
  return runSql(
    `SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;`
  )
}
