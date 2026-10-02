import os
import sys
import json
import time
import signal
import asyncio
import aiohttp

from urllib.parse import parse_qs

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "HCOW Spin Miniapp"
BASE_URL = "https://hashcow.vercel.app"
REF_CODE = "6004380466"


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        after_at = proxy_url.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def countdown(seconds, label):
    start = time.time()
    while True:
        remaining = seconds - (time.time() - start)
        if remaining <= 0:
            print(f"\r{' ' * 70}\r", end="", flush=True)
            break
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        s = int(remaining % 60)
        print(f"\r{YELLOW}{BOLD}{label} {h:02d}:{m:02d}:{s:02d}{RESET}", end="", flush=True)
        time.sleep(1)


def load_config():
    defaults = {"settings": {"sleep_seconds": 3600}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception:
        return defaults


def load_accounts():
    if not os.path.exists("data.txt"):
        log_red("File data.txt was not found.")
        sys.exit(1)
    lines = [l.strip() for l in open("data.txt").readlines() if l.strip()]
    if not lines:
        log_red("File data.txt is empty.")
        sys.exit(1)
    return lines


def load_proxies():
    if not os.path.exists("proxy.txt"):
        return []
    try:
        return [l.strip() for l in open("proxy.txt").readlines() if l.strip()]
    except Exception:
        return []


def get_proxy(proxies, idx):
    if not proxies:
        return None
    return proxies[idx % len(proxies)]


def parse_account(line):
    value = line.strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0].split("&tgWebAppPlatform")[0]
        from urllib.parse import unquote
        value = unquote(value)
    user_id = ""
    username = ""
    try:
        raw = (parse_qs(value).get("user") or [""])[0]
        if raw:
            info = json.loads(raw)
            user_id = str(info.get("id") or "")
            username = info.get("username") or info.get("first_name") or ""
    except Exception:
        pass
    return value, user_id, username


def base_headers():
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://hashcow.vercel.app",
        "referer": "https://hashcow.vercel.app/",
        "user-agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
    }


def token_headers(token):
    header = base_headers()
    header["authorization"] = f"Bearer {token}"
    return header


