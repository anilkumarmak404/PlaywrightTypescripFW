import { Locator, Page } from "@playwright/test";

export class Dashboardpage {
    readonly page: Page;
    readonly dashboardHeader: Locator;
    constructor(page: Page) {
        this.page = page;
        this.dashboardHeader = page.getByRole('heading', { name: 'Dashboard' });
    }
}