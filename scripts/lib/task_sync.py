"""タスク同期 — Google Tasks (正) ↔ tasks.json (キャッシュ+拡張メタ)

同期方針:
- Google Tasks が Single Source of Truth
- tasks.json は拡張フィールド（priority, tag, quest_id）を持つ
- Google Tasks にないローカルタスクは Google に追加
- Google Tasks で完了されたタスクはローカルも完了に
- ローカルで追加されたタスクは Google にも反映
"""

import re
from datetime import datetime, date, timedelta
from .config import DATA_DIR
from .data_loader import load_json, save_json, load_tasks, save_tasks
from .google_api import tasks_list_all, tasks_create, tasks_complete


def sync_tasks(account: str = "private") -> dict:
    """Google Tasks ↔ tasks.json を同期。結果サマリーを返す。"""
    google_tasks = tasks_list_all(account, include_completed=False)
    if google_tasks and "error" in google_tasks[0]:
        return {"error": google_tasks[0]["error"]}

    local_tasks = load_tasks()

    # ローカルタスクの google_task_id マップ
    local_by_gid = {t["google_task_id"]: t for t in local_tasks if t.get("google_task_id")}
    local_by_name = {t["name"]: t for t in local_tasks}

    stats = {"added_local": 0, "added_google": 0, "updated": 0, "completed": 0}

    # 1. Google → ローカル: Google にあってローカルにないものを追加
    seen_gids = set()
    for gt in google_tasks:
        gid = gt["google_task_id"]
        seen_gids.add(gid)

        if gid in local_by_gid:
            # 既にリンク済み — タイトル・期限を同期
            lt = local_by_gid[gid]
            lt["name"] = gt["title"]
            lt["deadline"] = gt["due"][:10] if gt["due"] else ""
            if gt.get("notes") and not lt.get("notes"):
                lt["notes"] = gt["notes"]
            stats["updated"] += 1
        else:
            # Google にあるがローカルにない → ローカルに追加
            # タイトルで名寄せ試行
            existing = local_by_name.get(gt["title"])
            if existing and not existing.get("google_task_id"):
                existing["google_task_id"] = gid
                existing["google_list_id"] = gt["google_list_id"]
                stats["updated"] += 1
            else:
                # 新規追加
                tag, priority = _parse_task_prefix(gt["title"])
                new_task = {
                    "id": str(_next_id(local_tasks)),
                    "name": gt["title"],
                    "regulation": "ONCE",
                    "deadline": gt["due"][:10] if gt["due"] else "",
                    "priority": priority,
                    "tag": tag,
                    "quest_id": "",
                    "quest_task_id": "",
                    "completed": False,
                    "timestamp": datetime.now().isoformat(),
                    "google_task_id": gid,
                    "google_list_id": gt["google_list_id"],
                    "notes": gt.get("notes", ""),
                }
                local_tasks.append(new_task)
                stats["added_local"] += 1

    # 2. ローカル → Google: ローカルにあって Google にないもの（未完了）を Google に追加
    for lt in local_tasks:
        if lt.get("completed"):
            continue
        if lt.get("google_task_id"):
            continue
        # Google に存在しない → 作成
        try:
            result = tasks_create(
                title=lt["name"],
                due=lt.get("deadline", ""),
                notes=lt.get("notes", ""),
                account=account,
            )
            lt["google_task_id"] = result.get("id", "")
            lt["google_list_id"] = result.get("selfLink", "").split("/lists/")[1].split("/")[0] if "/lists/" in result.get("selfLink", "") else ""
            stats["added_google"] += 1
        except Exception:
            pass

    # 3. ローカルで google_task_id があるが Google に存在しない → Google 側で完了/削除済み
    for lt in local_tasks:
        if lt.get("completed"):
            continue
        gid = lt.get("google_task_id")
        if gid and gid not in seen_gids:
            lt["completed"] = True
            stats["completed"] += 1

    # 4. 定期タスクの自動再生成
    regenerated = _regenerate_recurring(local_tasks, account)
    stats["regenerated"] = regenerated

    # 5. タグ未付与のタスクに自動タグ付け（notes に [GROUP/CAT]）
    tagged = _auto_tag_tasks(local_tasks, account)
    stats["tagged"] = tagged

    save_tasks(local_tasks)
    return stats


