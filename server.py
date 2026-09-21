from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import json
import requests
from urllib.parse import urlparse


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8000))
SEASON = 16


# =========================================================
# 統計計算
# =========================================================

def calc_stats(events):

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

    win_rate_val = (
        round((wins / total_games) * 100)
        if total_games > 0
        else 0
    )

    return {
        "win_rate": f"{win_rate_val}%",
        "wl": f"{wins}-{losses}",

        "mmr_change": (
            f"+{total_mmr_change}"
            if total_mmr_change > 0
            else str(total_mmr_change)
        ),

        "avg_score": (
            round(sum(scores) / len(scores), 1)
            if scores
            else "-"
        ),

        "top_score": (
            max(scores)
            if scores
            else "-"
        ),
    }


# =========================================================
# Format 6 判定
# =========================================================

def is_format_6(e):

    fmt = str(
        e.get("format", "")
    ).lower()

    num_teams = str(
        e.get("numTeams", "")
    )

    tier = str(
        e.get("tier", "")
    ).lower()

    event_name = str(
        e.get("eventName", "")
    ).lower()

    if fmt in [
        "6",
        "6v6",
        "format6"
    ] or tier in [
        "6",
        "6v6"
    ]:
        return True

    if "6v6" in event_name:
        return True

    if "6v6" in fmt:
        return True

    if (
        num_teams == "2"
        and (
            "6" in fmt
            or fmt == ""
            or "squad" in fmt
        )
    ):
        return True

    return False


# =========================================================
# MKCentralからプレイヤーデータ取得
# =========================================================

def get_player_data(player_id):

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64)"
    }

    api_player_url = (
        "https://lounge.mkcentral.com/api/player"
        f"?id={player_id}&season={SEASON}"
    )

    api_details_url = (
        "https://lounge.mkcentral.com/api/player/details"
        f"?id={player_id}&season={SEASON}"
    )

    # -----------------------------------------
    # Player API
    # -----------------------------------------

    res_player = requests.get(
        api_player_url,
        headers=headers,
        timeout=15
    )

    res_player.raise_for_status()

    data_player = res_player.json()

    # -----------------------------------------
    # DEBUG
    # Peak MMRの実際のキーを確認するためのログ
    # -----------------------------------------

    print()
    print("======================================")
    print(" MKCENTRAL PLAYER API RESPONSE")
    print("======================================")

    print(
        json.dumps(
            data_player,
            ensure_ascii=False,
            indent=2
        )
    )

    print("======================================")
    print()

    # -----------------------------------------
    # Details API
    # -----------------------------------------

    res_details = requests.get(
        api_details_url,
        headers=headers,
        timeout=15
    )

    res_details.raise_for_status()

    data_details = res_details.json()

    # -----------------------------------------
    # 基本情報
    # -----------------------------------------

    player_name = data_player.get(
        "name",
        "2.4 WB Party"
    )

    mmr = data_player.get(
        "mmr",
        0
    )

    # -----------------------------------------
    # 全試合履歴
    # -----------------------------------------

    all_events = data_details.get(
        "mmrChanges",
        []
    )

    # -----------------------------------------
    # LAST MATCH
    # -----------------------------------------

    if all_events:

        last_delta = all_events[0].get(
            "mmrDelta",
            0
        )

        if last_delta > 0:
            last_change = f"+{last_delta}"

        else:
            last_change = str(last_delta)

    else:

        last_change = "±0"

    # -----------------------------------------
    # LAST 10
    # -----------------------------------------

    last10_stats = calc_stats(
        all_events[:10]
    )

    # -----------------------------------------
    # FORMAT 6
    # -----------------------------------------

    format6_events = [
        e
        for e in all_events
        if is_format_6(e)
    ]

    if not format6_events:
        format6_events = all_events

    format6_stats = calc_stats(
        format6_events[:10]
    )

    # -----------------------------------------
    # JSON
    # -----------------------------------------

    return {

        "player": player_name,

        "mmr": mmr,

        "last_change": last_change,

        "win_rate":
            last10_stats["win_rate"],

        "wl":
            last10_stats["wl"],

        "mmr_change":
            last10_stats["mmr_change"],

        "avg_score":
            last10_stats["avg_score"],

        "top_score":
            last10_stats["top_score"],

        "f6_win_rate":
            format6_stats["win_rate"],

        "f6_wl":
            format6_stats["wl"],

        "f6_mmr_change":
            format6_stats["mmr_change"],

        "f6_avg_score":
            format6_stats["avg_score"],
    }


# =========================================================
# HTTP Handler
# =========================================================

class OverlayHandler(
    SimpleHTTPRequestHandler
):

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        # =================================================
        # API
        #
        # /api/player/22693
        #
        # =================================================

        if path.startswith(
            "/api/player/"
        ):

            player_id_str = (
                path
                .split(
                    "/api/player/",
                    1
                )[1]
                .strip("/")
            )

            if not player_id_str.isdigit():

                self.send_error(
                    400,
                    "Invalid Player ID"
                )

                return

            player_id = int(
                player_id_str
            )

            try:

                data = get_player_data(
                    player_id
                )

                body = json.dumps(
                    data,
                    ensure_ascii=False
                ).encode("utf-8")

                self.send_response(
                    200
                )

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                self.send_header(
                    "Cache-Control",
                    "no-store"
                )

                self.send_header(
                    "Content-Length",
                    str(len(body))
                )

                self.end_headers()

                self.wfile.write(
                    body
                )

            except Exception as e:

                print(
                    f"[ERROR] "
                    f"Player {player_id}: "
                    f"{e}"
                )

                self.send_error(
                    500,
                    "Failed to retrieve player data"
                )

            return

        # =================================================
        # Overlay
        #
        # /overlay/22693
        #
        # =================================================

        if path.startswith(
            "/overlay/"
        ):

            player_id_str = (
                path
                .split(
                    "/overlay/",
                    1
                )[1]
                .strip("/")
            )

            if not player_id_str.isdigit():

                self.send_error(
                    400,
                    "Invalid Player ID"
                )

                return

            self.path = "/index.html"

            return super().do_GET()

        # =================================================
        # その他
        # =================================================

        return super().do_GET()

    def log_message(
        self,
        format,
        *args
    ):

        print(
            "[HTTP]",
            format % args
        )


# =========================================================
# サーバー起動
# =========================================================

server = ThreadingHTTPServer(
    (HOST, PORT),
    OverlayHandler
)


print()
print("======================================")
print(" MMR Overlay WEB")
print("======================================")
print()
print(
    f"Server : http://{HOST}:{PORT}"
)
print()
print(
    "Overlay:"
)
print(
    f"http://{HOST}:{PORT}/overlay/22693"
)
print()
print(
    "API:"
)
print(
    f"http://{HOST}:{PORT}/api/player/22693"
)
print()


server.serve_forever()
