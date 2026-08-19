// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';
import remarkDirective from 'remark-directive';
import { remarkCallouts } from './src/plugins/remark-callouts.mjs';
import { rehypeInArticleAd } from './src/plugins/rehype-in-article-ad.mjs';

export default defineConfig({
  site: 'https://techlog.ta-yan.ai',
  trailingSlash: 'ignore',
  build: {
    format: 'directory',
  },
  integrations: [sitemap()],
  markdown: {
    // 記号の自動変換(-- → ダッシュ、' → 曲線引用符)は技術記事のコマンド表記を壊すため無効化
    smartypants: false,
    remarkPlugins: [remarkDirective, remarkCallouts],
    rehypePlugins: [rehypeInArticleAd],
    shikiConfig: {
      theme: 'github-light',
      wrap: true,
    },
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
