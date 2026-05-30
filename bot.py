import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ضع التوكن وID الخاص بك هنا
BOT_TOKEN = "8996497547:AAEPchOmVa-E44d-Q2uYJEaYY02WBQwCrRI"
ADMIN_ID = 5324805376

DB_PATH = "pubg_store.db"

# حالات المحادثة
(ADD_ACC_INFO, ADD_ACC_SUPPLIER, ADD_ACC_PRICE, ADD_ACC_PHOTO,
 SELL_ACC_ID, SELL_CLIENT_NAME, SELL_CLIENT_PHONE, SELL_PRICE,
 ADD_DEBT_NAME, ADD_DEBT_AMOUNT, ADD_DEBT_TYPE, ADD_DEBT_NOTE) = range(12)

# ────────────────────────── قاعدة البيانات ──────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        info TEXT NOT NULL,
        supplier_name TEXT NOT NULL,
        supplier_contact TEXT,
        buy_price REAL,
        sell_price REAL,
        status TEXT DEFAULT 'available',
        client_name TEXT,
        client_contact TEXT,
        photo_id TEXT,
        added_date TEXT,
        sold_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_name TEXT NOT NULL,
        amount REAL NOT NULL,
        debt_type TEXT NOT NULL,
        note TEXT,
        status TEXT DEFAULT 'pending',
        date TEXT
    )''')
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

# ────────────────────────── فحص الأدمن ──────────────────────────

def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("⛔ مش مصرح لك باستخدام هذا البوت.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper

# ────────────────────────── القائمة الرئيسية ──────────────────────────

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 الحسابات المتوفرة", callback_data="available"),
         InlineKeyboardButton("✅ الحسابات المباعة", callback_data="sold")],
        [InlineKeyboardButton("➕ إضافة حساب", callback_data="add_acc"),
         InlineKeyboardButton("💰 تسجيل بيع", callback_data="sell_acc")],
        [InlineKeyboardButton("📊 الديون", callback_data="debts_menu"),
         InlineKeyboardButton("📈 الإحصائيات", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(keyboard)

@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *مرحباً في بوت إدارة حسابات PUBG*\n\nاختر من القائمة:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ────────────────────────── عرض الحسابات ──────────────────────────

async def show_available(query):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, info, supplier_name, buy_price FROM accounts WHERE status='available'")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await query.edit_message_text("📭 لا يوجد حسابات متوفرة حالياً.", reply_markup=back_btn())
        return

    text = "📦 *الحسابات المتوفرة:*\n\n"
    for r in rows:
        text += f"🆔 `{r[0]}` | {r[1]}\n👤 المورد: {r[2]} | 💵 سعر الشراء: {r[3]} ريال\n─────────────\n"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

async def show_sold(query):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, info, supplier_name, buy_price, sell_price, client_name, client_contact, sold_date FROM accounts WHERE status='sold'")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await query.edit_message_text("📭 لا يوجد حسابات مباعة.", reply_markup=back_btn())
        return

    text = "✅ *الحسابات المباعة:*\n\n"
    for r in rows:
        profit = (r[4] or 0) - (r[3] or 0)
        text += (f"🆔 `{r[0]}` | {r[1]}\n"
                 f"👤 المورد: {r[2]}\n"
                 f"🛒 العميل: {r[5]} - {r[6]}\n"
                 f"💵 شراء: {r[3]} | بيع: {r[4]} | ربح: {profit:.1f}\n"
                 f"📅 {r[7]}\n─────────────\n")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

# ────────────────────────── إضافة حساب ──────────────────────────

async def add_acc_start(query, context):
    context.user_data.clear()
    await query.edit_message_text(
        "➕ *إضافة حساب جديد*\n\nأرسل معلومات الحساب (اسم اللاعب، المستوى، المحتوى...):",
        parse_mode="Markdown"
    )
    return ADD_ACC_INFO

async def add_acc_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    context.user_data['info'] = update.message.text
    await update.message.reply_text("👤 اسم المورد اللي اشتريت منه:")
    return ADD_ACC_SUPPLIER

async def add_acc_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    context.user_data['supplier_name'] = update.message.text
    await update.message.reply_text("📞 تواصل المورد (يوزر أو رقم) - أو أرسل /skip:")
    return ADD_ACC_PRICE

async def add_acc_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    if update.message.text != '/skip':
        context.user_data['supplier_contact'] = update.message.text
    await update.message.reply_text("💵 سعر الشراء (بالريال):")
    return ADD_ACC_PHOTO

async def add_acc_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    try:
        context.user_data['buy_price'] = float(update.message.text)
    except:
        await update.message.reply_text("❌ أدخل رقم صحيح:")
        return ADD_ACC_PHOTO
    await update.message.reply_text("📸 أرسل صورة الحساب - أو /skip لتخطي:")
    return ConversationHandler.END + 1  # نستخدم state خاص للصورة

async def add_acc_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    photo_id = None
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
    elif update.message.text != '/skip':
        await update.message.reply_text("أرسل صورة أو /skip:")
        return ConversationHandler.END + 1

    d = context.user_data
    conn = get_conn()
    conn.execute(
        "INSERT INTO accounts (info, supplier_name, supplier_contact, buy_price, photo_id, added_date) VALUES (?,?,?,?,?,?)",
        (d.get('info'), d.get('supplier_name'), d.get('supplier_contact'), d.get('buy_price'), photo_id, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ تم إضافة الحساب بنجاح!", reply_markup=main_menu())
    context.user_data.clear()
    return ConversationHandler.END

# ────────────────────────── تسجيل بيع ──────────────────────────

async def sell_start(query, context):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, info FROM accounts WHERE status='available'")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await query.edit_message_text("📭 ما في حسابات متوفرة للبيع.", reply_markup=back_btn())
        return ConversationHandler.END

    text = "💰 *تسجيل بيع*\n\nالحسابات المتوفرة:\n"
    for r in rows:
        text += f"🆔 `{r[0]}` | {r[1]}\n"
    text += "\nأرسل رقم ID الحساب المباع:"
    await query.edit_message_text(text, parse_mode="Markdown")
    return SELL_ACC_ID

async def sell_acc_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    try:
        acc_id = int(update.message.text)
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id FROM accounts WHERE id=? AND status='available'", (acc_id,))
        if not c.fetchone():
            await update.message.reply_text("❌ ID غير موجود أو الحساب مباع. أعد المحاولة:")
            conn.close()
            return SELL_ACC_ID
        conn.close()
        context.user_data['sell_id'] = acc_id
        await update.message.reply_text("👤 اسم العميل:")
        return SELL_CLIENT_NAME
    except:
        await update.message.reply_text("❌ أدخل رقم صحيح:")
        return SELL_ACC_ID

async def sell_client_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    context.user_data['client_name'] = update.message.text
    await update.message.reply_text("📞 تواصل العميل:")
    return SELL_CLIENT_PHONE

async def sell_client_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    context.user_data['client_contact'] = update.message.text
    await update.message.reply_text("💵 سعر البيع (بالريال):")
    return SELL_PRICE

async def sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    try:
        price = float(update.message.text)
    except:
        await update.message.reply_text("❌ أدخل رقم صحيح:")
        return SELL_PRICE

    d = context.user_data
    conn = get_conn()
    conn.execute(
        "UPDATE accounts SET status='sold', sell_price=?, client_name=?, client_contact=?, sold_date=? WHERE id=?",
        (price, d['client_name'], d['client_contact'], datetime.now().strftime("%Y-%m-%d %H:%M"), d['sell_id'])
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ *تم تسجيل البيع!*\n\n🆔 حساب: `{d['sell_id']}`\n👤 العميل: {d['client_name']}\n💵 سعر البيع: {price} ريال",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    context.user_data.clear()
    return ConversationHandler.END

# ────────────────────────── الديون ──────────────────────────

def debts_menu_kb():
    keyboard = [
        [InlineKeyboardButton("💸 ديون لي (مدينون لي)", callback_data="debts_for_me"),
         InlineKeyboardButton("🔴 ديون عليّ", callback_data="debts_on_me")],
        [InlineKeyboardButton("➕ إضافة دين", callback_data="add_debt"),
         InlineKeyboardButton("✅ تسوية دين", callback_data="settle_debt")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_debts(query, debt_type):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, person_name, amount, note, date FROM debts WHERE debt_type=? AND status='pending'", (debt_type,))
    rows = c.fetchall()
    conn.close()

    title = "💸 *الديون لي (مدينون لي):*" if debt_type == 'for_me' else "🔴 *الديون عليّ:*"
    if not rows:
        await query.edit_message_text(f"{title}\n\nلا يوجد ديون.", reply_markup=back_btn())
        return

    total = sum(r[2] for r in rows)
    text = f"{title}\n\n"
    for r in rows:
        text += f"🆔 `{r[0]}` | 👤 {r[1]}\n💰 {r[2]} ريال | 📝 {r[3] or '-'}\n📅 {r[4]}\n─────────\n"
    text += f"\n💰 *الإجمالي: {total} ريال*"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

async def add_debt_start(query, context):
    context.user_data.clear()
    await query.edit_message_text("➕ *إضافة دين*\n\nاسم الشخص:", parse_mode="Markdown")
    return ADD_DEBT_NAME

async def add_debt_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    context.user_data['debt_name'] = update.message.text
    await update.message.reply_text("💰 المبلغ (ريال):")
    return ADD_DEBT_AMOUNT

async def add_debt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    try:
        context.user_data['debt_amount'] = float(update.message.text)
    except:
        await update.message.reply_text("❌ أدخل رقم:")
        return ADD_DEBT_AMOUNT
    keyboard = [[InlineKeyboardButton("💸 دين لي", callback_data="dtype_for_me"),
                 InlineKeyboardButton("🔴 دين عليّ", callback_data="dtype_on_me")]]
    await update.message.reply_text("نوع الدين:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_DEBT_TYPE

async def add_debt_type_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['debt_type'] = 'for_me' if query.data == 'dtype_for_me' else 'on_me'
    await query.edit_message_text("📝 ملاحظة (أو /skip):")
    return ADD_DEBT_NOTE

async def add_debt_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return ConversationHandler.END
    note = None if update.message.text == '/skip' else update.message.text
    d = context.user_data
    conn = get_conn()
    conn.execute(
        "INSERT INTO debts (person_name, amount, debt_type, note, date) VALUES (?,?,?,?,?)",
        (d['debt_name'], d['debt_amount'], d['debt_type'], note, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()
    dtype = "لي 💸" if d['debt_type'] == 'for_me' else "عليّ 🔴"
    await update.message.reply_text(
        f"✅ تم تسجيل الدين!\n👤 {d['debt_name']}\n💰 {d['debt_amount']} ريال ({dtype})",
        reply_markup=main_menu()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def settle_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    try:
        debt_id = int(context.args[0])
        conn = get_conn()
        conn.execute("UPDATE debts SET status='settled' WHERE id=?", (debt_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تم تسوية الدين رقم {debt_id}", reply_markup=main_menu())
    except:
        await update.message.reply_text("الاستخدام: /settle 5 (رقم الدين)")

# ────────────────────────── الإحصائيات ──────────────────────────

async def show_stats(query):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM accounts WHERE status='available'")
    avail = c.fetchone()[0]
    c.execute("SELECT COUNT(*), SUM(sell_price), SUM(buy_price) FROM accounts WHERE status='sold'")
    sold_data = c.fetchone()
    c.execute("SELECT SUM(amount) FROM debts WHERE debt_type='for_me' AND status='pending'")
    debts_for_me = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM debts WHERE debt_type='on_me' AND status='pending'")
    debts_on_me = c.fetchone()[0] or 0
    conn.close()

    sold_count = sold_data[0] or 0
    total_revenue = sold_data[1] or 0
    total_cost = sold_data[2] or 0
    profit = total_revenue - total_cost

    text = (f"📈 *الإحصائيات:*\n\n"
            f"📦 حسابات متوفرة: {avail}\n"
            f"✅ حسابات مباعة: {sold_count}\n\n"
            f"💵 إجمالي المبيعات: {total_revenue:.1f} ريال\n"
            f"💰 إجمالي الربح: {profit:.1f} ريال\n\n"
            f"💸 مدينون لي: {debts_for_me:.1f} ريال\n"
            f"🔴 ديون عليّ: {debts_on_me:.1f} ريال\n"
            f"📊 صافي الديون: {debts_for_me - debts_on_me:.1f} ريال")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

# ────────────────────────── Callbacks ──────────────────────────

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text("🎮 *القائمة الرئيسية:*", reply_markup=main_menu(), parse_mode="Markdown")
    elif data == "available":
        await show_available(query)
    elif data == "sold":
        await show_sold(query)
    elif data == "stats":
        await show_stats(query)
    elif data == "debts_menu":
        await query.edit_message_text("📊 *قسم الديون:*", reply_markup=debts_menu_kb(), parse_mode="Markdown")
    elif data == "debts_for_me":
        await show_debts(query, "for_me")
    elif data == "debts_on_me":
        await show_debts(query, "on_me")

# ────────────────────────── تشغيل البوت ──────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler لإضافة حساب
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_acc_start, pattern="^add_acc$")],
        states={
            ADD_ACC_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_acc_info)],
            ADD_ACC_SUPPLIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_acc_supplier)],
            ADD_ACC_PRICE: [MessageHandler(filters.TEXT, add_acc_price)],
            ADD_ACC_PHOTO: [MessageHandler(filters.TEXT, add_acc_photo)],
            ConversationHandler.END + 1: [MessageHandler(filters.PHOTO | filters.TEXT, add_acc_save)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    # ConversationHandler لتسجيل بيع
    sell_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_start, pattern="^sell_acc$")],
        states={
            SELL_ACC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_acc_id)],
            SELL_CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_client_name)],
            SELL_CLIENT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_client_phone)],
            SELL_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_price)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    # ConversationHandler للديون
    debt_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_debt_start, pattern="^add_debt$")],
        states={
            ADD_DEBT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_debt_name)],
            ADD_DEBT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_debt_amount)],
            ADD_DEBT_TYPE: [CallbackQueryHandler(add_debt_type_cb, pattern="^dtype_")],
            ADD_DEBT_NOTE: [MessageHandler(filters.TEXT, add_debt_note)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settle", settle_debt))
    app.add_handler(add_conv)
    app.add_handler(sell_conv)
    app.add_handler(debt_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ البوت شغال!")
    app.run_polling()

if __name__ == "__main__":
    main()
