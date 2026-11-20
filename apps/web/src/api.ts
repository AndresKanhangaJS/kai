// SPEC-002: a sessão vive num cookie HttpOnly gerido pelo Laravel (Sanctum),
// nunca em localStorage. Todos os pedidos levam `credentials: 'include'`.

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

async function ensureCsrfCookie(): Promise<void> {
  if (readCookie('XSRF-TOKEN')) return
  await fetch(`${API_URL}/sanctum/csrf-cookie`, { credentials: 'include' })
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  await ensureCsrfCookie()

  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')

  const xsrf = readCookie('XSRF-TOKEN')
  if (xsrf) headers.set('X-XSRF-TOKEN', xsrf)

  return fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include' })
}

export type ApiSession = {
  id: string
  ip_address: string | null
  user_agent: string | null
  last_activity: number
  last_authenticated_at: string | null
  current: boolean
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export async function loginWithTotp(email: string, code: string): Promise<void> {
  const response = await apiFetch('/login/totp', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  })

  if (!response.ok) {
    throw new ApiError('Credenciais inválidas.', response.status)
  }
}

export async function loginWithRecoveryCode(email: string, recoveryCode: string): Promise<void> {
  const response = await apiFetch('/login/totp', {
    method: 'POST',
    body: JSON.stringify({ email, recovery_code: recoveryCode }),
  })

  if (!response.ok) {
    throw new ApiError('Credenciais inválidas.', response.status)
  }
}

function base64UrlToBuffer(value: string): ArrayBuffer {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(value.length / 4) * 4, '=')
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}

function bufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * Cerimónia WebAuthn de login por passkey (AC-02a). O browser trata da
 * assinatura com a chave privada do autenticador; o servidor só vê a
 * assertion assinada (`VerifyPasskey`, threat-model T-02/T-03).
 */
export async function loginWithPasskey(): Promise<void> {
  const optionsResponse = await apiFetch('/passkeys/login/options')
  if (!optionsResponse.ok) {
    throw new ApiError('Não foi possível iniciar o login por passkey.', optionsResponse.status)
  }
  const { options } = await optionsResponse.json()

  const publicKey: PublicKeyCredentialRequestOptions = {
    ...options,
    challenge: base64UrlToBuffer(options.challenge),
    allowCredentials: options.allowCredentials?.map((credential: { id: string; type: 'public-key' }) => ({
      ...credential,
      id: base64UrlToBuffer(credential.id),
    })),
  }

  const credential = (await navigator.credentials.get({ publicKey })) as PublicKeyCredential | null
  if (!credential) {
    throw new ApiError('Cerimónia de passkey cancelada.', 0)
  }

  const response = credential.response as AuthenticatorAssertionResponse

  const loginResponse = await apiFetch('/passkeys/login', {
    method: 'POST',
    body: JSON.stringify({
      credential: {
        id: credential.id,
        rawId: bufferToBase64Url(credential.rawId),
        type: credential.type,
        response: {
          clientDataJSON: bufferToBase64Url(response.clientDataJSON),
          authenticatorData: bufferToBase64Url(response.authenticatorData),
          signature: bufferToBase64Url(response.signature),
          userHandle: response.userHandle ? bufferToBase64Url(response.userHandle) : null,
        },
      },
    }),
  })

  if (!loginResponse.ok) {
    throw new ApiError('Passkey não reconhecida.', loginResponse.status)
  }
}

export async function listSessions(): Promise<ApiSession[]> {
  const response = await apiFetch('/api/sessions')
  if (!response.ok) {
    throw new ApiError('Não autenticado.', response.status)
  }
  const body = await response.json()
  return body.data as ApiSession[]
}

export async function revokeSession(id: string): Promise<void> {
  const response = await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' })
  if (!response.ok && response.status !== 404) {
    throw new ApiError('Não foi possível revogar a sessão.', response.status)
  }
}

export async function logout(): Promise<void> {
  await apiFetch('/logout', { method: 'POST' })
}
