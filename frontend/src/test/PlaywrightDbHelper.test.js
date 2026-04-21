/* @vitest-environment node */

import { describe, expect, it } from 'vitest'

import {
  buildDockerHostCandidates,
  resolveDockerHost,
} from '../../tests/helpers/db.js'


describe('Playwright DB helper docker host resolution', () => {
  it('prefers explicit env vars before filesystem sockets', () => {
    const candidates = buildDockerHostCandidates({
      env: {
        E2E_DOCKER_HOST: 'unix:///custom/docker.sock',
        DOCKER_HOST: 'unix:///run/user/1000/docker.sock',
      },
      uid: 1000,
      pathExists: () => true,
    })

    expect(candidates).toEqual([
      'unix:///custom/docker.sock',
      'unix:///run/user/1000/docker.sock',
      'unix:///var/run/docker.sock',
    ])
  })

  it('falls back to /var/run/docker.sock when env docker host is invalid', () => {
    const attemptedHosts = []

    const dockerHost = resolveDockerHost({
      env: {
        DOCKER_HOST: 'unix:///run/user/1000/docker.sock',
      },
      uid: 1000,
      pathExists: (candidatePath) => candidatePath === '/var/run/docker.sock',
      probeDockerHost: (host) => {
        attemptedHosts.push(host)
        if (host === 'unix:///run/user/1000/docker.sock') {
          throw new Error('connect: no such file or directory')
        }
      },
    })

    expect(dockerHost).toBe('unix:///var/run/docker.sock')
    expect(attemptedHosts).toEqual([
      'unix:///run/user/1000/docker.sock',
      'unix:///var/run/docker.sock',
    ])
  })
})
