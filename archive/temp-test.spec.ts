import { expect } from '@playwright/test';
import { test } from '..//fixtures/hooks-fixture';


//SECRET_KEY=Hgv npm run test_demo_ff_hd
//SECRET_KEY=Hgv npm run test_demo_api

// test.beforeEach('before each test', async ({ page, loginPage }) => {
//     await loginPage.gotoOrangeHRM();
// })

// test.afterEach('after each test', async ({ page, userPage }) => {
//     await userPage.logout();
// })
test('temp test', async ({ page, gotourl }) => {
    //SECRET_KEY=Hgv npm run test_demo_ff_hd
    // console.log(process.env.BASE_URL);
    // console.log(process.env.USER_NAME);
    // console.log(process.env.PASSWORD);
    // console.log(commonUtils.encryptData('Admin'));
    // console.log(commonUtils.encryptData('admin123'));
    //commonUtils.decryptData(process.env.PASSWORD as string
    // await loginPage.gotoOrangeHRM();
    console.log(await page.title());
})

test('test2 temp', async ({ page, gotourl }) => {
    // await loginPage.gotoOrangeHRM();
    console.log(await page.title());
})
test('test3 temp', async ({ page, gotourl, logout }) => {
    // await loginPage.gotoOrangeHRM();
    await expect(page).toHaveTitle('OrangeHRM');
})
