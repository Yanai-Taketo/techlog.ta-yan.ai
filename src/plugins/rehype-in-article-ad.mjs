/**
 * 記事本文の中盤に AdSense の In-article 広告(ネイティブ・fluid)を1つ挿入する。
 *
 * 方針:
 *  - 十分に長い記事だけを対象にする(短い記事に3枠目を足すとユーザー負担・広告密度の面で不利)
 *  - 挿入位置は本文中盤の見出し(h2)の直前を最優先。段落の切れ目より section の切れ目のほうが
 *    読者の流れを邪魔しないため
 *  - 画像(figure)の直後は避ける。広告が画像の説明と誤認されるのを防ぐ
 *  - 記事冒頭(タイトル下の広告)と記事末尾の広告から一定のブロック数を空ける
 */

const AD_CLIENT = 'ca-pub-9704812408336522';
const AD_SLOT = '7677567045';

/** 挿入対象とする最小の本文ブロック数 */
const MIN_BLOCKS = 12;
/** 冒頭・末尾から空けるブロック数 */
const EDGE_MARGIN = 4;

function adNode() {
  return {
    type: 'element',
    tagName: 'div',
    properties: {
      className: ['ad-slot', 'ad-slot-in-article'],
      'data-pagefind-ignore': '',
    },
    children: [
      {
        type: 'element',
        tagName: 'span',
        properties: { className: ['ad-label'] },
        children: [{ type: 'text', value: 'スポンサーリンク' }],
      },
      {
        type: 'element',
        tagName: 'ins',
        properties: {
          className: ['adsbygoogle'],
          style: 'display:block; text-align:center;',
          'data-ad-layout': 'in-article',
          'data-ad-format': 'fluid',
          'data-ad-client': AD_CLIENT,
          'data-ad-slot': AD_SLOT,
        },
        children: [],
      },
      {
        type: 'element',
        tagName: 'script',
        properties: {},
        children: [
          { type: 'text', value: '(adsbygoogle = window.adsbygoogle || []).push({});' },
        ],
      },
    ],
  };
}

/** そのノード配下に画像が含まれるか(Markdownの画像は <p><img></p> になるため要再帰探索) */
function containsImage(node) {
  if (!node) return false;
  if (node.tagName === 'img') return true;
  return (node.children || []).some((c) => c.type === 'element' && containsImage(c));
}

/** 広告を差し込むインデックスを決める。挿入しない場合は -1 */
function findInsertIndex(blocks) {
  if (blocks.length < MIN_BLOCKS) return -1;

  const lower = EDGE_MARGIN;
  const upper = blocks.length - EDGE_MARGIN;
  if (upper <= lower) return -1;

  const mid = Math.floor(blocks.length / 2);
  const HEADINGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
  // 挿入位置 i は「blocks[i] の直前」を意味する。直前ブロックが
  //  - 画像を含む  … 広告が画像の説明と誤認される
  //  - 見出し      … その見出しが広告のラベルとして誤解される(ポリシー違反)
  // のいずれかなら避ける。どちらも満たせない記事には挿入しない。
  const usable = (i) => {
    if (i <= lower - 1 || i >= upper) return false;
    const prev = blocks[i - 1];
    if (!prev) return false;
    if (HEADINGS.includes(prev.tagName)) return false;
    return !containsImage(prev);
  };

  // 1) 中盤の見出し(h2)の直前。画像の直後になる見出しは候補から外す
  const headings = [];
  for (let i = lower; i < upper; i++) {
    if (blocks[i].tagName === 'h2' && usable(i)) headings.push(i);
  }
  if (headings.length) {
    return headings.reduce((a, b) => (Math.abs(b - mid) < Math.abs(a - mid) ? b : a));
  }

  // 2) 見出しが無ければ中盤のブロック境界
  for (let d = 0; d < blocks.length; d++) {
    for (const i of [mid - d, mid + d]) {
      if (usable(i)) return i;
    }
  }
  return -1;
}

export function rehypeInArticleAd() {
  return (tree, file) => {
    // 記事(src/content/blog)のみ対象。固定ページには広告を入れない
    const path = file?.history?.[0] ?? file?.path ?? '';
    if (!path.replace(/\\/g, '/').includes('/content/blog/')) return;

    const blocks = tree.children.filter((n) => n.type === 'element');
    const target = findInsertIndex(blocks);
    if (target === -1) return;

    const at = tree.children.indexOf(blocks[target]);
    if (at === -1) return;
    tree.children.splice(at, 0, adNode());
  };
}
