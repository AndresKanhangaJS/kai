import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, loginWithPasskey, registerPasskey } from './api'

// Cliente WebAuthn (SPEC-002 AC-02a, T-12): as estruturas binárias têm de ir
// em base64url nos dois sentidos, e cada pedido leva o token CSRF. Sem rede:
// `fetch` e `navigator.credentials` são simulados.

const API_URL = 'http://localhost:8000'

function bytes(...values: number[]): ArrayBuffer {
  return new Uint8Array(values).buffer
}

function asArray(buffer: BufferSource): number[] {
  return Array.from(new Uint8Array(buffer as ArrayBuffer))
}

type Route = { status: number; body?: unknown }

function mockFetch(routes: Record<string, Route>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const path = String(input).replace(API_URL, '')
    const route = routes[path]
    if (!route) throw new Error(`Pedido inesperado: ${path}`)
    return new Response(route.body === undefined ? null : JSON.stringify(route.body), { status: route.status })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function mockCredentials(credentials: Partial<CredentialsContainer>) {
  Object.defineProperty(navigator, 'credentials', { value: credentials, configurable: true })
}

beforeEach(() => {
  // Valor com caracteres codificados: o cliente tem de o descodificar (Sanctum).
  document.cookie = 'XSRF-TOKEN=token%3Dabc; path=/'
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('registerPasskey', () => {
  it('descodifica as opções e envia a attestation em base64url, com o token CSRF', async () => {
    const fetchMock = mockFetch({
      '/user/passkeys/options': {
        status: 200,
        body: {
          options: {
            challenge: 'AQID',
            rp: { id: 'localhost', name: 'KAI' },
            user: { id: 'BAUG', name: 'owner@example.test', displayName: 'Owner' },
            pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
            excludeCredentials: [{ id: 'BwgJ', type: 'public-key' }],
          },
        },
      },
      '/user/passkeys': { status: 200, body: {} },
    })
    const create = vi.fn(async () => ({
      id: 'AQL_',
      rawId: bytes(1, 2, 255),
      type: 'public-key',
      response: {
        clientDataJSON: bytes(10, 11),
        attestationObject: bytes(251, 239),
        getTransports: () => ['internal'],
      },
    }))
    mockCredentials({ create } as unknown as CredentialsContainer)

    await registerPasskey('Passkey de teste')

    const { publicKey } = (create.mock.calls[0] as unknown as [CredentialCreationOptions])[0]
    expect(asArray(publicKey!.challenge)).toEqual([1, 2, 3])
    expect(asArray(publicKey!.user.id)).toEqual([4, 5, 6])
    expect(asArray(publicKey!.excludeCredentials![0].id)).toEqual([7, 8, 9])

    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/user/passkeys'))! as [
      string,
      RequestInit,
    ]
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('include')
    expect(new Headers(init.headers).get('X-XSRF-TOKEN')).toBe('token=abc')
    expect(JSON.parse(String(init.body))).toEqual({
      name: 'Passkey de teste',
      credential: {
        id: 'AQL_',
        // 0x01 0x02 0xFF → "AQL/" em base64 → "AQL_" em base64url, sem padding.
        rawId: 'AQL_',
        type: 'public-key',
        response: { clientDataJSON: 'Cgs', attestationObject: '--8', transports: ['internal'] },
      },
    })
  })

  it('T-12: com o login antigo (423), explica que é preciso voltar a entrar e não inicia a cerimónia', async () => {
    mockFetch({ '/user/passkeys/options': { status: 423, body: { message: 'Password confirmation required.' } } })
    const create = vi.fn()
    mockCredentials({ create } as unknown as CredentialsContainer)

    const error = await registerPasskey('x').catch((err: unknown) => err)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(423)
    expect((error as ApiError).message).toContain('10 minutos')
    expect(create).not.toHaveBeenCalled()
  })

  it('falha com uma mensagem clara se o utilizador cancelar a cerimónia', async () => {
    mockFetch({
      '/user/passkeys/options': {
        status: 200,
        body: { options: { challenge: 'AQID', user: { id: 'BAUG', name: 'o', displayName: 'o' } } },
      },
    })
    mockCredentials({ create: vi.fn(async () => null) } as unknown as CredentialsContainer)

    await expect(registerPasskey('x')).rejects.toThrow('Registo da passkey cancelado.')
  })
})

describe('loginWithPasskey', () => {
  it('envia a assertion em base64url, aceitando userHandle nulo', async () => {
    const fetchMock = mockFetch({
      '/passkeys/login/options': { status: 200, body: { options: { challenge: 'AQID', allowCredentials: [] } } },
      '/passkeys/login': { status: 200, body: {} },
    })
    const get = vi.fn(async () => ({
      id: 'cred',
      rawId: bytes(1, 2, 255),
      type: 'public-key',
      response: {
        clientDataJSON: bytes(10, 11),
        authenticatorData: bytes(1),
        signature: bytes(2),
        userHandle: null,
      },
    }))
    mockCredentials({ get } as unknown as CredentialsContainer)

    await loginWithPasskey()

    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/passkeys/login'))! as [
      string,
      RequestInit,
    ]
    expect(JSON.parse(String(init.body)).credential).toEqual({
      id: 'cred',
      rawId: 'AQL_',
      type: 'public-key',
      response: { clientDataJSON: 'Cgs', authenticatorData: 'AQ', signature: 'Ag', userHandle: null },
    })
  })

  it('rejeita com "Passkey não reconhecida." quando o servidor recusa a assertion', async () => {
    mockFetch({
      '/passkeys/login/options': { status: 200, body: { options: { challenge: 'AQID' } } },
      '/passkeys/login': { status: 422, body: { message: 'invalid' } },
    })
    mockCredentials({
      get: vi.fn(async () => ({
        id: 'cred',
        rawId: bytes(1),
        type: 'public-key',
        response: { clientDataJSON: bytes(1), authenticatorData: bytes(1), signature: bytes(1), userHandle: null },
      })),
    } as unknown as CredentialsContainer)

    await expect(loginWithPasskey()).rejects.toThrow('Passkey não reconhecida.')
  })
})
