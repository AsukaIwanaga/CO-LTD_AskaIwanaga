#!/usr/bin/env python3
"""
Skylark ポータル取得スクリプト（本文・PDF対応版）

- ポータルアクセス → Google OAuth へリダイレクト → .env の認証情報で自動ログイン
- 直近 DETAIL_DAYS 日以内の通達は本文・PDF添付テキストも取得して保存
- PDF はダウンロード → テキスト抽出 → 削除のフローで処理
"""

import os, json, re, tempfile
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

load_dotenv(dotenv_path=Path(__file__).parent / "../../.env")

PORTAL_URL      = os.getenv("SKYLARK_PORTAL_URL", "https://skylark.shoprun.jp/h2/STRStorePage.do")
GOOGLE_EMAIL    = os.getenv("SKYLARK_EMAIL", "")
GOOGLE_PASSWORD = os.getenv("SKYLARK_GOOGLE_PASSWORD", "")
OUTPUT_PATH     = (Path(__file__).parent / "../../drafts/portal_latest.json").resolve()

DETAIL_DAYS     = 14   # 本文・PDF取得対象: 直近何日以内か
PDF_TEXT_LIMIT  = 6000 # PDFテキストの最大文字数
NOTICES_DB_PATH = (Path(__file__).parent / "../../data/portal_notices.json").resolve()


# ─── ログイン ────────────────────────────────────────────────────────────────

def complete_google_login(page):
    """Google OAuth フォームを自動入力してログイン"""
    try:
        page.wait_for_selector("input[type='email']", timeout=10000)
        email_input = page.locator("input[type='email']")
        email_input.click()
        page.wait_for_timeout(500)
        email_input.fill(GOOGLE_EMAIL)
        page.wait_for_timeout(1000)
        page.click("#identifierNext")

        # メール入力後のページ遷移を待つ（identifier → challenge or password）
        for _ in range(10):
            page.wait_for_timeout(1000)
            if "identifier" not in page.url or page.locator("input[type='password']:visible").count() > 0:
                break

        page.wait_for_timeout(2000)

        # パスキー / チャレンジ画面の処理（最大3回リトライ）
        for _retry in range(3):
            # パスワード入力が見えていればループ脱出
            if page.locator("input[type='password']:visible").count() > 0:
                break
            if "challenge" not in page.url:
                break

            print(f"  → チャレンジ画面を検出。パスワード認証に切り替え中...")

            # 「パスキーを使用」のキャンセル / 「別の方法を試す」
            for btn_text in ["キャンセル", "Cancel", "Not now"]:
                try:
                    page.click(f"button:has-text('{btn_text}')", timeout=2000)
                    page.wait_for_timeout(1500)
                    break
                except Exception:
                    continue

            try:
                page.evaluate(
                    "Array.from(document.querySelectorAll('button, a'))"
                    ".find(b => /別の方法|Try another way|other way/i.test(b.innerText))?.click()"
                )
                page.wait_for_timeout(3000)
            except Exception:
                pass

            # パスワード認証を選択
            for sel in ["[data-challengetype='11']", "li:has-text('パスワード')",
                        "li:has-text('password')", "div[data-challengeindex]:has-text('パスワード')"]:
                try:
                    page.click(sel, timeout=2000)
                    page.wait_for_timeout(2000)
                    break
                except Exception:
                    continue

        page.wait_for_selector("input[type='password']:visible", timeout=20000)
        page.fill("input[type='password']:visible", GOOGLE_PASSWORD)
        page.wait_for_timeout(500)
        page.click("#passwordNext")
        page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"  自動ログインエラー: {e}")
        return False


# ─── PDF テキスト抽出 ────────────────────────────────────────────────────────

def extract_pdf_text(pdf_path: Path) -> str:
    """
    PDFファイルからテキストを抽出。
    通常抽出が空の場合（イラスト主体PDF）は Vision API でOCR フォールバック。
    """
    text = _extract_pdf_text_native(pdf_path)
    if len(text.strip()) >= 50:
        return text.strip()

    # テキストが取れない → イラスト主体PDF → Vision API で読む
    print(f"    テキスト抽出が空/不十分 → Vision API でOCR試行...")
    vision_text = _extract_pdf_text_via_vision(pdf_path)
    return vision_text if vision_text.strip() else text


