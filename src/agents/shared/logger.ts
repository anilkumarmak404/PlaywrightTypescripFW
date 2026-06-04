export const logger = {
  info: (message: string) => console.log(`[${new Date().toISOString()}] [INFO] ${message}`),
  warn: (message: string) => console.warn(`[${new Date().toISOString()}] [WARN] ${message}`),
  error: (message: string) => console.error(`[${new Date().toISOString()}] [ERROR] ${message}`),
};
