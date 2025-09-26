
@bp.post("/api/ar-map/bulk_assign")
def api_ar_map_bulk_assign():
    """Bulk assign projects to multiple sales invoices."""
    body = request.get_json(force=True) or {}
    assignments = body.get("assignments") or []
    
    if not isinstance(assignments, list) or not assignments:
        return jsonify({"ok": False, "error": "assignments must be non-empty list"}), 400
    
    con = _db(_get_db_path())
    assigned = 0
    failed = 0
    
    try:
        cur = con.cursor()
        for assignment in assignments:
            if not isinstance(assignment, dict):
                failed += 1
                continue
                
            invoice_id = assignment.get("invoice_id")
            project_id = assignment.get("project_id")
            
            if not invoice_id or not project_id:
                failed += 1
                continue
            
            try:
                cur.execute(
                    "UPDATE sales_invoices SET project_id = ? WHERE id = ?",
                    (str(project_id), int(invoice_id))
                )
                if cur.rowcount > 0:
                    assigned += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        
        con.commit()
        return jsonify({
            "ok": True,
            "assigned": assigned,
            "failed": failed,
            "rules_created": 0
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        con.close()