def _regenerate_recurring(tasks: list[dict], account: str = "private") -> int:
    """完了履歴から定期タスクのパターンを検知し、次回分を自動生成"""
    from collections import Counter

    completed = [t for t in tasks if t.get("completed")]
    incomplete_names = {t["name"] for t in tasks if not t.get("completed")}

    # 同名タスクの完了回数をカウント
    name_counts = Counter(t["name"] for t in completed)

    # 2回以上完了されたタスク = 定期タスクの可能性
    recurring_candidates = {name for name, count in name_counts.items() if count >= 2}

    regenerated = 0
    today = date.today()

    for name in recurring_candidates:
        # 既に未完了で同名タスクがあればスキップ
        if name in incomplete_names:
            continue

        # 完了済みの同名タスクから期限パターンを分析
        same_tasks = sorted(
            [t for t in completed if t["name"] == name and t.get("deadline")],
            key=lambda t: t["deadline"],
        )
        if len(same_tasks) < 2:
            continue

        # 直近2件の期限差から間隔を推定
        deadlines = [date.fromisoformat(t["deadline"][:10]) for t in same_tasks[-2:]]
        interval = (deadlines[-1] - deadlines[-2]).days
        if interval <= 0 or interval > 35:
            continue  # 1日以下や月超えは対象外

        # 次の期限を計算
        last_deadline = deadlines[-1]
        next_deadline = last_deadline + timedelta(days=interval)

        # 過去の期限になってしまう場合は今日以降に調整
        while next_deadline < today:
            next_deadline += timedelta(days=interval)

        # 次回分が既に存在しないか確認（期限ベース）
        next_dl_str = next_deadline.isoformat()
        exists = any(
            t["name"] == name and t.get("deadline", "")[:10] == next_dl_str
            for t in tasks
        )
        if exists:
            continue

        # 生成
        try:
            last_task = same_tasks[-1]
            result = tasks_create(
                title=name,
                due=next_dl_str,
                notes=last_task.get("notes", ""),
                account=account,
            )
            new_task = {
                "id": str(_next_id(tasks)),
                "name": name,
                "regulation": "RECURRING",
                "deadline": next_dl_str,
                "priority": last_task.get("priority", "MEDIUM"),
                "tag": last_task.get("tag", "WORK"),
                "quest_id": "",
                "quest_task_id": "",
                "completed": False,
                "timestamp": datetime.now().isoformat(),
                "google_task_id": result.get("id", ""),
                "google_list_id": last_task.get("google_list_id", ""),
                "notes": last_task.get("notes", ""),
            }
            tasks.append(new_task)
            regenerated += 1
        except Exception:
            pass

    return regenerated


def _auto_tag_tasks(tasks: list[dict], account: str = "private") -> int:
    """タグなしのタスクに notes で [GROUP/CATEGORY] タグを自動付与"""
    import json
    import urllib.request
    from .google_api import _get_auth

    CATEGORY_HINTS = {
        "mngt": ["管理", "修正", "入力", "作成", "締め", "報告", "確認", "実棚",
                 "HRBrain", "勤怠", "雇用", "契約", "日報", "経営", "ニュース",
                 "商品", "日客", "労務", "発注", "予算"],
        "rsvt": ["予約", "予定", "勉強会", "研修", "面接", "健康診断", "車検"],
        "pchs": ["買う", "購入", "キャベツ", "スパゲッティ"],
        "kpcl": ["洗濯", "掃除", "部屋", "車", "片付"],
        "evnt": ["イベント", "インストアメディア", "POP", "ツール", "通達"],
        "fnnc": ["ローン", "返済", "銀行", "支払", "振込"],
    }

    tagged = 0
    auth = _get_auth(account)

    for t in tasks:
        if t.get("completed"):
            continue

        notes = t.get("notes", "") or ""

        # 既にタグがあればスキップ
        if notes.startswith("[WRK/") or notes.startswith("[PRV/"):
            # title にプレフィックスが残っていたら除去
            name = t["name"]
            parts = name.split("_", 2)
            if len(parts) >= 3 and parts[0] in ("WRK", "PRV"):
                t["name"] = parts[2]
                _patch_google_task(auth, t, title=t["name"])
                tagged += 1
            continue

        name = t["name"]

        # title にプレフィックスが付いている場合 → notes に移動
        parts = name.split("_", 2)
        if len(parts) >= 3 and parts[0] in ("WRK", "PRV"):
            group, cat, clean_title = parts[0], parts[1], parts[2]
            tag_line = f"[{group}/{cat}]"
            t["name"] = clean_title
            t["notes"] = f"{tag_line}\n{notes}".strip()
            _patch_google_task(auth, t, title=clean_title, notes=t["notes"])
            tagged += 1
            continue

        # タグもプレフィックスもない → カテゴリ推定して notes に付与
        tag = t.get("tag", "WORK")
        group = "PRV" if tag == "PRIVATE" else "WRK"
        category = "misc"
        for cat, keywords in CATEGORY_HINTS.items():
            if any(kw in name for kw in keywords):
                category = cat
                break

        tag_line = f"[{group}/{category}]"
        t["notes"] = f"{tag_line}\n{notes}".strip()
        t["tag"] = "PRIVATE" if group == "PRV" else "WORK"
        _patch_google_task(auth, t, notes=t["notes"])
        tagged += 1

    return tagged


