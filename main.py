import sqlite3
import telebot
from telebot import types
import time
import random

# --- ตั้งค่าบอท ---
TOKEN = "8618360067:AAHA7FxHpnXXtTqF-dwWoD25iMWQZ6G8Jr0"
bot = telebot.TeleBot(TOKEN)

# --- 1. ข้อมูลเกม (Config) ---
CROP_BOOK = {
    "basil": {"name": "กะเพรา", "emoji": "🌿", "time": 60, "buy": 50, "sell": 120, "exp": 20},
    "tomato": {"name": "มะเขือเทศ", "emoji": "🍅", "time": 180, "buy": 150, "sell": 400, "exp": 50},
    "melon": {"name": "เมล่อน", "emoji": "🍈", "time": 600, "buy": 500, "sell": 2000, "exp": 150},
    "pineapple": {"name": "สับปะรด", "emoji": "🍍", "time": 1200, "buy": 1000, "sell": 4500, "exp": 300},
    "grapes": {"name": "องุ่น", "emoji": "🍇", "time": 1800, "buy": 2000, "sell": 9000, "exp": 500}
}

ANIMAL_BOOK = {
    "chicken": {"name": "ไก่", "emoji": "🐔", "buy": 1000, "yield": 250, "time": 300, "exp": 40},
    "cow": {"name": "วัว", "emoji": "🐮", "buy": 5000, "yield": 1500, "time": 900, "exp": 120}
}

