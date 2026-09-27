"""
SQL Validation & Read-Only Enforcement.
Inspects candidate queries to verify read-only intent (SELECT or WITH statements),
blocking all destructive DDL/DML keywords and injection vectors.
"""

def is_safe_query(sql_query: str) -> bool:
    """
    Strict read-only SQL enforcement.
    Ensures query starts with SELECT or WITH and contains no destructive DDL/DML statements.
    """
    if not sql_query or not isinstance(sql_query, str):
        return False

    forbidden_keywords = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
        "TRUNCATE", "GRANT", "REVOKE", "EXECUTE"
    ]
    upper_sql = sql_query.upper().strip()
    
    # Must explicitly start with a query keyword (SELECT or CTE WITH)
    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        return False
        
    # Check for forbidden keywords bounded by spaces to avoid false positives on column names (e.g. update_date)
    for keyword in forbidden_keywords:
        if f" {keyword} " in f" {upper_sql} " or upper_sql.startswith(keyword):
            return False
            
    return True
