"""Anthropic Claude API ラッパー"""

import anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_HAIKU, CLAUDE_SONNET


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate(self, prompt: str, system: str = "",
                 model: str = CLAUDE_HAIKU,
                 max_tokens: int = 4096) -> str:
        msgs = [{"role": "user", "content": prompt}]
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": msgs}
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def generate_briefing_text(self, data: dict, template: str) -> str:
        """全収集データ → iPhone テンプレート形式のブリーフィング本文"""
        import json
        system = (
            "あなたは Don (岩永飛鳥) の秘書です。"
            "以下の情報源データから、iPhone で読みやすいモーニングブリーフィングを生成してください。\n\n"
            "フォーマットは以下のテンプレートに厳密に従ってください:\n"
            f"{template}\n\n"
            "ルール:\n"
            "- データが取得できなかった項目は「(取得不可)」と表示\n"
            "- 数値はカンマ区切り\n"
            "- 株価の矢印は上昇=↑、下降=↓\n"
            "- メールは最新5件まで、FROM/SUBJ 形式\n"
            "- 通達は全件表示（要約付き）"
        )
        return self.generate(
            prompt=f"以下のデータからブリーフィングを生成してください:\n\n{json.dumps(data, ensure_ascii=False, default=str)}",
            system=system,
            model=CLAUDE_HAIKU,
            max_tokens=8000,
        )

    def generate_tts_script(self, data: dict) -> str:
        """ブリーフィングデータ → 自然な日本語読み上げ文"""
        import json
        system = (
            "あなたは Don (岩永飛鳥) の秘書です。"
            "以下のデータを自然な日本語の話し言葉に変換してください。\n\n"
            "ルール:\n"
            "- 「おはようございます、ドン。本日〇月〇日のブリーフィングをお伝えします。」で始める\n"
            "- 天気・予定・タスク・通達・営業・メール・財務・習慣・株価をすべて読み上げる\n"
            "- 英数字・記号は読み替え: % → パーセント、AMT → セールス、T/C → ティーシー、A/C → エーシー\n"
            "- 一続きの文章として生成（箇条書き・記号不可）\n"
            "- 「準備は整いました。良い一日を、ドン。」で締める"
        )
        return self.generate(
            prompt=f"以下のデータから読み上げ文を生成してください:\n\n{json.dumps(data, ensure_ascii=False, default=str)}",
            system=system,
            model=CLAUDE_HAIKU,
            max_tokens=6000,
        )

    def analyze_notices(self, notices: list[dict]) -> dict:
        """通達リスト → 重要度判定 + タスク抽出"""
        import json
        system = (
            "あなたはすかいらーくグループ店舗の通達アナリストです。\n"
            "以下の通達を分析し、JSON形式で出力してください。\n\n"
            "判定基準:\n"
            "- 緊急: 本日・翌日に対応が必要、期限切れ間近\n"
            "- 要対応: 1週間以内に対応が必要\n"
            "- 情報周知: 対応不要の連絡事項\n\n"
            "タスク抽出基準:\n"
            "- 具体的な作業指示があり期限が明記されているもの\n"
            "- 回答フォーム提出、ツール設置、報告など\n"
            "- 「確認してください」レベルはタスク化しない\n\n"
            "出力形式 (JSON):\n"
            '{"notices": [{"id": "...", "title": "...", "importance": "緊急|要対応|情報周知", '
            '"summary": "要約", "tasks": [{"name": "...", "deadline": "YYYY-MM-DD", "tag": "WORK"}]}]}'
        )
        result = self.generate(
            prompt=f"以下の通達を分析してください:\n\n{json.dumps(notices, ensure_ascii=False, default=str)}",
            system=system,
            model=CLAUDE_HAIKU,
            max_tokens=4096,
        )
        # JSON 部分を抽出
        try:
            import re
            match = re.search(r'\{[\s\S]*\}', result)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {"notices": []}

    def analyze_sales(self, sales_data: dict, history: list[dict]) -> str:
        """営業データ → トレンド分析テキスト"""
        import json
        system = (
            "あなたはすかいらーくグループの営業データアナリストです。\n"
            "以下のデータを分析し、簡潔なレポートを生成してください。\n\n"
            "含めるべき内容:\n"
            "- 前日比の変動要因の推測\n"
            "- 月累計の進捗評価\n"
            "- 人件費率の評価\n"
            "- 改善提案があれば簡潔に"
        )
        return self.generate(
            prompt=f"営業データ:\n{json.dumps(sales_data, ensure_ascii=False, default=str)}\n\n直近30日:\n{json.dumps(history[-10:], ensure_ascii=False, default=str)}",
            system=system,
            model=CLAUDE_HAIKU,
            max_tokens=2000,
        )
