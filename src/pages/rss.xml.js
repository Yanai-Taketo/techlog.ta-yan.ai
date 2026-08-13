import rss from '@astrojs/rss';
import { getPublishedPosts } from '../lib/posts';

export async function GET(context) {
  const posts = await getPublishedPosts();
  return rss({
    title: 'テックろぐ',
    description:
      '日々の気づき、パソコン・ネットワークのテクニックやトラブル解決の備忘録を書き留める技術ブログです。',
    site: context.site,
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description,
      pubDate: post.data.pubDate,
      link: `/${post.id}/`,
      categories: post.data.categories,
    })),
    customData: '<language>ja</language>',
  });
}
