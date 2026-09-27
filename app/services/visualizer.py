"""
Intelligent Semantic Visualization & Table Formatting Engine.
Analyzes query syntax, metric types, and database result dimensions to dynamically
synthesize Chart.js visualization payloads (bar, line, doughnut, horizontal bar)
and structured 2D table rows for 1-click CSV export.
"""
import re
import ast
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple

COLUMN_TITLE_MAP = {
    "customer_name": "Customer Name",
    "customer_vehicle_number": "Vehicle Number",
    "vehicle_type": "Vehicle Model",
    "total_amt": "Total Amount (₹)",
    "total_billing_amount": "Total Billing (₹)",
    "amount": "Amount (₹)",
    "quantity": "Quantity",
    "service_desc": "Service Description",
    "supervisor_name": "Supervisor",
    "bill_type": "Bill Type",
    "problem_desc": "Complaint Description",
    "technician_name": "Technician Name",
    "labour_revenue": "Labour Revenue (₹)",
    "parts_revenue": "Parts Revenue (₹)",
    "total_parts_cost": "Total Parts Cost (₹)",
    "total_revenue": "Total Revenue (₹)",
    "total_spent": "Total Spent (₹)",
    "kilometer_driven": "Kilometers Driven",
    "customer_mobile": "Mobile Number",
    "customer_email": "Email Address",
    "first_name": "First Name",
    "last_name": "Last Name",
    "designation": "Designation",
    "workshop_name": "Workshop Name",
    "location_name": "Location",
    "replacement_count": "Replacement Count"
}

