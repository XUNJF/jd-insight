import json
import re
import time

import psycopg2
import requests

API = "https://api.deepseek.com/chat/completions"
DSN = "host=127.0.0.1 port=5432 dbname=jd user=postgres password=devpass"
KEY = open(r"D:\code\python-practice\day46-47\key.txt", encoding="utf-8").read().strip()


PROMPT ="""你是信息抽取助手。从下面的招聘帖中提取结构化信息。

只输出一个JSON对象，不要任何解释，不要用markdown代码块包裹。

字段说明：
-company：招聘公司名称，原文没提则为null
-job_title：岗位名称。如果一个帖子只招 1-3 个岗位，用一个字符串表示，用「、」连接；
            如果招 4 个以上（批量招聘/岗位列表），填 null
-city：工作城市，一律用中文城市名（如"上海""杭州"），不要用英文名（Shanghai），原文没提则为 null
-salary：薪资，保留原文写法，原文没提则为null
-experience：经验要求，保留原文写法，原文没提则为null
-tech_stack：这个岗位要求的技术名称数组。判断标准是「能不能写进简历的技能栏」。
  包括：
    · 编程语言、框架、库、数据库、中间件、云服务、开发工具
    · AI 应用开发相关：RAG、Agent、Prompt 工程、Function Calling、
      向量数据库、Embedding、Rerank、多轮对话、记忆系统 等
  例如 ["Java", "Golang", "Netty", "RAG", "Agent", "LangChain", "向量数据库"]
  不要包含：
    · 公司名（Meta / Stripe）、广告或产品平台名（Google Ads）
    · 纯能力描述（如"高并发""分布式""微服务架构""可扩展"）
    · 过于宽泛的词（如"AI""LLM""大模型"）

严格要求：
-不要推测，不要补全，不要根据常识填空
-原文没有的信息一律null或【】
-只提取原文中明确写出来的内容

【招聘帖】
标题：{title}

正文：
{content}
"""

FIELDS = ["company","job_title","city","salary","experience"]

STOPWORDS = {
    "ai", "llm", "大模型", "人工智能",
}

def normalize_tech_stack(items):
    out, seen = [], set()
    for x in items:
        k = x.strip().lower()
        if not k or k in STOPWORDS or k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
    return out

def normalize_job_title(title):
    if not title:
        return None
    t = title.strip()
    return t if len(t) <= 40 else None


def call_model(title, content):
    """调模型，返回解析后的 dict"""
    body = PROMPT.format(title=title, content=(content or "")[:3000])
    r = requests.post(
        API,
        headers={"Authorization":f"Bearer {KEY}", "Content-Type":"application/json"},
        json={
            "model":"deepseek-flash",
            "messages":[{"role":"user","content":body}]
        },
        timeout=90,
    )
    d = r.json()
    if "choices" not in d:
        raise RuntimeError(f"接口异常:{d}")
    text = d["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:json)?\s*","",text)
    text = re.sub(r"\s*```$","",text)
    return json.loads(text)



def validate(obj):
    if not isinstance(obj, dict):
        raise ValueError("返回的不是JSON对象")
    for f in FIELDS:
        v =obj.get(f)
        if v is not None and not isinstance(v, str):
            raise ValueError(f"{f}应该是字符串或null，实际是{type(v).__name__}")
    ts = obj.get("tech_stack",[])
    if not isinstance(ts,list) or any(not isinstance(x, str)for x in ts):
        raise ValueError(f"tech_stack应该是字符串数组，实际是{ts!r}")
    return obj


def main():
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id,title,content FROM jobs
                WHERE extracted_at IS NULL
                ORDER BY id
            """)
            rows = cur.fetchall()
        print(f"  待抽取 {len(rows)} 条")
        ok = fail = 0
        for rid, title, content in rows:
            try:
                obj = validate(call_model(title,content))
                obj["tech_stack"] = normalize_tech_stack(obj.get("tech_stack",[]))
                obj["job_title"] = normalize_job_title(obj.get("job_title"))
            except Exception as e:
                print(f"  ✗ id={rid} {type(e).__name__}:{str(e)[:80]}")
                fail += 1
                continue
            with conn.cursor() as cur:
                cur.execute("""
                        UPDATE jobs SET
                            company = %s, job_title = %s, city = %s,
                            salary = %s, experience = %s, tech_stack = %s,
                            extracted_at = NOW()
                        WHERE id = %s
                    """,(
                        obj.get("company"),obj.get("job_title"),obj.get("city"),
                        obj.get("salary"),obj.get("experience"),
                        json.dumps(obj.get("tech_stack",[]),ensure_ascii=False),
                        rid,
                    ))
            conn.commit()
            ok += 1
            print(f"  ✓ id={rid}  {obj.get('job_title') or '-'} | {obj.get('city') or '-'} | {len(obj.get('tech_stack', []))} 个技术词")
        print(f"\n  完成：成功 {ok} 条，失败 {fail} 条")
    finally:
        conn.close()


if __name__ =="__main__":
    main()  