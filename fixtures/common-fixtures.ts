import { test as baseTest } from '../fixtures/pom-fixtures';
import CommonUtils from '../utils/commonUtils';

type commonFixtureType = {
    commonUtils: CommonUtils;
}

export const test = baseTest.extend<commonFixtureType>({
    commonUtils: async ({ }, use) => {
        use(new CommonUtils());
    }

});