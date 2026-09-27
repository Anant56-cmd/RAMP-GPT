"""
Conversational Session Memory & Entity Resolution Service.
Maintains state across multi-turn interactions, tracking active entities
(customer, vehicle number, vehicle model, supervisor) and resolving
pronouns/demonstratives in follow-up queries.
"""
import re
from typing import Dict, Any, Optional

# In-memory dictionary for conversational session state
SESSION_MEMORY: Dict[str, Dict[str, Any]] = {}

def resolve_conversational_context(user_query: str, session_id: str = "default") -> str:
    """
    Resolves pronouns ('their', 'his', 'its', 'they') and demonstratives ('that car', 'this customer')
    using active entities recorded in session memory.
    """
    session = SESSION_MEMORY.get(session_id)
    if not session:
        return user_query
        
    last_cust = session.get("customer_name")
    last_veh = session.get("vehicle_number")
    last_model = session.get("vehicle_type")
    
    q_lower = user_query.lower().strip()
    
    has_pronoun = bool(re.search(r"\b(their|theirs|his|her|him|they|them|its)\b", q_lower))
    has_demonstrative = bool(re.search(r"\b(that|this|the same)\s+(customer|client|owner|vehicle|car|service|bill|supervisor)\b", q_lower))
    is_short_followup = len(user_query.split()) <= 7 and any(k in q_lower for k in [
        "phone", "mobile", "contact", "email", "cars", "vehicles", "service", "bill", "cost", "address", "supervisor"
    ]) and not any(k in q_lower for k in ["virtus", "thar", "scorpio", "innova", "audi", "test customer", "supervisor 1", "supervisor x"])

    if not (has_pronoun or has_demonstrative or is_short_followup):
        return user_query

    # 1. Customer Follow-up Resolution
    if last_cust:
        if any(w in q_lower for w in ["phone", "mobile", "contact", "email", "number"]):
            return f"What is the mobile number and email of {last_cust}?"
        if any(w in q_lower for w in ["car", "cars", "vehicle", "vehicles", "model"]) and "spent" not in q_lower:
            return f"Which vehicle models belong to {last_cust}?"
        if any(w in q_lower for w in ["spent", "cost", "bill", "money", "total"]):
            return f"How much total money was spent by {last_cust}?"
        if any(w in q_lower for w in ["service", "services", "complaint", "history"]):
            return f"Show all service history and complaints for {last_cust}."
        augmented = re.sub(r"\b(their|his|her)\b", f"{last_cust}'s", user_query, flags=re.IGNORECASE)
        augmented = re.sub(r"\b(they|them|that customer|this customer|the same customer)\b", last_cust, augmented, flags=re.IGNORECASE)
        return augmented

    # 2. Vehicle Registration Follow-up Resolution
    if last_veh:
        if any(w in q_lower for w in ["supervisor", "handled", "technician"]):
            return f"Which supervisor handled the service for vehicle {last_veh}?"
        if any(w in q_lower for w in ["bill", "cost", "amount", "spent"]):
            return f"What was the total billing amount for vehicle {last_veh}?"
        if any(w in q_lower for w in ["parts", "spares"]):
            return f"What parts were used for vehicle {last_veh}?"
        augmented = re.sub(r"\b(that vehicle|this vehicle|that car|this car|it)\b", f"vehicle {last_veh}", user_query, flags=re.IGNORECASE)
        return augmented

    # 3. Vehicle Model Follow-up Resolution
    if last_model:
        augmented = re.sub(r"\b(that vehicle|this vehicle|that car|this car|it)\b", last_model, user_query, flags=re.IGNORECASE)
        return augmented

    return user_query

def extract_and_update_session_memory(session_id: str, query: str, sql: str, raw_result: str):
    """
    Inspects user query, generated SQL, and execution results to record
    active conversational entities (customer name, vehicle reg, vehicle model, supervisor) in memory.
    """
    if session_id not in SESSION_MEMORY:
        SESSION_MEMORY[session_id] = {}
        
    s = SESSION_MEMORY[session_id]
    s["last_query"] = query
    s["last_sql"] = sql
    
    combined = f"{query} {sql} {raw_result}"
    
    # Customer
    cust_match = re.search(r"(?:TEST\s*CUSTOMER\s*\d+|customer\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)|John\s+Doe)", combined, re.IGNORECASE)
    if cust_match:
        val = cust_match.group(1) or cust_match.group(0)
        s["customer_name"] = val.strip()
    elif "johndoe" in combined.lower().replace(" ", ""):
        s["customer_name"] = "John Doe"
        
    # Vehicle Registration Number
    veh_match = re.search(r"\b([A-Z]{2}[X0-9]{2}[A-Z0-9]{1,2}[X0-9]{4})\b", combined)
    if veh_match:
        s["vehicle_number"] = veh_match.group(1).upper()
        
    # Vehicle Model
    for model in [
        "Volkswagen-VIRTUS-TOPLINE TSI",
        "Toyota-Innova-CRYSTA 2.4G",
        "Mahindra-Scorpio-1.9 S4",
        "Mahindra-Thar-LX HARDTOP",
        "Audi-A3-2.0 TSI",
        "Toyota-Land Cruiser-200 VX Option Pack"
    ]:
        if model.lower() in combined.lower():
            s["vehicle_type"] = model
            break

    # Supervisor
    sup_match = re.search(r"Supervisor\s+[X0-9]+", combined, re.IGNORECASE)
    if sup_match:
        s["supervisor_name"] = sup_match.group(0).title()

def get_session_context(session_id: str = "default") -> Optional[str]:
    """Retrieves current primary context entity (customer, vehicle, or model) for a session."""
    active_ctx = SESSION_MEMORY.get(session_id, {})
    return active_ctx.get("customer_name") or active_ctx.get("vehicle_number") or active_ctx.get("vehicle_type")
