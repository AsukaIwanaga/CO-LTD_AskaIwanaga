# 並行実行方式の比較評価

自動ルーチン（morning_auto.py 等）での並行実行方式を比較する。

---

## 方式一覧

### A. Python ThreadPoolExecutor

cron → Python スクリプト内で `concurrent.futures.ThreadPoolExecutor` を使い、
複数の情報収集を並行実行する。

```python
with ThreadPoolExecutor(max_workers=8) as pool:
    weather = pool.submit(fetch_weather)
    stocks  = pool.submit(fetch_stocks)
    mails   = pool.submit(gmail_list_unread)
    ...
# 全部揃ったら Claude Haiku で整形
```

### B. claude -p（非対話 CLI）

cron → `claude -p "プロンプト"` で Claude Code を非対話モードで起動。
内部で Agent ツールが使えるため、並行実行も可能。

```bash
claude -p "朝のブリーフィングを実行して" --allowedTools "Read,Bash,Agent"
```

### C. Claude Agent SDK

cron → Python から Agent SDK を使い、自前でエージェントループを構築。
ツール定義・並行実行を完全に制御可能。

```python
from claude_agent_sdk import query
async for msg in query(prompt="...", options={...}):
    ...
```

### D. Agent ツール（Claude Code セッション内）

Don が手動で `/morning` を実行した時のみ利用可能。
Claude Code 内の Agent ツールで並行取得。

---

## 比較表

| 観点 | A. ThreadPool | B. claude -p | C. Agent SDK | D. Agent ツール |
|------|-------------|-------------|-------------|---------------|
| **実行環境** | cron ✅ | cron ✅ | cron ✅ | 手動のみ ❌ |
| **並行実行** | ✅ スレッド並行 | ✅ Agent 並行 | ✅ 完全制御 | ✅ Agent 並行 |
| **速度** | ◎ 最速（直接API） | ○ Agent起動分の遅延 | ○ SDK起動分の遅延 | ◎ 最速 |
| **API コスト** | ◎ Haiku 1回 $0.02 | ✗ Opus 相当 $0.5〜 | ○ Haiku/Sonnet 選択可 | ◎ なし（CC内） |
| **月額目安** | ~$0.60 | ~$15〜 | ~$1〜5 | $0 |
| **実装難易度** | ◎ 簡単（10行） | ◎ 簡単（1行） | △ 中程度 | ◎ スキル修正のみ |
| **柔軟性** | △ 固定ロジック | ◎ 自然言語で指示 | ◎ ツール定義自由 | ◎ 自然言語 |
| **エラー処理** | ○ try/except | ○ Claude判断 | ○ 自前制御 | ○ Claude判断 |
| **Don との対話** | ✗ 不可 | ✗ 不可（非対話） | ✗ 不可 | ✅ 可能 |
| **ツール追加** | △ コード修正必要 | ◎ プロンプト変更のみ | ○ ツール定義追加 | ◎ プロンプト変更のみ |
| **デバッグ** | ◎ ログ明確 | △ CC内部で不透明 | ○ ログ可能 | ○ 会話で確認 |
| **安定性** | ◎ シンプルで壊れにくい | △ CC起動失敗リスク | ○ SDK依存 | ◎ 安定 |
| **依存関係** | Python標準ライブラリのみ | Claude Code CLI | claude-agent-sdk | Claude Code |

---

## 各方式の詳細評価

### A. Python ThreadPoolExecutor

**メリット:**
- 追加コストが最小（Haiku 1回/日のみ）
- 実装がシンプル（concurrent.futures は Python 標準）
- 外部依存なし（Claude Code や SDK が不要）
- デバッグしやすい（各タスクの成功/失敗が明確）
- 最も安定（ネットワーク障害以外で壊れない）

**デメリット:**
- 情報ソース追加時にコード修正が必要
- ブリーフィング文の生成ロジックが固定的
- Don との対話ができない（完全自動のみ）
- Claude の判断力を活かせない（テンプレート埋め込みのみ）

**適性:** 毎日の定型ルーチン ◎ / 柔軟な判断 △

### B. claude -p（非対話 CLI）

**メリット:**
- プロンプト1つで全てを指示できる（コード不要）
- Agent ツールが使える（並行実行も可能）
- 情報ソース追加がプロンプト変更のみ
- Claude の判断力をフル活用（異常値の解釈等）

**デメリット:**
- コストが高い（Opus モデルが使われる可能性）
- Claude Code の起動自体に10-20秒かかる
- 非対話モードでは Don に質問できない
- Claude Code のバージョンアップで挙動が変わるリスク
- ログが Claude Code 内部に閉じる（外部から追跡しにくい）

**適性:** プロトタイプ・一時利用 ○ / 毎日の定型ルーチン △

### C. Claude Agent SDK

**メリット:**
- ツール定義を自由にカスタマイズ可能
- Haiku/Sonnet をタスクに応じて使い分け可能
- エージェントループを完全に制御
- 将来の LINE Bot（Phase 2）と共通基盤にできる

**デメリット:**
- SDK の学習コスト・実装工数がやや大きい
- SDK のバージョンアップに追従が必要
- エージェントループの挙動が予測しにくい場合がある
- A に比べてコストが高い（複数ターンの API コール）

**適性:** Phase 2（LINE Bot）との統合 ◎ / 単体の定型ルーチン ○

### D. Agent ツール（手動実行）

**メリット:**
- コスト $0（Claude Code サブスクリプション内）
- Don との対話が可能（STEP 4 のアップデート確認）
- 最も柔軟（その場でアドホックな指示が出せる）
- 実装済みのスキルをそのまま活用

**デメリット:**
- Don がターミナルの前にいる必要がある
- 自動実行不可（cron で使えない）
- 起動を忘れるとブリーフィングが来ない

**適性:** 手動のルーチン ◎ / 自動化 ✗

---

## 推奨構成

```
                     ┌─────────────┐
                     │  Don の1日   │
                     └──────┬──────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
    ┌─────▼──────┐  ┌──────▼───────┐  ┌───────▼───────┐
    │ 自動(cron)  │  │ 手動(CC)     │  │ LINE Bot      │
    │ 方式A       │  │ 方式D        │  │ 方式C         │
    │ ThreadPool  │  │ Agent ツール  │  │ Agent SDK     │
    │             │  │              │  │               │
    │ 毎朝5時     │  │ 起床後       │  │ いつでも      │
    │ 定型収集    │  │ 対話的確認    │  │ 自然言語指示  │
    │ メール通知  │  │ STEP 4       │  │               │
    │ $0.02/日    │  │ $0           │  │ $0.02/対話    │
    └────────────┘  └──────────────┘  └───────────────┘
```

### Phase 1（今すぐ）
- **自動:** 方式 A（ThreadPool）で morning_auto.py を実装
- **手動:** 方式 D（Agent ツール）で /morning を並行化

### Phase 2（LINE Bot 導入後）
- **随時:** 方式 C（Agent SDK）で LINE から自然言語で指示
- 方式 A は引き続き毎朝の定型ルーチンとして稼働

### コスト最適化
- 定型 = A（最安）
- 対話 = D（無料）
- 柔軟 = C（Phase 2）
- B は不採用（コスト高・メリット薄）
