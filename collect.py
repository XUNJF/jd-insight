import time
from datetime import datetime

import psycopg2
import requests

API = "https://www.v2ex.com/api/topics/show.json?node_name=jobs"
HEADERS = {"User-Agent": "Mozilla/5.0 (jd-insight/0.1;personal project)"}
DSN = "host=127.0.0.1 port=5432 dbname=jd user=postgres password=devpass"


def fetch_topics():
    r = requests.get(API, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"接口返回{r.status_code}:{r.text[:200]}")
    return r.json()

def save_topics(conn, topics):
    sql = """
        INSERT INTO jobs (source_id, url, title, content, posted_at, replies)
        VALUES(%s,%s,%s,%s,%s,%s)
        ON CONFLICT (source_id) DO NOTHING
    """
    inserted = 0
    with conn.cursor() as cur:
        for t in topics:
            created = t.get("created")
            cur.execute(sql,(
                str(t["id"]),
                t.get("url"),
                t.get("title","").strip(),
                t.get("content",""),
                datetime.fromtimestamp(created) if created else None,
                t.get("replies",0),
            ))
            inserted += cur.rowcount
    conn.commit()
    return inserted


if __name__ == "__main__":
    topics =fetch_topics()
    print(f"  接口返回 {len(topics)} 条")
    conn = psycopg2.connect(DSN)
    try:
        n = save_topics(conn, topics)
    finally:
        conn.close()
    print(f"  实际新增 {n} 条（重复的已跳过）")