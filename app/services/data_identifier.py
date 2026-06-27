from typing import List, Dict


def identify_data_type(data: List[Dict]) -> str:
    if not data:
        return "empty"
    if "date" in data[0]:
        return "time_series"
    if "ticket_id" in data[0]:
        return "tabular_support"
    if "customer_id" in data[0]:
        return "tabular_crm"
    return "unknown"
