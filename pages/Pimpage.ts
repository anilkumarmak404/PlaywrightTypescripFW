import { Locator, Page } from "@playwright/test";

export class Pimpage {
    readonly page: Page;
    readonly addPimButton: Locator;
    readonly firstNameTextBox: Locator;
    readonly middleNameTextBox: Locator;
    readonly lastNameTextBox: Locator;
    readonly employeeIdTextBox: Locator;
    readonly saveButton1: Locator;
    readonly newEmployeeNameHeading: Locator;

    constructor(page: Page) {
        this.page = page;
        this.addPimButton = page.locator('button').filter({ hasText: 'Add' });
        this.firstNameTextBox = page.locator('input[name="firstName"]');
        this.middleNameTextBox = page.locator('input[name="middleName"]');
        this.lastNameTextBox = page.locator('input[name="lastName"]');
        this.employeeIdTextBox = page.locator(
            'xpath=//label[normalize-space()="Employee Id"]/ancestor::div[contains(@class,"oxd-input-group")]//input'
        );
        this.saveButton1 = page.locator('button[type="submit"]');
        this.newEmployeeNameHeading = page.locator('div.orangehrm-edit-employee-name');
    }

    private createEmployeeId() {
        return `${Date.now()}`.slice(-7);
    }

    async addNewEmployee(firstName: string, middleName: string, lastName: string) {
        await this.page.goto(`${process.env.BASE_URL}/web/index.php/pim/addEmployee`, {
            waitUntil: 'domcontentloaded',
            timeout: 90000
        });
        await this.firstNameTextBox.waitFor();
        await this.firstNameTextBox.fill(firstName);
        await this.middleNameTextBox.fill(middleName);
        await this.lastNameTextBox.fill(lastName);
        await this.employeeIdTextBox.fill(this.createEmployeeId());
        await this.saveButton1.click();
        await this.page.waitForURL('**/web/index.php/pim/viewPersonalDetails/**', { timeout: 90000 });
        await this.firstNameTextBox.waitFor();
    }
}