# --- 2. ระบบฐานข้อมูล ---
def init_db():
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    # ตารางผู้เล่น
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (user_id TEXT PRIMARY KEY, name TEXT, money INTEGER, exp INTEGER, level INTEGER)''')
    # ตารางปลูกผัก
    c.execute('''CREATE TABLE IF NOT EXISTS plots 
                 (plot_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, crop_key TEXT, plant_time REAL)''')
    # ตารางเลี้ยงสัตว์
    c.execute('''CREATE TABLE IF NOT EXISTS animals 
                 (ani_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ani_key TEXT, last_collect REAL)''')
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=?", (str(user_id),))
    p = c.fetchone()
    conn.close()
    return p

def check_levelup(user_id):
    p = get_player(user_id)
    exp, level = p[3], p[4]
    req = level * 150
    if exp >= req:
        new_lvl = level + 1
        conn = sqlite3.connect('farm_game.db')
        c = conn.cursor()
        c.execute("UPDATE players SET level = ?, exp = exp - ? WHERE user_id = ?", (new_lvl, req, user_id))
        conn.commit()
        conn.close()
        return new_lvl
    return None

# --- 3. คำสั่งหลัก ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    if not get_player(uid):
        conn = sqlite3.connect('farm_game.db')
        c = conn.cursor()
        c.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?)", (uid, name, 1000, 0, 1))
        conn.commit()
        conn.close()
        msg = f"🚜 ยินดีต้อนรับเกษตรกรใหม่คุณ {name}! รับเงินขวัญถุง 1,000.-"
    else:
        msg = f"สวัสดีครับคุณ {name} กลับมาดูแลฟาร์มกันเถอะ!"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚜 ตรวจฟาร์ม', '🐥 ตรวจคอกสัตว์')
    markup.add('🛒 ร้านค้าเมล็ด', '🏪 ตลาดสัตว์')
    markup.add('💰 กระเป๋าตังค์', '🏆 อันดับ')
    bot.send_message(message.chat.id, msg, reply_markup=markup)

# --- ระบบร้านค้า ---
@bot.message_handler(func=lambda m: m.text in ['🛒 ร้านค้าเมล็ด', '🏪 ตลาดสัตว์'])
def shop(message):
    p = get_player(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    
    if "เมล็ด" in message.text:
        text = "🌱 **ร้านขายเมล็ดพันธุ์**\nเลือกพืชที่ต้องการปลูก:"
        for k, v in CROP_BOOK.items():
            markup.add(types.InlineKeyboardButton(f"{v['emoji']} {v['name']} ({v['buy']}.-)", callback_data=f"buy_crop_{k}"))
    else:
        text = "🐄 **ตลาดค้าสัตว์**\nซื้อไปเลี้ยงเพื่อเก็บผลผลิตได้เรื่อยๆ:"
        for k, v in ANIMAL_BOOK.items():
            markup.add(types.InlineKeyboardButton(f"{v['emoji']} {v['name']} ({v['buy']}.-)", callback_data=f"buy_ani_{k}"))
            
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buying(call):
    uid = str(call.from_user.id)
    action = call.data.split('_')
    p = get_player(uid)
    
    if action[1] == "crop":
        item = CROP_BOOK[action[2]]
        if p[2] >= item['buy']:
            conn = sqlite3.connect('farm_game.db')
            c = conn.cursor()
            c.execute("UPDATE players SET money = money - ? WHERE user_id = ?", (item['buy'], uid))
            c.execute("INSERT INTO plots (user_id, crop_key, plant_time) VALUES (?, ?, ?)", (uid, action[2], time.time()))
            conn.commit() ; conn.close()
            bot.answer_callback_query(call.id, f"ปลูก {item['name']} แล้ว!")
            bot.edit_message_text(f"🌱 ปลูก {item['emoji']} เรียบร้อย! รอเก็บเกี่ยวได้เลย", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "เงินไม่พอจ้า!", show_alert=True)
            
    elif action[1] == "ani":
        item = ANIMAL_BOOK[action[2]]
        if p[2] >= item['buy']:
            conn = sqlite3.connect('farm_game.db')
            c = conn.cursor()
            c.execute("UPDATE players SET money = money - ? WHERE user_id = ?", (item['buy'], uid))
            c.execute("INSERT INTO animals (user_id, ani_key, last_collect) VALUES (?, ?, ?)", (uid, action[2], time.time()))
            conn.commit() ; conn.close()
            bot.answer_callback_query(call.id, f"ซื้อ {item['name']} เข้าคอกแล้ว!")
            bot.edit_message_text(f"✨ {item['emoji']} เข้าคอกเรียบร้อย! มันจะผลิตของให้คุณเรื่อยๆ", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "เงินไม่พอซื้อสัตว์!", show_alert=True)

# --- ระบบตรวจฟาร์มและเก็บเกี่ยว ---
@bot.message_handler(func=lambda m: m.text == '🚜 ตรวจฟาร์ม')
def view_farm(message):
    uid = str(message.from_user.id)
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT plot_id, crop_key, plant_time FROM plots WHERE user_id=?", (uid,))
    plots = c.fetchall()
    conn.close()

    if not plots:
        bot.send_message(message.chat.id, "ฟาร์มว่างเปล่า ลองไปซื้อเมล็ดมาปลูกดูนะ")
        return

    res = "👨‍🌾 **ฟาร์มของคุณ**\n\n"
    now = time.time()
    for pid, key, ptime in plots:
        crop = CROP_BOOK[key]
        remain = crop['time'] - (now - ptime)
        if remain <= 0:
            res += f"✅ {crop['emoji']} {crop['name']} | เก็บเกี่ยว: /harvest_{pid}\n"
        else:
            res += f"⏳ {crop['emoji']} {crop['name']} | อีก {int(remain)} วิ\n"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

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
        c.execute("UPDATE players SET money = money + ?, exp = exp + ? WHERE user_id = ?", (crop['sell'], crop['exp'], uid))
        c.execute("DELETE FROM plots WHERE plot_id=?", (pid,))
        conn.commit() ; conn.close()
        bot.reply_to(message, f"Basket! เก็บ {crop['emoji']} ขายได้ {crop['sell']}.- ✨+{crop['exp']} EXP")
        new_lvl = check_levelup(uid)
        if new_lvl: bot.send_message(message.chat.id, f"🎊 LEVEL UP! ตอนนี้เลเวล {new_lvl} แล้ว!")
    else: bot.reply_to(message, "ไม่มีพืชนี้แล้ว หรืออาจจะโดนขโมยไป!")

# --- ระบบเลี้ยงสัตว์ ---
@bot.message_handler(func=lambda m: m.text == '🐥 ตรวจคอกสัตว์')
def view_barn(message):
    uid = str(message.from_user.id)
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT ani_id, ani_key, last_collect FROM animals WHERE user_id=?", (uid,))
    anis = c.fetchall()
    conn.close()
    if not anis:
        bot.send_message(message.chat.id, "ไม่มีสัตว์ในคอกเลย")
        return
    res = "🐄 **คอกสัตว์ของคุณ**\n\n"
    now = time.time()
    for aid, key, ltime in anis:
        ani = ANIMAL_BOOK[key]
        remain = ani['time'] - (now - ltime)
        if remain <= 0:
            res += f"📦 {ani['emoji']} {ani['name']} | เก็บผลผลิต: /collect_{aid}\n"
        else:
            res += f"⏳ {ani['emoji']} {ani['name']} | รอกินหญ้าอีก {int(remain)} วิ\n"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

@bot.message_handler(regexp=r'/collect_(\d+)')
def collect_yield(message):
    aid = message.text.split('_')[1]
    uid = str(message.from_user.id)
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT ani_key FROM animals WHERE ani_id=? AND user_id=?", (aid, uid))
    row = c.fetchone()
    if row:
        ani = ANIMAL_BOOK[row[0]]
        c.execute("UPDATE players SET money = money + ?, exp = exp + ? WHERE user_id = ?", (ani['yield'], ani['exp'], uid))
        c.execute("UPDATE animals SET last_collect = ? WHERE ani_id = ?", (time.time(), aid))
        conn.commit() ; conn.close()
        bot.reply_to(message, f"🥛 เก็บผลผลิตจาก {ani['name']} ได้เงิน {ani['yield']}.- ✨+{ani['exp']} EXP")
    else: bot.reply_to(message, "ไม่พบสัตว์ตัวนี้")

# --- ระบบขโมย (Steal) ---
@bot.message_handler(commands=['steal'])
def steal(message):
    uid = str(message.from_user.id)
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ วิธีขโมย: ให้ Reply ข้อความของเพื่อนแล้วพิมพ์ /steal")
        return
    victim_id = str(message.reply_to_message.from_user.id)
    if uid == victim_id: return
    
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT plot_id, crop_key FROM plots WHERE user_id=?", (victim_id,))
    plots = c.fetchall()
    
    if plots and random.random() < 0.4: # โอกาส 40%
        target = random.choice(plots)
        crop = CROP_BOOK[target[1]]
        loot = int(crop['sell'] * 0.8)
        c.execute("DELETE FROM plots WHERE plot_id=?", (target[0],))
        c.execute("UPDATE players SET money = money + ? WHERE user_id=?", (loot, uid))
        conn.commit()
        bot.reply_to(message, f"🥷 ขโมยสำเร็จ! คุณจิ๊ก {crop['emoji']} {crop['name']} ของเพื่อนไปขาย ได้เงิน {loot}.-")
    else:
        penalty = 150
        c.execute("UPDATE players SET money = MAX(0, money - ?) WHERE user_id=?", (penalty, uid))
        conn.commit()
        bot.reply_to(message, f"👮‍♂️ โดนจับได้! คุณถูกปรับ {penalty}.-")
    conn.close()

# --- ระบบข้อมูลและอันดับ ---
@bot.message_handler(func=lambda m: m.text == '💰 กระเป๋าตังค์')
def wallet(message):
    p = get_player(message.from_user.id)
    bot.reply_to(message, f"👤 {p[1]}\n⭐ เลเวล: {p[4]}\n✨ EXP: {p[3]}/{p[4]*150}\n💰 เงิน: {p[2]:,} บาท")

@bot.message_handler(func=lambda m: m.text == '🏆 อันดับ')
def top_players(message):
    conn = sqlite3.connect('farm_game.db')
    c = conn.cursor()
    c.execute("SELECT name, money FROM players ORDER BY money DESC LIMIT 5")
    rows = c.fetchall()
    res = "🏆 **เกษตรกรที่รวยที่สุด**\n"
    for i, r in enumerate(rows, 1): res += f"{i}. {r[0]} - {r[1]:,} บาท\n"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    print("Farm Bot with Animals & Steal System is Running...")
    bot.polling(none_stop=True)