def _extract_pdf_text_native(pdf_path: Path) -> str:
    """通常のテキスト抽出（pdfplumber / fitz / pypdf を順に試行）"""
    # pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        if text.strip():
            return text.strip()
    except Exception:
        pass

    # PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = "\n".join(pg.get_text() for pg in doc)
        doc.close()
        if text.strip():
            return text.strip()
    except Exception:
        pass

    # pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        if text.strip():
            return text.strip()
    except Exception:
        pass

    return ""


def _extract_pdf_text_via_vision(pdf_path: Path) -> str:
    """
    イラスト主体のPDFを fitz でページ画像化 → Claude Vision API でテキスト抽出。
    日本語の手順書・通達詳細に対応。
    """
    try:
        import fitz
        import anthropic
        import base64

        client = anthropic.Anthropic()
        doc    = fitz.open(str(pdf_path))
        texts  = []

        for page_num, page in enumerate(doc):
            # 2x解像度でレンダリング（読み取り精度向上）
            pix    = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_b64 = base64.standard_b64encode(pix.tobytes("png")).decode()

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": "image/png",
                                "data":       img_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "このPDFページの内容を日本語でテキスト化してください。"
                                "図表・手順・箇条書きの構造を保ちつつ、読み取れるテキストをすべて書き起こしてください。"
                                "イラストや写真は「[図: 説明]」形式で簡潔に説明してください。"
                            ),
                        },
                    ],
                }],
            )
            texts.append(f"--- ページ {page_num + 1} ---\n{response.content[0].text}")

        doc.close()
        return "\n\n".join(texts)

    except Exception as e:
        print(f"    Vision API エラー: {e}")
        return ""


def classify_pdf(text: str) -> str:
    """PDFの種類を判定: 'manual'（手順書・マニュアル）or 'detail'（通達詳細）"""
    manual_keywords = ["手順", "マニュアル", "取扱", "操作方法", "説明書", "手引き", "ガイド", "フロー", "ステップ"]
    for kw in manual_keywords:
        if kw in text:
            return "manual"
    return "detail"


# ─── ユーティリティ ──────────────────────────────────────────────────────────

def _strip_zwsp(text: str) -> str:
    """ゼロ幅スペース・ソフトハイフン等の不可視文字を除去"""
    import unicodedata
    # U+200B (ZWSP), U+200C (ZWNJ), U+200D (ZWJ), U+FEFF (BOM), U+00AD (SHY)
    return re.sub(r'[\u200B\u200C\u200D\uFEFF\u00AD]', '', text)


def _js_escape(text: str) -> str:
    """JS文字列リテラル内で安全に使えるようエスケープ"""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


# ─── フレーム操作 ────────────────────────────────────────────────────────────

def get_portal_frame(page):
    """通達一覧フレームを取得"""
    for frame in page.frames:
        if "STRStorePortal" in frame.url:
            return frame
    return None


def get_detail_frame(page, retries=10, interval=1000):
    """詳細表示フレームを取得（リトライ付き）。
    about:blank だったフレームに詳細が読み込まれるパターンに対応。
    STRMessageView は常時存在するメタデータフレームなので除外する。
    """
    # 詳細専用のURLパターン（STRMessageView は除外）
    detail_patterns = ["STRViewNotice", "STRNoticeDetail", "STRMessageDetail",
                       "STRNoticeView", "NoticeDetail", "MessageDetail",
                       "STRNoticeRefer", "NoticeRefer"]
    for attempt in range(retries):
        for frame in page.frames:
            url = frame.url
            # 明確な詳細ページURLにマッチ
            if any(k in url for k in detail_patterns):
                return frame
            # about:blank 以外で、既知のフレーム以外に新しく読み込まれたフレーム
            if (url != "about:blank"
                and "STRStorePage" not in url
                and "STRStorePortal" not in url
                and "STRMessageView" not in url
                and "STRStoreSideMenu" not in url
                and "RestoreSummaryFrame" not in url
                and "hiddenFrame" not in url):
                # 未知のフレーム = 詳細フレームの可能性
                try:
                    content = frame.content()
                    if len(content) > 500:  # 空でない
                        return frame
                except Exception:
                    pass
        if attempt < retries - 1:
            page.wait_for_timeout(interval)
    return None


