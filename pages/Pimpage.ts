import { Locator, Page, expect } from "@playwright/test";

export class Pimpage {
    readonly page: Page;
    readonly addPimButton: Locator;
    readonly firstNameTextBox: Locator;
    readonly middleNameTextBox: Locator;
    readonly lastNameTextBox: Locator;
    readonly saveButton1: Locator;
    readonly newEmployeeNameHeading: Locator;

    constructor(page: Page) {
        this.page = page;
        this.addPimButton = page.getByRole('button', { name: ' Add' });
        this.firstNameTextBox = page.getByRole('textbox', { name: 'First Name' });
        this.lastNameTextBox = page.getByRole('textbox', { name: 'Last Name' });
        this.middleNameTextBox = page.getByRole('textbox', { name: 'Middle Name' });
        this.saveButton1 = page.locator('button[type="submit"]')
        this.newEmployeeNameHeading = page.locator('div[class="orangehrm-edit-employee-name"]')

    }
    async addNewEmployee(firstName: string, middleName: string, lastName: string) {
        await this.addPimButton.click();
        await this.firstNameTextBox.fill(firstName);
        await this.middleNameTextBox.fill(middleName);
        await this.lastNameTextBox.fill(lastName);
        await this.saveButton1.click();
    }

}