import cryptoJs from 'crypto-js'

export default class commonUtils {
    private secretkey: string;

    constructor() {
        if (process.env.SECRET_KEY) {
            this.secretkey = process.env.SECRET_KEY;
        }
        else {
            throw new Error('please provide secret key while starting execution');
        }
    }
    public encryptData(data: string) {
        const encryptData = cryptoJs.AES.encrypt(data, this.secretkey).toString();
        return encryptData;
    }
    public decryptData(encdata: string) {
        const decryptData = cryptoJs.AES.decrypt(encdata, this.secretkey).toString(cryptoJs.enc.Utf8);
        return decryptData;
    }
}