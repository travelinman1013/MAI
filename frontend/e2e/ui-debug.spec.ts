import { test, expect } from '@playwright/test'

test.describe('MAI Frontend UI Debug', () => {
  test.beforeEach(async ({ page }) => {
    // Capture all console messages
    page.on('console', msg => {
      const type = msg.type()
      if (type === 'error' || type === 'warning') {
        console.log(`[${type.toUpperCase()}] ${msg.text()}`)
      }
    })

    // Capture page errors
    page.on('pageerror', err => {
      console.log(`[PAGE ERROR] ${err.message}`)
    })
  })

  test('load home page and check for errors', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Take screenshot of initial state
    await page.screenshot({ path: 'e2e/screenshots/01-home.png', fullPage: true })

    // Check sidebar is visible
    const sidebar = page.locator('aside')
    await expect(sidebar).toBeVisible()

    console.log('Home page loaded successfully')
  })

  test('click Settings button in sidebar', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Find and click Settings button
    const settingsBtn = page.locator('button:has-text("Settings")')
    await expect(settingsBtn).toBeVisible()

    console.log('Clicking Settings button...')
    await settingsBtn.click()

    // Wait a bit for dialog to open
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/02-settings-clicked.png', fullPage: true })

    // Check if settings dialog opened
    const settingsDialog = page.locator('[role="dialog"]')
    const isDialogVisible = await settingsDialog.isVisible().catch(() => false)
    console.log(`Settings dialog visible: ${isDialogVisible}`)

    if (isDialogVisible) {
      await page.screenshot({ path: 'e2e/screenshots/03-settings-dialog.png', fullPage: true })
    }
  })

  test('click Analytics button in sidebar', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Find and click Analytics button
    const analyticsBtn = page.locator('button:has-text("Analytics")')
    await expect(analyticsBtn).toBeVisible()

    console.log('Clicking Analytics button...')
    await analyticsBtn.click()

    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/04-analytics-page.png', fullPage: true })

    // Check URL changed
    const url = page.url()
    console.log(`Current URL: ${url}`)
    expect(url).toContain('/analytics')
  })

  test('toggle sidebar', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Find sidebar close button (PanelLeftClose icon)
    const closeBtn = page.locator('button:has([class*="lucide-panel-left-close"])')
    const closeBtnAlt = page.locator('aside button').first()

    console.log('Looking for sidebar toggle button...')

    // Try clicking the close button in the header
    const headerCloseBtn = page.locator('aside .border-b button')
    if (await headerCloseBtn.isVisible()) {
      console.log('Clicking sidebar close button...')
      await headerCloseBtn.click()
      await page.waitForTimeout(300)
      await page.screenshot({ path: 'e2e/screenshots/05-sidebar-closed.png', fullPage: true })

      // Check if sidebar collapsed
      const sidebarWidth = await page.locator('aside').evaluate(el => el.offsetWidth)
      console.log(`Sidebar width after close: ${sidebarWidth}px`)
    }
  })

  test('create new chat', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Find and click New Chat button
    const newChatBtn = page.locator('button:has-text("New Chat")')
    await expect(newChatBtn).toBeVisible()

    console.log('Clicking New Chat button...')
    await newChatBtn.click()

    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/06-new-chat.png', fullPage: true })

    const url = page.url()
    console.log(`URL after new chat: ${url}`)
  })

  test('check provider dropdown in settings', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Open settings
    const settingsBtn = page.locator('button:has-text("Settings")')
    await settingsBtn.click()
    await page.waitForTimeout(500)

    // Look for provider select
    const providerSelect = page.locator('[id="provider"]')
    if (await providerSelect.isVisible()) {
      console.log('Found provider select, clicking...')
      await providerSelect.click()
      await page.waitForTimeout(300)
      await page.screenshot({ path: 'e2e/screenshots/07-provider-dropdown.png', fullPage: true })

      // Check for MLX option
      const mlxOption = page.locator('text=MLX-LM')
      const hasMlx = await mlxOption.isVisible().catch(() => false)
      console.log(`MLX-LM option visible: ${hasMlx}`)
    } else {
      console.log('Provider select not found - settings dialog may not have opened')
      await page.screenshot({ path: 'e2e/screenshots/07-no-provider.png', fullPage: true })
    }
  })
})
