import os
import sqlite3
import random
import requests
import re
import time
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

DB = "faals.db"
DATA_URL = "https://raw.githubusercontent.com/Matinsojoudi/faal-hafez/refs/heads/main/create_db.py"

IRAN_OFFSET = timedelta(hours=3, minutes=30)
MAX_RETRY = 5

MONTHS = {
    1: ("فروردین", "🐏"),
    2: ("اردیبهشت", "🐂"),
    3: ("خرداد", "🦋"),
    4: ("تیر", "🦀"),
    5: ("مرداد", "🦁"),
    6: ("شهریور", "🌾"),
    7: ("مهر", "⚖️"),
    8: ("آبان", "🦂"),
    9: ("آذر", "🏹"),
    10: ("دی", "🐐"),
    11: ("بهمن", "🏺"),
    12: ("اسفند", "🐟"),
}


def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS faals (
            id INTEGER PRIMARY KEY,
            Poem TEXT,
            Interpretation TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent (
            month INTEGER,
            fal_id INTEGER,
            day TEXT,
            UNIQUE(month, fal_id, day)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            attempts INTEGER DEFAULT 0,
            last_error TEXT,
            locked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY,
            last_run TEXT
        )
    """)

    cur.execute("INSERT OR IGNORE INTO state (id, last_run) VALUES (1, '')")

    conn.commit()
    conn.close()


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    err = None

    for i in range(MAX_RETRY):
        try:
            r = requests.post(
                url,
                json={
                    "chat_id": CHANNEL_ID,
                    "text": text,
                    "parse_mode": "HTML"
                },
                timeout=20
            )

            if r.status_code == 200:
                return True, None

        except Exception as e:
            err = str(e)

        time.sleep(2 ** i)

    return False, err


def enqueue(message):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO queue (message) VALUES (?)", (message,))
    conn.commit()
    conn.close()


def process_queue():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, message, attempts
        FROM queue
        WHERE status='pending' AND locked=0
        ORDER BY id ASC
    """)

    rows = cur.fetchall()

    for qid, msg, attempts in rows:

        cur.execute("UPDATE queue SET locked=1 WHERE id=?", (qid,))
        conn.commit()

        success, err = send_to_telegram(msg)

        if success:
            cur.execute("""
                UPDATE queue
                SET status='sent',
                    locked=0
                WHERE id=?
            """, (qid,))
        else:
            status = "pending" if attempts + 1 < MAX_RETRY else "failed"

            cur.execute("""
                UPDATE queue
                SET attempts=?,
                    last_error=?,
                    status=?,
                    locked=0
                WHERE id=?
            """, (attempts + 1, err, status, qid))

        conn.commit()
        time.sleep(1)

    conn.close()


def load_faals():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM faals")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    text = requests.get(DATA_URL, timeout=60).text

    pattern = r"\(\s*(\d+)\s*,\s*'([\s\S]*?)'\s*,\s*'([\s\S]*?)'\s*\)"
    rows = re.findall(pattern, text)

    clean_rows = []
    for r in rows:
        fid = int(r[0])
        poem = r[1].replace("\\r\\n", "\n").replace("\\n", "\n")
        interp = r[2].replace("\\r\\n", "\n").replace("\\n", "\n")
        clean_rows.append((fid, poem, interp))

    cur.executemany("INSERT OR REPLACE INTO faals VALUES (?,?,?)", clean_rows)

    conn.commit()
    conn.close()


def get_used(month, day):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT fal_id FROM sent WHERE month=? AND day=?", (month, day))
    used = [i[0] for i in cur.fetchall()]
    conn.close()
    return used


def pick_fal(exclude):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    if exclude:
        q = f"SELECT * FROM faals WHERE id NOT IN ({','.join(['?']*len(exclude))})"
        cur.execute(q, exclude)
    else:
        cur.execute("SELECT * FROM faals")

    rows = cur.fetchall()

    if not rows:
        cur.execute("SELECT * FROM faals")
        rows = cur.fetchall()

    conn.close()
    return random.choice(rows)


def save(month, fid, day):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT OR IGNORE INTO sent VALUES (?,?,?)",
        (month, fid, day)
    )
    conn.commit()
    conn.close()


def extract_bit(poem):
    lines = [x.strip() for x in poem.split("\r\n") if x.strip()]
    pairs = [(lines[i], lines[i+1] if i+1 < len(lines) else "")
             for i in range(0, len(lines), 2)]

    if not pairs:
        return ""

    a, b = random.choice(pairs)
    return (a + "\n" + b).strip()


def build(month, emoji, bit, interp):
    name = MONTHS[month][0]
    return f"""📖 <b>فال و سرگرمی</b>
{emoji} متولدین {name}

🌺🍂🍃🌺🍂🍃🌺🍂🍃

<b>{bit}</b>

{interp}

🌺
🍂
🍃
🌺🍂
🍂🍃🌺
🍃🌺🍂🍃
🌺🍂🍃🌺🍂🍃🌺🍂🍃

➖➖➖➖➖➖➖➖
<blockquote>@aristapanel</blockquote>
➖➖➖➖➖➖➖➖
#فال_حافظ #سرگرمی #آریستا"""


def acquire_lock():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    today = str(datetime.now().date())

    cur.execute("SELECT last_run FROM state WHERE id=1")
    last = cur.fetchone()[0]

    if last == today:
        conn.close()
        return False

    cur.execute("UPDATE state SET last_run=? WHERE id=1", (today,))
    conn.commit()
    conn.close()
    return True


def get_today_key():
    now = datetime.now(timezone.utc) + IRAN_OFFSET
    return str(now.date())


def enqueue_daily_batch():
    day = get_today_key()

    for month in range(1, 13):

        used = get_used(month, day)
        fid, poem, interp = pick_fal(used)

        bit = extract_bit(poem)
        text = build(month, MONTHS[month][1], bit, interp)

        enqueue(text)
        save(month, fid, day)


def run():
    init_db()
    load_faals()

    if not acquire_lock():
        return

    enqueue_daily_batch()
    process_queue()


if __name__ == "__main__":
    run()
