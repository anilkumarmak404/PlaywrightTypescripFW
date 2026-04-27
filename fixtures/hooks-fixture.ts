import { test as baseTest } from './common-fixtures';

type hooksFixtureType = {
    gotourl: any;
    logout: any;
}

export const test = baseTest.extend<hooksFixtureType>({
    gotourl: async ({ loginPage }: any, use: () => any) => {
        await loginPage.gotoOrangeHRM();
        await use();
    },
    logout: async ({ userPage }: any, use: () => any) => {
        await userPage.logout();
        await use();
    }

})

export { expect } from '@playwright/test';