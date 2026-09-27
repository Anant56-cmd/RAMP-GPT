"""
Golden Queries Management Utility
Manages verified golden queries in data/golden_queries.json (Single Source of Truth).

Usage:
  python manage_golden_queries.py --list
  python manage_golden_queries.py --count
  python manage_golden_queries.py --add --query "..." --sql "..."
  python manage_golden_queries.py --delete --query "..."
  python manage_golden_queries.py --validate
"""

import os
import json
import argparse
import re

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
JSON_PATH = os.path.join(PROJECT_ROOT, "data", "golden_queries.json")

def load_queries():
    if not os.path.exists(JSON_PATH):
        return []
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error reading {JSON_PATH}: {e}")
        return []

def save_queries(queries):
    try:
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(queries, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[!] Error writing to {JSON_PATH}: {e}")
        return False

def normalize(text):
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())

def list_queries(filter_term=None):
    queries = load_queries()
    if not queries:
        print("No golden queries found.")
        return
    
    count = 0
    print(f"\n{'='*70}\nGolden Queries ({len(queries)} total in {JSON_PATH})\n{'='*70}")
    for idx, item in enumerate(queries, 1):
        q = item.get("query", "")
        sql = item.get("sql", "").replace("\n", " ").strip()
        if filter_term and filter_term.lower() not in q.lower() and filter_term.lower() not in sql.lower():
            continue
        count += 1
        print(f"\n[{idx}] Question: {q}")
        print(f"    SQL: {sql[:120]}{'...' if len(sql) > 120 else ''}")
    print(f"\nDisplayed {count} / {len(queries)} queries.\n")

def count_queries():
    queries = load_queries()
    print(f"Total golden queries: {len(queries)}")

def add_query(query_text, sql_text):
    if not query_text or not sql_text:
        print("[!] Both --query and --sql must be non-empty.")
        return
    
    queries = load_queries()
    norm_target = normalize(query_text)
    updated = False
    
    for item in queries:
        if normalize(item.get("query", "")) == norm_target:
            item["query"] = query_text.strip()
            item["sql"] = sql_text.strip()
            updated = True
            print(f"[+] Updated existing query: \"{query_text.strip()}\"")
            break
            
    if not updated:
        queries.append({
            "query": query_text.strip(),
            "sql": sql_text.strip()
        })
        print(f"[+] Added new golden query: \"{query_text.strip()}\"")
        
    if save_queries(queries):
        print(f"[OK] Successfully saved. Total entries: {len(queries)}")

def delete_query(query_text):
    if not query_text:
        print("[!] Must specify --query to delete.")
        return
        
    queries = load_queries()
    norm_target = normalize(query_text)
    initial_len = len(queries)
    
    new_queries = [item for item in queries if normalize(item.get("query", "")) != norm_target]
    
    if len(new_queries) == initial_len:
        print(f"[-] No matching query found for: \"{query_text}\"")
        return
        
    if save_queries(new_queries):
        print(f"[OK] Deleted 1 query. Total remaining entries: {len(new_queries)}")

def validate_queries():
    queries = load_queries()
    print(f"Validating {len(queries)} golden queries...")
    issues = []
    seen = {}
    
    for idx, item in enumerate(queries, 1):
        q = item.get("query", "").strip()
        s = item.get("sql", "").strip()
        
        if not q:
            issues.append(f"Item #{idx}: Missing or empty 'query'")
        if not s:
            issues.append(f"Item #{idx}: Missing or empty 'sql'")
        elif not re.match(r"^(SELECT|WITH)\b", s, re.IGNORECASE):
            issues.append(f"Item #{idx}: SQL does not start with SELECT or WITH ('{s[:30]}...')")
            
        norm = normalize(q)
        if norm in seen:
            issues.append(f"Item #{idx}: Duplicate query text with item #{seen[norm]} ('{q}')")
        else:
            seen[norm] = idx

    if issues:
        print(f"[!] Validation failed with {len(issues)} issue(s):")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print(f"[OK] All {len(queries)} queries are valid! No duplicates, all queries have valid SELECT/WITH SQL statements.")

def main():
    parser = argparse.ArgumentParser(description="Manage Golden Queries in data/golden_queries.json")
    parser.add_argument("--list", action="store_true", help="List all golden queries")
    parser.add_argument("--count", action="store_true", help="Show count of golden queries")
    parser.add_argument("--filter", type=str, default=None, help="Filter query list by keyword")
    parser.add_argument("--add", action="store_true", help="Add or update a golden query (requires --query and --sql)")
    parser.add_argument("--delete", action="store_true", help="Delete a golden query (requires --query)")
    parser.add_argument("--validate", action="store_true", help="Validate all queries and SQL formatting")
    parser.add_argument("--query", type=str, help="Question text")
    parser.add_argument("--sql", type=str, help="SQL query text")

    args = parser.parse_args()

    if args.list:
        list_queries(args.filter)
    elif args.count:
        count_queries()
    elif args.add:
        add_query(args.query, args.sql)
    elif args.delete:
        delete_query(args.query)
    elif args.validate:
        validate_queries()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