def _wait_for_detail_load(page, timeout=10000):
    """クリック後にネットワーク安定 + 詳細フレーム出現を待つ"""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(1500)


def _go_back_to_list(page):
    """詳細画面から通達一覧に戻る"""
    # STRViewNotice フレーム内の「戻る」ボタンをクリック
    for frame in page.frames:
        if "STRViewNotice" in frame.url:
            try:
                back_btn = frame.locator("a:has-text('戻る'), button:has-text('戻る'), input[value='戻る']")
                if back_btn.count() > 0:
                    back_btn.first.click(timeout=5000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)
                    return
            except Exception:
                pass
    # フォールバック: ブラウザバック
    try:
        for frame in page.frames:
            if "STRViewNotice" in frame.url:
                frame.goto(frame.url.split("STRViewNotice")[0] + "STRStorePortal.do")
                page.wait_for_timeout(3000)
                return
    except Exception:
        pass


def click_notice_by_id(page, notice_id: str, notice_title: str,
                       notice_category: str = "") -> bool:
    """
    通達一覧フレームで該当通達をクリックする。
    STRViewNotice.do リンクを直接ナビゲートするか、タイトル/カテゴリでマッチしてクリック。
    """
    portal_frame = get_portal_frame(page)
    if not portal_frame:
        return False

    # 戦略1: noticeId を含む href リンクをクリック（Playwright の click でイベント発火）
    try:
        loc = portal_frame.locator(f"a[href*='noticeId={notice_id}']")
        if loc.count() > 0:
            loc.first.click(timeout=5000)
            _wait_for_detail_load(page)
            return True
    except Exception:
        pass

    # 戦略2: STRViewNotice リンクのうち notice_id を含むものを探す
    try:
        loc = portal_frame.locator(f"a[href*='STRViewNotice'][href*='{notice_id}']")
        if loc.count() > 0:
            loc.first.click(timeout=5000)
            _wait_for_detail_load(page)
            return True
    except Exception:
        pass

    # タイトルからマッチ候補を生成（ゼロ幅スペース除去）
    clean_title = _strip_zwsp(notice_title)
    clean_category = _strip_zwsp(notice_category)
    title_candidates = [clean_title[:20].strip()]
    # 作業通達の場合、categoryに親通達名が入っている
    if clean_category and clean_category not in ["連絡", "業務", "重要", "緊急"]:
        title_candidates.append(clean_category[:30].strip())

    # 戦略3: タイトルテキストでマッチしてクリック
    for snippet in title_candidates:
        if not snippet:
            continue
        try:
            loc = portal_frame.locator(f"a[href*='STRViewNotice']:has-text('{snippet}')")
            if loc.count() > 0:
                loc.first.click(timeout=5000)
                _wait_for_detail_load(page)
                return True
        except Exception:
            pass

    # 戦略4: JS でゼロ幅スペースを無視してテキストマッチ（全リンク対象）
    for snippet in title_candidates:
        if not snippet:
            continue
        try:
            clicked = portal_frame.evaluate(f"""() => {{
                const target = '{_js_escape(snippet)}';
                for (const a of document.querySelectorAll('a[href*="STRViewNotice"]')) {{
                    const text = a.textContent.replace(/[\\u200B\\u200C\\u200D\\uFEFF\\u00AD]/g, '').trim();
                    if (text.includes(target)) {{
                        a.click();
                        return true;
                    }}
                }}
                return false;
            }}""")
            if clicked:
                _wait_for_detail_load(page)
                return True
        except Exception:
            pass

    # 戦略5: 旧来のID検索（6桁IDがhrefに含まれるケース）
    id_selectors = [
        f"a[href*='{notice_id}']",
        f"a[onclick*='{notice_id}']",
        f"input[onclick*='{notice_id}']",
    ]
    for sel in id_selectors:
        try:
            loc = portal_frame.locator(sel)
            if loc.count() > 0:
                loc.first.click(timeout=5000)
                _wait_for_detail_load(page)
                return True
        except Exception:
            continue

    return False


