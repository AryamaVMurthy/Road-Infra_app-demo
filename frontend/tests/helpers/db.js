import { execSync } from 'child_process'

const DB_CONTAINER = 'lucky-panda-db-1'
const DB_NAME = 'app'
const DB_USER = 'postgres'
const DB_HOST = 'localhost'
const DB_PASSWORD = 'toto'

export const runSql = (sql) => {
  return execSync(
    `docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c "${sql}"`
  )
    .toString()
    .trim()
}

export const resetDatabase = () => {
  execSync(
    `docker exec lucky-panda-backend-1 python reset_db.py`,
    { stdio: 'inherit' }
  )
}

export const getLatestOtp = (email) => {
  return runSql(
    `SELECT code FROM otp WHERE email='${email}' ORDER BY created_at DESC LIMIT 1;`
  )
}
