import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string().default(''),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    categories: z.array(z.string()).default([]),
    image: z.string().optional(),
    wpId: z.number().optional(),
    draft: z.boolean().default(false),
    affiliate: z.boolean().default(false),
    // 関連記事(手動指定)。他の記事のファイル名(拡張子なし)を並べる。
    // 未指定なら「前後の記事」ナビだけが表示される
    related: z.array(z.string()).default([]),
  }),
});

const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: z.object({
    title: z.string(),
    description: z.string().default(''),
    pubDate: z.coerce.date().optional(),
  }),
});

export const collections = { blog, pages };
