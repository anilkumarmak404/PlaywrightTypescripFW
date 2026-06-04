
import { Page, Locator } from '@playwright/test';

export class Loginpage {
    readonly page: Page;
    readonly userNameInput: Locator;
    readonly passwordInput: Locator;
    readonly loginButton: Locator;
    readonly invalidCredentailErrorPopup: Locator
    constructor(page: Page) {
        this.page = page;
        this.userNameInput = page.locator('input[name="username"]')
        this.passwordInput = page.locator('input[name="password"]')
        this.loginButton = page.locator('button[type="submit"]')
        this.invalidCredentailErrorPopup = page.locator('[class*="oxd-alert-content--error"]')

    }
    /**
     * Login to oraneHRM url
     */
    async gotoOrangeHRM() {
        await this.page.goto(`${process.env.BASE_URL}/web/index.php/auth/login`, {
            waitUntil: 'commit',
            timeout: 90000
        });
        await this.userNameInput.waitFor();

    }
    /**
     * 
     * @param userName 
     * @param password 
     */
    async loginToOranageHRM(userName: string, password: string) {
        await this.userNameInput.fill(userName);
        await this.passwordInput.fill(password);
        await this.loginButton.click();
    }


}
