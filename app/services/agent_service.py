"""
Master Text-to-SQL Query Orchestration Pipeline.
Coordinates conversational context resolution, sub-millisecond semantic caching,
dynamic schema routing, hybrid LLM invocation, 10-layer self-healing, read-only
AST security checks, database execution with self-correction, PII masking,
natural English translation, Chart.js payload synthesis, and session memory tracking.
"""
import os
import sys
import re
import ast
from decimal import Decimal
from typing import Optional, Dict, Any, Union, List

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.database import get_db_connection
from app.services.llm_factory import get_models
from app.services.retriever import get_similar_example, get_golden_match, save_golden_query
from app.services.schema_router import get_categorical_context, get_dynamic_schema
from app.services.sql_healer import heal_sql_query
from app.services.visualizer import detect_chart_data, parse_database_output_to_rows, extract_columns_from_sql
from app.services.memory_service import resolve_conversational_context, extract_and_update_session_memory, SESSION_MEMORY, get_session_context
from app.core.sql_validator import is_safe_query
from app.core.pii_masker import sanitize_database_output

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def safe_print(msg: str):
    """Safely print strings even if console encoding does not support special characters."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass

def generate_english_answer(chat_client, original_question, db_result, fallback_client=None):
    """Translates database results into natural, professional English with ₹ currency enforcement."""
    translation_template = """
    You are a professional manager at an automobile workshop in India.
    A user asked you this question: "{question}"
    You queried the database and got this exact mathematical result: {result}
    
    Write a short, polite, and direct English sentence answering the user's question using the database result. 
    CRITICAL RULE: Whenever the answer involves money, cost, or revenue, you MUST use the Indian Rupee symbol (₹). NEVER use Dollars ($).
    Do not explain the SQL. Do not add any extra formatting. Just give the final human-readable answer.
    """
    prompt = PromptTemplate.from_template(translation_template)
    try:
        chain = prompt | chat_client | StrOutputParser()
        ans = chain.invoke({
            "question": original_question,
            "result": db_result
        })
        return str(ans).strip()
    except Exception as e:
        if fallback_client and chat_client is not fallback_client:
            safe_print(f"> Cloud translation fallback activated ({e}). Using Local Qwen...")
            fallback_chain = prompt | fallback_client | StrOutputParser()
            fb_ans = fallback_chain.invoke({
                "question": original_question,
                "result": db_result
            })
            return str(fb_ans).strip()
        raise e

def process_sql_query(user_query: str, session_id: str = "default", return_details: bool = False) -> Union[str, Dict[str, Any]]:
    """
    Core Text-to-SQL Analytics Pipeline:
    1. Conversational context resolution
    2. Semantic cache lookup (<1ms retrieval)
    3. Dynamic schema routing & Few-shot golden query injection
    4. Hybrid LLM invocation (Groq primary with Ollama fallback)
    5. 10-layer SQL healing & AST security validation
    6. Database execution with self-correction retry loop
    7. PII sanitization, Chart.js detection, and Natural language translation
    """
    db = get_db_connection()
    sql_llm, chat_llm, embedder, active_engine, fallback_sql_llm, fallback_chat_llm = get_models()
    
    # 1. CONVERSATIONAL CONTEXT RESOLUTION
    effective_query = resolve_conversational_context(user_query, session_id)
    if effective_query != user_query:
        safe_print(f"> Follow-up Context Resolved: '{user_query}' -> '{effective_query}'")
    
    # 2. GOLDEN QUERY CACHE & CATEGORICAL LOOKUP
    safe_print(f"\n> Checking Knowledge Cache for: '{effective_query}'")
    categorical_context = ""
    
    try:
        best_match = None
        best_similarity = 0.0

        try:
            g_sql, g_score, g_query = get_golden_match(effective_query)
            if g_sql and g_score <= 0.15:
                safe_print(f"> Golden Query Direct HIT! (Distance: {g_score:.4f}, Matched: '{g_query}')")
                best_match = {
                    "sql": g_sql,
                    "original_query": g_query
                }
                best_similarity = round(1.0 - g_score, 2)
        except Exception as ge:
            safe_print(f"> Golden query check note: {ge}")

        if best_match:
            safe_print(f"> Semantic Cache HIT! (Similarity: {best_similarity:.2f})")
            safe_print(f"> Bypassing LLM. Reusing SQL: {best_match['sql']}")
            
            database_output = db.run(best_match['sql'])
            if not database_output or database_output == "[]" or database_output == "None" or database_output == "[(None,)]":
                msg = "No matching records found in the database for that query."
                if return_details:
                    return {"answer": msg, "sql": best_match['sql'], "raw_result": None, "chart_data": None, "table_data": None, "cached": True, "engine": "Semantic Cache (Instant)"}
                return msg
            
            clean_result = str(database_output).replace("Decimal", "").replace("(", "").replace(")", "").replace("'", "").replace("[", "").replace("]", "").replace(",", "").strip()
            safe_print("> Translating cached result into natural English...")
            safe_result = sanitize_database_output(clean_result, effective_query)
            
            try:
                final_english_answer = generate_english_answer(
                    chat_client=chat_llm, 
                    original_question=effective_query, 
                    db_result=safe_result,
                    fallback_client=fallback_chat_llm
                )
            except Exception as e:
                safe_print(f"> Translation failed ({e}), returning formatted database result.")
                final_english_answer = f"The result from records is: {safe_result}"
            
            safe_print(f"\nFinal Answer: {final_english_answer}")
            chart_data = detect_chart_data(effective_query, best_match['sql'], safe_result, database_output)
            
            # Extract structured table data for CSV export & table viewer
            table_data = None
            rows = parse_database_output_to_rows(database_output)
            cols = extract_columns_from_sql(best_match['sql'])
            if rows and len(rows) > 0 and cols and len(cols) > 0:
                table_data = {
                    "columns": cols,
                    "rows": rows,
                    "total_rows": len(rows)
                }
                
            # Update session memory for follow-up questions
            extract_and_update_session_memory(session_id, effective_query, best_match['sql'], str(database_output))
            ctx_entity = get_session_context(session_id)

            if return_details:
                return {
                    "answer": final_english_answer,
                    "sql": best_match['sql'],
                    "raw_result": safe_result,
                    "chart_data": chart_data,
                    "table_data": table_data,
                    "context_entity": ctx_entity,
                    "cached": True,
                    "status": "SUCCESS",
                    "pii_masked": "XXXXXX" in safe_result or "XXXX" in safe_result,
                    "resolved_query": effective_query if effective_query != user_query else None,
                    "engine": "Semantic Cache (Instant)"
                }
            return final_english_answer
                
        safe_print(f"> Semantic Cache MISS. Passing to LLM...")
        categorical_context = get_categorical_context(effective_query)
        
    except Exception as e:
        safe_print(f"> Cache/Lookup check bypassed due to error: {str(e)}")
    
    # 3. Dynamic schema & few-shot retrieval
    dynamic_schema = get_dynamic_schema(effective_query)
    golden_example = get_similar_example(effective_query)
    few_shot_context = f"\nHere is a correct example to learn from:\n{golden_example}" if golden_example else ""
    
    # 4. Master Prompt Template
    template = f"""You are an Elite MySQL Database Administrator and Data Analyst. {few_shot_context}
    Your job is to translate natural language questions into perfect, executable MySQL queries. 

