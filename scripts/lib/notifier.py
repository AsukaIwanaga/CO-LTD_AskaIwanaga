"""エラー通知（ログ保存 + メール）"""

import traceback
from datetime import datetime
from .config import DRAFTS_DIR
from .mailer import send_error_notification


def notify_error(feature_name: str, error: Exception) -> None:
    """エラー発生時にログ保存 + メール通知"""
    tb = traceback.format_exc()
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # ログ保存
    log_path = DRAFTS_DIR / f"{feature_name}_error_{now}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"[{now}] {feature_name}\n{str(error)}\n\n{tb}", encoding="utf-8")

    # メール通知
    send_error_notification(feature_name, str(error), tb)

    print(f"[{feature_name}] ERROR: {error}")
    print(f"  → ログ: {log_path}")
