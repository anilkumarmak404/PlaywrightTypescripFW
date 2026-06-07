import { Locator, Page } from "@playwright/test";

export class Pimpage {
    readonly page: Page;
    readonly addPimButton: Locator;
    readonly employeeListHeading: Locator;
    readonly addEmployeeHeading: Locator;
    readonly firstNameTextBox: Locator;
    readonly middleNameTextBox: Locator;
    readonly lastNameTextBox: Locator;
    readonly employeeIdTextBox: Locator;
    readonly employeeNameSearchInput: Locator;
    readonly employeeIdSearchInput: Locator;
    readonly searchButton: Locator;
    readonly resetButton: Locator;
    readonly employeeTable: Locator;
    readonly requiredValidation: Locator;
    readonly successToast: Locator;
    readonly formLoader: Locator;
    readonly deleteConfirmButton: Locator;
    readonly cancelDeleteButton: Locator;
    readonly createLoginSwitch: Locator;
    readonly usernameTextBox: Locator;
    readonly passwordTextBoxes: Locator;
    readonly personalDetailsSaveButton: Locator;
    readonly saveButton1: Locator;
    readonly newEmployeeNameHeading: Locator;

    constructor(page: Page) {
        this.page = page;
        this.addPimButton = page.locator('button').filter({ hasText: 'Add' });
        this.employeeListHeading = page.getByRole('heading', { name: 'Employee Information' });
        this.addEmployeeHeading = page.getByRole('heading', { name: 'Add Employee' });
        this.firstNameTextBox = page.locator('input[name="firstName"]');
        this.middleNameTextBox = page.locator('input[name="middleName"]');
        this.lastNameTextBox = page.locator('input[name="lastName"]');
        this.employeeIdTextBox = page.locator(
            'xpath=//label[normalize-space()="Employee Id"]/ancestor::div[contains(@class,"oxd-input-group")]//input'
        );
        this.employeeNameSearchInput = page.locator('input[placeholder="Type for hints..."]').first();
        this.employeeIdSearchInput = page.locator(
            'xpath=//label[normalize-space()="Employee Id"]/ancestor::div[contains(@class,"oxd-input-group")]//input'
        );
        this.searchButton = page.getByRole('button', { name: 'Search' });
        this.resetButton = page.getByRole('button', { name: 'Reset' });
        this.employeeTable = page.locator('.oxd-table, .orangehrm-container').first();
        this.requiredValidation = page.getByText('Required');
        this.successToast = page.locator('.oxd-toast--success');
        this.formLoader = page.locator('.oxd-form-loader');
        this.deleteConfirmButton = page.getByRole('button', { name: 'Yes, Delete' });
        this.cancelDeleteButton = page.getByRole('button', { name: 'No, Cancel' });
        this.createLoginSwitch = page.locator('.oxd-switch-input');
        this.usernameTextBox = page.locator(
            'xpath=//label[normalize-space()="Username"]/ancestor::div[contains(@class,"oxd-input-group")]//input'
        );
        this.passwordTextBoxes = page.locator('input[type="password"]');
        this.personalDetailsSaveButton = page
            .locator('.orangehrm-edit-employee-content')
            .first()
            .locator('button[type="submit"]')
            .first();
        this.saveButton1 = page.locator('button[type="submit"]');
        this.newEmployeeNameHeading = page.locator('div.orangehrm-edit-employee-name');
    }

    private createEmployeeId() {
        return `${Date.now()}`.slice(-7);
    }

    private createUsername() {
        return `pimuser${Date.now().toString().slice(-8)}`;
    }

    async openEmployeeList() {
        const employeeListUrl = `${process.env.BASE_URL}/web/index.php/pim/viewEmployeeList`;

        for (let attempt = 1; attempt <= 3; attempt += 1) {
            if (attempt === 1) {
                await this.page.goto(employeeListUrl, {
                    waitUntil: 'commit',
                    timeout: 90000
                });
            } else {
                await this.page.goto(`${process.env.BASE_URL}/web/index.php/dashboard/index`, {
                    waitUntil: 'commit',
                    timeout: 90000
                });
                await this.page.getByRole('link', { name: 'PIM' }).click();
            }

            try {
                await this.searchButton.waitFor({ timeout: 30000 });
                return;
            } catch (error) {
                if (attempt === 3) {
                    throw error;
                }

                await this.page.waitForTimeout(2000);
            }
        }
    }

    async openAddEmployee() {
        await this.openEmployeeList();
        await this.addPimButton.click();
        await this.firstNameTextBox.waitFor({ timeout: 90000 });
    }

    async addNewEmployee(
        firstName: string,
        middleName: string,
        lastName: string,
        options: { withLogin?: boolean } = {}
    ) {
        const employeeId = this.createEmployeeId();

        await this.openAddEmployee();
        await this.firstNameTextBox.fill(firstName);
        await this.middleNameTextBox.fill(middleName);
        await this.lastNameTextBox.fill(lastName);
        await this.employeeIdTextBox.fill(employeeId);

        if (options.withLogin) {
            const password = 'Password123!';
            await this.createLoginSwitch.click();
            await this.usernameTextBox.fill(this.createUsername());
            await this.passwordTextBoxes.nth(0).fill(password);
            await this.passwordTextBoxes.nth(1).fill(password);
        }

        await this.saveButton1.click();
        await this.page.waitForURL('**/web/index.php/pim/viewPersonalDetails/**', { timeout: 90000 });
        await this.firstNameTextBox.waitFor();

        return {
            employeeId,
            firstName,
            middleName,
            lastName,
            fullName: `${firstName} ${middleName} ${lastName}`
        };
    }

    async searchEmployeeById(employeeId: string) {
        await this.openEmployeeList();
        await this.employeeIdSearchInput.fill(employeeId);
        await this.searchButton.click();
        await this.page.getByText(employeeId).first().waitFor({ timeout: 90000 });
    }

    async searchEmployeeByName(name: string) {
        await this.openEmployeeList();
        await this.employeeNameSearchInput.fill(name);
        await this.searchButton.click();
        await this.page.waitForLoadState('networkidle');
    }

    async resetEmployeeFilters(employeeId: string) {
        await this.openEmployeeList();
        await this.employeeIdSearchInput.fill(employeeId);
        await this.resetButton.click();
    }

    async deleteEmployeeById(employeeId: string, confirm = true) {
        await this.searchEmployeeById(employeeId);
        const row = this.page.locator('.oxd-table-row').filter({ hasText: employeeId }).first();
        await row.locator('button').last().click();

        if (confirm) {
            await this.deleteConfirmButton.click();
            await this.successToast.waitFor({ timeout: 90000 });
        } else {
            await this.cancelDeleteButton.click();
        }
    }

    async savePersonalDetails() {
        await this.formLoader.waitFor({ state: 'hidden', timeout: 90000 }).catch(() => undefined);
        await this.personalDetailsSaveButton.click();
        await this.successToast.waitFor({ timeout: 90000 });
    }
}
