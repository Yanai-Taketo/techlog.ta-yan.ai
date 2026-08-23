import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * CMS(Sveltia)は未入力の項目を「省略」ではなく `''` や `null` として書き出す。
 * スキーマ側でそれを未入力として扱わないと、新規記事の作成時にビルドが落ちる。
 */
const blank = (v: unknown) => (v === '' || v === null ? undefined : v);
const blankTo = <T>(fallback: T) => (v: unknown) => (v === '' || v === null || v === undefined ? fallback : v);

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.preprocess(blankTo(''), z.string()),
    pubDate: z.coerce.date(),
    updatedDate: z.preprocess(blank, z.coerce.date().optional()),
    categories: z.preprocess(blankTo([]), z.array(z.string())),
    image: z.preprocess(blank, z.string().optional()),
    wpId: z.preprocess(blank, z.number().optional()),
    draft: z.preprocess(blankTo(false), z.boolean()),
    // アフィリエイトリンクを含む記事は true。記事冒頭に景表法(ステマ規制)対応の表記が出る
    affiliate: z.preprocess(blankTo(false), z.boolean()),
    // 関連記事(手動指定)。他の記事のファイル名(拡張子なし)を並べる。
    // 未指定なら「前後の記事」ナビだけが表示される
    related: z.preprocess(blankTo([]), z.array(z.string())),
  }),
});

const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: z.object({
    title: z.string(),
    description: z.preprocess(blankTo(''), z.string()),
    pubDate: z.preprocess(blank, z.coerce.date().optional()),
  }),
});

export const collections = { blog, pages };