# ─── 本文取得 ────────────────────────────────────────────────────────────────

def get_notice_body(detail_frame) -> str:
    """詳細フレームから本文テキストを取得し、UI要素を除去して返す"""
    if not detail_frame:
        return ""
    try:
        soup = BeautifulSoup(detail_frame.content(), "html.parser")
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # メインコンテンツ候補を優先的に探す
        raw = ""
        for selector in ["div.content", "div.body", "div.main", "div.message",
                         "div.detail", "#content", "#main", "article", "section"]:
            elem = soup.select_one(selector)
            if elem:
                raw = elem.get_text(separator="\n", strip=True)
                break

        if not raw:
            raw = soup.get_text(separator="\n", strip=True)

        return _clean_notice_body(raw)
    except Exception:
        return ""


# UI要素として除去する行（完全一致）
_UI_LINES_EXACT = {
    "データ通信中です。しばらくお待ちください。",
    "通達", "戻る", "未読にして戻る", "その他の操作",
    "リンクをコピーする", "印刷する", "作業を登録する",
    "店舗メモを登録する", "↑画面のトップに戻る",
    "作業を印刷する", "実施状況を報告する",
    "HiddenFrame",
    "​",  # ゼロ幅スペースのみの行
}

# メタデータのラベル行（次の行が値）— これらは構造化データとして別途保持済み
_META_LABELS = {
    "キーワード", "公開日", "タイトル", "添付PDF", "発行元",
    "対象者", "連絡文書", "発行部門", "掲示期限", "発行責任者",
    "回答", "回答期限:", "〜",
}

# ヘッダー区間の終了を示すキーワード（これ以降が本文）
_BODY_START_MARKERS = ["主旨", "内容", "実施する作業"]


def _clean_notice_body(text: str) -> str:
    """通達本文からUI要素・メタデータヘッダーを除去し、実質的な内容のみ返す"""
    lines = text.split("\n")

    # まず「主旨」「内容」の位置を探す
    body_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in _BODY_START_MARKERS:
            body_start = i
            break

    # 「主旨」が見つかった場合、その手前をメタデータとして分離
    if body_start >= 0:
        meta_lines = lines[:body_start]
        body_lines = lines[body_start:]
    else:
        # 見つからない場合は全体を対象に
        meta_lines = []
        body_lines = lines

    # メタデータ部分から構造化情報を抽出（将来用）
    metadata = {}
    for i, line in enumerate(meta_lines):
        stripped = line.strip()
        if stripped in _META_LABELS and i + 1 < len(meta_lines):
            val = meta_lines[i + 1].strip()
            if val and val not in _META_LABELS and val not in _UI_LINES_EXACT:
                metadata[stripped] = val

    # 本文部分をクリーニング
    cleaned = []
    for line in body_lines:
        stripped = line.strip()

        # 空行は保持（段落区切り）
        if not stripped:
            if cleaned and cleaned[-1] == "":
                continue
            cleaned.append("")
            continue

        # UI要素を除去
        if stripped in _UI_LINES_EXACT:
            continue

        # ページ番号パターン "8/10" を除去
        if re.match(r"^\d+/\d+$", stripped):
            continue

        # ゼロ幅スペースのみの行を除去
        if not _strip_zwsp(stripped):
            continue

        # メタデータラベルが本文中に再出現した場合（末尾のUI）
        if stripped in _META_LABELS:
            continue

        cleaned.append(stripped)

    # 先頭・末尾の空行を除去
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    # 末尾に残る通達IDっぽい数字のみの行（3-6桁）を除去
    while cleaned and re.match(r"^\d{3,6}$", cleaned[-1]):
        cleaned.pop()

    # 末尾の繰り返しUI（「戻る」等が2回目に出る場合）を除去
    while cleaned and cleaned[-1] in _UI_LINES_EXACT:
        cleaned.pop()

    return "\n".join(cleaned)


