import { execSync } from 'child_process'
import path from 'path'

const DB_CONTAINER = process.env.E2E_DB_CONTAINER || 'happy-river-db-1'
const DB_NAME = 'app'
const DB_USER = 'postgres'
const REPO_ROOT = process.env.E2E_REPO_ROOT || path.resolve(process.cwd())
const PYTHON_BIN = process.env.E2E_PYTHON || path.join(REPO_ROOT, '.venv/bin/python')
const DOCKER_HOST = process.env.E2E_DOCKER_HOST || 'unix:///var/run/docker.sock'

export const runSql = (sql) => {
  return execSync(
    `docker exec -i ${DB_CONTAINER} psql -v ON_ERROR_STOP=1 -U ${DB_USER} -d ${DB_NAME} -qAt`,
    { input: sql, env: { ...process.env, DOCKER_HOST } }
  )
    .toString()
    .trim()
}

export const resetDatabase = () => {
  execSync(
    `cd ${REPO_ROOT} && PYTHONPATH=backend ${PYTHON_BIN} backend/reset_db.py`,
    { stdio: 'inherit' }
  )
}

export const getLatestOtp = (email) => {
  return runSql(
    `SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;`
  )
}
