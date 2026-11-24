import { type Page, expect, test } from '@playwright/test'
import { totp } from './totp.ts'

// SPEC-005 (protótipo do chat) de ponta a ponta, num browser real, contra a stack
// `kai-e2e` (scripts/e2e.sh). As respostas são simuladas no browser: não há servidor
// de conversa nem modelo. Dados sintéticos.

const EMAIL = requiredEnv('KAI_E2E_EMAIL')
const TOTP_SECRET = requiredEnv('KAI_E2E_TOTP_SECRET')

function requiredEnv(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`${name} não definido: corre o E2E via scripts/e2e.sh.`)
  return value
}

type AxeResult = { violations: { id: string; help: string; nodes: unknown[] }[] }

async function axeViolations(page: Page): Promise<string[]> {
  // axe-core (P-023, só dev) injectado na página real: aqui o contraste é calculado.
  await page.addScriptTag({ path: 'node_modules/axe-core/axe.min.js' })
  const result = await page.evaluate(
    () => (window as unknown as { axe: { run: () => Promise<AxeResult> } }).axe.run(),
  )
  return result.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)
}

test.describe.serial('SPEC-005 protótipo do chat', () => {
  let page: Page

  test.beforeAll(async ({ browser }) => {
    // O AC-02 já usou um código TOTP: espera pela janela seguinte (o mesmo código não serve duas vezes).
    const untilNextWindow = 30_000 - (Date.now() % 30_000) + 500
    await new Promise((resolve) => setTimeout(resolve, untilNextWindow))
    page = await (await browser.newContext()).newPage()
    await page.goto('/')
    await page.getByLabel('Email').fill(EMAIL)
    await page.getByLabel('Código TOTP').fill(totp(TOTP_SECRET))
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  })

  test.afterAll(async () => {
    await page.context().close()
  })

  test('AC-005-01: depois do login, a conversa é a página inicial, com o aviso e o estado em espera', async () => {
    await expect(page.getByRole('heading', { name: 'Conversa' })).toBeVisible()
    await expect(page.getByRole('note')).toContainText('Respostas simuladas')
    await expect(page.getByTestId('status-badge')).toHaveText('Em espera')
  })

  test('AC-005-02: envia e vê a resposta a chegar aos poucos até ficar completa', async () => {
    await page.getByLabel('Mensagem').fill('Olá KAI, estás aí?')
    await page.getByLabel('Mensagem').press('Enter')
    await expect(page.getByTestId('status-badge')).toHaveText('A processar')
    const reply = page.getByTestId('assistant-message').last()
    await expect(reply).toHaveAttribute('data-state', 'streaming')
    await expect(reply.locator('.msg-text')).toBeVisible()
    await expect(reply).toHaveAttribute('data-state', 'done', { timeout: 15_000 })
    await expect(page.getByTestId('status-badge')).toHaveText('Em espera')
    await expect(page.getByLabel('Mensagem')).toBeFocused()
  })

  test('AC-005-04: cancelar a meio mostra Erro com o motivo', async () => {
    await page.getByLabel('Mensagem').fill('Conta-me uma história longa.')
    await page.getByRole('button', { name: 'Enviar' }).click()
    const reply = page.getByTestId('assistant-message').last()
    await expect(reply.locator('.msg-text')).toBeVisible()
    await page.getByRole('button', { name: 'Cancelar' }).click()
    await expect(reply).toHaveAttribute('data-state', 'interrupted', { timeout: 2_000 })
    await expect(page.getByTestId('status-badge')).toContainText('Cancelado')
  })

  test('AC-005-05: o cenário de orçamento excedido mostra o motivo e o trace_id', async () => {
    await page.getByLabel('Cenário simulado').selectOption('budget_exceeded')
    await page.getByLabel('Mensagem').fill('Mais uma.')
    await page.getByRole('button', { name: 'Enviar' }).click()
    const failure = page.getByTestId('turn-error').last()
    await expect(failure).toContainText('Orçamento do turno excedido', { timeout: 5_000 })
    await expect(failure.locator('code')).toHaveText(/^[0-9a-f]{32}$/)
  })

  test('AC-005-08: sem violações axe num browser real, incluindo contraste', async () => {
    expect(await axeViolations(page)).toEqual([])
  })

  test('AC-005-01: as sessões continuam acessíveis pela navegação', async () => {
    await page.getByRole('button', { name: 'Sessões' }).click()
    await expect(page.getByRole('heading', { name: 'As tuas sessões' })).toBeVisible()
  })
})