def _patch_google_task(auth, task: dict, title: str = None, notes: str = None):
    """Google Tasks のタスクを PATCH 更新"""
    import json
    import urllib.request

    gid = task.get("google_task_id", "")
    lid = task.get("google_list_id", "")
    if not gid or not lid:
        return
    try:
        url = f"https://tasks.googleapis.com/tasks/v1/lists/{lid}/tasks/{gid}"
        token = auth.get_access_token()
        body = {}
        if title is not None:
            body["title"] = title
        if notes is not None:
            body["notes"] = notes
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="PATCH")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass


def add_task(name: str, deadline: str = "", priority: str = "MEDIUM",
             tag: str = "WORK", notes: str = "", quest_id: str = "",
             account: str = "private") -> dict:
    """タスクを Google Tasks + tasks.json の両方に追加"""
    # Google に作成
    result = tasks_create(title=name, due=deadline, notes=notes, account=account)
    gid = result.get("id", "")

    # ローカルにも追加
    local_tasks = load_tasks()
    new_task = {
        "id": str(_next_id(local_tasks)),
        "name": name,
        "regulation": "ONCE",
        "deadline": deadline,
        "priority": priority,
        "tag": tag,
        "quest_id": quest_id,
        "quest_task_id": "",
        "completed": False,
        "timestamp": datetime.now().isoformat(),
        "google_task_id": gid,
        "google_list_id": "",
        "notes": notes,
    }
    local_tasks.append(new_task)
    save_tasks(local_tasks)
    return new_task


def complete_task(task_id: str = "", google_task_id: str = "",
                  account: str = "private") -> bool:
    """タスクを Google Tasks + tasks.json の両方で完了にする"""
    local_tasks = load_tasks()
    target = None
    for t in local_tasks:
        if task_id and t["id"] == task_id:
            target = t
            break
        if google_task_id and t.get("google_task_id") == google_task_id:
            target = t
            break

    if not target:
        return False

    # ローカル完了
    target["completed"] = True

    # Google 完了
    gid = target.get("google_task_id")
    lid = target.get("google_list_id", "")
    if gid:
        try:
            tasks_complete(gid, lid, account)
        except Exception:
            pass

    save_tasks(local_tasks)
    return True


def _next_id(tasks: list[dict]) -> int:
    if not tasks:
        return 1
    return max(int(t.get("id", 0)) for t in tasks) + 1


def _parse_task_prefix(title: str) -> tuple[str, str]:
    """Google Tasks のタイトル命名規則からタグと優先度を推定
    WRK_xxx → WORK, PRV_xxx → PRIVATE
    """
    title_upper = title.upper()
    if title_upper.startswith("WRK_"):
        return "WORK", "MEDIUM"
    elif title_upper.startswith("PRV_"):
        return "PRIVATE", "LOW"
    elif "【" in title or "確認" in title or "報告" in title:
        return "WORK", "MEDIUM"
    else:
        return "WORK", "MEDIUM"
