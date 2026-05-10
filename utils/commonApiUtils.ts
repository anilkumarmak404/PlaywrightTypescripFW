import { APIRequestContext } from "@playwright/test";
import apiPathData from '../data/api-data/api-path-data.json'
import commonUtils from "./commonUtils";

export default class commonApiUtils {
    private request: APIRequestContext;
    constructor(request: APIRequestContext) {
        this.request = request;
    }

    public async createToken() {
        const commonUtilsobj = new commonUtils()
        const apiUsername = commonUtilsobj.decryptData(process.env.API_USERNAME as string);
        const apiPassword = commonUtilsobj.decryptData(process.env.API_PASSWORD as string);
        const createTokenRes = await this.request.post(apiPathData.auth_path, {
            data: {
                "username": apiUsername,
                "password": apiPassword
            }

        });
        const createTokenResJson = createTokenRes.json();
        console.log(createTokenResJson);
        return createTokenResJson;
    }


}