import { type BrowserContext, type CDPSession, type Page, expect, test } from '@playwright/test'
import { totp } from './totp.ts'

// AC-02 (SPEC-002) de ponta a ponta, num browser real, contra a stack
// `kai-e2e` provisionada por scripts/e2e.sh: owner criado por CLI
// (kai:create-owner) com TOTP activado por CLI (kai:enable-totp).
// Dados sintéticos; o segredo só existe durante a corrida.

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000'
const EMAIL = requiredEnv('KAI_E2E_EMAIL')
const TOTP_SECRET = requiredEnv('KAI_E2E_TOTP_SECRET')
const RECOVERY_CODE = requiredEnv('KAI_E2E_RECOVERY_CODE')
// config/session.php: Str::slug(APP_NAME).'-session' (APP_NAME=Laravel no .env.example).
const SESSION_COOKIE = process.env.E2E_SESSION_COOKIE ?? 'laravel-session'

function requiredEnv(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`${name} não definido: corre o E2E via scripts/e2e.sh.`)
  return value
}

async function sessionsStatus(page: Page): Promise<number> {
  return page.evaluate(async (apiUrl) => {
    const response = await fetch(`${apiUrl}/api/sessions`, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
    return response.status
  }, API_URL)
}

async function loginWithTotp(page: Page, code: string): Promise<void> {
  await page.goto('/')
  await page.getByLabel('Email').fill(EMAIL)
  await page.getByLabel('Código TOTP').fill(code)
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
}

// Virtual Authenticator do Chrome DevTools Protocol: um autenticador de
// plataforma com chaves residentes (passkey "discoverable") e verificação
// do utilizador simulada. A criptografia WebAuthn é real; só o hardware é virtual.
async function addVirtualAuthenticator(
  context: BrowserContext,
  page: Page,
): Promise<{ cdp: CDPSession; authenticatorId: string }> {
  const cdp = await context.newCDPSession(page)
  await cdp.send('WebAuthn.enable')
  const { authenticatorId } = await cdp.send('WebAuthn.addVirtualAuthenticator', {
    options: {
      protocol: 'ctap2',
      transport: 'internal',
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  })
  return { cdp, authenticatorId }
}

test.describe.serial('AC-02 Identity & Access', () => {
  let ownerContext: BrowserContext
  let ownerPage: Page
  let cdp: CDPSession
  let authenticatorId: string

  test.beforeAll(async ({ browser }) => {
    ownerContext = await browser.newContext()
    ownerPage = await ownerContext.newPage()
    ;({ cdp, authenticatorId } = await addVirtualAuthenticator(ownerContext, ownerPage))
  })

  test.afterAll(async () => {
    await ownerContext.close()
  })

  test('AC-02c: um código TOTP inválido não cria sessão', async ({ page }) => {
    const valid = totp(TOTP_SECRET)
    const invalid = ((Number(valid) + 1) % 1_000_000).toString().padStart(6, '0')

    await loginWithTotp(page, invalid)

    await expect(page.getByRole('alert')).toHaveText('Credenciais inválidas.')
    await expect(page.getByRole('heading', { name: 'As tuas sessões' })).toHaveCount(0)
    expect(await sessionsStatus(page)).toBe(401)
  })

  test('AC-02b + T-07: o owner entra com um código TOTP válido; cookie de sessão endurecido e regenerado', async ({
    browser,
  }) => {
    // T-07: cookie de sessão anónimo, obtido antes do login.
    await ownerPage.goto('/')
    await ownerPage.evaluate(async (apiUrl) => {
      await fetch(`${apiUrl}/sanctum/csrf-cookie`, { credentials: 'include' })
    }, API_URL)
    const before = (await ownerContext.cookies(API_URL)).find((cookie) => cookie.name === SESSION_COOKIE)
    expect(before).toBeDefined()

    await loginWithTotp(ownerPage, totp(TOTP_SECRET))

    await expect(ownerPage.getByRole('heading', { name: 'As tuas sessões' })).toBeVisible()
    await expect(ownerPage.getByText('Esta sessão')).toBeVisible()
    expect(await sessionsStatus(ownerPage)).toBe(200)

    // T-07: HttpOnly + SameSite=Lax. "Secure" não é verificável em http://localhost;
    // em produção vem de SESSION_SECURE_COOKIE (HTTPS, M10).
    const cookies = await ownerContext.cookies(API_URL)
    const session = cookies.find((cookie) => cookie.name === SESSION_COOKIE)
    expect(session?.httpOnly).toBe(true)
    expect(session?.sameSite).toBe('Lax')
    // O XSRF-TOKEN é lido pelo SPA por desenho (Sanctum), por isso não é HttpOnly.
    expect(cookies.find((cookie) => cookie.name === 'XSRF-TOKEN')?.httpOnly).toBe(false)

    // T-07 (session fixation): o cookie anónimo de antes do login não ficou autenticado.
    const attacker = await browser.newContext()
    await attacker.addCookies([before!])
    const attackerPage = await attacker.newPage()
    await attackerPage.goto('/')
    expect(await sessionsStatus(attackerPage)).toBe(401)
    await attacker.close()
  })

  test('AC-02a: o owner regista uma passkey e entra com ela', async () => {
    await ownerPage.getByRole('button', { name: 'Registar passkey' }).click()
    await expect(ownerPage.getByRole('status')).toHaveText('Passkey registada. Já podes entrar com ela.')

    const { credentials } = await cdp.send('WebAuthn.getCredentials', { authenticatorId })
    expect(credentials).toHaveLength(1)
    expect(credentials[0].isResidentCredential).toBe(true)

    await ownerPage.getByRole('button', { name: 'Terminar sessão' }).click()
    await expect(ownerPage.getByRole('button', { name: 'Entrar com passkey' })).toBeVisible()
    expect(await sessionsStatus(ownerPage)).toBe(401)

    await ownerPage.getByRole('button', { name: 'Entrar com passkey' }).click()

    await expect(ownerPage.getByRole('heading', { name: 'As tuas sessões' })).toBeVisible()
    expect(await sessionsStatus(ownerPage)).toBe(200)
  })

  test('T-02 + T-03: uma assertion adulterada ou reenviada é rejeitada', async () => {
    await ownerPage.getByRole('button', { name: 'Terminar sessão' }).click()
    await expect(ownerPage.getByRole('button', { name: 'Entrar com passkey' })).toBeVisible()

    // T-02: assinatura adulterada em trânsito → o servidor rejeita.
    await ownerPage.route('**/passkeys/login', async (route) => {
      const request = route.request()
      if (request.method() !== 'POST') return route.continue()
      const body = JSON.parse(request.postData() ?? '{}')
      const signature: string = body.credential.response.signature
      const flipped = signature[10] === 'A' ? 'B' : 'A'
      body.credential.response.signature = signature.slice(0, 10) + flipped + signature.slice(11)
      await route.continue({ postData: JSON.stringify(body) })
    })
    await ownerPage.getByRole('button', { name: 'Entrar com passkey' }).click()
    await expect(ownerPage.getByRole('alert')).toHaveText('Passkey não reconhecida.')
    expect(await sessionsStatus(ownerPage)).toBe(401)
    await ownerPage.unroute('**/passkeys/login')

    // T-03: captura uma assertion válida (login legítimo)…
    let captured: string | null = null
    await ownerPage.route('**/passkeys/login', async (route) => {
      if (route.request().method() === 'POST') captured = route.request().postData()
      await route.continue()
    })
    await ownerPage.getByRole('button', { name: 'Entrar com passkey' }).click()
    await expect(ownerPage.getByRole('heading', { name: 'As tuas sessões' })).toBeVisible()
    await ownerPage.unroute('**/passkeys/login')
    expect(captured).not.toBeNull()

    await ownerPage.getByRole('button', { name: 'Terminar sessão' }).click()
    await expect(ownerPage.getByRole('button', { name: 'Entrar com passkey' })).toBeVisible()

    // …e reenvia-a, mesmo com um challenge novo pedido na sessão → rejeitada.
    const replayStatus = await ownerPage.evaluate(
      async ({ apiUrl, body }) => {
        await fetch(`${apiUrl}/passkeys/login/options`, { credentials: 'include', headers: { Accept: 'application/json' } })
        const xsrf = decodeURIComponent(document.cookie.match(/(?:^|; )XSRF-TOKEN=([^;]*)/)?.[1] ?? '')
        const response = await fetch(`${apiUrl}/passkeys/login`, {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-XSRF-TOKEN': xsrf },
          body,
        })
        return response.status
      },
      { apiUrl: API_URL, body: captured! },
    )
    expect(replayStatus).toBeGreaterThanOrEqual(400)
    expect(await sessionsStatus(ownerPage)).toBe(401)

    // Volta a entrar legitimamente, para o teste seguinte revogar esta sessão.
    await ownerPage.getByRole('button', { name: 'Entrar com passkey' }).click()
    await expect(ownerPage.getByRole('heading', { name: 'As tuas sessões' })).toBeVisible()
    expect(await sessionsStatus(ownerPage)).toBe(200)
  })

  test('AC-02g + AC-02e + AC-02f: noutro browser, entra com código de recuperação e revoga a sessão da passkey', async ({
    browser,
  }) => {
    const otherContext = await browser.newContext()
    const otherPage = await otherContext.newPage()

    await otherPage.goto('/')
    await otherPage.getByLabel('Email').fill(EMAIL)
    await otherPage.getByRole('button', { name: 'Usar código de recuperação' }).click()
    await otherPage.getByLabel('Código de recuperação').fill(RECOVERY_CODE)
    await otherPage.getByRole('button', { name: 'Entrar', exact: true }).click()

    await expect(otherPage.getByRole('heading', { name: 'As tuas sessões' })).toBeVisible()
    const revokeButtons = otherPage.getByRole('button', { name: 'Revogar' })
    await expect(revokeButtons).toHaveCount(1)

    await revokeButtons.click()
    await expect(revokeButtons).toHaveCount(0)

    // AC-02f: a sessão revogada deixa de autenticar pedidos, logo a seguir.
    expect(await sessionsStatus(ownerPage)).toBe(401)
    // A sessão de quem revogou continua válida.
    expect(await sessionsStatus(otherPage)).toBe(200)

    await otherContext.close()
  })
})