# ─── PDF ダウンロード＆抽出 ──────────────────────────────────────────────────

def download_and_extract_pdfs(page, detail_frame) -> list:
    """
    詳細フレーム内の PDF をダウンロードしてテキスト抽出後に削除。
    Playwright locator.click() で全 PDF リンクを処理する。
    Returns: [{"filename": str, "type": str, "text": str}]
    """
    if not detail_frame:
        return []

    results = []
    seen_names = set()

    # PDF リンク候補を Playwright で直接検索（href/onclick 両方）
    try:
        pdf_elements = detail_frame.locator(
            "a[href*='.pdf'], a[href*='/pdf'], a[href*='download'], a[href*='attach'], "
            "[onclick*='pdf'], [onclick*='download'], [onclick*='attach']"
        )
        count = pdf_elements.count()
    except Exception:
        count = 0

    for idx in range(count):
        try:
            el = pdf_elements.nth(idx)
            name = (el.text_content() or "").strip() or "attachment.pdf"
            if not name.lower().endswith(".pdf"):
                name = name.split(".")[0] + ".pdf" if "." in name else name + ".pdf"

            # 重複排除
            if name in seen_names:
                continue
            seen_names.add(name)

            print(f"  → PDF取得中: {name}")
            tmp_path = None
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                tmp_path = Path(f.name)

            downloaded = False

            # 方法1: expect_download でダウンロードイベントを待つ
            try:
                with page.expect_download(timeout=8000) as dl_info:
                    el.click(timeout=5000)
                dl_info.value.save_as(str(tmp_path))
                downloaded = True
            except Exception:
                pass

            # 方法2: 新しいページ（タブ）が開かれた場合、そこからPDFを取得
            if not downloaded:
                try:
                    with page.context.expect_page(timeout=8000) as new_page_info:
                        el.click(timeout=5000)
                    new_page = new_page_info.value
                    new_page.wait_for_load_state("networkidle", timeout=10000)
                    # 新タブのURLがPDFかチェック
                    if new_page.url and ("pdf" in new_page.url.lower() or "download" in new_page.url.lower()):
                        import urllib.request
                        # Cookieを引き継いでダウンロード
                        cookies = page.context.cookies()
                        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                        req = urllib.request.Request(new_page.url)
                        req.add_header("Cookie", cookie_str)
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            tmp_path.write_bytes(resp.read())
                        downloaded = True
                    new_page.close()
                except Exception:
                    pass

            # 方法3: href属性からURLを直接取得してダウンロード
            if not downloaded:
                try:
                    href = el.get_attribute("href") or ""
                    if href and not href.startswith("javascript"):
                        import urllib.request
                        # 相対URLを絶対URLに変換
                        if href.startswith("/"):
                            href = "https://skylark.shoprun.jp" + href
                        cookies = page.context.cookies()
                        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                        req = urllib.request.Request(href)
                        req.add_header("Cookie", cookie_str)
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            tmp_path.write_bytes(resp.read())
                        if tmp_path.stat().st_size > 0:
                            downloaded = True
                except Exception:
                    pass

            if downloaded and tmp_path.exists() and tmp_path.stat().st_size > 0:
                text = extract_pdf_text(tmp_path)
                pdf_type = classify_pdf(text)
                truncated = text[:PDF_TEXT_LIMIT] if len(text) > PDF_TEXT_LIMIT else text
                results.append({
                    "filename": name,
                    "type":     pdf_type,
                    "text":     truncated,
                })
                print(f"    → 完了（{len(text)}文字 / 種別: {pdf_type}）")
            else:
                print(f"    → ダウンロード失敗")
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

        except Exception as e:
            print(f"  PDF処理エラー: {e}")

    return results


# ─── メイン取得フロー ────────────────────────────────────────────────────────

