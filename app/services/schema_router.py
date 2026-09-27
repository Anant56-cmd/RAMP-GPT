"""
Dynamic Schema Routing and Categorical Context Extraction
Reduces LLM prompt context by up to ~65% by injecting only the tables relevant to the user's intent.
"""

VEHICLE_SYNONYMS = {
    "volkswagen virtus": "Volkswagen-VIRTUS-TOPLINE TSI",
    "volkswagen-virtus": "Volkswagen-VIRTUS-TOPLINE TSI",
    "vw vertus": "Volkswagen-VIRTUS-TOPLINE TSI",
    "vw virtus": "Volkswagen-VIRTUS-TOPLINE TSI",
    "vw-virtus": "Volkswagen-VIRTUS-TOPLINE TSI",
    "virtus": "Volkswagen-VIRTUS-TOPLINE TSI",
    "mahindra thar lx hd": "Mahindra-Thar-LX HARDTOP",
    "mahindra-thar-lx-hd": "Mahindra-Thar-LX HARDTOP",
    "mahindra thar": "Mahindra-Thar-LX HARDTOP",
    "mahindra-thar": "Mahindra-Thar-LX HARDTOP",
    "thar": "Mahindra-Thar-LX HARDTOP",
    "mahindra scorpio n": "Mahindra-Scorpio-1.9 S4",
    "mahindra-scorpio-n": "Mahindra-Scorpio-1.9 S4",
    "mahindra scorpio": "Mahindra-Scorpio-1.9 S4",
    "mahindra-scorpio": "Mahindra-Scorpio-1.9 S4",
    "scorpio": "Mahindra-Scorpio-1.9 S4",
    "toyota land cruiser": "Toyota-Land Cruiser-200 VX Option Pack",
    "toyota-land cruiser": "Toyota-Land Cruiser-200 VX Option Pack",
    "toyota-land-cruiser": "Toyota-Land Cruiser-200 VX Option Pack",
    "land cruiser": "Toyota-Land Cruiser-200 VX Option Pack",
    "toyota innova": "Toyota-Innova-CRYSTA 2.4G",
    "toyota-innova": "Toyota-Innova-CRYSTA 2.4G",
    "innova": "Toyota-Innova-CRYSTA 2.4G",
    "audi a3": "Audi-A3-2.0 TSI",
    "audi-a3": "Audi-A3-2.0 TSI",
    "audi": "Audi-A3-2.0 TSI"
}

SERVICE_SYNONYMS = {
    "engine noise": "ENGINE SOUND",
    "ac issue": "AC COOLING ISSUE",
    "wash": "WATER WASH",
    "alignment": "WHEEL ALIGNMENT",
    "balancing": "WHEEL BALANCING",
    "general service": "GENERAL SERVICING",
    "cleaning": "WASHING AND CLEANING"
}

DB_SYNONYMS = {**VEHICLE_SYNONYMS, **SERVICE_SYNONYMS}

def get_categorical_context(user_query: str) -> str:
    """Fast deterministic lookup for vehicle models and workshop services."""
    query_lower = user_query.lower()
    for fuzzy_term, exact_db_string in DB_SYNONYMS.items():
        if fuzzy_term in query_lower:
            return f"""
            --- CONTEXT MAPPING ---
            User Input: '{user_query}'
            Database Value: '{exact_db_string}'
            INSTRUCTION: You MUST use '{exact_db_string}' as the literal value for this vehicle/service.
            """
    return ""

