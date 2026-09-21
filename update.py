import json
import requests

PLAYER_ID = 22693
SEASON = 16

API_PLAYER_URL = (
    f"https://lounge.mkcentral.com/api/player?id={PLAYER_ID}&season={SEASON}"
)
API_DETAILS_URL = f"https://lounge.mkcentral.com/api/player/details?id={PLAYER_ID}&season={SEASON}"


def calc_stats(events):
    """試合リストから勝率、W-L (数字のみ)、MMR変動、平均スコアを計算する"""
    if not events:
        return {
            "win_rate": "-",
            "wl": "-",
            "mmr_change": "-",
            "avg_score": "-",
            "top_score": "-",
        }

    scores = []
    wins = 0
    losses = 0
    total_mmr_change = 0

    for e in events:
        score = e.get("score")
        if score is not None:
            scores.append(score)

        mmr_delta = e.get("mmrDelta", 0)
        total_mmr_change += mmr_delta

        if mmr_delta > 0:
            wins += 1
        elif mmr_delta < 0:
            losses += 1

    total_games = len(events)
    win_rate_val = round((wins / total_games) * 100) if total_games > 0 else 0

    return {
        "win_rate": f"{win_rate_val}%",
        "wl": f"{wins}-{losses}",  # 7-2 形式に変更
        "mmr_change": (
            f"+{total_mmr_change}"
            if total_mmr_change > 0
            else str(total_mmr_change)
        ),
        "avg_score": (
            round(sum(scores) / len(scores), 1) if scores else "-"
        ),
        "top_score": max(scores) if scores else "-",
    }


def is_format_6(e):
    fmt = str(e.get("format", "")).lower()
    num_teams = str(e.get("numTeams", ""))
    tier = str(e.get("tier", "")).lower()
    event_name = str(e.get("eventName", "")).lower()

    if fmt in ["6", "6v6", "format6"] or tier in ["6", "6v6"]:
        return True
    if "6v6" in event_name or "6v6" in fmt:
        return True
    if num_teams == "2" and ("6" in fmt or fmt == "" or "squad" in fmt):
        return True

    return False


def get_player_data():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    res_player = requests.get(API_PLAYER_URL, headers=headers)
    res_player.raise_for_status()
    data_player = res_player.json()

    res_details = requests.get(API_DETAILS_URL, headers=headers)
    res_details.raise_for_status()
    data_details = res_details.json()

    player_name = data_player.get("name", "2.4 WB Party")
    mmr = data_player.get("mmr", 0)

    # 全試合履歴
    all_events = data_details.get("mmrChanges", [])

    # 直近1試合のMMR変動値
    if all_events:
        last_delta = all_events[0].get("mmrDelta", 0)
        last_change = f"+{last_delta}" if last_delta > 0 else str(last_delta)
    else:
        last_change = "±0"

    # 直近10試合（全体）
    last10_stats = calc_stats(all_events[:10])

    # フォーマット6の試合抽出
    format6_events = [e for e in all_events if is_format_6(e)]
    if not format6_events:
        format6_events = all_events

    format6_stats = calc_stats(format6_events[:10])

    return {
        "player": player_name,
        "mmr": mmr,
        "last_change": last_change,
        "win_rate": last10_stats["win_rate"],
        "wl": last10_stats["wl"],
        "mmr_change": last10_stats["mmr_change"],
        "avg_score": last10_stats["avg_score"],
        "top_score": last10_stats["top_score"],
        "f6_win_rate": format6_stats["win_rate"],
        "f6_wl": format6_stats["wl"],
        "f6_mmr_change": format6_stats["mmr_change"],
        "f6_avg_score": format6_stats["avg_score"],
    }


if __name__ == "__main__":
    try:
        data = get_player_data()

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("\n[SUCCESS] data.json を更新しました！")
        print(f"Player       : {data['player']}")
        print(f"MMR          : {data['mmr']} (Last: {data['last_change']})")
        print(f"Format 6 WR  : {data['f6_win_rate']} ({data['f6_wl']})")
        print(f"Format 6 MMR : {data['f6_mmr_change']}")
        print(f"Format 6 Avg : {data['f6_avg_score']}\n")

    except Exception as e:
        print(f"\n[ERROR] データ更新に失敗しました: {e}\n")