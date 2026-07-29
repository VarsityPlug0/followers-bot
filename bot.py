# ============================================
# TELEGRAM BOT — Follower Selling Bot
# Payment: PayPal + Manual Entry (any method)
# ============================================

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from config import BOT_TOKEN, ADMIN_IDS, SERVICES, PAYPAL_ME_LINK
from database import (
    init_db, get_or_create_user, create_order, update_order_panel_id,
    update_order_status, get_order, get_user_orders, get_pending_payment_orders,
    add_transaction, total_revenue, total_orders
)
from panel_api import place_order, get_balance

# ─── Setup ───

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ─── Helper Functions ───

def package_keyboard(platform):
    buttons = []
    for pid, svc in SERVICES.items():
        if pid.startswith(platform):
            price = f"${svc['price_cents']/100:.2f}"
            buttons.append([InlineKeyboardButton(
                f"{svc['name']} — {price}",
                callback_data=f"select_{pid}"
            )])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back_platform")])
    return InlineKeyboardMarkup(buttons)


def platform_keyboard():
    buttons = [
        [InlineKeyboardButton("📸 Instagram Followers", callback_data="plat_ig")],
        [InlineKeyboardButton("❤️ Instagram Likes", callback_data="plat_ig_likes")],
        [InlineKeyboardButton("🎵 TikTok Followers", callback_data="plat_tt")],
        [InlineKeyboardButton("💜 TikTok Likes", callback_data="plat_tt_likes")],
    ]
    return InlineKeyboardMarkup(buttons)


def user_order_summary(order):
    status_icons = {
        'pending': '⏳', 'processing': '🔄', 'completed': '✅',
        'partial': '⚠️', 'canceled': '❌', 'refilled': '🔄'
    }
    icon = status_icons.get(order['status'], '❓')
    svc_name = SERVICES.get(order['package_id'], {}).get('name', order['service_name'])
    pay_method = order.get('payment_method', '?')
    return (
        f"{icon} *{svc_name}*\n"
        f"   Link: `{order['link']}`\n"
        f"   Qty: {order['quantity']} | Status: {order['status']}\n"
        f"   Paid: ${order['amount_cents']/100:.2f} ({pay_method})\n"
        f"   Ordered: {order['created_at'][:19]}"
    )


# ─── Command Handlers ───

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username or user.first_name)

    await update.message.reply_text(
        "👋 *Welcome to GrowthBoost!*\n\n"
        "Get real Instagram & TikTok followers and likes delivered fast.\n\n"
        "👇 Select a service to get started:",
        parse_mode='Markdown',
        reply_markup=platform_keyboard()
    )


async def services_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👇 Select a service:",
        reply_markup=platform_keyboard()
    )


async def select_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    platform = query.data.replace('plat_', '')
    context.user_data['platform'] = platform

    platform_names = {
        'ig': '📸 Instagram Followers',
        'ig_likes': '❤️ Instagram Likes',
        'tt': '🎵 TikTok Followers',
        'tt_likes': '💜 TikTok Likes',
    }
    name = platform_names.get(platform, platform)

    await query.edit_message_text(
        f"{name}\n\nSelect a package:",
        reply_markup=package_keyboard(platform)
    )