def extract_columns_from_sql(sql: str) -> List[str]:
    """Extracts clean column headers from SQL SELECT clause."""
    try:
        select_match = re.search(r"SELECT\s+(DISTINCT\s+)?(.*?)\s+FROM\s+", sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return []
        raw_cols = select_match.group(2).strip()
        
        parts = []
        bracket_depth = 0
        current = ""
        for char in raw_cols:
            if char == '(':
                bracket_depth += 1
            elif char == ')':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += char
        if current.strip():
            parts.append(current.strip())
            
        column_headers = []
        for p in parts:
            alias_match = re.search(r"\bAS\s+([a-zA-Z0-9_]+)$", p, re.IGNORECASE)
            if alias_match:
                raw_name = alias_match.group(1).lower()
            else:
                col_match = re.search(r"([a-zA-Z0-9_]+)$", p)
                raw_name = col_match.group(1).lower() if col_match else "column"
                
            header = COLUMN_TITLE_MAP.get(raw_name, raw_name.replace("_", " ").title())
            column_headers.append(header)
            
        return column_headers
    except Exception:
        return []

def parse_database_output_to_rows(db_output: Any) -> List[List[Any]]:
    """Parses database output into clean 2D row array for table, chart, and CSV export."""
    if not db_output or db_output in ("[]", "None", "[(None,)]"):
        return []
        
    parsed = None
    if isinstance(db_output, str):
        try:
            clean_str = re.sub(r"Decimal\(['\"]?([0-9.-]+)['\"]?\)", r"\1", db_output)
            parsed = ast.literal_eval(clean_str)
        except Exception:
            return []
    else:
        parsed = db_output
        
    if not isinstance(parsed, list):
        return []
        
    rows = []
    for item in parsed:
        if isinstance(item, (list, tuple)):
            clean_row = []
            for val in item:
                if isinstance(val, (int, float, Decimal)):
                    clean_row.append(round(float(val), 2) if isinstance(val, (float, Decimal)) else val)
                elif val is None:
                    clean_row.append("N/A")
                else:
                    clean_row.append(str(val))
            rows.append(clean_row)
        elif isinstance(item, dict):
            clean_row = []
            for v in item.values():
                if isinstance(v, (int, float, Decimal)):
                    clean_row.append(round(float(v), 2) if isinstance(v, (float, Decimal)) else v)
                elif v is None:
                    clean_row.append("N/A")
                else:
                    clean_row.append(str(v))
            rows.append(clean_row)
        else:
            rows.append([str(item)])
    return rows

# =====================================================================
# INTELLIGENT SEMANTIC CHART ENGINE
# =====================================================================

CHART_PALETTE = [
    "rgba(0, 240, 255, 0.75)",    # Cyan
    "rgba(112, 0, 255, 0.75)",   # Purple
    "rgba(255, 0, 122, 0.75)",   # Neon Pink
    "rgba(0, 255, 102, 0.75)",   # Neon Green
    "rgba(255, 184, 0, 0.75)",   # Amber
    "rgba(255, 0, 85, 0.75)",    # Red
    "rgba(0, 229, 255, 0.75)",   # Sky
    "rgba(168, 85, 247, 0.75)",  # Violet
    "rgba(251, 146, 60, 0.75)",  # Orange
    "rgba(56, 189, 248, 0.75)"   # Blue
]

CHART_BORDER_PALETTE = [
    "#00F0FF",
    "#7000FF",
    "#FF007A",
    "#00FF66",
    "#FFB800",
    "#FF0055",
    "#00E5FF",
    "#A855F7",
    "#FB923C",
    "#38BDF8"
]

def _is_numeric_value(v: Any) -> bool:
    """Checks if a cell value represents a quantitative metric (not a phone, date, or code)."""
    if v is None:
        return False
    if isinstance(v, (int, float, Decimal)):
        return True
    s = str(v).strip().replace(',', '')
    # Check if looks like a phone number or masked text (e.g. 84XXXXXX17)
    if re.match(r'^[6-9]\d{9}$', s) or 'XXXX' in s:
        return False
    # Check if looks like a vehicle registration number or date
    if re.match(r'^[A-Z]{2}\d{2}', s) or re.match(r'^\d{4}-\d{2}-\d{2}', s):
        return False
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False

def _to_numeric_float(v: Any) -> float:
    if isinstance(v, (int, float, Decimal)):
        return round(float(v), 2)
    try:
        return round(float(str(v).replace(',', '').strip()), 2)
    except Exception:
        return 0.0

def _clean_chart_label(lbl: Any) -> str:
    s = str(lbl).strip()
    s = s.replace('-', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s

def _classify_metric(user_query: str, sql: str, col_name: str = "") -> Tuple[str, str]:
    """
    Determines metric type ('currency', 'count', 'percent', 'distance', 'duration')
    and appropriate unit suffix (' (₹)', '', ' (%)', ' km', ' min').
    Never misclassifies SQL LIKE '%' wildcards as percentage.
    """
    q_lower = user_query.lower()
    c_lower = col_name.lower()
    
    # 1. Percent: Must be in user query, column name, or explicit percentage calculation in SQL
    is_percent = (
        any(k in q_lower for k in ["percent", "percentage", "proportion", "share of", "ratio of"])
        or any(k in c_lower for k in ["percent", "percentage", "pct", "share", "ratio"])
        or bool(re.search(r'\*\s*100(\.0)?\s*/', sql))
        or bool(re.search(r'\bAS\s+(percent|percentage|pct|share)\b', sql, re.IGNORECASE))
    )
    if is_percent:
        return "percent", " (%)"
    
    # 2. Currency: Cost, revenue, spent, bill, amount
    combined_text = f"{q_lower} {c_lower}"
    sql_lower = sql.lower()
    if any(k in combined_text for k in [
        "cost", "spent", "spending", "revenue", "bill", "billing", "amount", 
        "price", "money", "paid", "sales", "total_amt", "total_revenue", 
        "labour_revenue", "parts_revenue", "avg_service_cost", "average_service_cost"
    ]) or any(k in sql_lower for k in ["total_amt", "total_revenue", "parts_revenue", "labour_revenue", "avg_service_cost", "average_service_cost"]):
        return "currency", " (₹)"
        
    # 3. Distance (km)
    if any(k in combined_text for k in ["kilometer", "km", "mileage", "odometer"]) or "kilometer_driven" in sql_lower:
        return "distance", " (km)"
        
    # 4. Duration (minutes)
    if any(k in combined_text for k in ["duration", "minutes", "time taken", "delivery duration"]):
        return "duration", " (min)"
        
    # 5. Count
    if any(k in combined_text for k in [
        "count", "how many", "number of", "bookings", "complaints", "visits", 
        "invoices", "customers", "registered", "quantity", "total_bookings"
    ]) or "count(" in sql_lower:
        return "count", ""
        
    return "numeric", ""

def _synthesize_smart_title(user_query: str, labels: List[str], metric_type: str, col_name: str = "") -> str:
    """Synthesizes a clean, natural chart title that directly reflects the user's question."""
    q = user_query.strip().rstrip('?.!')
    q_lower = q.lower()
    
    # Multi-vehicle comparison (requires 2 or more distinct labels)
    known_cars = ["virtus", "thar", "scorpio", "audi", "innova", "land cruiser", "toyota", "volkswagen", "mahindra"]
    
    if len(labels) >= 2 and any(any(c in l.lower() for c in known_cars) for l in labels):
        car_titles = [l.split()[0] if len(l.split()) > 0 else l for l in labels[:4]]
        if "average" in q_lower or "avg" in q_lower:
            return f"Average Service Cost: {' vs '.join(car_titles)}"
        return f"Service Cost Comparison: {' vs '.join(car_titles)}"
        
    if ("spare parts" in q_lower or "parts" in q_lower) and ("labour" in q_lower or "labor" in q_lower):
        return "Spare Parts vs Labour Revenue Breakdown"
        
    if "detailed" in q_lower and "standard" in q_lower:
        return "Invoice Type Distribution"
        
    if "city" in q_lower or "location" in q_lower:
        return "Customer Distribution by City"
        
    if "trend" in q_lower or "year" in q_lower or "month" in q_lower:
        year_match = re.search(r'\b(20\d{2})\b', q)
        if year_match:
            return f"Monthly Revenue Trend ({year_match.group(1)})"
        return "Annual Revenue Trend"
        
    if any(k in q_lower for k in ["top", "highest", "most"]):
        if any(k in q_lower for k in ["complaint", "problem", "issue"]):
            return "Top Complaints Breakdown"
        if any(k in q_lower for k in ["technician", "employee"]):
            return "Top Technicians by Revenue"
        if any(k in q_lower for k in ["model", "vehicle", "car"]):
            return "Top Vehicle Models"
        if any(k in q_lower for k in ["part", "spare", "spares", "component", "item"]):
            return "Most Replaced Spare Part"

    if any(k in q_lower for k in ["percent", "percentage", "ratio"]):
        clean_q = re.sub(r'^(what is the percentage of|what percentage of|percentage of|ratio of|share of)\s+', '', q, flags=re.IGNORECASE).strip()
        return f"{clean_q.title()} Distribution"
            
    if len(labels) == 1:
        target_name = labels[0]
        if "average" in q_lower or "avg" in q_lower:
            return f"Average Service Cost: {target_name}"
        if any(k in q_lower for k in ["total", "spent", "spending", "amount", "cost", "bill"]):
            return f"Total Service Cost: {target_name}"
        return f"{col_name or 'Service Summary'}: {target_name}"
        
    if col_name:
        return f"{col_name} Breakdown"
        
    clean_q = re.sub(r'^(what is|what are|show me|tell me|give me|compare|list)\s+', '', q, flags=re.IGNORECASE).strip()
    return clean_q.title()

def detect_chart_data(user_query: str, sql: str, raw_result: str, database_output: Any) -> Optional[Dict[str, Any]]:
    """
    Intelligently analyzes query context, linguistic intent, and database results
    to construct the ideal Chart.js visualization (bar, horizontal bar, doughnut, pie, line).
    Prevents false charts on non-numeric lookup queries.
    """
    try:
        rows = parse_database_output_to_rows(database_output)
        if not rows or len(rows) == 0:
            return None
            
        headers = extract_columns_from_sql(sql)
        q_lower = user_query.lower()
        
        # 0. Check explicit chart type requests from user
        user_requested_type = None
        is_horizontal = "horizontal" in q_lower
        
        if "pie" in q_lower:
            user_requested_type = "pie"
        elif "doughnut" in q_lower or "donut" in q_lower:
            user_requested_type = "doughnut"
        elif "line chart" in q_lower or "line graph" in q_lower or "trend line" in q_lower:
            user_requested_type = "line"
        elif "bar chart" in q_lower or "bar graph" in q_lower:
            user_requested_type = "bar"

        # CASE A: Multi-row dataset (2 to 30 rows)
        if 2 <= len(rows) <= 30:
            num_cols = len(rows[0])
            if num_cols >= 2:
                col0_numeric = all(_is_numeric_value(r[0]) for r in rows)
                col1_numeric = all(_is_numeric_value(r[1]) for r in rows)
                
                # Subcase A1: [Category Label, Numeric Value]
                if not col0_numeric and col1_numeric:
                    labels = [_clean_chart_label(r[0]) for r in rows]
                    values = [_to_numeric_float(r[1]) for r in rows]
                    
                    metric_col = headers[1] if len(headers) >= 2 else ""
                    metric_type, unit = _classify_metric(user_query, sql, metric_col)
                    
                    if user_requested_type:
                        chart_type = user_requested_type
                    elif any(k in q_lower for k in ["share", "proportion", "breakdown", "distribution"]) and len(rows) <= 6:
                        chart_type = "doughnut"
                    else:
                        chart_type = "bar"
                        
                    title = _synthesize_smart_title(user_query, labels, metric_type, metric_col)
                    metric_label = metric_col or ("Revenue" if metric_type == "currency" else "Count")
                    if unit and not unit.strip() in metric_label:
                        metric_label += unit
                        
                    bg_colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]
                    bd_colors = [CHART_BORDER_PALETTE[i % len(CHART_BORDER_PALETTE)] for i in range(len(labels))]
                    
                    chart_dict = {
                        "type": chart_type,
                        "title": title,
                        "labels": labels,
                        "datasets": [{
                            "label": metric_label,
                            "data": values,
                            "backgroundColor": bg_colors,
                            "borderColor": bd_colors,
                            "borderWidth": 2
                        }]
                    }
                    if is_horizontal and chart_type == "bar":
                        chart_dict["horizontal"] = True
                    return chart_dict
                    
                # Subcase A2: [Time / Year / Date, Numeric Value] (Chronological trend)
                if col0_numeric and col1_numeric:
                    labels = [str(r[0]) for r in rows]
                    values = [_to_numeric_float(r[1]) for r in rows]
                    
                    metric_col = headers[1] if len(headers) >= 2 else ""
                    metric_type, unit = _classify_metric(user_query, sql, metric_col)
                    
                    is_trend = any(k in q_lower for k in ["trend", "year", "month", "over time", "history", "growth"])
                    chart_type = user_requested_type or ("line" if (is_trend and len(rows) >= 3) else "bar")
                    
                    title = _synthesize_smart_title(user_query, labels, metric_type, metric_col)
                    metric_label = metric_col or "Total"
                    if unit and not unit.strip() in metric_label:
                        metric_label += unit
                        
                    if chart_type == "line":
                        return {
                            "type": "line",
                            "title": title,
                            "labels": labels,
                            "datasets": [{
                                "label": metric_label,
                                "data": values,
                                "borderColor": "#00F0FF",
                                "backgroundColor": "rgba(0, 240, 255, 0.15)",
                                "fill": True,
                                "tension": 0.35,
                                "borderWidth": 2,
                                "pointBackgroundColor": "#00F0FF",
                                "pointBorderColor": "#ffffff",
                                "pointRadius": 5
                            }]
                        }
                    else:
                        bg_colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]
                        bd_colors = [CHART_BORDER_PALETTE[i % len(CHART_BORDER_PALETTE)] for i in range(len(labels))]
                        return {
                            "type": "bar",
                            "title": title,
                            "labels": labels,
                            "datasets": [{
                                "label": metric_label,
                                "data": values,
                                "backgroundColor": bg_colors,
                                "borderColor": bd_colors,
                                "borderWidth": 2
                            }]
                        }

        # CASE B: Single row with multiple numeric columns (e.g. Parts Revenue vs Labour Revenue)
        if len(rows) == 1 and len(rows[0]) >= 2:
            if all(_is_numeric_value(c) for c in rows[0][:len(headers) if headers else 2]):
                values = [_to_numeric_float(c) for c in rows[0]]
                labels = headers[:len(values)] if headers else [f"Metric {i+1}" for i in range(len(values))]
                
                metric_type, unit = _classify_metric(user_query, sql, " ".join(labels))
                chart_type = user_requested_type or ("doughnut" if len(values) <= 6 else "bar")
                title = _synthesize_smart_title(user_query, labels, metric_type)
                
                bg_colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]
                bd_colors = [CHART_BORDER_PALETTE[i % len(CHART_BORDER_PALETTE)] for i in range(len(labels))]
                
                return {
                    "type": chart_type,
                    "title": title,
                    "labels": labels,
                    "datasets": [{
                        "label": "Revenue (₹)" if metric_type == "currency" else "Value",
                        "data": values,
                        "backgroundColor": bg_colors,
                        "borderColor": bd_colors,
                        "borderWidth": 1
                    }]
                }

        # CASE C: Single row: 1 category & 1 numeric value OR single numeric metric
        if len(rows) == 1:
            row = rows[0]
            # [Category, Value]
            if len(row) >= 2 and not _is_numeric_value(row[0]) and _is_numeric_value(row[1]):
                val = _to_numeric_float(row[1])
                label = _clean_chart_label(row[0])
                metric_col = headers[1] if len(headers) >= 2 else ""
                metric_type, unit = _classify_metric(user_query, sql, metric_col)
                
                title = _synthesize_smart_title(user_query, [label], metric_type, metric_col)
                metric_label = metric_col or ("Total Amount" if metric_type == "currency" else "Value")
                if unit and not unit.strip() in metric_label:
                    metric_label += unit
                    
                return {
                    "type": "bar",
                    "title": title,
                    "labels": [label],
                    "datasets": [{
                        "label": metric_label,
                        "data": [val],
                        "backgroundColor": "rgba(112, 0, 255, 0.6)",
                        "borderColor": "#7000FF",
                        "borderWidth": 2
                    }]
                }
                
            # [Scalar Numeric Value]
            elif len(row) >= 1 and _is_numeric_value(row[0]):
                val = _to_numeric_float(row[0])
                metric_col = headers[0] if headers else ""
                metric_type, unit = _classify_metric(user_query, sql, metric_col)
                
                # If percentage AND mathematically valid ratio (0 to 100)
                if (metric_type == "percent" or "percent" in q_lower) and 0.0 <= val <= 100.0:
                    pct = round(val, 1)
                    other_pct = round(100.0 - pct, 1)
                    metric_name = "General Service" if "general" in q_lower else "Selected Metric"
                    return {
                        "type": "doughnut",
                        "title": _synthesize_smart_title(user_query, [metric_name], "percent"),
                        "labels": [f"{metric_name} (%)", "Other (%)"],
                        "datasets": [{
                            "label": "Percentage (%)",
                            "data": [pct, other_pct],
                            "backgroundColor": ["#00F0FF", "rgba(255, 255, 255, 0.2)"],
                            "borderColor": ["#00F0FF", "rgba(255, 255, 255, 0.4)"],
                            "borderWidth": 1
                        }]
                    }
                    
                # Single numeric metric for a car, technician, workshop, or general metric
                known_cars = ["virtus", "thar", "scorpio", "audi", "innova", "land cruiser", "toyota", "volkswagen", "mahindra"]
                matched_car = next((c for c in known_cars if c in q_lower), None)
                
                if matched_car:
                    label_name = matched_car.title()
                elif any(k in q_lower for k in ["technician", "employee", "supervisor"]):
                    label_name = "Staff"
                elif metric_col:
                    label_name = metric_col.replace("_", " ").title()
                else:
                    label_name = "Overall Metric"
                
                if ("average" in q_lower or "avg" in q_lower) and metric_type == "currency":
                    metric_label = "Average Service Cost (₹)"
                elif metric_type == "currency":
                    metric_label = "Total Amount (₹)"
                elif metric_type == "count":
                    metric_label = "Count"
                else:
                    metric_label = "Value"
                    
                if unit and not unit.strip() in metric_label:
                    metric_label += unit
                    
                return {
                    "type": "bar",
                    "title": _synthesize_smart_title(user_query, [label_name], metric_type, metric_col),
                    "labels": [label_name],
                    "datasets": [{
                        "label": metric_label,
                        "data": [round(val, 2)],
                        "backgroundColor": "rgba(0, 240, 255, 0.6)",
                        "borderColor": "#00F0FF",
                        "borderWidth": 2
                    }]
                }

    except Exception as e:
        print(f"> Chart detection note: {e}")

    return None
