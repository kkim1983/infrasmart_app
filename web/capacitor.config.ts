import type { CapacitorConfig } from '@capacitor/cli';

const isDev = process.env.NODE_ENV !== 'production';

const config: CapacitorConfig = {
  appId: 'com.infrasmart.app',
  appName: 'InfraSmart',
  webDir: 'out',
  server: isDev
    ? {
        // 개발 시 Next.js dev 서버를 바라봄
        url: 'http://localhost:3000',
        cleartext: true,
      }
    : {
        androidScheme: 'https',
      },
};

export default config;
