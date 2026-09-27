"""
SQL Self-Healing Interceptor Engine.
Applies a 10-layer deterministic regex and heuristic pipeline to correct common LLM
schema hallucinations, join errors, column mismatches, and multi-brand comparisons
prior to MySQL execution.
"""
import re
from typing import Optional
from app.services.schema_router import VEHICLE_SYNONYMS

def heal_sql_query(clean_sql: str, effective_query: str) -> str:
    """
    Applies a 10-layer heuristic and regex interceptor pipeline to heal
    common LLM schema hallucinations and syntax mistakes before database execution.
    """
    # 0. Canonicalize vehicle model synonyms
    for short_name, full_name in VEHICLE_SYNONYMS.items():
        clean_sql = re.sub(
            rf"(=\s*['\"]){re.escape(short_name)}(['\"])",
            rf"\g<1>{full_name}\g<2>",
            clean_sql,
            flags=re.IGNORECASE
        )
        clean_sql = re.sub(
            rf"(LIKE\s*['\"]%?){re.escape(short_name)}(%?['\"])",
            rf"\g<1>{full_name}\g<2>",
            clean_sql,
            flags=re.IGNORECASE
        )

    # 1. Alias correction: if s.total_amt is present but 'vehicle_service_details s' was written
    if "s.total_amt" in clean_sql:
        clean_sql = re.sub(
            r'\bvehicle_service_details\s+s\b',
            'vehicle_service_summary s',
            clean_sql,
            flags=re.IGNORECASE
        )

    # 2. Repair hallucinated job_card_id in s or d
    clean_sql = re.sub(
        r'\b([sd])\.job_card_id\s*=\s*j\.job_card_id\b',
        r'\1.vehicle_svc_id = j.vehicle_svc_id AND \1.customer_id = j.customer_id',
        clean_sql,
        flags=re.IGNORECASE
    )
    clean_sql = re.sub(
        r'\bj\.job_card_id\s*=\s*([sd])\.job_card_id\b',
        r'j.vehicle_svc_id = \1.vehicle_svc_id AND j.customer_id = \1.customer_id',
        clean_sql,
        flags=re.IGNORECASE
    )

    # 3. Repair hallucinated service_id -> vehicle_svc_id
    clean_sql = re.sub(
        r'\b([csjde])\.service_id\b',
        r'\1.vehicle_svc_id',
        clean_sql,
        flags=re.IGNORECASE
    )

    # 4. Repair supervisor join hallucinations
    if re.search(r'INNER\s+JOIN\s+employee_info\s+e\s+ON\s+[sd]\.supervisor_id\s*=\s*e\.employee_id', clean_sql, re.IGNORECASE):
        has_s = bool(re.search(r'\bvehicle_service_summary\s+s\b', clean_sql, re.IGNORECASE))
        clean_sql = re.sub(
            r'\s*INNER\s+JOIN\s+employee_info\s+e\s+ON\s+[sd]\.supervisor_id\s*=\s*e\.employee_id',
            '',
            clean_sql,
            flags=re.IGNORECASE
        )
        if not has_s and re.search(r'\bvehicle_service_details\s+d\b', clean_sql, re.IGNORECASE):
            clean_sql = re.sub(
                r'(\bFROM\s+vehicle_service_details\s+d\b)',
                r'\1 INNER JOIN vehicle_service_summary s ON d.vehicle_svc_id = s.vehicle_svc_id AND d.customer_id = s.customer_id',
                clean_sql,
                flags=re.IGNORECASE
            )
        clean_sql = re.sub(
            r"e\.first_name\s*=\s*['\"](\w+)['\"]\s*AND\s*e\.last_name\s*=\s*['\"](\w+)['\"]",
            r"s.supervisor_name = '\1 \2'",
            clean_sql,
            flags=re.IGNORECASE
        )
        clean_sql = re.sub(
            r"CONCAT\s*\(\s*e\.first_name\s*,\s*['\"]\s+['\"]\s*,\s*e\.last_name\s*\)",
            's.supervisor_name',
            clean_sql,
            flags=re.IGNORECASE
        )
        clean_sql = re.sub(
            r'e\.first_name\s*,\s*e\.last_name',
            's.supervisor_name',
            clean_sql,
            flags=re.IGNORECASE
        )
        clean_sql = re.sub(r'\be\.first_name\b', 's.supervisor_name', clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r'\be\.last_name\b', "''", clean_sql, flags=re.IGNORECASE)

    # 5. Repair hallucinated bill_type column (Labour -> 'S', Parts -> 'PR')
    clean_sql = re.sub(r"\b[sd]\.bill_type\s*=\s*['\"]Labour['\"]", "d.service_type_cd = 'S'", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"\bbill_type\s*=\s*['\"]Labour['\"]", "service_type_cd = 'S'", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"\b[sd]\.bill_type\s*=\s*['\"]Parts['\"]", "d.service_type_cd = 'PR'", clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"\bbill_type\s*=\s*['\"]Parts['\"]", "service_type_cd = 'PR'", clean_sql, flags=re.IGNORECASE)

    # 6. Repair hallucinated technician_details / workshop_details table names
    clean_sql = re.sub(r'\btechnician_details\b', 'employee_info', clean_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r'\bworkshop_details\b', 'workshop_info', clean_sql, flags=re.IGNORECASE)

    # 7. Repair hallucinated customer_city -> city
    clean_sql = re.sub(r'\b([c])\.customer_city\b', r'\1.city', clean_sql, flags=re.IGNORECASE)

    # 8. Repair Visit-level vs Line-item level average/total cost confusion
    # If the user asked about overall service cost/average bill/service expenditure and did not specify parts or labour,
    # but the model queried vehicle_service_details (d.amount), heal it to vehicle_service_summary (s.total_amt).
    is_generic_cost_query = bool(re.search(r'\b(average|avg|overall|mean)\s+(service\s+)?(cost|bill|amount|charge|expenditure)\b|\baverage\s+cost\b', effective_query, re.IGNORECASE))
    has_explicit_item_filter = bool(re.search(r'\b(part|parts|spare|spares|labour|labor|line\s*item|desc)\b', effective_query, re.IGNORECASE))
    if is_generic_cost_query and not has_explicit_item_filter:
        if re.search(r'\bvehicle_service_details\s+d\b', clean_sql, re.IGNORECASE) and not re.search(r'\bvehicle_service_summary\s+s\b', clean_sql, re.IGNORECASE):
            clean_sql = re.sub(r'\bvehicle_service_details\s+d\b', 'vehicle_service_summary s', clean_sql, flags=re.IGNORECASE)
            clean_sql = re.sub(r'CAST\s*\(\s*d\.amount\s+AS\s+DECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)\s*\)', 's.total_amt', clean_sql, flags=re.IGNORECASE)
            clean_sql = re.sub(r'\bd\.amount\b', 's.total_amt', clean_sql, flags=re.IGNORECASE)

    # 9. Repair vehicle brand comparisons and bare brand names in vehicle_type
    known_brands = {
        "audi": "Audi",
        "toyota": "Toyota",
        "volkswagen": "Volkswagen",
        "mahindra": "Mahindra"
    }
    query_brands = [b for b in known_brands if b in effective_query.lower()]
    is_comp_query = len(query_brands) >= 2 and any(k in effective_query.lower() for k in ["compare", "vs", "versus", "between", "both", "and", "each"])

    if is_comp_query and "group by brand" not in clean_sql.lower():
        case_clauses = " ".join([f"WHEN c.vehicle_type LIKE '%{known_brands[b]}%' THEN '{known_brands[b]}'" for b in query_brands])
        where_clauses = " OR ".join([f"c.vehicle_type LIKE '%{known_brands[b]}%'" for b in query_brands])
        if "avg" in clean_sql.lower() or "average" in effective_query.lower() or "avg" in effective_query.lower():
            clean_sql = f"SELECT CASE {case_clauses} END AS brand, COALESCE(AVG(s.total_amt), 0) AS average_service_cost FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE {where_clauses} GROUP BY brand;"
        elif "sum" in clean_sql.lower() or any(k in effective_query.lower() for k in ["total", "spent", "revenue", "cost"]):
            clean_sql = f"SELECT CASE {case_clauses} END AS brand, COALESCE(SUM(s.total_amt), 0) AS total_spent FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE {where_clauses} GROUP BY brand;"
        elif "count" in clean_sql.lower():
            clean_sql = f"SELECT CASE {case_clauses} END AS brand, COUNT(*) AS total_count FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE {where_clauses} GROUP BY brand;"
    else:
        # For single brand queries, ensure bare brand matches like c.vehicle_type = 'Toyota' become LIKE '%Toyota%'
        for b_key, b_name in known_brands.items():
            clean_sql = re.sub(
                rf"\bc\.vehicle_type\s*=\s*['\"]{b_name}['\"]",
                f"c.vehicle_type LIKE '%{b_name}%'",
                clean_sql,
                flags=re.IGNORECASE
            )

    # 10. Repair hallucinated part name/number columns in vehicle_service_details
    clean_sql = re.sub(
        r'\b([d])\.(part_number|part_no|part_name|parts_name|spare_part|spare_parts|part_desc)\b',
        r'\1.service_desc',
        clean_sql,
        flags=re.IGNORECASE
    )
    clean_sql = re.sub(
        r'(?<=\s)(part_number|part_no|part_name|parts_name|spare_part|spare_parts|part_desc)(?=\s|,|\)|;)',
        'd.service_desc',
        clean_sql,
        flags=re.IGNORECASE
    )

    return clean_sql
