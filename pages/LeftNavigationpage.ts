import { Locator, Page } from "@playwright/test";

export class LeftNavigationpage {
    readonly page: Page;
    readonly pimLink: Locator;
    readonly orangeHRMLogo: Locator;
    readonly leftNavigationSidePanelBody: Locator;

    constructor(page: Page) {
        this.page = page;
        this.pimLink = page.locator('[href*="pim/viewPimModule"]');
        this.orangeHRMLogo = page.locator('img[alt="client brand banner"]');
        this.leftNavigationSidePanelBody = page.locator('div.oxd-sidepanel-body');
    }
    async openPimModule() {
        await this.pimLink.click();
    }
}