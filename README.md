<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=HCOW%20Spin%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Points%7CSpins%7CGames%7CMulti%20Account%7CCountdown"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Full%20daily%20cycle%20automation%20for%20the%20HCOW%20Spin%20Miniapp;The%20mining%20is%20collected%20and%20the%20daily%20check-in%20is%20credited%20first;Every%20game%20is%20cleared%20and%20its%20reward%20is%20claimed%20after%20the%20server%20timer;Free%20spins%20and%20the%20whole%20point%20balance%20are%20spent%20on%20the%20wheel;Multi%20account%20with%20proxy%20support%20and%20a%20live%20countdown%20between%20cycles"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-HCOW%20Spin%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>HCOW Spin Bot</b> is a full automation bot for the HCOW Spin Telegram Miniapp.<br/>
  It runs the complete free daily cycle: the login is settled from the credential itself, the mining is collected, the daily check-in is credited, the ad rewards are turned into free spins, every game in the catalog is cleared and its reward claimed after the server timer, the achievement tiers, the daily task board, the game combo bonus, the daily quiz, the verifiable missions and the friend milestone are all claimed, and the whole point balance that is left is spent on the wheel. Every credited amount is printed only after the server confirms it, and all accounts run one after another with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Hcow-Miniapp.git
cd Hcow-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with the Telegram WebApp `initData` string of each account, one per line:

```
query_id=AAH...&user=%7B%22id%22%3A6004380466...&auth_date=1759...&hash=c41a...
query_id=AAH...&user=%7B%22id%22%3A7113873680...&auth_date=1759...&hash=9f2c...
```

> `initData` can be obtained from the browser DevTools when opening HCOW Spin on Telegram Web. The bot reads the Telegram user id out of the string itself; nothing is typed in by hand. The referral is carried inside the `initData` string as the start parameter of the link the credential was minted from, so an account is bound to its inviter at the first login and no extra field is needed.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

```json
{
  "settings": {
    "sleep_seconds": 3600
  }
}
```

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Account Sign-In

Every credential line is traded for a session on the login call, and the same session token is used for the rest of the cycle. The player name and the point balance are printed exactly as the server returns them. A line that holds no valid initData, or an account the server refuses, is reported in red with the reason string.

### Mining Collection

The pending mining is collected on every cycle and the credited amount is printed only when the server confirms it, together with the new pending value it sends back.

### Daily Check-In

The daily attendance check-in is credited once per day and the awarded amount is printed together with the streak day the server reports. An account that already checked in is reported in yellow instead.

### Ad Rewards

When the ad rewards are enabled for the account, the reward call is repeated until the server reports no remaining ad slot, and the free spins it grants are printed in green. An account with ad rewards switched off is reported in yellow.

### Game Clearing

The full game catalog is read from the server and every game whose reward was not collected today is launched, waited out for the exact timer the server returns for that game plus a small safety margin, and then claimed. The credited amount is printed per game in green, so the timer, the reward and the game names all come from the server instead of being written into the bot.

### Achievement Tiers

The game achievement tiers are read from the server and the ones that are reached but not collected yet are claimed in a single call, so the credited point and HCOW amounts are printed exactly as the server returns them.

### Daily Task Board

The daily task board is read from the server and every finished but uncollected task is claimed by its own key, then the game combo bonus is collected on top. Every credited task prints its title and the awarded points, and a task board that is already fully collected is reported in green.

### Daily Quiz

The daily quiz question and its options are read from the server, the mission id is taken from the mission list, and the answer is submitted with the exact question id and the option order the server sent, so a wrong answer only costs the cooldown the server reports instead of breaking the cycle.

### Missions

The mission list is read from the server and every automatically verifiable mission is settled through the matching rail: link visits and channel or group joins are verified directly, while the bot contact mission is submitted once the chat was opened. Missions that need an X account are left untouched, and every verified mission prints its title and the awarded points.

### Friend Milestone

The friend milestone claim is called on every cycle and the credited points and HCOW are printed when the server confirms them. A milestone that has nothing claimable is reported in yellow with the reason string.

### Wheel Spins

The free spins the account holds are spent first, then the remaining point balance is spent on the wheel at the price the server reports, and the loop keeps spinning until the balance can no longer pay for a spin. The spin count, the points won and the HCOW won across the whole run are printed in a single green line, so the whole balance really is used up instead of being left on the table.

### Multi Account

All accounts in `data.txt` are processed one after another in the order they are listed within every cycle. The cycle number is logged at the start of each round, and each account block is separated by a blank line.

### Proxy Support

Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown

After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
HCOWSpin-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
├── README.md       # This documentation
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>