def get_dynamic_schema(user_query: str) -> str:
    """Routes the query to the correct schema tables based on intent to save context window."""
    query_lower = user_query.lower()

    hr_schema = """Table 5: employee_info (Alias: e)
- PK: employee_id | FK: workshop_id
- Joins: w ON e.workshop_id = w.workshop_id
- Columns: first_name, last_name, designation, status ('ACTIVE', 'BLOCKED'), contact_number, is_authorized ('Y','N'), full_perm_flag ('Y','N'), login_type ('OLD', 'NEW'), first_time_login ('Y','N'), email_id, tnc_accept_flag ('Y','N')

Table 6: workshop_info (Alias: w)
- PK: workshop_id
- Columns: workshop_name, address, location_name, city, state, country, contact_person_name, contact_nbr, email_id, caption, tin_no, company_name, cin_no, service_tax_no, owner_number, daily_notifications ('N','Y'), gst_number, reset_invoice ('Yes','No'), pincode, website, jma_flag ('N','Y'), tnm ('N','Y'), about_us, geo_location"""

    service_schema = """Table 1: customer_vehicle_info (Alias: c)
- PK: customer_id
- Columns: customer_name, customer_mobile, customer_vehicle_number, vehicle_type, vehicle_category, fuel_type, color, location_name, city, state, pincode, reg_valid_dt, date_of_registeration, nbr_of_coupons, manufactured_year, customer_status ('ACTIVE', 'BLOCKED'), user_status ('E', 'D')

Table 2: vehicle_service_details (Alias: d)
- PK: vehicle_svc_details_id | FK: customer_id, vehicle_svc_id
- Joins: c ON d.customer_id = c.customer_id | s ON (d.vehicle_svc_id = s.vehicle_svc_id AND d.customer_id = s.customer_id) | j ON (d.vehicle_svc_id = j.vehicle_svc_id AND d.customer_id = j.customer_id)
- NOTE: There is NO job_card_id, supervisor_id, or service_id in this table! The service key is vehicle_svc_id.
- CRITICAL SCOPE: This table stores INDIVIDUAL LINE ITEMS (parts 'PR' and labour 'S'). NEVER query this table for general visit costs, overall bills, or average service costs!
- Columns: service_type_cd ('PR'=Parts, 'S'=Service/Labour, 'SL'=Salvage), service_desc, service_cat_code, amount, quantity, service_date, location_name, bill_type, tax_rate, tax_name, tax_sub_type, discount_amount, identifier ('Billing'=Servicing, 'CounterSales'=Over the counter), part_identifier ('Spares', 'Consumables'), approval_status ('A'=Accepted, 'R'=Rejected)

Table 3: vehicle_service_summary (Alias: s)
- PK: vehicle_svc_summary_id | FK: customer_id, vehicle_svc_id
- Joins: c ON s.customer_id = c.customer_id | j ON (s.vehicle_svc_id = j.vehicle_svc_id AND s.customer_id = j.customer_id) | d ON (s.vehicle_svc_id = d.vehicle_svc_id AND s.customer_id = d.customer_id)
- NOTE: Supervisor name ('Supervisor X', 'Supervisor 1', etc.) and technician name are stored DIRECTLY here in supervisor_name and technician! Do NOT join employee_info for service supervisors. There is NO supervisor_id, job_card_id, or service_id.
- CRITICAL SCOPE: 'total_amt' in this table stores the OVERALL INVOICE BILL FOR THE VISIT. ALWAYS use 's.total_amt' when calculating average service costs, total service amounts, or overall spending for vehicles/customers!
- Columns: total_amt, service_amt, parts_amt, service_date, bill_type ('Standard', 'Detailed', ''), kilometer_driven, location_name, discount_amount, due_date, service_status ('A'=Arrived, 'R'=Ready, 'B'=Blocked, 'D'=Done), sms_reminders ('Y','N'), technician, supervisor_name, insurance_claim ('Yes', 'No'), total_paid_cust, total_due_cust

Table 4: job_card_details (Alias: j)
- PK: job_card_id | FK: customer_id, vehicle_svc_id
- Joins: c ON j.customer_id = c.customer_id | s ON (j.vehicle_svc_id = s.vehicle_svc_id AND j.customer_id = s.customer_id) | d ON (j.vehicle_svc_id = d.vehicle_svc_id AND j.customer_id = d.customer_id)
- NOTE: Common key to link with services is vehicle_svc_id and customer_id.
- Columns: problem_desc, workshop_finding, complaint_status, created_on, created_by"""

    hr_keywords = ["employee", "staff", "workshop", "supervisor", "designation", "login", "access", "permission", "technician"]
    service_keywords = ["customer", "vehicle", "car", "service", "complaint", "revenue", "cost", "part", "invoice", "bill", "audi", "repair", "volkswagen", "mahindra", "toyota", "booking", "bookings"]

    needs_hr = any(kw in query_lower for kw in hr_keywords)
    needs_service = any(kw in query_lower for kw in service_keywords)

    if needs_hr and not needs_service:
        print("> Dynamic Router: Injecting HR Schema only.")
        return hr_schema
    elif needs_service and not needs_hr:
        print("> Dynamic Router: Injecting Service/Vehicle Schema only.")
        return service_schema
    else:
        print("> Dynamic Router: Injecting Full Database Schema.")
        return service_schema + "\n\n" + hr_schema
