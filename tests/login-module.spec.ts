import { test, expect } from '../fixtures/hooks-fixture';
import loginModuleData from '../data/login-module.data.json';
import process from 'node:process';




test.use({
    storageState: {
        cookies: [],
        origins: []
    }
})

test.describe('[Login]  Visual validation Scenarios', {
    tag: ['@ValidLogin']
}, () => {
    test('[Login] User can login with valid username and valid password', {
        tag: ['@UAT, @REGRESSION', '@VISUAL'],
        annotation: {
            type: "Testcasid-89986",
            description: "Verify user can login with valid username and valid password",
        }
    }, async ({ gotourl, loginPage, commonUtils, leftNavigationPage }) => {
        const Password = commonUtils.decryptData(process.env.PASSWORD as string);
        await loginPage.loginToOranageHRM(process.env.USER_NAME as string, Password);
        await expect(leftNavigationPage.orangeHRMLogo).toHaveScreenshot('orangeHRMLogo.png');
        await expect(leftNavigationPage.leftNavigationSidePanelBody).toHaveScreenshot('leftNavigationPanel.png');

    })

    test('[Login] User can login with invalid username and invalid password', {
        tag: ['@UAT, @REGRESSION', '@SMOKE'],
        annotation: {
            type: "Testcasid-89087",
            description: "Verify user can login with invalid username and invalid password",
        }
    }, async ({ gotourl, loginPage }) => {
        await loginPage.loginToOranageHRM(loginModuleData.wrong_username, loginModuleData.wrong_password);
        await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
        await expect(loginPage.userNameInput).toBeVisible();
    })
});



test('[Login] User can login with invalid password', {
    tag: ['@UAT, @REGRESSION', '@UI'],
    annotation: {
        type: "Testcasid-89089",
        description: "Verify user can login with invalid password",
    }

}, async ({ gotourl, loginPage }) => {
    const userName = process.env.USER_NAME as string;
    await loginPage.loginToOranageHRM(userName, loginModuleData.wrong_password);
    await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
    await expect(loginPage.userNameInput).toBeVisible();
})
test.describe('[Login] Negative Scenarios', {
    tag: ['@InvalidLogin']
}, () => {
    test('[Login] User can login with invalid username', {
        tag: ['@UAT, @REGRESSION', '@UI'],
        annotation: {
            type: "Testcasid-89086",
            description: "Verify user can login with invalid username",
        }
    }, async ({ gotourl, loginPage, commonUtils }) => {
        const Password = commonUtils.decryptData(process.env.PASSWORD as string);
        await loginPage.loginToOranageHRM(loginModuleData.wrong_username, Password);
        await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
        await expect(loginPage.userNameInput).toBeVisible();
    })
    test('[Login] User can login with invalid username and invalid password', {
        tag: ['@UAT, @REGRESSION', '@SMOKE'],
        annotation: {
            type: "Testcasid-89087",
            description: "Verify user can login with invalid username and invalid password",
        }
    }, async ({ gotourl, loginPage }) => {
        await loginPage.loginToOranageHRM(loginModuleData.wrong_username, loginModuleData.wrong_password);
        await expect(loginPage.invalidCredentailErrorPopup).toHaveText(loginModuleData.invalid_credential_text);
        await expect(loginPage.userNameInput).toBeVisible();
    })
});
