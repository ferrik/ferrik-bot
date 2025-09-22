def get_item_by_id(item_id):
    items = get_menu_from_sheet()
    item_id_str = str(item_id).strip()
    for it in items:
        if str(it.get("ID") or it.get("id") or "").strip() == item_id_str:
            return it
    return None
