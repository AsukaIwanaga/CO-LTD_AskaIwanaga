# ニュース（営業部）

最新ニュースを RSS フィードから取得して表示します。

## ニュースソース

### 日本語
- NHK: `https://www3.nhk.or.jp/rss/news/cat0.xml`
- 朝日新聞: `https://www.asahi.com/rss/asahi/newsheadlines.rdf`

### 英語
- AP: `https://feeds.feedburner.com/APTopHeadlines` (または `https://apnews.com/rss`)
- BBC: `http://feeds.bbci.co.uk/news/rss.xml`
- Reuters: `https://feeds.reuters.com/reuters/topNews`

## フロー

1. ユーザーに「日本語・英語・両方」を確認する
2. 該当するRSSフィードを WebFetch で取得する
3. XMLをパースして最新10件のタイトル・リンクを抽出する
4. 以下のフォーマットで表示する：

```
📰 最新ニュース — YYYY-MM-DD
─────────────────────────
【日本語】
1. [タイトル]
2. [タイトル]
...

【English】
1. [Title]
2. [Title]
...
```

5. ユーザーが番号を指定したら、そのURLのページを WebFetch で取得して内容を要約する

## 注意事項

- RSSのXMLタグから `<title>` と `<link>` を抽出する
- 取得できないフィードはスキップして他のソースで代替する
