// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';
import remarkDirective from 'remark-directive';
import { remarkCallouts } from './src/plugins/remark-callouts.mjs';

export default defineConfig({
  site: 'https://techlog.ta-yan.ai',
  trailingSlash: 'ignore',
  build: {
    format: 'directory',
  },
  integrations: [sitemap()],
  markdown: {
    remarkPlugins: [remarkDirective, remarkCallouts],
    shikiConfig: {
      theme: 'github-light',
      wrap: true,
    },
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