def fetch_notices(headless=False):
    if not GOOGLE_EMAIL or not GOOGLE_PASSWORD:
        print("⚠ .env に SKYLARK_EMAIL / SKYLARK_GOOGLE_PASSWORD が設定されていません。")
        return None

    cutoff = datetime.now() - timedelta(days=DETAIL_DAYS)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=800,600",
                "--window-position=0,0",
            ],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print("ポータルへアクセス中...")
        page.goto(PORTAL_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        # Google OAuth
        if "accounts.google.com" in page.url:
            print("  → Google認証を自動入力中...")
            if not complete_google_login(page):
                print("⚠ 自動ログイン失敗。手動でログインしてください...")

        # ポータルへのリダイレクト待ち
        try:
            page.wait_for_url(
                lambda url: "STRStorePage" in url or "STRAutoLoginStaff" in url,
                timeout=60000
            )
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
        except Exception:
            if "accounts.google.com" in page.url:
                print("⚠ Google追加認証が必要です。ブラウザで完了してください...")
                try:
                    page.wait_for_url("**/STRStorePage.do**", timeout=120000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                except Exception:
                    browser.close()
                    return None
            else:
                print(f"⚠ タイムアウト。URL: {page.url}")
                browser.close()
                return None

        # 店舗選択
        if "STRAutoLoginStaff" in page.url:
            print("  → 店舗選択画面。保土ヶ谷を選択中...")
            try:
                page.click(
                    "a:has-text('保土ヶ谷'), button:has-text('保土ヶ谷'), "
                    "td:has-text('保土ヶ谷'), li:has-text('保土ヶ谷')",
                    timeout=10000
                )
                page.wait_for_url("**/STRStorePage.do**", timeout=30000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  店舗選択エラー: {e}")
                browser.close()
                return None

        # iframe 読み込み待ち
        print("通達を読み込み中...")
        for _ in range(8):
            if any("STRStorePortal" in f.url or "STRMessageView" in f.url for f in page.frames):
                break
            page.wait_for_timeout(2000)

        # 一覧テキスト・メタデータ取得
        notices_text = ""
        message_text = ""
        for frame in page.frames:
            try:
                soup = BeautifulSoup(frame.content(), "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                if "STRStorePortal" in frame.url and text.strip():
                    notices_text = text
                if "STRMessageView" in frame.url and text.strip():
                    message_text = text
            except Exception:
                pass

        notices  = parse_notices(notices_text)
        metadata = parse_metadata(message_text)
        print(f"通達数: {len(notices)} 件（直近{DETAIL_DAYS}日分の本文・PDFを取得します）")

        # 直近N日以内の通達の本文・PDFを取得
        for i, notice in enumerate(notices):
            date_str = notice.get("date", "")[:10].replace("/", "-")
            try:
                notice_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                notice["body"] = ""
                notice["pdfs"] = []
                continue

            if notice_date < cutoff:
                notice["body"] = ""
                notice["pdfs"] = []
                continue

            label = notice["title"][:30]
            print(f"  [{i+1}/{len(notices)}] {label}... の詳細を取得中")

            clicked = click_notice_by_id(page, notice["id"], notice["title"],
                                            notice.get("category", ""))
            if clicked:
                detail_frame = get_detail_frame(page)
                if detail_frame:
                    notice["body"] = get_notice_body(detail_frame)
                    notice["pdfs"] = download_and_extract_pdfs(page, detail_frame)
                else:
                    print(f"    → 詳細フレーム検出失敗。本文取得スキップ。")
                    notice["body"] = ""
                    notice["pdfs"] = []

                # 一覧に戻る（ポータルフレームが詳細に遷移するため）
                _go_back_to_list(page)
            else:
                print(f"    → クリック失敗。スキップ。")
                notice["body"] = ""
                notice["pdfs"] = []

            page.wait_for_timeout(500)

        browser.close()
        return build_result(notices, metadata)


# ─── パース・ビルド ──────────────────────────────────────────────────────────

def parse_notices(text: str) -> list:
    notices = []
    # テキスト全体からゼロ幅スペースを除去
    text = _strip_zwsp(text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.isdigit() and len(line) == 6:
            notices.append({
                "id":         line,
                "category":   lines[i+1] if i+1 < len(lines) else "",
                "title":      lines[i+2] if i+2 < len(lines) else "",
                "date":       lines[i+3] if i+3 < len(lines) else "",
                "department": lines[i+4] if i+4 < len(lines) else "",
                "body":       "",
                "pdfs":       [],
            })
            i += 5
        else:
            i += 1
    return notices


def parse_metadata(text: str) -> dict:
    unread_count = 0
    store_name   = ""
    staff_name   = ""
    for line in text.split("\n"):
        line = line.strip()
        if "件" in line and "未読" in line:
            try:
                unread_count = int("".join(filter(str.isdigit, line.split("件")[0])))
            except Exception:
                pass
        if "店舗" in line and "：" in line:
            store_name = line.split("：")[-1].strip()
        if "スタッフ" in line and "：" in line:
            staff_name = line.split("：")[-1].strip()
    return {"unread_count": unread_count, "store_name": store_name, "staff_name": staff_name}


def build_result(notices: list, metadata: dict) -> dict:
    fetched_at = datetime.now().isoformat()
    result = {
        "fetched_at":   fetched_at,
        "store_name":   metadata["store_name"],
        "staff_name":   metadata["staff_name"],
        "unread_count": metadata["unread_count"],
        "notices":      notices,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    upsert_notices_db(notices, fetched_at)
    return result


# ─── スケジュール抽出 ────────────────────────────────────────────────────────

def extract_schedules(title: str, body: str, pdfs: list) -> list:
    """
    通達のタイトル・本文・PDFテキストから日時情報を抽出する。
    Returns: [{"date": "YYYY-MM-DD[THH:MM]", "date_type": str, "description": str}]
    """
    full_text = title + "\n" + body + "\n" + "\n".join(p.get("text", "") for p in pdfs)
    schedules = []
    seen = set()
    now = datetime.now()

    # 日付パターン定義
    patterns = [
        # YYYY年MM月DD日 HH:MM
        (r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*[（(]?[日月火水木金土]?[）)]?\s*(\d{1,2})[時:：](\d{2})",
         lambda m: (f"{m[0]}-{int(m[1]):02d}-{int(m[2]):02d}T{int(m[3]):02d}:{m[4]}", True)),
        # YYYY年MM月DD日
        (r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",
         lambda m: (f"{m[0]}-{int(m[1]):02d}-{int(m[2]):02d}", False)),
        # YYYY/MM/DD または YYYY-MM-DD
        (r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})",
         lambda m: (f"{m[0]}-{int(m[1]):02d}-{int(m[2]):02d}", False)),
        # MM月DD日 HH:MM（年なし → 当年補完）
        (r"(\d{1,2})月\s*(\d{1,2})日\s*[（(]?[日月火水木金土]?[）)]?\s*(\d{1,2})[時:：](\d{2})",
         lambda m: (f"{now.year}-{int(m[0]):02d}-{int(m[1]):02d}T{int(m[2]):02d}:{m[3]}", True)),
        # MM月DD日（年なし → 当年補完）
        (r"(\d{1,2})月\s*(\d{1,2})日",
         lambda m: (f"{now.year}-{int(m[0]):02d}-{int(m[1]):02d}", False)),
        # MM/DD（年なし → 当年補完、YYYY/MM/DD の部分マッチを除外）
        (r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d|/)",
         lambda m: (f"{now.year}-{int(m[0]):02d}-{int(m[1]):02d}", False)),
    ]

    # 日付種別キーワード（前後30文字で判定）
    deadline_kw  = ["締切", "期限", "まで", "〆切", "提出", "報告", "回答", "申請", "登録"]
    schedule_kw  = ["実施", "開催", "予定", "配送", "発効", "開始", "から", "以降"]

    for pattern, date_fn in patterns:
        for m in re.finditer(pattern, full_text):
            try:
                date_str, has_time = date_fn(m.groups())
            except Exception:
                continue

            if date_str in seen:
                continue
            seen.add(date_str)

            # 前後文脈を取得して日付種別を判定
            start = max(0, m.start() - 30)
            end   = min(len(full_text), m.end() + 30)
            ctx   = full_text[start:end]

            if any(kw in ctx for kw in deadline_kw):
                date_type = "deadline"
            elif any(kw in ctx for kw in schedule_kw):
                date_type = "schedule"
            else:
                date_type = "info"

            # 周辺テキストから説明文を生成
            ctx_clean = ctx.replace("\n", " ").strip()
            # 文脈がほぼ日付のみの場合やボイラープレートの場合はタイトルを使う
            boilerplate_kw = ["件 が未読です", "公開された通達"]
            if len(ctx_clean) < 10 or any(kw in ctx_clean for kw in boilerplate_kw):
                desc = title[:60].strip()
            else:
                desc = ctx_clean

            schedules.append({
                "date":      date_str,
                "date_type": date_type,
                "description": desc,
            })

    return schedules


# ─── portal_notices.json への upsert ─────────────────────────────────────────

def upsert_notices_db(notices: list, fetched_at: str):
    """
    portal_notices.json に通達をupsert（id単位）する。
    本文・PDF・スケジュールを永続保存。
    """
    # 既存データ読み込み
    existing: list = []
    if NOTICES_DB_PATH.exists():
        try:
            with open(NOTICES_DB_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing_map = {n["id"]: n for n in existing}

    updated = 0
    inserted = 0
    for notice in notices:
        nid = notice.get("id", "")
        if not nid:
            continue

        body  = notice.get("body", "")
        pdfs  = notice.get("pdfs", [])
        schedules = extract_schedules(notice.get("title", ""), body, pdfs)

        record = {
            "id":          nid,
            "category":    notice.get("category", ""),
            "title":       notice.get("title", ""),
            "date":        notice.get("date", ""),
            "department":  notice.get("department", ""),
            "body":        body,
            "pdfs":        pdfs,
            "schedules":   schedules,
            "fetched_at":  fetched_at,
        }

        if nid in existing_map:
            prev = existing_map[nid]
            # 本文・PDF は空で上書きしない（取得済みデータを保持）
            if not body:
                record["body"] = _clean_notice_body(prev.get("body", ""))
            if not pdfs:
                record["pdfs"] = prev.get("pdfs", [])
            # スケジュールは常に再抽出（タイトルから取れるものも含む）
            record["schedules"] = extract_schedules(
                record["title"], record["body"], record["pdfs"]
            )
            existing_map[nid] = record
            updated += 1
        else:
            existing_map[nid] = record
            inserted += 1

    # 日付降順でソートして保存
    merged = sorted(existing_map.values(), key=lambda n: n.get("date", ""), reverse=True)
    NOTICES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTICES_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"→ portal_notices.json: {inserted}件追加 / {updated}件更新（計{len(merged)}件）")


# ─── 表示 ────────────────────────────────────────────────────────────────────

def print_result(data: dict):
    print(f"\n{'='*50}")
    print(f"すかいらーくポータル通達")
    print(f"{'='*50}")
    print(f"取得日時 : {data['fetched_at']}")
    print(f"店舗     : {data['store_name'] or '（取得中）'}")
    print(f"スタッフ : {data['staff_name'] or '（取得中）'}")
    print(f"未読件数 : {data['unread_count']} 件")
    print(f"\n--- 通達一覧 ({len(data['notices'])}件) ---")
    for n in data["notices"]:
        date      = n.get("date", "")[:10]
        cat       = n.get("category", "")
        title     = n.get("title", "")
        dept      = n.get("department", "")
        body_len  = len(n.get("body", ""))
        pdf_count = len(n.get("pdfs", []))
        extras = []
        if body_len  > 0: extras.append(f"本文:{body_len}文字")
        if pdf_count > 0: extras.append(f"PDF:{pdf_count}件")
        extra_str = f" [{', '.join(extras)}]" if extras else ""
        print(f"[{date}] {cat} | {title[:40]} — {dept}{extra_str}")
    print(f"\n→ 保存: {OUTPUT_PATH}")


if __name__ == "__main__":
    import argparse as _ap
    _parser = _ap.ArgumentParser()
    _parser.add_argument("--headless", action="store_true", help="ヘッドレスモードで実行")
    _args = _parser.parse_args()

    data = fetch_notices(headless=_args.headless)
    if data:
        print_result(data)
    else:
        print("取得に失敗しました。")
