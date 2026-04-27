
import { Page, Locator } from '@playwright/test';

export class Loginpage {
    static userNameInput(): any {
        throw new Error('Method not implemented.');
    }
    readonly page: Page;
    readonly userNameInput: Locator;
    readonly passwordInput: Locator;
    readonly loginButton: Locator;
    readonly invalidCredentailErrorPopup: Locator
    constructor(page: Page) {
        this.page = page;
        this.userNameInput = page.getByRole('textbox', { name: 'Username' })
        this.passwordInput = page.getByRole('textbox', { name: 'Password' })
        this.loginButton = page.getByRole('button', { name: 'Login' })
        this.invalidCredentailErrorPopup = page.locator('[class*="oxd-alert-content--error"]')

    }
    /**
     * Login to oraneHRM url
     */
    async gotoOrangeHRM() {
        await this.page.goto(`${process.env.BASE_URL}/web/index.php/auth/login`);

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