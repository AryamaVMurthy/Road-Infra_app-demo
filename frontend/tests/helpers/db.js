import { execSync } from 'child_process'

const DB_CONTAINER = 'spec_requirements-db-1'
const DB_NAME = 'app'
const DB_USER = 'postgres'
const DB_HOST = '172.20.0.2'
const DB_PASSWORD = 'toto'

export const runSql = (sql) => {
  return execSync(
    `docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c "${sql}"`
  )
    .toString()
    .trim()
}

export const getLatestOtp = (email) => {
  return runSql(
    `SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;`
  )
}

export const resetDatabase = () => {
  execSync(
    `export POSTGRES_SERVER=${DB_HOST} POSTGRES_PASSWORD=${DB_PASSWORD} PYTHONPATH=$PYTHONPATH:$(pwd)/../backend && ../venv/bin/python3 ../backend/reset_db.py`,
    { stdio: 'inherit' }
  )
}
