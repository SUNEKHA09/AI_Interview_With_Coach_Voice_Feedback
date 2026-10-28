import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

DB = str(Path(__file__).parent / "coach.db")


def _c():
    return sqlite3.connect(DB)


def init():
    with _c() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, role TEXT, level TEXT,
            avg_score REAL, fillers INTEGER, avg_wpm REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS answers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, question TEXT,
            answer TEXT, score REAL, weak_topic TEXT)""")


def save_session(role, level, results):
    scores = [r["ev"]["score"] for r in results]
    fillers = sum(sum(r["fillers"].values()) for r in results)
    wpms = [r["wpm"] for r in results if r["wpm"]]
    conn = _c()
    try:
        cur = conn.execute(
            "INSERT INTO sessions(ts,role,level,avg_score,fillers,avg_wpm) VALUES(?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), role, level,
             round(sum(scores) / len(scores), 2), fillers,
             round(sum(wpms) / len(wpms), 1) if wpms else None))
        sid = cur.lastrowid
        for r in results:
            conn.execute(
                "INSERT INTO answers(session_id,question,answer,score,weak_topic) VALUES(?,?,?,?,?)",
                (sid, r["q"], r["answer"], r["ev"]["score"], r["ev"].get("weak_topic", "")))
        conn.commit()
    finally:
        conn.close()


def sessions():
    conn = _c()
    try:
        return conn.execute(
            "SELECT id,ts,role,level,avg_score,fillers,avg_wpm FROM sessions ORDER BY id").fetchall()
    finally:
        conn.close()


def weak_topics(role, limit=3):
    conn = _c()
    try:
        rows = conn.execute("""SELECT a.weak_topic FROM answers a JOIN sessions s ON s.id=a.session_id
                               WHERE s.role=? AND a.score<7""", (role,)).fetchall()
    finally:
        conn.close()
    return [t for t, _ in Counter(r[0] for r in rows if r[0]).most_common(limit)]


def all_weak_counts():
    conn = _c()
    try:
        rows = conn.execute("SELECT weak_topic FROM answers WHERE score<7").fetchall()
    finally:
        conn.close()
    return Counter(r[0] for r in rows if r[0])


def streak():
    days = sorted({datetime.fromisoformat(s[1]).date() for s in sessions()}, reverse=True)
    if not days or days[0] < date.today() - timedelta(days=1):
        return 0
    n = 1
    for a, b in zip(days, days[1:]):
        if (a - b).days == 1:
            n += 1
        else:
            break
    return n


def badges():
    s = sessions()
    b = []
    if len(s) >= 1:
        b.append("🥇 First Step")
    if len(s) >= 3:
        b.append("🔥 Consistent (3+ sessions)")
    if any(x[4] >= 8 for x in s):
        b.append("🌟 High Scorer (8+)")
    if any(x[5] <= 3 for x in s):
        b.append("🎯 Smooth Talker")
    if len(s) >= 2 and s[-1][4] > s[0][4]:
        b.append("📈 Improver")
    return b


def clear_history():
    with _c() as c:
        c.execute("DELETE FROM answers")
        c.execute("DELETE FROM sessions")