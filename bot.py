import os
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import init_db, get_user, update_sant

TOKEN = "8507497335:AAGAAyTag5KuSFFGJpUijuOTgDzU6UeCHOg"
ADMIN_ID = 8854073031

admin_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    user = update.effective_user
    
    if chat_type == "private":
        get_user(user.id, user.username or "")
        keyboard = [
            [InlineKeyboardButton("🎁 دریافت کد هدیه", callback_data="get_promo")],
            [InlineKeyboardButton("➕ افزودن ربات به گروه", url=f"https://t.me/{context.bot.username}?startgroup=true")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "سلام! به ربات خوش اومدی. برای استفاده از بازی‌ها، ربات رو به گروه خودت اضافه کن.",
            reply_markup=reply_markup
        )

async def sant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    user = update.effective_user
    sant, _ = get_user(user.id, user.username or "")
    await update.message.reply_text(f"📏 اندازه سانت شما: {sant} سانت")

async def kir_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    user = update.effective_user
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_claim FROM users WHERE user_id = ?', (user.id,))
    res = cursor.fetchone()
    conn.close()
    
    now = datetime.now()
    if res and res[0]:
        last_time = datetime.fromisoformat(res[0])
        if now - last_time < timedelta(hours=5):
            remaining = timedelta(hours=5) - (now - last_time)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            await update.message.reply_text(f"⏳ باید {hours} ساعت و {minutes} دقیقه دیگر صبر کنید!")
            return

    # سیستم شانس (۱ تا ۳۰ شانس بیشتر)
    if random.random() < 0.75:
        amount = random.randint(1, 30)
    else:
        amount = random.randint(31, 70)
        
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET sant = sant + ?, last_claim = ? WHERE user_id = ?', (amount, now.isoformat(), user.id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"🎉 شانس شما: {amount} سانت به موجودی شما اضافه شد!")

async def bazi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("❌ لطفاً مقدار سانت را وارد کنید. مثال: بازی 20")
        return
    
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ مقدار نامعتبر است.")
        return
        
    sant, _ = get_user(user.id, user.username or "")
    if sant < amount:
        await update.message.reply_text("❌ موجودی ناکافی هست!")
        return
        
    update_sant(user.id, -amount)
    
    keyboard = [
        [InlineKeyboardButton("🚪 ورود به بازی", callback_data=f"join_{user.id}_{amount}"),
         InlineKeyboardButton("❌ لغو بازی", callback_data=f"cancel_{user.id}_{amount}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = await update.message.reply_text(
        f"🎮 بازی {amount} سانتی ساخته شد!\nسازنده: @{user.username or user.first_name}\nبرای لغو روی لغو و برای ورود روی ورود بزنید.",
        reply_markup=reply_markup
    )
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO games (creator_id, amount, message_id, chat_id) VALUES (?, ?, ?, ?)', 
                   (user.id, amount, msg.message_id, update.effective_chat.id))
    conn.commit()
    conn.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    
    if data.startswith("cancel_"):
        _, creator_id, amount = data.split("_")
        creator_id = int(creator_id)
        amount = int(amount)
        
        if user.id != creator_id:
            await query.answer("❌ فقط سازنده بازی می‌تواند آن را لغو کند!", show_alert=True)
            return
            
        update_sant(creator_id, amount)
        await query.message.edit_text("❌ بازی توسط سازنده لغو شد و سانت برگشت داده شد.")
        
    elif data.startswith("join_"):
        _, creator_id, amount = data.split("_")
        creator_id = int(creator_id)
        amount = int(amount)
        
        if user.id == creator_id:
            await query.answer("❌ سازنده نمی‌تواند وارد بازی خود شود!", show_alert=True)
            return
            
        sant, _ = get_user(user.id, user.username or "")
        if sant < amount:
            await query.answer("❌ موجودی شما ناکافی است!", show_alert=True)
            return
            
        update_sant(user.id, -amount)
        winner = random.choice([creator_id, user.id])
        prize = amount * 2
        update_sant(winner, prize)
        
        winner_user = await context.bot.get_chat(winner)
        winner_name = winner_user.username or winner_user.first_name
        
        await query.message.edit_text(
            f"🏆 بازی به پایان رسید!\nمبلغ کل جایزه: {prize} سانت\nبرنده: @{winner_name} 🎉"
        )
        
    elif data == "get_promo":
        await query.message.reply_text("لطفاً کد هدیه خود را ارسال کنید:")
        admin_states[user.id] = "waiting_promo_input"
        await query.answer()

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
        
    admin_states[user.id] = "step_code"
    await update.message.reply_text("🛠 پنل مدیریت:\nلطفاً متن/نام کد هدیه را بفرستید:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message or not update.message.text:
        return
    text = update.message.text
    
    if user.id == ADMIN_ID and user.id in admin_states:
        state = admin_states[user.id]
        
        if state == "step_code":
            admin_states[f"{user.id}_code"] = text
            admin_states[user.id] = "step_count"
            await update.message.reply_text("ظرفیت این کد هدیه را بفرستید (مثلاً 3):")
            return
            
        elif state == "step_count":
            try:
                admin_states[f"{user.id}_count"] = int(text)
                admin_states[user.id] = "step_amount"
                await update.message.reply_text("تعداد سانت هدیه را بفرستید:")
            except ValueError:
                await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
            return
            
        elif state == "step_amount":
            try:
                amount = int(text)
                code = admin_states.pop(f"{user.id}_code")
                count = admin_states.pop(f"{user.id}_count")
                admin_states.pop(user.id)
                
                conn = sqlite3.connect('bot_database.db')
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO promo_codes (code, count, amount) VALUES (?, ?, ?)', (code, count, amount))
                conn.commit()
                conn.close()
                
                await update.message.reply_text(f"✅ کد هدیه '{code}' با ظرفیت {count} نفر و مبلغ {amount} سانت با موفقیت ساخته شد.")
            except ValueError:
                await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
            return

    if user.id in admin_states and admin_states[user.id] == "waiting_promo_input":
        code = text.strip()
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT count, amount FROM promo_codes WHERE code = ?', (code,))
        promo = cursor.fetchone()
        
        if not promo:
            await update.message.reply_text("❌ کد هدیه نامعتبر است.")
            conn.close()
            return
            
        count, amount = promo
        
        cursor.execute('SELECT * FROM used_promos WHERE user_id = ? AND code = ?', (user.id, code))
        if cursor.fetchone():
            await update.message.reply_text("❌ شما قبلاً از این کد استفاده کرده اید!")
            conn.close()
            return
            
        cursor.execute('SELECT COUNT(*) FROM used_promos WHERE code = ?', (code,))
        used_count = cursor.fetchone()[0]
        
        if used_count >= count:
            await update.message.reply_text("❌ کد هدیه تمام شده است!")
            conn.close()
            return
            
        cursor.execute('INSERT INTO used_promos (user_id, code) VALUES (?, ?)', (user.id, code))
        conn.commit()
        conn.close()
        
        update_sant(user.id, amount)
        sant, _ = get_user(user.id)
        admin_states.pop(user.id, None)
        
        await update.message.reply_text(f"🎁 تبریک! {amount} سانت به شما اضافه شد.\n📏 موجودی جدید: {sant} سانت")

def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sant", sant_command))
    application.add_handler(CommandHandler("kir", kir_command))
    application.add_handler(CommandHandler("bazi", bazi_command))
    application.add_handler(CommandHandler("panel", panel_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    application.run_polling()

if __name__ == '__main__':
    main()
