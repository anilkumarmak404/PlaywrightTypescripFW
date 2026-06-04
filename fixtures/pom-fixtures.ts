import { test as baseTest } from '@playwright/test';
import { Loginpage } from '../pages/Loginpage';
import { Dashboardpage } from '../pages/Dashboardpage';
import { Userpage } from '../pages/Userpage';
import { LeftNavigationpage } from '../pages/LeftNavigationpage';
import { Pimpage } from '../pages/Pimpage';
import { Leavepage } from '../pages/Leavepage';

type pomFixtureType = {
    loginPage: Loginpage;
    dashboardPage: Dashboardpage;
    userPage: Userpage;
    leftNavigationPage: LeftNavigationpage;
    pimPage: Pimpage;
    leavePage: Leavepage;
}

export const test = baseTest.extend<pomFixtureType>({
    loginPage: async ({ page }, use) => {
        await use(new Loginpage(page));
    },
    dashboardPage: async ({ page }, use) => {
        await use(new Dashboardpage(page));
    },
    userPage: async ({ page }, use) => {
        await use(new Userpage(page));
    },
    leftNavigationPage: async ({ page }, use) => {
        await use(new LeftNavigationpage(page));
    },
    pimPage: async ({ page }, use) => {
        await use(new Pimpage(page));
    },
    leavePage: async ({ page }, use) => {
        await use(new Leavepage(page));
    }

});


