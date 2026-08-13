import { visit } from 'unist-util-visit';

/**
 * remark-directive で解析したディレクティブをHTMLへマッピングする。
 *
 *   :::memo{title="MEMO"} …… 補足(青)      :::alert{title="注意"} …… 注意(黄)
 *   :::box{title="..."}   …… 汎用ボックス   ::linkcard[タイトル]{url="…" site="…" image="…"}
 */
const KNOWN = ['memo', 'alert', 'box', 'linkcard'];

export function remarkCallouts() {
  return (tree) => {
    visit(tree, (node, index, parent) => {
      if (
        node.type !== 'containerDirective' &&
        node.type !== 'leafDirective' &&
        node.type !== 'textDirective'
      ) {
        return;
      }

      // 未定義のディレクティブは文字どおりのテキストに戻す
      // (本文中の「localhost:5000」の「:5000」等がディレクティブとして
      //  誤解釈されリンクや段落が壊れるのを防ぐ)
      if (!KNOWN.includes(node.name)) {
        if (parent && typeof index === 'number') {
          const literal = { type: 'text', value: `:${node.name}` };
          parent.children.splice(index, 1, literal, ...(node.children || []));
        }
        return;
      }

      const data = node.data || (node.data = {});
      const attrs = node.attributes || {};

      if (node.name === 'memo' || node.name === 'alert' || node.name === 'box') {
        data.hName = 'div';
        data.hProperties = { className: ['callout', `callout-${node.name}`] };
        const title = attrs.title;
        if (title) {
          node.children.unshift({
            type: 'paragraph',
            data: { hName: 'p', hProperties: { className: ['callout-title'] } },
            children: [{ type: 'text', value: title }],
          });
        }
        return;
      }

      if (node.name === 'linkcard') {
        const { url = '#', site, image } = attrs;
        const label = node.children.length
          ? node.children
          : [{ type: 'text', value: url }];
        let host = '';
        try {
          host = new URL(url).hostname;
        } catch {
          /* 相対URL等はホスト表示なし */
        }
        data.hName = 'a';
        data.hProperties = {
          href: url,
          className: ['linkcard'],
          target: '_blank',
          rel: 'noopener noreferrer',
        };
        const children = [];
        if (image) {
          children.push({
            type: 'paragraph',
            data: { hName: 'span', hProperties: { className: ['linkcard-thumb'] } },
            children: [{ type: 'image', url: image, alt: '' }],
          });
        }
        const body = [
          {
            type: 'paragraph',
            data: { hName: 'span', hProperties: { className: ['linkcard-title'] } },
            children: label,
          },
        ];
        if (site) {
          body.push({
            type: 'paragraph',
            data: { hName: 'span', hProperties: { className: ['linkcard-site'] } },
            children: [{ type: 'text', value: site }],
          });
        }
        if (host) {
          body.push({
            type: 'paragraph',
            data: { hName: 'span', hProperties: { className: ['linkcard-url'] } },
            children: [{ type: 'text', value: host }],
          });
        }
        children.push({
          type: 'paragraph',
          data: { hName: 'span', hProperties: { className: ['linkcard-body'] } },
          children: body,
        });
        node.children = children;
      }
    });
  };
}
