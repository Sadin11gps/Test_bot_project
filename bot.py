import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# এডমিন পাসওয়ার্ড
ADMIN_PASSWORD = "Rdsvai11"

# ডাটাবেস সেটআপ
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            subscription_type TEXT DEFAULT 'free',
            subscription_expiry DATE,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# নিউজ ক্যাটাগরি
NEWS_CATEGORIES = {
    'tech': {
        'name': '💻 টেকনোলজি',
        'articles': [
            {'title': 'AI কীভাবে বিশ্ব বদলে দিচ্ছে', 'summary': 'কৃত্রিম বুদ্ধিমত্তার নতুন বিপ্লব...', 'url': 'https://example.com/ai-revolution'},
            {'title': 'মেটাভার্সের ভবিষ্যৎ', 'summary': 'আগামী ৫ বছরে মেটাভার্স...', 'url': 'https://example.com/metaverse-future'},
            {'title': 'সাইবার নিরাপত্তা টিপস', 'summary': 'আপনার ডেটা কীভাবে সুরক্ষিত রাখবেন...', 'url': 'https://example.com/cyber-security'}
        ]
    },
    'business': {
        'name': '📈 ব্যবসা-বাণিজ্য',
        'articles': [
            {'title': 'স্টার্টআপ ফান্ডিং গাইড', 'summary': 'কীভাবে ভেনচার ক্যাপিটাল পাওয়া যায়...', 'url': 'https://example.com/startup-funding'},
            {'title': '২০২৪-এর মার্কেট ট্রেন্ড', 'summary': 'এই বছর কোন সেক্টরে বিনিয়োগ করবেন...', 'url': 'https://example.com/market-trends'}
        ]
    },
    'education': {
        'name': '🎓 শিক্ষা',
        'articles': [
            {'title': 'ফ্রিতে প্রোগ্রামিং শিখুন', 'summary': 'শীর্ষ ৫ বাংলা রিসোর্স...', 'url': 'https://example.com/free-programming'},
            {'title': 'অনলাইন ডিগ্রির মান', 'summary': 'বিশ্ববিদ্যালয়ের অনলাইন কোর্স...', 'url': 'https://example.com/online-degree'}
        ]
    }
}

# ইউটিলিটি ফাংশন
def add_user(user_id, username, full_name):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, full_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, full_name))
    conn.commit()
    conn.close()

def get_user_subscription(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subscription_type, subscription_expiry FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else ('free', None)

def is_premium(user_id):
    sub_type, expiry = get_user_subscription(user_id)
    if sub_type == 'premium':
        if expiry:
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
            return expiry_date >= datetime.now().date()
        return True
    return False

def is_admin(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_admin(user_id, added_by):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)', (user_id, added_by))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE subscription_type = "premium"')
    premium = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE("now")')
    today = cursor.fetchone()[0]
    
    conn.close()
    return total, premium, today

def log_user_action(user_id, action):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_stats (user_id, action) VALUES (?, ?)', (user_id, action))
    conn.commit()
    conn.close()

def get_user_by_username(username):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, full_name FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result

def update_user_subscription(user_id, sub_type, days):
    expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET subscription_type = ?, subscription_expiry = ?
        WHERE user_id = ?
    ''', (sub_type, expiry_date, user_id))
    conn.commit()
    conn.close()
    return expiry_date

def get_recent_users(limit=10):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, full_name, subscription_type, 
               subscription_expiry, join_date
        FROM users
        ORDER BY join_date DESC
        LIMIT ?
    ''', (limit,))
    users = cursor.fetchall()
    conn.close()
    return users

# কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.full_name)
    log_user_action(user.id, 'start')
    
    welcome_text = f"""
✨ **স্বাগতম, {user.full_name}!** ✨

আমি **NewsHub BD**, আপনার ব্যক্তিগত নিউজ অ্যাগ্রিগেটর বট। 
আপনার পছন্দের ক্যাটাগরির সর্বশেষ আর্টিকেল এবং গাইড আমি আপনার কাছে পৌঁছে দিব।

📊 **আপনার স্ট্যাটাস:** {'🌟 **প্রিমিয়াম ইউজার**' if is_premium(user.id) else '🆓 **ফ্রি ট্রায়াল**'}
🆓 **ফ্রি ইউজার:** ৩টি আর্টিকেল/দিন
🌟 **প্রিমিয়াম ইউজার:** আনলিমিটেড + বিশেষ কন্টেন্ট

নিচের বাটন থেকে আপনার পছন্দের অপশন বেছে নিন!
    """
    
    keyboard = [
        [InlineKeyboardButton("📰 নিউজ ক্যাটাগরি", callback_data='news_categories')],
        [InlineKeyboardButton("🌟 প্রিমিয়াম আপগ্রেড", callback_data='premium_upgrade')],
        [InlineKeyboardButton("👤 আমার প্রোফাইল", callback_data='my_profile')],
        [InlineKeyboardButton("ℹ️ সাহায্য", callback_data='help'), InlineKeyboardButton("📞 যোগাযোগ", callback_data='contact')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        # এডমিন না হলে পাসওয়ার্ড চাইবে
        await update.message.reply_text(
            "🔐 **এডমিন লগইন**\n\nদয়া করে এডমিন পাসওয়ার্ড দিন:"
        )
        context.user_data['awaiting_admin_pass'] = True
        return
    
    # এডমিন হলে সরাসরি প্যানেল দেখাবে
    await show_admin_panel(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_admin_pass'):
        user = update.effective_user
        password = update.message.text
        
        if password == ADMIN_PASSWORD:
            add_admin(user.id, user.id)
            await update.message.reply_text("✅ **লগইন সফল!**\n\nএডমিন হিসেবে যুক্ত করা হয়েছে।")
            await show_admin_panel(update, context)
        else:
            await update.message.reply_text("❌ **ভুল পাসওয়ার্ড!**\n\nআবার চেষ্টা করুন বা /start কমান্ড দিন।")
        
        context.user_data['awaiting_admin_pass'] = False
        return

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        if update.callback_query:
            await update.callback_query.answer("⛔ আপনার এডমিন অ্যাক্সেস নেই!", show_alert=True)
            return
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    total_users, premium_users, today_users = get_all_users()
    
    admin_text = f"""
🔐 **এডমিন প্যানেল** - NewsHub BD

📊 **বট স্ট্যাটিস্টিকস:**
├ 👥 **মোট ইউজার:** {total_users}
├ 🌟 **প্রিমিয়াম ইউজার:** {premium_users}
├ 📈 **আজকের নতুন ইউজার:** {today_users}
└ 📊 **প্রিমিয়াম রেট:** {round((premium_users/total_users*100 if total_users > 0 else 0), 2)}%

⚙️ **এডমিন টুলস:**

নিচের বাটন থেকে অপশন সিলেক্ট করুন:
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 ইউজার ম্যানেজমেন্ট", callback_data='admin_users')],
        [InlineKeyboardButton("🎫 সাবস্ক্রিপশন ম্যানেজ", callback_data='admin_subs')],
        [InlineKeyboardButton("📢 ব্রডকাস্ট মেসেজ", callback_data='admin_broadcast')],
        [InlineKeyboardButton("➕ এডমিন ম্যানেজমেন্ট", callback_data='admin_add')],
        [InlineKeyboardButton("🔙 বট মেনু", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ অ্যাক্সেস ডিনাইড!", show_alert=True)
        return
    
    recent_users = get_recent_users(10)
    
    users_text = "👥 **সর্বশেষ ১০ ইউজার:**\n\n"
    
    for idx, user_data in enumerate(recent_users, 1):
        user_id, username, full_name, sub_type, sub_expiry, join_date = user_data
        
        username_display = f"@{username}" if username else "N/A"
        expiry_display = sub_expiry if sub_expiry else "N/A"
        
        users_text += f"{idx}. **{full_name}**\n"
        users_text += f"   ├ ID: `{user_id}`\n"
        users_text += f"   ├ Username: {username_display}\n"
        users_text += f"   ├ সাবস্ক্রিপশন: {sub_type}\n"
        users_text += f"   └ যোগদান: {join_date[:10]}\n\n"
    
    total_users, premium_users, today_users = get_all_users()
    users_text += f"📈 **সারাংশ:**\n"
    users_text += f"• মোট: {total_users} ইউজার\n"
    users_text += f"• প্রিমিয়াম: {premium_users}\n"
    users_text += f"• আজ যুক্ত: {today_users}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 এডমিন প্যানেল", callback_data='admin_panel')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(users_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ অ্যাক্সেস ডিনাইড!", show_alert=True)
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE subscription_type = 'premium' 
        AND DATE(subscription_expiry) >= DATE('now')
    ''')
    active_premium = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE subscription_type = 'premium' 
        AND DATE(subscription_expiry) BETWEEN DATE('now') AND DATE('now', '+7 days')
    ''')
    expiring_soon = cursor.fetchone()[0]
    
    conn.close()
    
    monthly_revenue = active_premium * 150
    
    subs_text = f"""
🎫 **সাবস্ক্রিপশন ম্যানেজমেন্ট**

📊 **কারেন্ট স্ট্যাটাস:**
├ 🌟 **একটিভ প্রিমিয়াম:** {active_premium} ইউজার
├ ⚠️ **৭ দিনের মধ্যে এক্সপায়ার:** {expiring_soon} ইউজার
└ 💰 **অনুমানিক মাসিক রেভিনিউ:** ৳{monthly_revenue}

**কমান্ড:**
• প্রিমিয়াম দিতে: `/givepremium [user_id] [days]`
• প্রিমিয়াম বাতিল: `/removepremium [user_id]`
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 এডমিন প্যানেল", callback_data='admin_panel')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(subs_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ অ্যাক্সেস ডিনাইড!", show_alert=True)
        return
    
    broadcast_text = """
📢 **ব্রডকাস্ট মেসেজ**

**কমান্ড:**
• সব ইউজারকে: `/broadcastall [message]`
• শুধু প্রিমিয়াম: `/broadcastpremium [message]`
• শুধু ফ্রি: `/broadcastfree [message]`

⚠️ **সতর্কতা:** বেশি ব্রডকাস্ট করলে বট স্প্যাম হিসেবে চিহ্নিত হতে পারে।
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 এডমিন প্যানেল", callback_data='admin_panel')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(broadcast_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ অ্যাক্সেস ডিনাইড!", show_alert=True)
        return
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.user_id, u.username, u.full_name, a.added_date
        FROM admins a
        LEFT JOIN users u ON a.user_id = u.user_id
    ''')
    admins = cursor.fetchall()
    conn.close()
    
    admin_text = "👑 **বর্তমান এডমিন লিস্ট:**\n\n"
    
    for idx, admin_data in enumerate(admins, 1):
        admin_id, username, full_name, added_date = admin_data
        username_display = f"@{username}" if username else "N/A"
        admin_text += f"{idx}. **{full_name}**\n"
        admin_text += f"   ├ ID: `{admin_id}`\n"
        admin_text += f"   ├ Username: {username_display}\n"
        admin_text += f"   └ যোগদান: {added_date[:10]}\n\n"
    
    admin_text += "\n**কমান্ড:**
➕ এডমিন যোগ: `/addadmin [user_id]`
➖ এডমিন রিমুভ: `/removeadmin [user_id]`
🔍 ইউজার খুঁজুন: `/finduser [username]`"
    
    keyboard = [
        [InlineKeyboardButton("🔙 এডমিন প্যানেল", callback_data='admin_panel')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_admin_panel(update, context)

async def addadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/addadmin [user_id]`\n\nযেমন: `/addadmin 123456789`")
        return
    
    try:
        new_admin_id = int(context.args[0])
        add_admin(new_admin_id, user.id)
        
        await update.message.reply_text(f"✅ **সফল!**\n\nইউজার `{new_admin_id}` কে এডমিন হিসেবে যোগ করা হয়েছে।")
    except ValueError:
        await update.message.reply_text("❌ **ভুল ইউজার আইডি!**\n\nসঠিক সংখ্যা দিন।")

async def removeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/removeadmin [user_id]`\n\nযেমন: `/removeadmin 123456789`")
        return
    
    try:
        admin_id = int(context.args[0])
        
        if admin_id == user.id:
            await update.message.reply_text("❌ **আপনি নিজেকে রিমুভ করতে পারবেন না!**")
            return
        
        remove_admin(admin_id)
        await update.message.reply_text(f"✅ **সফল!**\n\nইউজার `{admin_id}` কে এডমিন লিস্ট থেকে রিমুভ করা হয়েছে।")
    except ValueError:
        await update.message.reply_text("❌ **ভুল ইউজার আইডি!**\n\nসঠিক সংখ্যা দিন。")

async def finduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/finduser [username]`\n\nইউজারনেমে @ ব্যবহার করবেন না।\nযেমন: `/finduser username`")
        return
    
    username = context.args[0].replace('@', '')
    user_data = get_user_by_username(username)
    
    if user_data:
        user_id, full_name = user_data
        await update.message.reply_text(
            f"✅ **ইউজার পাওয়া গেছে!**\n\n"
            f"👤 **নাম:** {full_name}\n"
            f"📛 **ইউজারনেম:** @{username}\n"
            f"🆔 **ইউজার আইডি:** `{user_id}`"
        )
    else:
        await update.message.reply_text(f"❌ **ইউজার পাওয়া যায়নি!**\n\nইউজারনেম: @{username}")

async def givepremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/givepremium [user_id] [days]`\n\nযেমন: `/givepremium 123456789 30`")
        return
    
    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1])
        
        expiry_date = update_user_subscription(target_user_id, 'premium', days)
        
        await update.message.reply_text(
            f"✅ **সফল!**\n\n"
            f"ইউজার `{target_user_id}` কে {days} দিনের জন্য প্রিমিয়াম দেওয়া হয়েছে।\n"
            f"📅 **মেয়াদ শেষ:** {expiry_date}"
        )
    except ValueError:
        await update.message.reply_text("❌ **ভুল ইনপুট!**\n\nসঠিক সংখ্যা দিন。")

async def removepremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/removepremium [user_id]`\n\nযেমন: `/removepremium 123456789`")
        return
    
    try:
        target_user_id = int(context.args[0])
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET subscription_type = 'free', subscription_expiry = NULL
            WHERE user_id = ?
        ''', (target_user_id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ **সফল!**\n\nইউজার `{target_user_id}` এর প্রিমিয়াম বাতিল করা হয়েছে।")
    except ValueError:
        await update.message.reply_text("❌ **ভুল ইউজার আইডি!**\n\nসঠিক সংখ্যা দিন。")

async def broadcastall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/broadcastall [message]`\n\nযেমন: `/broadcastall নতুন আপডেট আসছে!`")
        return
    
    message = ' '.join(context.args)
    
    await update.message.reply_text("📤 **ব্রডকাস্ট শুরু...**")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    all_users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user_data in all_users:
        try:
            user_id = user_data[0]
            await context.bot.send_message(chat_id=user_id, text=f"📢 **ব্রডকাস্ট:**\n\n{message}")
            success += 1
        except Exception as e:
            failed += 1
    
    await update.message.reply_text(f"✅ **ব্রডকাস্ট সম্পন্ন!**\n\nসফল: {success}\nব্যর্থ: {failed}")

async def broadcastpremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/broadcastpremium [message]`")
        return
    
    message = ' '.join(context.args)
    
    await update.message.reply_text("📤 **প্রিমিয়াম ইউজারদের কাছে ব্রডকাস্ট শুরু...**")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id FROM users 
        WHERE subscription_type = 'premium' 
        AND DATE(subscription_expiry) >= DATE('now')
    ''')
    premium_users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user_data in premium_users:
        try:
            user_id = user_data[0]
            await context.bot.send_message(chat_id=user_id, text=f"🌟 **প্রিমিয়াম ব্রডকাস্ট:**\n\n{message}")
            success += 1
        except Exception as e:
            failed += 1
    
    await update.message.reply_text(f"✅ **ব্রডকাস্ট সম্পন্ন!**\n\nসফল: {success}\nব্যর্থ: {failed}")

async def broadcastfree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ **অ্যাক্সেস ডিনাইড!**\n\nআপনার এডমিন অ্যাক্সেস নেই।")
        return
    
    if not context.args:
        await update.message.reply_text("❌ **ইউজেজ:**\n`/broadcastfree [message]`")
        return
    
    message = ' '.join(context.args)
    
    await update.message.reply_text("📤 **ফ্রি ইউজারদের কাছে ব্রডকাস্ট শুরু...**")
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id FROM users 
        WHERE subscription_type = 'free' 
        OR subscription_type IS NULL
        OR subscription_expiry < DATE('now')
    ''')
    free_users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user_data in free_users:
        try:
            user_id = user_data[0]
            await context.bot.send_message(chat_id=user_id, text=f"🆓 **ফ্রি ব্রডকাস্ট:**\n\n{message}")
            success += 1
        except Exception as e:
            failed += 1
    
    await update.message.reply_text(f"✅ **ব্রডকাস্ট সম্পন্ন!**\n\nসফল: {success}\nব্যর্থ: {failed}")

async def news_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for cat_id, cat_info in NEWS_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(cat_info['name'], callback_data=f'cat_{cat_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "**📰 নিউজ ক্যাটাগরি**\n\nনিচের ক্যাটাগরি থেকে আপনার পছন্দের টপিক নির্বাচন করুন:"
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_category_articles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    cat_id = query.data.split('_')[1]
    category = NEWS_CATEGORIES[cat_id]
    
    articles = category['articles']
    
    text = f"**{category['name']}**\n\n"
    
    user_id = query.from_user.id
    if not is_premium(user_id):
        articles = articles[:1]
        text += "⚠️ *ফ্রি ভার্সনে শুধু ১টি আর্টিকেল দেখানো হচ্ছে*\n"
        text += "🌟 **প্রিমিয়াম আপগ্রেড** করে সবগুলো আর্টিকেল পেতে নিচের বাটনে ক্লিক করুন!\n\n"
    
    for i, article in enumerate(articles, 1):
        text += f"{i}. **{article['title']}**\n"
        text += f"   {article['summary']}\n"
        text += f"   [📖 পুরো আর্টিকেল পড়ুন]({article['url']})\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🌟 প্রিমিয়াম আপগ্রেড", callback_data='premium_upgrade')],
        [InlineKeyboardButton("📰 অন্যান্য ক্যাটাগরি", callback_data='news_categories')],
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def premium_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🌟 **প্রিমিয়াম সাবস্ক্রিপশন**

**ফ্রি ভার্সনের সীমাবদ্ধতা:**
• শুধুমাত্র ১টি আর্টিকেল/ক্যাটাগরি
• দৈনিক ৩টি আর্টিকেল লিমিট
• কিছু ক্যাটাগরি লক করা

**প্রিমিয়াম সুবিধা:**
✅ আনলিমিটেড আর্টিকেল অ্যাক্সেস
✅ সব ক্যাটাগরি আনলক
✅ প্রিয়ারিটি সাপোর্ট
✅ বিশেষ রিসার্চ রিপোর্ট
✅ বিজ্ঞাপন মুক্ত অভিজ্ঞতা

**মূল্য:**
• ৳১৫০/মাস
• ৳৪০০/৩ মাস (সাশ্রয়ী!)
• ৳১২০০/বছর (২ মাস ফ্রি!)

নিচের পেমেন্ট অপশন থেকে নির্বাচন করুন:
    """
    
    keyboard = [
        [InlineKeyboardButton("💳 bKash পেমেন্ট", callback_data='payment_bkash')],
        [InlineKeyboardButton("💳 Nagad পেমেন্ট", callback_data='payment_nagad')],
        [InlineKeyboardButton("🆓 ৩-দিনের ফ্রি ট্রায়াল", callback_data='free_trial')],
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    sub_type, expiry = get_user_subscription(user.id)
    
    if expiry:
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
        remaining = (expiry_date - datetime.now().date()).days
        expiry_text = f"{expiry_date} ({remaining} দিন বাকি)"
    else:
        expiry_text = "সেট আপ হয়নি"
    
    text = f"""
👤 **আপনার প্রোফাইল**

🆔 **আইডি:** `{user.id}`
📛 **নাম:** {user.full_name}
📧 **ইউজারনেম:** @{user.username if user.username else 'N/A'}

📊 **সাবস্ক্রিপশন:**
• **স্ট্যাটাস:** {'🌟 **প্রিমিয়াম**' if is_premium(user.id) else '🆓 **ফ্রি**'}
• **টাইপ:** {sub_type}
• **মেয়াদ শেষ:** {expiry_text}
    """
    
    keyboard = [
        [InlineKeyboardButton("🌟 আপগ্রেড করুন", callback_data='premium_upgrade')],
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
ℹ️ **সাহায্য**

**কীভাবে ব্যবহার করবেন:**
1. /start কমান্ড দিয়ে শুরু করুন
2. নিউজ ক্যাটাগরি থেকে আপনার পছন্দের বিষয় বেছে নিন
3. আর্টিকেল পড়তে "📖 পুরো আর্টিকেল পড়ুন" লিংকে ক্লিক করুন

**কমান্ড লিস্ট:**
/start - বট শুরু করুন
/profile - আপনার প্রোফাইল দেখুন
/help - সাহায্য পান
/contact - আমাদের সাথে যোগাযোগ করুন

**সমস্যা সমাধান:**
• বট কাজ করছে না? রিস্টার্ট করুন
• আর্টিকেল লোড হচ্ছে না? কিছুক্ষণ পর আবার চেষ্টা করুন
• প্রিমিয়াম নিয়ে সমস্যা? যোগাযোগ করুন

📞 **সাপোর্ট:** @NewsHubBD_Support
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
📞 **যোগাযোগ**

**আমাদের সাথে যোগাযোগ করুন:**
✉️ **ইমেইল:** support@newshub-bd.com
📱 **টেলিগ্রাম:** @NewsHubBD_Support

**বিজনেস ইনকোয়ারি:**
📧 **ইমেইল:** business@newshub-bd.com

**প্রিমিয়াম সাপোর্ট:**
• ২৪ ঘণ্টার মধ্যে প্রতিউত্তর
• ভয়েস/ভিডিও কল সাপোর্ট

**কার্যকালীন সময়:**
শনিবার - বৃহস্পতিবার: সকাল ৯টা - রাত ১১টা
শুক্রবার: বন্ধ

🔙 **মেনুতে ফিরতে নিচের বাটনে ক্লিক করুন**
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def free_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    expiry_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET subscription_type = 'premium', subscription_expiry = ?
        WHERE user_id = ?
    ''', (expiry_date, user_id))
    conn.commit()
    conn.close()
    
    text = f"""
🎉 **অভিনন্দন!**

আপনি সফলভাবে **৩ দিনের ফ্রি ট্রায়াল** পেয়েছেন!

✅ **এখন থেকে আপনি:**
• সব ক্যাটাগরিতে আনলিমিটেড অ্যাক্সেস পাবেন
• প্রিমিয়াম কন্টেন্ট দেখতে পারবেন
• বিজ্ঞাপন মুক্ত অভিজ্ঞতা ভোগ করবেন

⏰ **ট্রায়াল শেষ হবে:** {expiry_date}

🌟 **ট্রায়াল শেষ হওয়ার পর** প্রিমিয়াম চালিয়ে যেতে চাইলে প্রিমিয়াম মেনু থেকে পেমেন্ট করুন।

ভালো অভিজ্ঞতা কামনা করছি! ✨
    """
    
    keyboard = [
        [InlineKeyboardButton("📰 নিউজ ক্যাটাগরি", callback_data='news_categories')],
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def payment_bkash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""
💳 **bKash পেমেন্ট**

পেমেন্ট সেন্ড মানি অপশন ব্যবহার করে নিচের নাম্বারে পাঠান:

📱 **bKash নাম্বার:** ০১৭১২-৩৪৫৬৭৮
📝 **রেফারেন্স:** আপনার টেলিগ্রাম আইডি (`{query.from_user.id}`)

**পেমেন্ট স্টেপস:**
1. bKash অ্যাপ খুলুন
2. 'Send Money' নির্বাচন করুন
3. উপরের নাম্বারটি দিন
4. টাকার পরিমাণ দিন (৳১৫০/৳৪০০/৳১২০০)
5. রেফারেন্স হিসাবে আপনার টেলিগ্রাম আইডি দিন
6. পেমেন্ট স্লিপের স্ক্রিনশট নিন

📸 **পেমেন্ট ভেরিফিকেশন:**
পেমেন্ট স্লিপের স্ক্রিনশট @NewsHubBD_Payment পাঠান।

✅ **ভেরিফিকেশনের পর** আপনার অ্যাকাউন্ট ২৪ ঘণ্টার মধ্যে আপগ্রেড করা হবে।
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 প্রিমিয়াম মেনু", callback_data='premium_upgrade')],
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def payment_nagad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""
💳 **Nagad পেমেন্ট**

পেমেন্ট সেন্ড মানি অপশন ব্যবহার করে নিচের নাম্বারে পাঠান:

📱 **Nagad নাম্বার:** ০১৭১২-৩৪৫৬৭৮
📝 **রেফারেন্স:** NBD{query.from_user.id}

**পেমেন্ট স্টেপস:**
1. Nagad অ্যাপ খুলুন
2. 'Send Money' নির্বাচন করুন
3. উপরের নাম্বারটি দিন
4. টাকার পরিমাণ দিন (৳১৫০/৳৪০০/৳১২০০)
5. রেফারেন্স হিসাবে 'NBD{query.from_user.id}' দিন
6. পেমেন্ট স্লিপের স্ক্রিনশট নিন

📸 **পেমেন্ট ভেরিফিকেশন:**
পেমেন্ট স্লিপের স্ক্রিনশট @NewsHubBD_Payment পাঠান।

✅ **ভেরিফিকেশনের পর** আপনার অ্যাকাউন্ট ২৪ ঘণ্টার মধ্যে আপগ্রেড করা হবে।
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 প্রিমিয়াম মেনু", callback_data='premium_upgrade')],
        [InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data='back_to_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "❌ কিছু একটা সমস্যা হয়েছে। দয়া করে কিছুক্ষণ পর আবার চেষ্টা করুন।"
            )
        elif update.message:
            await update.message.reply_text(
                "❌ কিছু একটা সমস্যা হয়েছে। দয়া করে কিছুক্ষণ পর আবার চেষ্টা করুন।"
            )
    except:
        pass

def main():
    TOKEN = "8059084521:AAGuVxr-6-X0Izld_uOD4nazPqd3yaKQgzo"
    
    application = Application.builder().token(TOKEN).build()
    
    # কমান্ড হ্যান্ডলার
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("addadmin", addadmin_command))
    application.add_handler(CommandHandler("removeadmin", removeadmin_command))
    application.add_handler(CommandHandler("finduser", finduser_command))
    application.add_handler(CommandHandler("givepremium", givepremium_command))
    application.add_handler(CommandHandler("removepremium", removepremium_command))
    application.add_handler(CommandHandler("broadcastall", broadcastall_command))
    application.add_handler(CommandHandler("broadcastpremium", broadcastpremium_command))
    application.add_handler(CommandHandler("broadcastfree", broadcastfree_command))
    application.add_handler(CommandHandler("profile", my_profile))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("contact", contact_command))
    
    # কলব্যাক ক্যোয়েরি হ্যান্ডলার
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_subs, pattern='^admin_subs$'))
    application.add_handler(CallbackQueryHandler(admin_broadcast, pattern='^admin_broadcast$'))
    application.add_handler(CallbackQueryHandler(admin_add, pattern='^admin_add$'))
    
    application.add_handler(CallbackQueryHandler(news_categories, pattern='^news_categories$'))
    application.add_handler(CallbackQueryHandler(show_category_articles, pattern='^cat_'))
    application.add_handler(CallbackQueryHandler(premium_upgrade, pattern='^premium_upgrade$'))
    application.add_handler(CallbackQueryHandler(my_profile, pattern='^my_profile$'))
    application.add_handler(CallbackQueryHandler(help_command, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(contact_command, pattern='^contact$'))
    application.add_handler(CallbackQueryHandler(free_trial, pattern='^free_trial$'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$'))
    application.add_handler(CallbackQueryHandler(payment_bkash, pattern='^payment_bkash$'))
    application.add_handler(CallbackQueryHandler(payment_nagad, pattern='^payment_nagad$'))
    
    # মেসেজ হ্যান্ডলার
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # এরর হ্যান্ডলার
    application.add_error_handler(error_handler)
    
    # পোলিং শুরু করুন
    print("🤖 বট চালু হয়েছে...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
