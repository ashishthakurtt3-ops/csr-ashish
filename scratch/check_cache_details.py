import os, sqlite3

cache_path = os.path.join(os.getcwd(), ".cache", "ai_classifier", "ai_cache.sqlite3")
conn = sqlite3.connect(cache_path)
cur = conn.cursor()
rows = cur.execute("SELECT stage, model_name, provider, created_at, count(*) FROM ai_cache GROUP BY stage, model_name, provider, created_at").fetchall()
print("Grouped by created_at:")
for r in rows[:20]:
    print(r)

rows_summary = cur.execute("SELECT stage, model_name, provider, min(created_at), max(created_at), count(*) FROM ai_cache GROUP BY stage, model_name, provider").fetchall()
print("\nSummary:")
for r in rows_summary:
    print(r)
conn.close()