async def select_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    package_id = query.data.replace('select_', '')
    svc = SERVICES.get(package_id)
    if not svc:
        await query.edit_message_text("❌ Invalid package. Try again.", reply_markup=platform_keyboard())
        return

    context.user_data['package_id'] = package_id
    context.user_data['package_info'] = svc

    price = f"${svc['price_cents']/100:.2f}"

    await query.edit_message_text(
        f"You selected: *{svc['name']}*\n"
        f"Price: *{price}*\n\n"
        f"Send me your Instagram or TikTok *username* or *profile URL*.\n"
        f"Example: `@yourusername` or `https://instagram.com/yourusername`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_link'] = True


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_link'):
        return

    link = update.message.text.strip()
    telegram_id = update.effective_user.id
    package_id = context.user_data['package_id']
    svc = context.user_data['package_info']

    if link.startswith('@'):
        if 'ig' in package_id or 'tt' in package_id:
            link = f"https://instagram.com/{link[1:]}" if 'ig' in package_id else f"https://tiktok.com/@{link[1:]}"

    context.user_data['target_link'] = link
    context.user_data['awaiting_link'] = False

    price = f"${svc['price_cents']/100:.2f}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 PayPal", callback_data="pay_paypal")],
        [InlineKeyboardButton("💰 EFT / Binance / Crypto", callback_data="pay_manual")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_platform")]
    ])

    await update.message.reply_text(
        f"📋 *Order Summary*\n\n"
        f"Service: {svc['name']}\n"
        f"Link: `{link}`\n"
        f"Total: *{price}*\n\n"
        f"Select payment method:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


# ─── PayPal ───

async def choose_paypal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    svc = context.user_data['package_info']
    link = context.user_data['target_link']
    package_id = context.user_data['package_id']
    price = f"${svc['price_cents']/100:.2f}"

    order_id = create_order(telegram_id, package_id, svc['name'], 0, link, svc['price_cents'], 'paypal')
    context.user_data['order_id'] = order_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay with PayPal", url=f"https://{PAYPAL_ME_LINK}/{svc['price_cents']/100:.2f}")],
        [InlineKeyboardButton("✅ I've Paid", callback_data=f"notify_paid_{order_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]
    ])

    await query.edit_message_text(
        f"💳 *PayPal Payment*\n\n"
        f"1️⃣ Click below to send *{price}* via PayPal\n"
        f"2️⃣ After payment, click *\"I've Paid\"*\n\n"
        f"Service: {svc['name']}\n"
        f"Link: `{link}`\n"
        f"Amount: *{price}*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


# ─── Manual Payment (Admin enters details) ───

async def choose_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User chose manual payment. Admin will be asked to provide details."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    svc = context.user_data['package_info']
    link = context.user_data['target_link']
    package_id = context.user_data['package_id']
    price = f"${svc['price_cents']/100:.2f}"

    order_id = create_order(telegram_id, package_id, svc['name'], 0, link, svc['price_cents'], 'manual')
    context.user_data['order_id'] = order_id

    # Tell the user to wait
    await query.edit_message_text(
        f"⏳ *Generating payment details...*\n\n"
        f"Admin will send you the payment info shortly.\n"
        f"Order #{order_id} — please stand by.",
        parse_mode='Markdown'
    )

    # Tell the admin to input payment details
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📩 *New Manual Payment Order*\n\n"
                f"Order: #{order_id}\n"
                f"User: @{update.effective_user.username or 'no_username'} (ID: {telegram_id})\n"
                f"Service: {svc['name']}\n"
                f"Link: `{link}`\n"
                f"Amount: {price}\n\n"
                f"➡️ *Reply with the payment details to send to the user:*\n"
                f"   e.g. `Capitec - Bevan Ndzhaka - 1234567890`\n"
                f"   or `BTC: bc1qxyz...`\n"
                f"   or *anything you want the user to pay to*",
                parse_mode='Markdown'
            )
            # Save which admin we're waiting on
            context.bot_data[f'awaiting_details_{order_id}'] = admin_id
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")


async def handle_admin_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin replies with payment details for a manual order."""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    # Check if this is a reply to the bot's message about a manual order
    reply = update.message.reply_to_message
    if not reply:
        return

    # Try to find which order we're handling by looking at awaiting_details in bot_data
    # We need to figure out the order ID from context
    # The admin should use: /senddetails <order_id> <details>
    # OR we check bot_data for the most recent awaiting_details
    await update.message.reply_text(
        "Use: `/senddetails <order_id> <payment info>`\n"
        "Example: `/senddetails 42 Capitec - Bevan - 1234567890`\n\n"
        "Or: `/senddetails 42 BTC: bc1qabc123def456`",
        parse_mode='Markdown'
    )


async def send_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /senddetails <order_id> <payment details>"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: `/senddetails <order_id> <payment info>`\n"
            "Example: `/senddetails 42 Capitec - Bevan - 1234567890`",
            parse_mode='Markdown'
        )
        return

    try:
        order_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid order ID.")
        return

    details = ' '.join(args[1:])

    order = get_order(order_id)
    if not order:
        await update.message.reply_text(f"❌ Order #{order_id} not found.")
        return

    # Set the payment details directly on the order as a note
    # We'll store it in bot_data for simplicity
    context.bot_data[f'payment_details_{order_id}'] = details
    update_order_status(order_id, 'awaiting_payment')

    # Send the details to the user
    svc_name = order['service_name']
    amount = f"${order['amount_cents']/100:.2f}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I've Paid (Notify Admin)", callback_data=f"notify_paid_{order_id}")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="cancel_order")]
    ])

    try:
        await context.bot.send_message(
            order['telegram_id'],
            f"💳 *Payment Instructions*\n\n"
            f"Order: #{order_id}\n"
            f"Service: *{svc_name}*\n"
            f"Amount: *{amount}*\n\n"
            f"*Send payment to:*\n"
            f"`{details}`\n\n"
            f"After payment, click the button below to notify admin.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send to user: {e}")
        return

    await update.message.reply_text(
        f"✅ *Payment details sent for Order #{order_id}*\n\n"
        f"User will see:\n`{details}`\n\n"
        f"Wait for them to click \"I've Paid\", then use /confirm {order_id}",
        parse_mode='Markdown'
    )


# ─── I've Paid (Notify Admin) ───

async def notify_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split('_')[2])
    order = get_order(order_id)
    if not order:
        await query.edit_message_text("❌ Order not found.")
        return

    update_order_status(order_id, 'pending_confirmation')

    svc_name = order['service_name']
    amount = f"${order['amount_cents']/100:.2f}"
    pay_method = order['payment_method']
    username = update.effective_user.username or update.effective_user.first_name

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🔔 *Payment Notification*\n\n"
                f"User: @{username} (ID: {update.effective_user.id})\n"
                f"Order: #{order_id}\n"
                f"Service: {svc_name}\n"
                f"Amount: {amount}\n"
                f"Method: {pay_method}\n\n"
                f"Use /confirm {order_id} to verify and process.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

    await query.edit_message_text(
        f"✅ *Notification Sent!*\n\n"
        f"Admin has been notified of your payment for *{svc_name}* ({amount}).\n\n"
        f"⏳ Your order will be processed once payment is confirmed.\n"
        f"📦 Use /orders to check status.",
        parse_mode='Markdown'
    )


# ─── Confirm Payment & Place Order ───

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/confirm <order_id>`", parse_mode='Markdown')
        return

    try:
        order_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid order ID.")
        return

    order = get_order(order_id)
    if not order:
        await update.message.reply_text(f"❌ Order #{order_id} not found.")
        return

    if order['status'] not in ('pending_confirmation', 'awaiting_payment'):
        await update.message.reply_text(
            f"❌ Order #{order_id} is '{order['status']}'. Use /forceconfirm {order_id} to override."
        )
        return

    # Place order on panel
    svc = SERVICES.get(order['package_id'])
    if not svc:
        await update.message.reply_text(f"❌ Invalid package: {order['package_id']}")
        return

    result = place_order(svc['panel_id'], order['link'], svc.get('quantity', 0))
    panel_order_id = result.get('order') if result and 'order' in result else None

    if panel_order_id:
        update_order_panel_id(order_id, panel_order_id)
    else:
        update_order_status(order_id, 'pending_manual')

    add_transaction(
        order['telegram_id'], 'payment', order['amount_cents'],
        description=f"Confirmed: {order['service_name']} (order #{order_id})"
    )

    try:
        await context.bot.send_message(
            order['telegram_id'],
            f"✅ *Payment Confirmed!*\n\n"
            f"Your order for *{order['service_name']}* is now processing.\n"
            f"📦 Use /orders to check status.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Failed to notify user: {e}")

    await update.message.reply_text(
        f"✅ *Order #{order_id} Confirmed*\n\n"
        f"Panel Order ID: {panel_order_id or 'manual'}\n"
        f"Status: {'processing' if panel_order_id else 'pending_manual'}",
        parse_mode='Markdown'
    )


async def force_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/forceconfirm <order_id>`", parse_mode='Markdown')
        return

    try:
        order_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid order ID.")
        return

    order = get_order(order_id)
    if not order:
        await update.message.reply_text(f"❌ Order #{order_id} not found.")
        return

    svc = SERVICES.get(order['package_id'])
    if not svc:
        await update.message.reply_text(f"❌ Invalid package.")
        return

    result = place_order(svc['panel_id'], order['link'], svc.get('quantity', 0))
    panel_order_id = result.get('order') if result and 'order' in result else None

    if panel_order_id:
        update_order_panel_id(order_id, panel_order_id)
    else:
        update_order_status(order_id, 'pending_manual')

    add_transaction(
        order['telegram_id'], 'payment', order['amount_cents'],
        description=f"Force confirmed: {order['service_name']} (order #{order_id})"
    )

    await update.message.reply_text(
        f"✅ *Order #{order_id} Force Confirmed*\nPanel Order: {panel_order_id or 'manual'}",
        parse_mode='Markdown'
    )


# ─── Other Admin Commands ───

async def pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    orders = get_pending_payment_orders()
    if not orders:
        await update.message.reply_text("✅ No pending orders.")
        return

    lines = ["⏳ *Pending Orders*\n"]
    for o in orders:
        lines.append(
            f"`#{o['id']}` — {o['service_name']}\n"
            f"   ${o['amount_cents']/100:.2f} | {o.get('payment_method', '?')} | Status: {o['status']}\n"
            f"   User: `{o['telegram_id']}`"
        )
    lines.append("\nUse `/confirm <id>` to process. Use `/senddetails <id> <info>` to give payment details.")

    await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    orders = get_user_orders(telegram_id)

    if not orders:
        await update.message.reply_text(
            "📭 No orders yet.\n\nUse /start to browse services.",
            reply_markup=platform_keyboard()
        )
        return

    lines = ["📦 *Your Orders*\n"]
    for o in orders[:10]:
        lines.append(user_order_summary(o))

    await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')


async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    result = get_balance()
    if result and 'balance' in result:
        await update.message.reply_text(f"💰 Panel Balance: ${float(result['balance']):.2f}")
    else:
        await update.message.reply_text(f"❌ API Error: {result}")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    rev = total_revenue()
    ocount = total_orders()
    panel = get_balance()
    panel_bal = f"${float(panel['balance']):.2f}" if panel and 'balance' in panel else "Error"
    pending = get_pending_payment_orders()

    await update.message.reply_text(
        f"📊 *Admin Dashboard*\n\n"
        f"💰 Revenue: ${rev/100:.2f}\n"
        f"📦 Orders: {ocount}\n"
        f"⏳ Pending: {len(pending)}\n"
        f"🏦 Panel: {panel_bal}",
        parse_mode='Markdown'
    )


async def cancel_order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data.clear()
        await query.edit_message_text("❌ Order cancelled.", reply_markup=platform_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS

    text = (
        "📚 *Commands*\n\n"
        "/start — Browse & order\n"
        "/orders — Your order history\n\n"
    )
    if is_admin:
        text += (
            "*Admin:*\n"
            "/stats — Dashboard\n"
            "/balance — Panel balance\n"
            "/pending — List pending orders\n"
            "/senddetails <id> <info> — Give user payment details\n"
            "/confirm <id> — Confirm payment & process\n"
            "/forceconfirm <id> — Override & process\n"
        )

    await update.message.reply_text(text, parse_mode='Markdown')


# ─── Error Handler ───

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")


# ─── Main ───

def _run_health_server():
    port = int(os.environ.get('PORT', 8080))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        def log_message(self, *args):
            pass

    HTTPServer(('0.0.0.0', port), Handler).serve_forever()


def main():
    init_db()

    threading.Thread(target=_run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", my_orders))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pending", pending_orders))
    app.add_handler(CommandHandler("confirm", confirm_payment))
    app.add_handler(CommandHandler("forceconfirm", force_confirm))
    app.add_handler(CommandHandler("senddetails", send_details))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(CallbackQueryHandler(select_platform, pattern=r'^plat_'))
    app.add_handler(CallbackQueryHandler(select_package, pattern=r'^select_'))
    app.add_handler(CallbackQueryHandler(choose_paypal, pattern=r'^pay_paypal$'))
    app.add_handler(CallbackQueryHandler(choose_manual, pattern=r'^pay_manual$'))
    app.add_handler(CallbackQueryHandler(notify_paid, pattern=r'^notify_paid_'))
    app.add_handler(CallbackQueryHandler(services_menu, pattern=r'^back_platform$'))
    app.add_handler(CallbackQueryHandler(cancel_order_cmd, pattern=r'^cancel_order$'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_details))

    app.add_error_handler(error_handler)

    print("[+] Follower Bot (PayPal + Manual) is running...")
    app.run_polling()


if __name__ == '__main__':
    main()
