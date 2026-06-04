import { test, expect } from '../../fixtures/hooks-fixture'
import loginModuleData from '../../data/ui-data/login-module.data.json';

test.setTimeout(120000);



test.use({
    storageState: {
        cookies: [],
        origins: []
    }
})

test.describe('[Login]  Visual validation Scenarios', {
    tag: ['@ValidLogin']
}, () => {
    test('@id:LOGIN-001 @feature:login @owner:qa-auth @jira:HRM-LOGIN-001 [Login] User can login with valid username and valid password', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ gotourl, loginPage, commonUtils, leftNavigationPage }) => {
        const Password = commonUtils.decryptData(process.env.PASSWORD as string);
        await loginPage.loginToOranageHRM(process.env.USER_NAME as string, Password);
        await expect(leftNavigationPage.orangeHRMLogo).toBeVisible();
        await expect(leftNavigationPage.leftNavigationSidePanelBody).toBeVisible();

    })

    test('@id:LOGIN-002 @feature:login @owner:qa-auth @jira:HRM-LOGIN-002 [Login] User can login with invalid username and invalid password @SMOKE', {
        tag: ['@UAT', '@REGRESSION', '@SMOKE'],
    }, async ({ gotourl, loginPage }) => {
        await loginPage.loginToOranageHRM(loginModuleData.wrong_username, loginModuleData.wrong_password);
        await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
        await expect(loginPage.userNameInput).toBeVisible();
    })
});



test('@id:LOGIN-003 @feature:login @owner:qa-auth @jira:HRM-LOGIN-003 [Login] User can login with invalid password', {
    tag: ['@UAT, @REGRESSION', '@UI'],

}, async ({ gotourl, loginPage }) => {
    const userName = process.env.USER_NAME as string;
    await loginPage.loginToOranageHRM(userName, loginModuleData.wrong_password);
    await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
    await expect(loginPage.userNameInput).toBeVisible();
})
test.describe('[Login] Negative Scenarios', {
    tag: ['@InvalidLogin']
}, () => {
    test('@id:LOGIN-004 @feature:login @owner:qa-auth @jira:HRM-LOGIN-004 [Login] User can login with invalid username', {
        tag: ['@UAT, @REGRESSION', '@UI'],
    }, async ({ gotourl, loginPage, commonUtils }) => {
        const Password = commonUtils.decryptData(process.env.PASSWORD as string);
        await loginPage.loginToOranageHRM(loginModuleData.wrong_username, Password);
        await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
        await expect(loginPage.userNameInput).toBeVisible();
    })
    test('@id:LOGIN-005 @feature:login @owner:qa-auth @jira:HRM-LOGIN-005 [Login] User can login with invalid username and invalid password @SMOKE', {
        tag: ['@UAT', '@REGRESSION', '@SMOKE'],
    }, async ({ gotourl, loginPage }) => {
        await loginPage.loginToOranageHRM(loginModuleData.wrong_username, loginModuleData.wrong_password);
        await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
        await expect(loginPage.userNameInput).toBeVisible();
    })
});