async def api_get(session, path, token, proxy=None):
    try:
        async with session.get(
            BASE_URL + path,
            headers=token_headers(token),
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            raw = await r.read()
            return r.status, json.loads(raw)
    except Exception as e:
        log_red(f"Request to the server failed with {type(e).__name__}.")
        return None, None


async def api_post(session, path, payload, token, proxy=None):
    try:
        async with session.post(
            BASE_URL + path,
            headers=token_headers(token),
            json=payload if payload is not None else {},
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            raw = await r.read()
            return r.status, json.loads(raw)
    except Exception as e:
        log_red(f"Request to the server failed with {type(e).__name__}.")
        return None, None


def error_text(data):
    if isinstance(data, dict):
        return str(data.get("error") or data.get("message") or data.get("reason") or "")
    return ""


async def login(session, init_data, proxy):
    try:
        async with session.post(
            BASE_URL + "/api/auth",
            headers=base_headers(),
            json={"initData": init_data},
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            raw = await r.read()
            return r.status, json.loads(raw)
    except Exception as e:
        log_red(f"Request to the server failed with {type(e).__name__}.")
        return None, None


async def read_state(session, token, proxy):
    return await api_get(session, "/api/state", token, proxy)


async def collect_mining(session, token, proxy):
    status, data = await api_post(session, "/api/mining/collect", None, token, proxy)
    if data and data.get("collected") is not None:
        collected = data.get("collected") or 0
        log_green(f"Mining collection credited {collected} points to this account.")
        return
    reason = error_text(data)
    if reason:
        log_yellow(f"Mining collection says: {reason}.")
    else:
        log_yellow("Mining collection returned no new points on this run.")


async def daily_checkin(session, token, proxy):
    status, data = await api_post(session, "/api/attendance/checkin", None, token, proxy)
    if data and data.get("awarded") is not None:
        awarded = data.get("awarded") or 0
        streak = data.get("streakDay") or 0
        log_green(f"Daily check-in credited {awarded} points on streak day {streak}.")
        return
    reason = error_text(data)
    if reason:
        log_yellow(f"Daily check-in says: {reason}.")
    else:
        log_yellow("Daily check-in was already collected on this account.")


async def claim_ad_spins(session, token, proxy):
    status, data = await api_get(session, "/api/ads/config", token, proxy)
    if not isinstance(data, dict) or not data.get("enabled"):
        log_yellow("Ad rewards are not enabled for this account right now.")
        return
    total = 0
    for _ in range(10):
        status, data = await api_post(session, "/api/ads/reward", {"format": "pop", "placement": "spin"}, token, proxy)
        if not isinstance(data, dict) or not data.get("ok"):
            break
        total += int(data.get("spins") or 0)
        status_block = data.get("status") or {}
        if int(status_block.get("remaining") or 0) <= 0:
            break
    if total:
        log_green(f"Ad rewards added {total} free spins to this account.")
    else:
        log_yellow("Ad rewards returned no new free spins on this run.")


def pick_option(options):
    best = 0
    best_len = -1
    for idx, text in enumerate(options or []):
        size = len(str(text))
        if size > best_len:
            best_len = size
            best = idx
    return best


async def answer_quiz(session, token, proxy):
    status, data = await api_get(session, "/api/quiz", token, proxy)
    if not isinstance(data, dict) or not data.get("ok"):
        reason = (data or {}).get("reason") if isinstance(data, dict) else ""
        if reason:
            log_yellow(f"Daily quiz is not available because of {reason}.")
        else:
            log_yellow("Daily quiz is not available on this account now.")
        return
    question = data.get("q") or {}
    missions = await api_get(session, "/api/missions", token, proxy)
    mission_id = ""
    for item in ((missions[1] or {}).get("missions") or []):
        if item.get("kind") == "quiz" and item.get("state") == "available":
            mission_id = item.get("id")
            break
    if not mission_id:
        log_yellow("Daily quiz mission is not available on this account now.")
        return
    chosen = pick_option(question.get("options"))
    payload = {
        "missionId": mission_id,
        "questionId": question.get("questionId"),
        "chosen": chosen,
        "order": question.get("order"),
    }
    status, data = await api_post(session, "/api/quiz", payload, token, proxy)
    if isinstance(data, dict) and data.get("correct"):
        awarded = data.get("awarded") or 0
        log_green(f"Daily quiz answer was correct and credited {awarded} points.")
        return
    cooldown = (data or {}).get("cooldownSec") if isinstance(data, dict) else None
    if cooldown:
        log_yellow(f"Daily quiz answer was wrong and locked for {cooldown} seconds.")
    else:
        reason = error_text(data)
        if reason:
            log_yellow(f"Daily quiz submission says: {reason}.")
        else:
            log_yellow("Daily quiz submission returned no reward on this run.")


async def play_games(session, token, proxy):
    status, data = await api_get(session, "/api/games", token, proxy)
    games = (data or {}).get("games") if isinstance(data, dict) else None
    if not games:
        log_yellow("Game catalog was not returned by the server for this account.")
        return 0
    played = 0
    for game in games:
        slug = game.get("slug")
        name = game.get("name") or slug
        if not slug or game.get("claimedToday"):
            continue
        status, launch = await api_post(session, "/api/games/launch", {"slug": slug}, token, proxy)
        if not isinstance(launch, dict) or not launch.get("launchUrl"):
            reason = error_text(launch)
            if reason:
                log_yellow(f"Game {name} could not be launched because of {reason}.")
            continue
        wait_seconds = max(int(launch.get("minSeconds") or 30), 30) + 5
        countdown(wait_seconds, f"Playing {name} before the reward claim")
        claim = None
        for attempt in range(4):
            status, claim = await api_post(session, "/api/games/claim", {"slug": slug}, token, proxy)
            if isinstance(claim, dict) and claim.get("ok"):
                break
            if isinstance(claim, dict) and claim.get("notReady") and attempt < 3:
                countdown(15, f"Server still counts the play time of {name}")
                continue
            break
        if isinstance(claim, dict) and claim.get("ok") and (claim.get("awarded") or 0) > 0:
            awarded = claim.get("awarded")
            played += 1
            log_green(f"Game {name} was cleared and credited {awarded} points.")
            continue
        reason = error_text(claim) or str((claim or {}).get("reason") or "")
        if reason:
            log_yellow(f"Game {name} reward claim says: {reason}.")
        else:
            log_yellow(f"Game {name} reward claim returned no points on this run.")
    if not played:
        log_green("Every game reward was already collected for this account today.")
    return played


async def claim_achievements(session, token, proxy):
    status, data = await api_get(session, "/api/games/achievements", token, proxy)
    tiers = (data or {}).get("tiers") if isinstance(data, dict) else None
    ready = [t for t in (tiers or []) if t.get("reached") and not t.get("claimed")]
    if not ready:
        log_yellow("Game achievement tiers were already collected on this account.")
        return
    status, data = await api_post(session, "/api/games/achievements", None, token, proxy)
    if isinstance(data, dict) and data.get("ok"):
        points = data.get("points") or 0
        hcow = data.get("hcow") or 0
        claimed = len(data.get("tiers") or ready)
        log_green(f"{claimed} game achievement tiers credited {points} points and {hcow} HCOW.")
        return
    reason = error_text(data)
    if reason:
        log_yellow(f"Game achievement claim says: {reason}.")
    else:
        log_yellow("Game achievement claim returned no reward on this run.")


async def claim_daily_tasks(session, token, proxy):
    status, data = await api_get(session, "/api/daily", token, proxy)
    tasks = (data or {}).get("tasks") if isinstance(data, dict) else None
    if not tasks:
        log_yellow("Daily task list was not returned by the server for this account.")
        return
    claimed = 0
    for task in tasks:
        if not task.get("done") or task.get("claimed"):
            continue
        status, res = await api_post(session, "/api/daily", {"key": task.get("key")}, token, proxy)
        if isinstance(res, dict) and res.get("ok"):
            awarded = res.get("awarded") or 0
            claimed += 1
            log_green(f"Daily task {task.get('title')} credited {awarded} points to this account.")
            continue
        reason = error_text(res)
        if reason:
            log_yellow(f"Daily task {task.get('title')} claim says: {reason}.")
    if not claimed:
        log_green("All daily task rewards were already collected on this account.")
    status, res = await api_post(session, "/api/daily/combo", None, token, proxy)
    if isinstance(res, dict) and res.get("ok"):
        awarded = res.get("awarded") or 0
        log_green(f"Daily game combo bonus credited {awarded} points to this account.")
    else:
        log_yellow("Daily game combo bonus was not available on this run.")


async def run_missions(session, token, proxy):
    status, data = await api_get(session, "/api/missions", token, proxy)
    missions = (data or {}).get("missions") if isinstance(data, dict) else None
    if not missions:
        log_yellow("Mission list was not returned by the server for this account.")
        return
    done = 0
    for item in missions:
        kind = item.get("kind") or ""
        if item.get("state") != "available":
            continue
        if kind not in ("visit_link", "tg_join_channel", "tg_join_group", "bot_contact"):
            continue
        mission_id = item.get("id")
        if kind == "bot_contact":
            path = "/api/missions/submit"
        else:
            path = "/api/missions/claim-visit"
        status, res = await api_post(session, path, {"missionId": mission_id}, token, proxy)
        if isinstance(res, dict) and (res.get("status") == "verified" or res.get("ok")):
            awarded = res.get("awarded") or 0
            done += 1
            log_green(f"Mission {item.get('title')} was verified and credited {awarded} points.")
            continue
        reason = error_text(res)
        if reason:
            log_yellow(f"Mission {item.get('title')} says: {reason}.")
    if not done:
        log_green("No mission was verifiable automatically for this account now.")


async def claim_friends_milestone(session, token, proxy):
    status, data = await api_post(session, "/api/friends/milestone", None, token, proxy)
    if isinstance(data, dict) and data.get("ok"):
        points = data.get("points") or 0
        hcow = data.get("hcow") or 0
        log_green(f"Friend milestone credited {points} points and {hcow} HCOW on this account.")
        return
    reason = error_text(data)
    if reason:
        log_yellow(f"Friend milestone claim says: {reason}.")
    else:
        log_yellow("Friend milestone had nothing claimable on this run.")


async def spin_until_spent(session, token, proxy):
    status, data = await read_state(session, token, proxy)
    user = (data or {}).get("user") if isinstance(data, dict) else None
    if not user:
        log_yellow("Spin phase could not read the account balance on this run.")
        return
    free_spins = int(user.get("freeSpins") or 0)
    points = int(float(user.get("pointsBalance") or 0))
    cost = int(float((data.get("spinCost") or {}).get("base") or 10000))
    spins = 0
    won_points = 0
    won_hcow = 0.0
    budget = free_spins + 400
    for _ in range(budget):
        if free_spins > 0:
            free_spins -= 1
        elif points >= cost:
            points -= cost
        else:
            break
        status, res = await api_post(session, "/api/spin", {"count": 1}, token, proxy)
        if not isinstance(res, dict) or not res.get("results"):
            reason = error_text(res)
            if reason:
                log_yellow(f"Spin was refused by the server because of {reason}.")
            break
        spins += 1
        summary = res.get("summary") or {}
        won_points += int(summary.get("points") or 0)
        won_hcow += float(summary.get("hcow") or 0)
        won = int(summary.get("spins") or 0)
        if won:
            free_spins += won
        balances = res.get("balances") or {}
        if balances.get("pointsBalance") is not None:
            points = int(float(balances["pointsBalance"]))
    if spins:
        log_green(f"{spins} wheel spins were spent for {won_points} points and {won_hcow} HCOW total.")
    else:
        log_yellow("No wheel spin was affordable or available for this account.")


async def process_account(line, proxy, index):
    init_data, user_id, username = parse_account(line)
    if not init_data or not user_id:
        log_red(f"Credential line {index + 1} is not valid initData.")
        return

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        status, data = await login(session, init_data, proxy)
        token = (data or {}).get("token") if isinstance(data, dict) else None
        if not token:
            reason = error_text(data)
            if reason:
                log_red(f"Account login was refused by the server because of {reason}.")
            else:
                log_red("Failed to retrieve account state.")
            return

        user = (data or {}).get("user") or {}
        name = user.get("username") or user.get("firstName") or username or "player"
        points = user.get("pointsBalance") or 0
        log_green(f"Player {name} signed in with {points} points on the balance.")

        await collect_mining(session, token, proxy)
        await daily_checkin(session, token, proxy)
        await claim_ad_spins(session, token, proxy)
        await play_games(session, token, proxy)
        await claim_achievements(session, token, proxy)
        await claim_daily_tasks(session, token, proxy)
        await answer_quiz(session, token, proxy)
        await run_missions(session, token, proxy)
        await claim_friends_milestone(session, token, proxy)
        await spin_until_spent(session, token, proxy)

        status, data = await read_state(session, token, proxy)
        user = (data or {}).get("user") or user
        log_green(
            f"Account totals {user.get('pointsBalance', 0)} points with "
            f"{user.get('hcowPromisedTotal', 0)} HCOW earned so far."
        )


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {cycle}.")
        for idx, line in enumerate(accounts):
            if idx > 0:
                print()
            proxy_url = normalize_proxy(get_proxy(proxies, idx))
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}.")
            await process_account(line, proxy_url, idx)
        log_yellow(f"All accounts processed for cycle number {cycle}.")
        countdown(sleep_secs, "Next cycle starts in")
        cycle += 1
        show_banner(MY_PROJECT)


def main():
    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = load_config()
    sleep_secs = config.get("settings", {}).get("sleep_seconds", 3600)
    accounts = load_accounts()
    proxies = load_proxies()
    asyncio.run(main_async(accounts, proxies, sleep_secs))


if __name__ == "__main__":
    main()