CRITICAL SQL RULES (NEVER BREAK THESE):
1. Output ONLY the raw SQL query starting with SELECT and ending with a semicolon (;). No Markdown, no backticks, no chat.
2. ALIASING IS MANDATORY: You MUST use the assigned table aliases (c, d, s, j, e, w) for EVERY column to prevent 'ambiguous column' errors.
3. MATH & CASTING: The `amount` column in vehicle_service_details is text. You MUST use CAST(d.amount AS DECIMAL(10,2)) for any mathematical operations like SUM(), AVG(), or MAX().
4. TEXT SEARCH & NAMES: To prevent spacing errors and typos, you MUST remove all spaces from both the column and the search term using REPLACE. ALWAYS format text searches exactly like this: WHERE REPLACE(LOWER(c.customer_name), ' ', '') LIKE '%searchterm%'. Example: If searching for "John Doe", use WHERE REPLACE(LOWER(c.customer_name), ' ', '') LIKE '%johndoe%'.
5. NULL HANDLING: If asked for 'unresolved', 'missing', or 'never', use IS NULL or IS NOT NULL (e.g., j.complaint_status IS NULL).
6. CONDITIONAL COUNTING: If counting specific categories (like Detailed vs Standard), you MUST use SUM() instead of COUNT(). Example: SUM(CASE WHEN s.bill_type = 'Detailed' THEN 1 ELSE 0 END).
7. PERCENTAGES: To calculate a percentage, use this exact formula structure: (SUM(CASE WHEN [condition] THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
8. DATES & TRENDS: For "last quarter", use >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH). For "trends", group by YEAR(date_column) or MONTH(date_column). DO NOT invent machine learning predictive functions.
9. ANTI-HALLUCINATION & FILTER TRAP: DO NOT copy literal text filters from the examples (e.g., never filter for 'Audi' unless the user explicitly types 'Audi'). You MUST read every descriptive noun in the user's question and explicitly add corresponding WHERE clauses ONLY for those attributes.
10. SECURITY & PROMPT INJECTION TRAP: You are READ-ONLY. NEVER generate INSERT, UPDATE, DELETE, ALTER, or DROP commands. If a user asks you to perform any of these, DO NOT try to write a valid query. You MUST output this exact string: SELECT 'ERROR: SECURITY VIOLATION' AS result;
11. RUNAWAY DATA TRAP: Always append `LIMIT 50` to queries that return multiple rows (unless the user explicitly asked for a 'Top 1' or a specific limit).
12. STRICT MODIFIER CONSTRAINT TRAP: You MUST inspect every single noun, adjective, and role specified in the user's question. If a specific role or status is mentioned, you MUST explicitly add a matching WHERE clause for it (e.g., e.designation = 'Technician' or e.status = 'ACTIVE'). CRITICAL: When dealing with "Active" statuses for customers, vehicles, or employees, you MUST account for empty data by using this exact format: (c.customer_status = 'ACTIVE' OR c.customer_status IS NULL). NEVER assume a table alias implies a filter. 
13. NULL DATES TRAP: When calculating durations using date differences (like wait times), you MUST explicitly add IS NOT NULL clauses for both date columns in the WHERE clause to prevent returning rows with a NULL duration.
14. GROUP BY TRAP: Any time you use an aggregate mathematical function (like SUM, COUNT, AVG, MAX, MIN) alongside a non-aggregated column (like customer_name, location_name, or vehicle_type), you MUST include a GROUP BY clause for all non-aggregated columns. NEVER write an aggregate query without a GROUP BY.
15. PREDICTION & OUT OF SCOPE TRAP: If a user asks you to predict future trends, perform machine learning, or asks a question completely unrelated to the database schema, DO NOT output English. You MUST output this exact string: SELECT 'ERROR: OUT OF SCOPE' AS result;
16. MISSING JOIN TRAP: Before finalizing your SQL, check every single table alias used in your SELECT and WHERE clauses (c, d, s, j, e, w). If an alias is used, you MUST explicitly include that table in the FROM clause using an INNER JOIN. Never filter on a table you haven't joined.
17. STRICT JOIN TRAP: When joining tables, you MUST strictly follow the Foreign Keys (FK) defined in the schema. Never join a Primary Key to a mismatched Foreign Key. For example, vehicle_service_details (d) and job_card_details (j) MUST be joined using their shared keys: ON d.vehicle_svc_id = j.vehicle_svc_id AND d.customer_id = j.customer_id.
18. HYBRID LOOKUP OVERRIDE: If the system context provides an "Exact DB Term" (e.g., 'ENGINE SOUND', 'GENERAL SERVICING'), you MUST use that EXACT injected string in your LIKE or = clauses. Never use the user's original synonym if a database term is provided!
19. CONTEXT ENFORCEMENT: If a "CONTEXT MAPPING" block is provided in the system context, you MUST treat the 'Database Value' as an immutable constant. You are forbidden from modifying, truncating, or abbreviating this value in your SQL WHERE clause. You must copy it character-for-character.
20. NO ASSUMED FILTERS: Never add filtering conditions for status columns (like complaint_status, job_status, etc.) or IS NOT NULL checks unless the user explicitly asks for them.
21. STRICT COMPOSITE JOINS: Whenever you join vehicle_service_details (d) with job_card_details (j), you MUST use a composite join on both keys to prevent data duplication. 
Your ON clause MUST ALWAYS be: ON d.vehicle_svc_id = j.vehicle_svc_id AND d.customer_id = j.customer_id. Never join them using only one key.
22. UNIVERSAL REVENUE/COST MATH: WHENEVER the user asks for overall "total cost", "repair cost", "money spent", or "revenue", calculate COALESCE(SUM(s.total_amt), 0) from the vehicle_service_summary table.
EXCEPTION: If the user specifically asks for revenue from "Labour" or "General Service" (d.service_type_cd = 'S') or "Spare Parts" (d.service_type_cd = 'PR'), you MUST calculate it from vehicle_service_details using: COALESCE(SUM(CAST(d.amount AS DECIMAL(10,2)) * CAST(d.quantity AS DECIMAL(10,2))), 0). NEVER use s.bill_type = 'Labour' or s.bill_type = 'Parts' (bill_type is only 'Standard' or 'Detailed').
23. NO HALLUCINATED VEHICLE TABLE: THERE IS NO TABLE NAMED 'vehicle_info' OR 'vehicles'. Vehicle registration numbers and models are stored ONLY in 'customer_vehicle_info' (Alias: c) under columns 'customer_vehicle_number' and 'vehicle_type'. NEVER generate 'FROM vehicle_info' or 'c.vehicle_number'.
24. NO EMPLOYEE JOIN FOR CUSTOMER CONTACTS: Customer mobile and customer email are stored directly in 'customer_vehicle_info' (Alias: c) as 'c.customer_mobile' and 'c.customer_email'. 'customer_vehicle_info' does NOT have an 'employee_id' column. NEVER join 'employee_info' when searching for a customer's phone or email!
25. INSURANCE CLAIM COLUMN LOCATION: The 'insurance_claim' column is located ONLY in 'vehicle_service_summary' (Alias: s). It DOES NOT exist in 'vehicle_service_details'. To count or filter insurance claims, query 'vehicle_service_summary s WHERE s.insurance_claim = 'Yes''.
26. NO JOB_CARD_ID IN SUMMARY OR DETAILS: Neither 'vehicle_service_summary' (s) nor 'vehicle_service_details' (d) contains a column named 'job_card_id'. NEVER write 's.job_card_id' or 'd.job_card_id'. To join 'job_card_details' (j) with 'vehicle_service_summary' (s), ALWAYS use: ON s.vehicle_svc_id = j.vehicle_svc_id AND s.customer_id = j.customer_id.
27. IDENTIFIER IS vehicle_svc_id (NOT service_id): The service identifier in 'vehicle_service_summary', 'vehicle_service_details', and 'job_card_details' is 'vehicle_svc_id'. There is NO column named 'service_id'. NEVER write 's.service_id', 'd.service_id', or 'j.service_id'.
28. SUPERVISOR AND TECHNICIAN IN SERVICE SUMMARY: The supervisor name ('Supervisor X', 'Supervisor 1', etc.) and technician name are ALREADY present in 'vehicle_service_summary' (Alias: s) as 's.supervisor_name' and 's.technician'. Neither 'vehicle_service_summary' nor 'vehicle_service_details' has a 'supervisor_id'. NEVER join 'employee_info' when looking for service supervisors or technicians! Filter or select 's.supervisor_name' or 's.technician' directly.
29. PREVENT CARTESIAN PRODUCT ON SUMMARY REVENUE: If aggregating 's.total_amt' while filtering by complaints in 'job_card_details', a single service may have multiple complaints. To prevent duplicate billing totals, use an IN subquery: WHERE s.vehicle_svc_id IN (SELECT j.vehicle_svc_id FROM job_card_details j WHERE j.problem_desc LIKE '%...%').
30. CANONICAL MULTI-TABLE JOIN SYNTAX:
- 3-Table (Customer + Job Card + Summary):
  FROM customer_vehicle_info c INNER JOIN job_card_details j ON c.customer_id = j.customer_id INNER JOIN vehicle_service_summary s ON j.vehicle_svc_id = s.vehicle_svc_id AND j.customer_id = s.customer_id
- 4-Table (Customer + Job Card + Summary + Details):
  FROM customer_vehicle_info c INNER JOIN job_card_details j ON c.customer_id = j.customer_id INNER JOIN vehicle_service_summary s ON j.vehicle_svc_id = s.vehicle_svc_id AND j.customer_id = s.customer_id INNER JOIN vehicle_service_details d ON s.vehicle_svc_id = d.vehicle_svc_id AND s.customer_id = d.customer_id
31. NO HALLUCINATED TECHNICIAN OR WORKSHOP TABLES: There are NO tables named 'technician_details', 'supervisor_details', or 'workshop_details'. All technicians and supervisors are stored in 'employee_info' (Alias: e) with e.designation = 'Technician' or 'Supervisor'. Workshop info is in 'workshop_info' (Alias: w).
To find technicians in the same workshop as a supervisor:
SELECT CONCAT(e.first_name, ' ', e.last_name) AS technician_name FROM employee_info e WHERE e.designation = 'Technician' AND e.workshop_id = (SELECT e2.workshop_id FROM employee_info e2 WHERE CONCAT(e2.first_name, ' ', e2.last_name) LIKE '%Supervisor 1%' LIMIT 1);
32. NO PART_NUMBER OR PART_NAME COLUMN: In vehicle_service_details, there is NO column named 'part_number', 'part_name', 'part_no', or 'parts_name'. The spare part name/description is stored ONLY in 'd.service_desc'.
To find the most frequently replaced part:
SELECT d.service_desc, COUNT(*) AS replacement_count FROM vehicle_service_details d WHERE d.service_type_cd = 'PR' GROUP BY d.service_desc ORDER BY replacement_count DESC LIMIT 1;

{dynamic_schema}
{categorical_context}
BUSINESS VOCABULARY & INTENT TRANSLATION:
- "Parts" / "Spares" -> Filter using: d.service_type_cd = 'PR'
- "Specific spare parts" / "Part names" / "Brands" / "Consumables" / "Liquids" (like oil or coolant) -> You MUST return the part name using: SELECT d.service_desc. Search for the part using: d.service_desc LIKE '%keyword%' AND d.service_type_cd = 'PR'. Group by d.service_desc to find the most popular.
- "Labour" / "General Service" -> Filter using: d.service_type_cd = 'S'
- "Revenue" / "Total Sales" / "Billing" / "Spending" / "Spent" / "Money" -> Calculate overall revenue/spending using: COALESCE(SUM(s.total_amt), 0). If calculating revenue for specific line items, use: COALESCE(SUM(CAST(d.amount AS DECIMAL(10,2)) * CAST(d.quantity AS DECIMAL(10,2))), 0)
- "Average service cost" / "Average bill" / "Average invoice" / "Average service amount" / "Average spending" / "Average cost for [Vehicle/Brand/Customer]" -> You MUST calculate the average invoice total per service visit using: COALESCE(AVG(s.total_amt), 0) from 'vehicle_service_summary' (Alias: s). NEVER query 'vehicle_service_details' for general service/visit costs or averages!
- "Total bill" / "Total service cost" / "Total cost for [Vehicle/Brand/Customer]" -> Calculate overall visit total using: COALESCE(SUM(s.total_amt), 0) from 'vehicle_service_summary' (Alias: s).
- "Parts cost" / "Spare parts cost" / "Average part cost" -> Query 'vehicle_service_details' (Alias: d) with: d.service_type_cd = 'PR'.
- "Labour cost" / "Average labour cost" -> Query 'vehicle_service_details' (Alias: d) with: d.service_type_cd = 'S'.
- "SUMMARY VS DETAILS CRITICAL RULE": When a user asks about the cost, bill, spending, or average cost of a vehicle or customer in general, it refers to the invoice in 'vehicle_service_summary' (s.total_amt). NEVER query 'vehicle_service_details' (d.amount) unless the user explicitly mentions "parts", "spares", "labour", or itemized line items.
- "Most frequent" / "Top" / "Highest" / "Most common" -> ORDER BY COUNT(*) DESC LIMIT X OR ORDER BY SUM(X) DESC LIMIT X
- "Complaints" / "Issues" / "Symptoms" / "Heats up" / "Noise" -> You MUST search the mechanic notes using: j.problem_desc LIKE '%keyword%'. 
NEVER search for problems in the c.vehicle_type column. 
CONVERSELY, NEVER search for vehicle brands or models (e.g., Audi, Volkswagen, Toyota) in the j.problem_desc column. Brands MUST ALWAYS be filtered in c.vehicle_type.
- "Vehicles that had complaints" / "Vehicles with AC cooling issues" -> Join 'job_card_details' (j) with 'customer_vehicle_info' (c) ON j.customer_id = c.customer_id. Select 'c.customer_vehicle_number, c.vehicle_type, j.problem_desc'. Filter with: j.problem_desc LIKE '%AC COOLING%'. DO NOT join any other table.
- "Findings" / "Mechanic notes" -> j.workshop_finding
- "Unresolved complaints" -> j.complaint_status IS NULL
- "Completed services" -> s.service_status = 'D'
- "Rejected" / "Rejected services" -> d.approval_status = 'R'
- "Accepted" / "Accepted services" -> d.approval_status = 'A'
- "Insurance claims" / "Insurance filed" -> The column 'insurance_claim' is ONLY located in 'vehicle_service_summary' (Alias: s). NEVER query 'vehicle_service_details' for insurance claims! Use: SELECT COUNT(*) FROM vehicle_service_summary s WHERE s.insurance_claim = 'Yes';
- "Active employees" -> e.status = 'ACTIVE'
- "Mobile access enabled" -> e.is_authorized = 'Y'
- "Over the counter sales" -> d.identifier = 'CounterSales'
- "Odometer" / "1 lakh kilometers" -> Filter using: CAST(s.kilometer_driven AS UNSIGNED) > 100000.
- "Bookings" / "Total bookings" / "Services booked" -> Count all records from 'vehicle_service_summary' (Alias: s). For example: SELECT COUNT(*) AS total_bookings FROM vehicle_service_summary;
- "List vehicles with mileage" / "Vehicles driven more than 1 lakh km" -> Join 'vehicle_service_summary' (s) with 'customer_vehicle_info' (c) ON s.customer_id = c.customer_id. Select 'c.customer_vehicle_number, s.kilometer_driven'.
- Searching for an Employee Name -> CONCAT(e.first_name, ' ', e.last_name) LIKE '%Name%'
- "Time waiting for delivery" / "Delivery duration" / "Time taken" -> Calculate using: TIMESTAMPDIFF(MINUTE, s.vehicle_in_date, s.vehicle_out_date) (Ensure you add WHERE s.vehicle_in_date IS NOT NULL AND s.vehicle_out_date IS NOT NULL)
- "Today" / "Current Date" -> Use CURDATE() ONLY if the user explicitly asks for "today", "current", or "now". NEVER use CURDATE() to calculate historical job card or service durations.
- "Active customer" / "Active status" for vehicles -> (c.customer_status = 'ACTIVE' OR c.customer_status IS NULL)
- "Visited" / "Visited the workshop" / "Came in" -> This refers to service events, NOT registrations. Filter using the service date (e.g., YEAR(s.service_date)) and count unique customers using COUNT(DISTINCT s.customer_id).
- "Last" / "Latest" / "Most Recent" / "Newest" -> You MUST sort the results chronologically. Always append: ORDER BY [date_column] DESC LIMIT 1
- "Manufactured" / "Year made" -> The column is named 'manufactured_year'. Because it is text, NEVER use the YEAR() function. Filter using: CAST(c.manufactured_year AS UNSIGNED)
- "Vehicle Brands" / "Car Models" / "Cars" -> Car names are ONLY stored in the c.vehicle_type column. NEVER invent columns like 'vehicle_model'. You MUST use the exact matching string provided in the injected context (e.g., 'Mahindra-Thar-LX HARDTOP') instead of the user's raw text.
- "Give me the complaints" / "List issues" / "Problems" -> This simply means you should SELECT the j.problem_desc column. NEVER add a WHERE clause filtering for the literal words 'complaint', 'issue', or 'problem'.
- "DATA PRIVACY" / "PII" -> NEVER SELECT raw phone numbers, emails, or exact addresses. Mask them using SQL (e.g., CONCAT(LEFT(c.customer_mobile, 2), '******', RIGHT(c.customer_mobile, 2))). If asked about a customer by name, replace their full name in the output with their customer_id (e.g., 'Customer #4') to prevent PII leakage.
- "CONTEXT ENFORCEMENT" -> If the System Context provides an "Exact DB Term" (e.g., 'Mahindra-Thar-LX HARDTOP'), you MUST treat this string as a literal constant and use it exactly as provided in your WHERE clause. NEVER truncate, shorten, or modify it (e.g., do not change 'Mahindra-Thar-LX HARDTOP' to 'Mahindra-Thar'). You are forbidden from editing injected context strings.
- "Customer Email" -> You MUST use the column 'c.customer_email' in customer_vehicle_info. Do NOT use 'email_address' or 'owner_email'.
- "Customer Mobile / Phone" -> You MUST use the column 'c.customer_mobile' in customer_vehicle_info. Do NOT use 'customer_phone', 'phone_number', or 'mobile_number'.
- "Customer Mobile and Email" -> Both 'c.customer_mobile' and 'c.customer_email' are in customer_vehicle_info (Alias: c). NEVER join employee_info for customer contact info!
- "Employee Email" -> You MUST use the column 'e.email_id' in employee_info. Do NOT use 'email' or 'email_address'.
- "Employee Mobile / Phone" -> You MUST use the column 'e.contact_number' in employee_info. Do NOT use 'mobile_number' or 'customer_phone'.

- "MULTI-ENTITY AND BRAND-LEVEL COMPARISONS":
  The vehicle_type values in customer_vehicle_info are prefixed by brand ('Audi-A3-2.0 TSI', 'Volkswagen-VIRTUS-TOPLINE TSI', 'Toyota-Innova-CRYSTA 2.4G', 'Toyota-Land Cruiser-200 VX Option Pack', 'Mahindra-Scorpio-1.9 S4', 'Mahindra-Thar-LX HARDTOP').
  When comparing specific models (e.g., Thar vs Scorpio), filter and GROUP BY c.vehicle_type.
  When comparing BRANDS (e.g., "compare the average service cost for Audi and Toyota"):
  You MUST aggregate at the brand level using CASE:
  SELECT CASE WHEN c.vehicle_type LIKE '%Audi%' THEN 'Audi' WHEN c.vehicle_type LIKE '%Toyota%' THEN 'Toyota' END AS brand, COALESCE(AVG(s.total_amt), 0) AS average_service_cost FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type LIKE '%Audi%' OR c.vehicle_type LIKE '%Toyota%' GROUP BY brand;
  NEVER lump them into a single combined average. Each compared entity MUST have its own row and group.

FEW-SHOT EXAMPLES (Structure and logic templates):

Q: Tell me how much money was spent by John Doe?
A: SELECT COALESCE(SUM(s.total_amt), 0) AS total_spent FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE REPLACE(LOWER(c.customer_name), ' ', '') LIKE '%johndoe%';

Q: What is the total service amount for Volkswagen Virtus?
A: SELECT COALESCE(SUM(s.total_amt), 0) AS total_spent FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type = 'Volkswagen-VIRTUS-TOPLINE TSI';

Q: What is the average service cost for Audi?
A: SELECT COALESCE(AVG(s.total_amt), 0) AS average_service_cost FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type = 'Audi-A3-2.0 TSI';

Q: What is the average service cost for Audi and Volkswagen Virtus?
A: SELECT c.vehicle_type, COALESCE(AVG(s.total_amt), 0) AS average_service_cost FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type IN ('Audi-A3-2.0 TSI', 'Volkswagen-VIRTUS-TOPLINE TSI') GROUP BY c.vehicle_type;

Q: Compare the average service cost for Audi and Toyota.
A: SELECT CASE WHEN c.vehicle_type LIKE '%Audi%' THEN 'Audi' WHEN c.vehicle_type LIKE '%Toyota%' THEN 'Toyota' END AS brand, COALESCE(AVG(s.total_amt), 0) AS average_service_cost FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type LIKE '%Audi%' OR c.vehicle_type LIKE '%Toyota%' GROUP BY brand;

Q: What is the average service cost for Mahindra Thar?
A: SELECT COALESCE(AVG(s.total_amt), 0) AS average_service_cost FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type = 'Mahindra-Thar-LX HARDTOP';

Q: Compare spare parts vs labour revenue.
A: SELECT COALESCE(SUM(CASE WHEN d.service_type_cd = 'PR' THEN CAST(d.amount AS DECIMAL(10,2)) * CAST(d.quantity AS DECIMAL(10,2)) ELSE 0 END), 0) AS parts_revenue, COALESCE(SUM(CASE WHEN d.service_type_cd = 'S' THEN CAST(d.amount AS DECIMAL(10,2)) * CAST(d.quantity AS DECIMAL(10,2)) ELSE 0 END), 0) AS labour_revenue FROM vehicle_service_details d;

Q: Which vehicles had an engine complaint and what was the total billing amount for that service?
A: SELECT DISTINCT c.customer_vehicle_number, c.vehicle_type, s.total_amt FROM customer_vehicle_info c INNER JOIN job_card_details j ON c.customer_id = j.customer_id INNER JOIN vehicle_service_summary s ON j.vehicle_svc_id = s.vehicle_svc_id AND j.customer_id = s.customer_id WHERE j.problem_desc LIKE '%engine%';

Q: Which technicians work in the same workshop as Supervisor 1?
A: SELECT CONCAT(e.first_name, ' ', e.last_name) AS technician_name FROM employee_info e INNER JOIN workshop_info w ON e.workshop_id = w.workshop_id WHERE e.designation = 'Technician' AND e.workshop_id = (SELECT e2.workshop_id FROM employee_info e2 WHERE CONCAT(e2.first_name, ' ', e2.last_name) LIKE '%Supervisor 1%' LIMIT 1);

Q: Tell me which spare parts is replaced the most number of times.
A: SELECT d.service_desc, COUNT(*) AS replacement_count FROM vehicle_service_details d WHERE d.service_type_cd = 'PR' GROUP BY d.service_desc ORDER BY replacement_count DESC LIMIT 1;

QUESTION: {{question}}

RAW SQL QUERY:"""

    sql_prompt = PromptTemplate.from_template(template)
    write_query_chain = sql_prompt | sql_llm | StrOutputParser()
    
    # 5. SELF-CORRECTION LOOP
    max_retries = 3
    attempt = 0
    current_question = effective_query
    database_output = None
    clean_sql = ""
    had_mysql_error = False

    while attempt < max_retries:
        try:
            safe_print(f"\n> Processing User Query (Attempt {attempt + 1}) via [{active_engine}]: '{effective_query}'")
            
            try:
                generated_sql = write_query_chain.invoke({
                    "question": current_question,
                    "dynamic_schema": dynamic_schema,
                    "categorical_context": categorical_context
                })
            except Exception as cloud_err:
                if fallback_sql_llm and sql_llm is not fallback_sql_llm:
                    safe_print(f"> Cloud LLM invocation failed ({cloud_err}). Seamlessly switching to Local Qwen fallback...")
                    active_engine = "qwen2.5-coder:7b (Local Fallback)"
                    fallback_chain = sql_prompt | fallback_sql_llm | StrOutputParser()
                    generated_sql = fallback_chain.invoke({
                        "question": current_question,
                        "dynamic_schema": dynamic_schema,
                        "categorical_context": categorical_context
                    })
                else:
                    raise cloud_err
            
            clean_sql = str(generated_sql).replace("```sql", "").replace("```", "").strip()
            
            # Support both SELECT and WITH CTE statements
            sql_match = re.search(r"((?:WITH|SELECT)\s+.*)", clean_sql, re.IGNORECASE | re.DOTALL)
            if sql_match:
                clean_sql = sql_match.group(1).strip()
                
            if ";" in clean_sql:
                clean_sql = clean_sql.split(";")[0].strip() + ";"
    
            # --- APPLY 10-LAYER SQL HEALING INTERCEPTORS ---
            clean_sql = heal_sql_query(clean_sql, effective_query)

            safe_print(f"> Executing Cleaned SQL: {clean_sql}")

            if "ERROR: OUT OF SCOPE" in clean_sql.upper():
                msg = "This question is outside the analytical scope of the workshop database records."
                if return_details:
                    return {"answer": msg, "sql": clean_sql, "raw_result": None, "chart_data": None, "table_data": None, "cached": False, "status": "OUT_OF_SCOPE", "pii_masked": False, "engine": active_engine}
                return msg
                    
            if not is_safe_query(clean_sql) or "ERROR: SECURITY VIOLATION" in clean_sql.upper():
                safe_print("> Security Block Triggered: Detected forbidden SQL command.")
                msg = "Security Alert: Database execution is restricted to read-only analytical queries. Destructive operations are prohibited."
                if return_details:
                    return {"answer": msg, "sql": clean_sql, "raw_result": None, "chart_data": None, "table_data": None, "cached": False, "status": "SECURITY_BLOCKED", "pii_masked": False, "engine": active_engine}
                return msg
            
            database_output = db.run(clean_sql)

            # Auto-save as golden query ONLY if it genuinely recovered from an earlier MySQL failure
            if had_mysql_error and database_output and database_output != "[]":
                safe_print(f"> Self-Correction Successful! Auto-saving as Golden Query.")
                save_golden_query(effective_query, clean_sql)

            # Execution succeeded!
            break

        except Exception as e:
            had_mysql_error = True
            error_msg = str(e)
            safe_print(f"> Execution Failed on Attempt {attempt + 1}: {error_msg}")
            
            # Check for query timeout error (MySQL error 3024 / statement timeout)
            if "3024" in error_msg or "max_statement_time" in error_msg.lower() or "timeout" in error_msg.lower():
                safe_print(f"> Query Timeout Triggered: Execution exceeded safe limit (5000ms).")
                msg = "Query Timeout: The requested database query took longer than the safe limit (5 seconds) and was terminated to protect server performance."
                if return_details:
                    return {
                        "answer": msg,
                        "sql": clean_sql,
                        "raw_result": None,
                        "chart_data": None,
                        "table_data": None,
                        "cached": False,
                        "status": "TIMEOUT",
                        "pii_masked": False,
                        "error_detail": error_msg
                    }
                return msg

            current_question = f"""
The user originally asked: {effective_query}

You generated this SQL query:
{clean_sql}

It failed with this MySQL error:
{error_msg}

Rewrite the SQL query to fix this exact error. Ensure you use proper aliases, JOINs, and CASTing if needed. Output ONLY the corrected raw SQL starting with SELECT.
"""
            attempt += 1
            if attempt >= max_retries:
                msg = "Unable to generate an executable SQL query for this question. Please rephrase your query terms."
                if return_details:
                    return {"answer": msg, "sql": clean_sql, "raw_result": None, "chart_data": None, "table_data": None, "cached": False, "status": "ERROR", "pii_masked": False, "error_detail": error_msg}
                return msg

    # --- DEDUPLICATION ---
    try:
        if isinstance(database_output, str) and database_output.startswith("["):
            try:
                parsed_list = ast.literal_eval(database_output)
                if isinstance(parsed_list, list):
                    seen = set()
                    deduped = []
                    for item in parsed_list:
                        item_key = tuple(item) if isinstance(item, (list, tuple)) else str(item)
                        if item_key not in seen:
                            seen.add(item_key)
                            deduped.append(item)
                    database_output = str(deduped)
            except Exception:
                pass
        elif isinstance(database_output, list):
            try:
                seen = set()
                deduped = []
                for item in database_output:
                    item_key = tuple(item) if isinstance(item, (list, tuple)) else str(item)
                    if item_key not in seen:
                        seen.add(item_key)
                        deduped.append(item)
                database_output = deduped
            except Exception:
                pass
    except Exception:
        pass

    safe_print(f"> Database Row Output: {database_output}")

    # Update session memory for follow-up questions
    extract_and_update_session_memory(session_id, effective_query, clean_sql, str(database_output))

    if not database_output or database_output == "[]" or database_output == "None" or database_output == "[(None,)]":
        msg = "No matching records found in the database for that query."
        if return_details:
            ctx_entity = get_session_context(session_id)
            return {"answer": msg, "sql": clean_sql, "raw_result": None, "chart_data": None, "table_data": None, "cached": False, "context_entity": ctx_entity, "status": "SUCCESS"}
        return msg
        
    raw_clean_string = str(database_output).replace("Decimal", "").replace("(", "").replace(")", "").replace("'", "").replace("[", "").replace("]", "").replace(",", "").strip()
    clean_result = sanitize_database_output(raw_clean_string, effective_query)

    safe_print("> Translating raw database result into natural English...")

    try:
        final_english_answer = generate_english_answer(
            chat_client=chat_llm, 
            original_question=effective_query, 
            db_result=clean_result,
            fallback_client=fallback_chat_llm
        )
    except Exception as e:
        safe_print(f"> Translation warning ({e}), falling back to direct answer.")
        final_english_answer = f"According to workshop records, the result is: {clean_result}"

    safe_print(f"\nFinal Answer: {final_english_answer}")
    chart_data = detect_chart_data(effective_query, clean_sql, clean_result, database_output)
    
    # Extract structured table data for CSV export & table viewer
    table_data = None
    rows = parse_database_output_to_rows(database_output)
    cols = extract_columns_from_sql(clean_sql)
    if rows and len(rows) > 0 and cols and len(cols) > 0:
        table_data = {
            "columns": cols,
            "rows": rows,
            "total_rows": len(rows)
        }
        
    ctx_entity = get_session_context(session_id)

    if return_details:
        return {
            "answer": final_english_answer,
            "sql": clean_sql,
            "raw_result": clean_result,
            "chart_data": chart_data,
            "table_data": table_data,
            "context_entity": ctx_entity,
            "cached": False,
            "status": "SUCCESS",
            "pii_masked": "XXXXXX" in clean_result or "XXXX" in clean_result,
            "resolved_query": effective_query if effective_query != user_query else None,
            "engine": active_engine
        }
    return final_english_answer
