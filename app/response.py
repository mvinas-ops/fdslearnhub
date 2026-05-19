def success_response(data=None, message="Request successful", meta=None):
    body = {"success": True, "message": message, "data": data}
    if meta is not None:
        body["meta"] = meta
    return body

def error_response(message="Error", error_code="ERROR", details=None):
    return {"success": False, "message": message, "error_code": error_code, "details": details or {}}

def pagination_meta(page: int, limit: int, total: int):
    return {"page": page, "limit": limit, "total": total}
