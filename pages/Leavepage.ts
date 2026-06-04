import { Locator, Page } from "@playwright/test";

export class Leavepage {
    readonly page: Page;
    readonly leaveHeader: Locator;
    readonly leaveListHeading: Locator;
    readonly myLeaveHeading: Locator;
    readonly applyLeaveHeading: Locator;
    readonly assignLeaveHeading: Locator;
    readonly leaveTable: Locator;
    readonly leaveTypeDropdown: Locator;
    readonly fromDateInput: Locator;
    readonly toDateInput: Locator;
    readonly commentsTextArea: Locator;
    readonly employeeNameInput: Locator;
    readonly submitButton: Locator;
    readonly resetButton: Locator;
    readonly searchButton: Locator;
    readonly leaveStatusDropdown: Locator;
    readonly noRecordsMessage: Locator;
    readonly noLeaveBalanceMessage: Locator;

    constructor(page: Page) {
        this.page = page;
        this.leaveHeader = page.getByRole('heading', { name: 'Leave', exact: true });
        this.leaveListHeading = page.getByRole('heading', { name: 'Leave List' });
        this.myLeaveHeading = page.getByRole('heading', { name: 'My Leave List' });
        this.applyLeaveHeading = page.getByRole('heading', { name: 'Apply Leave' });
        this.assignLeaveHeading = page.getByRole('heading', { name: 'Assign Leave' });
        this.leaveTable = page.locator('.oxd-table, .orangehrm-container').first();
        this.leaveTypeDropdown = page.locator('.oxd-select-text').first();
        this.fromDateInput = page.locator('.oxd-date-input input').first();
        this.toDateInput = page.locator('.oxd-date-input input').nth(1);
        this.commentsTextArea = page.locator('textarea');
        this.employeeNameInput = page.locator('input[placeholder="Type for hints..."]');
        this.submitButton = page.locator('button[type="submit"]');
        this.resetButton = page.getByRole('button', { name: 'Reset' });
        this.searchButton = page.getByRole('button', { name: 'Search' });
        this.leaveStatusDropdown = page.locator('.oxd-select-text').first();
        this.noRecordsMessage = page.getByText('No Records Found');
        this.noLeaveBalanceMessage = page.getByText('No Leave Types with Leave Balance');
    }

    async openLeaveModule() {
        await this.page.goto(`${process.env.BASE_URL}/web/index.php/leave/viewLeaveList`, {
            waitUntil: 'commit',
            timeout: 90000
        });
        await this.page.getByRole('link', { name: 'Apply' }).waitFor({ timeout: 90000 });
    }

    async openLeaveList() {
        await this.page.goto(`${process.env.BASE_URL}/web/index.php/leave/viewLeaveList`, {
            waitUntil: 'commit',
            timeout: 90000
        });
        await this.searchButton.waitFor({ timeout: 90000 });
    }

    async openMyLeave() {
        await this.openLeaveList();
        await this.page.getByRole('link', { name: 'My Leave' }).click();
        await this.searchButton.waitFor({ timeout: 90000 });
    }

    async openApplyLeave() {
        await this.openLeaveList();
        await this.page.getByRole('link', { name: 'Apply' }).click();
        await this.applyLeaveHeading.waitFor({ timeout: 90000 });
    }

    async openAssignLeave() {
        await this.openLeaveList();
        await this.page.getByRole('link', { name: 'Assign Leave' }).click();
        await this.employeeNameInput.waitFor({ timeout: 90000 });
    }

    async selectFirstDropdownOption(dropdown: Locator) {
        await dropdown.click();
        await this.page.locator('[role="option"]').nth(1).click();
    }

    async searchLeaveListByDateRange(fromDate: string, toDate: string) {
        await this.fromDateInput.waitFor({ timeout: 90000 });
        await this.fromDateInput.fill(fromDate);
        if (await this.toDateInput.count()) {
            await this.toDateInput.fill(toDate);
        }
        await this.searchButton.click();
    }
}
