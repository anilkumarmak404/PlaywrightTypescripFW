import { expect, test } from '@playwright/test';
import mockapi from '../../data/api-data/mock-api.data.json';

test.beforeEach(async ({ page }) => {
    await page.route('https://conduit-api.bondaracademy.com/api/tags', async (route) => {
        // const tags = mockapi.tags;
        await route.fulfill({
            body: JSON.stringify(mockapi)
        })

    })
    await page.goto('https://conduit.bondaracademy.com/')



});
test.only('open the psge', async ({ page }) => {

    expect(page).toHaveTitle('Conduit | Practice Test Automation',);
    await page.waitForLoadState('networkidle');
})