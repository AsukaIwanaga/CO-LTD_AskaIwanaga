"""共通設定・定数"""

from pathlib import Path
from dotenv import load_dotenv
import os

# ─── パス定数 ─────────────────────────────────────────────────────────────

PROJECT_DIR = Path("/Users/askaiwanaga/CO-LTD_AskaIwanaga")
SCRIPTS_DIR = PROJECT_DIR / "scripts"
DATA_DIR    = PROJECT_DIR / "data"
DRAFTS_DIR  = PROJECT_DIR / "drafts"
PYTHON      = "/opt/anaconda3/bin/python3"

# ─── .env 読み込み ────────────────────────────────────────────────────────

load_dotenv(dotenv_path=PROJECT_DIR / ".env")

def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

# ─── 認証 ─────────────────────────────────────────────────────────────────

SKYLARK_EMAIL          = get_env("SKYLARK_EMAIL")
SKYLARK_GOOGLE_PASSWORD = get_env("SKYLARK_GOOGLE_PASSWORD")
ANTHROPIC_API_KEY      = get_env("ANTHROPIC_API_KEY")

# ─── Google OAuth ─────────────────────────────────────────────────────────

GCP_OAUTH_KEYS   = PROJECT_DIR / "gcp-oauth.keys.json"
GCP_TOKEN_PRIVATE = DRAFTS_DIR / "gcp_token_private.json"
GCP_TOKEN_WORK    = DRAFTS_DIR / "gcp_token_work.json"

# ─── メール ───────────────────────────────────────────────────────────────

TO_PRIVATE = "asuka.ctn1@gmail.com"
TO_WORK    = "asuka.iwanaga@skylark.co.jp"

# ─── 店舗 ─────────────────────────────────────────────────────────────────

STORES = {
    "017807": "GT保土ヶ谷駅前",
    "018974": "GTみなとみらい",
}
DEFAULT_STORE = "017807"

# ─── Claude モデル ────────────────────────────────────────────────────────

CLAUDE_HAIKU  = "claude-haiku-4-5-20251001"
CLAUDE_SONNET = "claude-sonnet-4-6"
