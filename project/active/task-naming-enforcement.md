# PROJECT: タスク命名規則の自動適用

**起票**: 2026-03-31
**期間**: 2026-04-01 〜 2026-04-30
**ステータス**: 進行中（自動実行）
**担当**: agent (自動化基盤)

---

## 目的

Google Tasks で自動再生成される定期タスク（商品管理・労務管理・日客修正など）は、
再生成時に命名規則（`GROUP_CATEGORY_TITLE`）のプレフィックスが付かない状態で作成される。
これを毎日自動検出・修正し、タスク一覧の統一性を維持する。

## 命名規則

```
GROUP_CATEGORY_TITLE

GROUP:  WRK (仕事) / PRV (プライベート)
CATEGORY:
  mngt  管理業務（レポート・入力・締め・確認）
  rsvt  予約・手続き・イベント
  pchs  買い物
  kpcl  家事・キープクリーン
  evnt  イベント・インストアメディア
  fnnc  金融・支払い
  misc  その他
```

## 仕組み

- `scripts/lib/task_sync.py` の `_auto_rename_tasks()` が同期時に自動リネーム
- `scripts/agents/task_sync_runner.py` を `scripts/cron/task_sync_cron.sh` 経由で毎朝6時に実行
- Google Tasks API (PATCH) でタイトルを更新、tasks.json も同時に更新

## crontab

```
0 6 * * * scripts/cron/task_sync_cron.sh
```

## 完了条件

- 4月末時点で、Google Tasks の定期再生成タスクが全て命名規則に沿った状態で維持されている
- 手動リネームが不要な状態が1ヶ月間続く

## ログ

- `drafts/task_sync_YYYY-MM-DD.log` に毎日の実行結果が記録される
- `renamed > 0` の場合、修正されたタスク数が記録される
