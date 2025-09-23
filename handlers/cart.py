from models.user import get_cart, set_cart
from services.sheets import get_item_by_id
from services.telegram import tg_send_message, tg_send_photo

def show_cart(chat_id):
    cart = get_cart(chat_id)
    items = cart.get("items", [])
    if not items:
        tg_send_message(chat_id, "🛒 Ваш кошик порожній. Додайте щось із меню! 🍽️")
        return

    total = sum(float(it.get("price", 0.0)) * int(it.get("qty", 0)) for it in items)
    cart_summary_text = "<b>🛒 Ваш кошик:</b>\n\n"
    inline_keyboard = []

    for idx, item_in_cart in enumerate(items):
        item_price = float(item_in_cart.get("price", 0.0))
        item_qty = int(item_in_cart.get("qty", 0))
        item_subtotal = item_price * item_qty
        cart_summary_text += f"🍕 {item_in_cart.get('name')} — {item_qty} × {item_price:.2f} = {item_subtotal:.2f} грн\n"
        inline_keyboard.append([
            {"text": "➖", "callback_data": f"qty_minus_{idx}"},
            {"text": f"{item_qty}", "callback_data": f"qty_info_{idx}"},
            {"text": "➕", "callback_data": f"qty_plus_{idx}"},
            {"text": "🗑️", "callback_data": f"remove_item_{idx}"}
        ])

    cart_summary_text += f"\n<b>Всього: {total:.2f} грн 🎉</b>"
    inline_keyboard.append([{"text": "✅ Оформити замовлення", "callback_data": "checkout"}])
    tg_send_message(chat_id, cart_summary_text, reply_markup={"inline_keyboard": inline_keyboard})

def add_item_to_cart(chat_id, item_id, quantity=1):
    selected_item_info = get_item_by_id(item_id)
    if not selected_item_info:
        tg_send_message(chat_id, "Вибачте, цю позицію не знайдено в меню. 😔")
        return

    user_cart = get_cart(chat_id)
    found_in_cart = False
    for item_in_cart in user_cart["items"]:
        if str(item_in_cart.get("id")) == str(selected_item_info.get("ID")):
            item_in_cart["qty"] = item_in_cart.get("qty", 0) + quantity
            found_in_cart = True
            break
    
    if not found_in_cart:
        user_cart["items"].append({
            "id": selected_item_info.get("ID"),
            "name": selected_item_info.get("Назва Страви", "N/A"),
            "price": selected_item_info.get("Ціна", 0.0),
            "qty": quantity
        })

    set_cart(chat_id, user_cart)
    caption = f"🍕 *{selected_item_info.get('Назва Страви', 'N/A')}* додано до кошика! Кількість: {user_cart['items'][-1]['qty'] if not found_in_cart else item_in_cart['qty']}."
    photo_url = selected_item_info.get("Фото URL", "")
    if photo_url:
        tg_send_photo(chat_id, photo_url, caption, parse_mode="Markdown")
    else:
        tg_send_message(chat_id, caption, parse_mode="Markdown")
