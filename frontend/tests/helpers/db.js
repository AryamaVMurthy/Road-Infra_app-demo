import { execSync } from 'child_process'

const DB_CONTAINER = 'lucky-panda-db-1'
const DB_NAME = 'app'
const DB_USER = 'postgres'

export const runSql = (sql) => {
  return execSync(
    `docker exec -i ${DB_CONTAINER} psql -v ON_ERROR_STOP=1 -U ${DB_USER} -d ${DB_NAME} -qAt`,
    { input: sql }
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
