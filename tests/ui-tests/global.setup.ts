import { test, expect } from '../../fixtures/hooks-fixture.ts'


test('Global setup for login', async ({ page, loginPage, commonUtils, dashboardPage }) => {
    const decryptedPassword = commonUtils.decryptData(process.env.PASSWORD as string);
    await loginPage.gotoOrangeHRM();
    await loginPage.loginToOranageHRM(process.env.USER_NAME as string, decryptedPassword);
    await page.waitForURL(`${process.env.BASE_URL}/web/index.php/dashboard/index`)
    await expect(dashboardPage.dashboardHeader).toHaveText('Dashboard');
    await page.context().storageState({
        path: './playwright/.auth/auth.json'
    })
})