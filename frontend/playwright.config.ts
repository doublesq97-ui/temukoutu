import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:120000,workers:1,fullyParallel:false,
  reporter:[['list'],['json',{outputFile:'../artifacts/playwright-results.json'}]],
  use:{baseURL:'http://127.0.0.1:7860',viewport:{width:1440,height:1100},headless:true,
    launchOptions:{channel:'chrome'},screenshot:'only-on-failure',trace:'retain-on-failure'},
  outputDir:'../artifacts/browser-tests'});
