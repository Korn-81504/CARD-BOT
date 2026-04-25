import sqlite3
import telebot
from telebot import types
import time
import random

# ⚠️ แก้ไขตรงนี้: ใส่ Token ที่ได้จาก @BotFather
TOKEN = "8618360067:AAHA7FxHpnXXtTqF-dwWoD25iMWQZ6G8Jr0"
bot = telebot.TeleBot(TOKEN)

# --- 1. ระบบฐานข้อมูล (SQLite) ---
def init_db():
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (user_id TEXT PRIMARY KEY, name TEXT, money INTEGER, exp INTEGER, level INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS plots 
                 (plot_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, crop_key TEXT, plant_time REAL)''')
    conn.commit()
    conn.close()

# --- 2. ข้อมูลผัก (Emoji & Spec) ---
CROP_BOOK = {
    "basil": {"name": "กะเพรา", "emoji": "🌿", "time": 60, "buy": 50, "sell": 120, "exp": 20},
    "tomato": {"name": "มะเขือเทศ", "emoji": "🍅", "time": 180, "buy": 150, "sell": 400, "exp": 50},
    "melon": {"name": "เมล่อน", "emoji": "🍈", "time": 600, "buy": 500, "sell": 2000, "exp": 150}
}

# --- 3. ฟังก์ชันระบบเกม ---

def get_player(user_id):
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=?", (str(user_id),))
    p = c.fetchone()
    conn.close()
    return p

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    
    if not get_player(uid):
        conn = sqlite3.connect('farm_game.db')
        c = conn.cursor()
        c.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?)", (uid, name, 500, 0, 1))
        conn.commit()
        conn.close()
        msg = f"🌾 ยินดีต้อนรับคุณ {name}! เรามอบเงินขวัญถุงให้ 500.-"
    else:
        msg = f"ยินดีต้อนรับกลับมาครับคุณ {name}!"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚜 ตรวจฟาร์ม', '🛒 ร้านค้า', '💰 กระเป๋าตังค์')
    bot.send_message(message.chat.id, msg, reply_markup=markup)

# --- ระบบร้านค้า (Inline Buttons) ---
@bot.message_handler(func=lambda m: m.text == '🛒 ร้านค้า')
def shop(message):
    p = get_player(message.from_user.id)
    text = f"💰 เงินของคุณ: {p[2]} บาท\nเลือกซื้อเมล็ดพันธุ์ที่ต้องการปลูก:"
    
    markup = types.InlineKeyboardMarkup()
    for key, val in CROP_BOOK.items():
        btn = types.InlineKeyboardButton(f"{val['emoji']} {val['name']} ({val['buy']}.-)", callback_data=f"buy_{key}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

# --- ระบบจัดการปุ่มกด (Callback) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    uid = str(call.from_user.id)
    crop_key = call.data.split('_')[1]
    crop = CROP_BOOK[crop_key]
    p = get_player(uid)
    
    if p[2] >= crop['buy']:
        # หักเงินและปลูกทันที
        conn = sqlite3.connect('farm_game.db')
        c = conn.cursor()
        c.execute("UPDATE players SET money = money - ? WHERE user_id = ?", (crop['buy'], uid))
        c.execute("INSERT INTO plots (user_id, crop_key, plant_time) VALUES (?, ?, ?)", (uid, crop_key, time.time()))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, f"ปลูก {crop['name']} สำเร็จ!")
        bot.edit_message_text(f"🌱 ปลูก {crop['name']} เรียบร้อย! รอโตแล้วมาเก็บเกี่ยวนะ", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "เงินไม่พอจ้า!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == '🚜 ตรวจฟาร์ม')
def view_farm(message):
    uid = str(message.from_user.id)
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT plot_id, crop_key, plant_time FROM plots WHERE user_id=?", (uid,))
    plots = c.fetchall()
    conn.close()

    if not plots:
        bot.send_message(message.chat.id, "ไม่มีอะไรในฟาร์มเลย ไปซื้อเมล็ดที่ร้านค้าสิ!")
        return

    res = "👨‍🌾 **ฟาร์มของคุณ**\n\n"
    now = time.time()
    for pid, key, ptime in plots:
        crop = CROP_BOOK[key]
        remain = crop['time'] - (now - ptime)
        if remain <= 0:
            res += f"✅ {crop['emoji']} {crop['name']} (โตแล้ว!) คลิก -> /harvest_{pid}\n"
        else:
            res += f"⏳ {crop['emoji']} {crop['name']} (รออีก {int(remain)} วิ)\n"
    
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '💰 กระเป๋าตังค์')
def wallet(message):
    p = get_player(message.from_user.id)
    bot.reply_to(message, f"👤 ชื่อ: {p[1]}\n⭐ เลเวล: {p[4]}\n✨ EXP: {p[3]}\n💰 เงิน: {p[2]} บาท")

# --- ระบบเก็บเกี่ยว ---
@bot.message_handler(regexp=r'/harvest_(\d+)')
def harvest(message):
    pid = message.text.split('_')[1]
    uid = str(message.from_user.id)
    
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT crop_key FROM plots WHERE plot_id=? AND user_id=?", (pid, uid))
    row = c.fetchone()
    
    if row:
        crop = CROP_BOOK[row[0]]
        # ให้เงินและ EXP
        c.execute("UPDATE players SET money = money + ?, exp = exp + ? WHERE user_id = ?", (crop['sell'], crop['exp'], uid))
        c.execute("DELETE FROM plots WHERE plot_id=?", (pid,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🧺 เก็บเกี่ยว {crop['emoji']} ขายได้ {crop['sell']}.- และได้รับ {crop['exp']} EXP!")
    else:
        bot.reply_to(message, "ไม่พบข้อมูลการเก็บเกี่ยว หรืออาจเก็บไปแล้ว")

# --- รันบอท ---
if __name__ == "__main__":
    init_db()
    print("Farm Bot is Running...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")
