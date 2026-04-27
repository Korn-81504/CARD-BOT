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
    "banana": {"name": "กล้วยหอม", "emoji": "🍌", "time": 300, "buy": 300, "sell": 850, "exp": 80},
    "orange": {"name": "ส้มสายน้ำผึ้ง", "emoji": "🍊", "time": 450, "buy": 400, "sell": 1200, "exp": 100},
    "watermelon": {"name": "แตงโม", "emoji": "🍉", "time": 900, "buy": 800, "sell": 2800, "exp": 200},
    "strawberry": {"name": "สตอเบอรี่", "emoji": "🍓", "time": 1500, "buy": 1500, "sell": 6000, "exp": 400},
    "mango": {"name": "มะม่วงน้ำดอกไม้", "emoji": "🥭", "time": 2400, "buy": 3000, "sell": 14000, "exp": 700},
    "durian": {"name": "ทุเรียนหมอนทอง", "emoji": "👑", "time": 3600, "buy": 5000, "sell": 25000, "exp": 1200},
}

ANIMAL_BOOK = {
    "chicken": {"name": "ไก่", "emoji": "🐔", "buy": 1000, "yield": 250, "time": 300, "exp": 40},
    "cow": {"name": "วัว", "emoji": "🐮", "buy": 5000, "yield": 1500, "time": 900, "exp": 120}
}

# --- 2. ระบบฐานข้อมูล ---
def get_db():
    return sqlite3.connect('farm_game.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (user_id TEXT PRIMARY KEY, name TEXT, money INTEGER, exp INTEGER, level INTEGER, dog_until REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS plots 
                 (plot_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, crop_key TEXT, plant_time REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS animals 
                 (ani_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ani_key TEXT, last_collect REAL)''')
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id=?", (str(user_id),))
    p = c.fetchone()
    conn.close()
    return p

def check_levelup(user_id):
    p = get_player(user_id)
    if not p: return None
    exp, level = p[3], p[4]
    req = level * 150
    if exp >= req:
        new_lvl = level + 1
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE players SET level = ?, exp = exp - ? WHERE user_id = ?", (new_lvl, req, str(user_id)))
        conn.commit()
        conn.close()
        return new_lvl
    return None

def get_weather():
    events = [("☀️ แดดจัด", 1), ("🌧️ ฝนตก (โตเร็ว x2!)", 2), ("☁️ เมฆมาก", 1)]
    return random.choice(events)

# --- 3. คำสั่งหลัก ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name.upper()
    if not get_player(uid):
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO players (user_id, name, money, exp, level) VALUES (?, ?, ?, ?, ?)", (uid, name, 1000, 0, 1))
        conn.commit()
        conn.close()
        msg = f"🚜 ยินดีต้อนรับเกษตรกรใหม่คุณ {name}! รับเงินขวัญถุง 1,000.-"
    else:
        msg = f"สวัสดีครับคุณ {name} กลับมาดูแลฟาร์มกันเถอะ!"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚜 ตรวจฟาร์ม', '🐥 ตรวจคอกสัตว์')
    markup.add('🛒 ร้านค้าเมล็ด', '🏪 ตลาดสัตว์')
    markup.add('🛡️ จ้างหมาเฝ้าฟาร์ม (500.-)', '💰 กระเป๋าตังค์')
    markup.add('🏆 อันดับ')
    bot.send_message(message.chat.id, msg, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '🛡️ จ้างหมาเฝ้าฟาร์ม (500.-)')
def buy_dog(message):
    uid = str(message.from_user.id)
    p = get_player(uid)
    if p and p[2] >= 500:
        protection_time = time.time() + 3600
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE players SET money = money - 500, dog_until = ? WHERE user_id = ?", (protection_time, uid))
        conn.commit() ; conn.close()
        bot.reply_to(message, "🐶 โฮ่ง! จ้างน้องหมามาช่วยเฝ้าฟาร์มแล้ว (กันขโมยได้ 1 ชม.)")
    else:
        bot.reply_to(message, "❌ เงินไม่พอจ้างน้องหมาครับ")

@bot.message_handler(func=lambda m: m.text in ['🛒 ร้านค้าเมล็ด', '🏪 ตลาดสัตว์'])
def shop(message):
    markup = types.InlineKeyboardMarkup()
    if "เมล็ด" in message.text:
        text = "🌱 **ร้านขายเมล็ดพันธุ์ผลไม้**\nเลือกพืชที่ต้องการปลูก:"
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
    if not p: return

    if action[1] == "crop":
        item = CROP_BOOK[action[2]]
        if p[2] >= item['buy']:
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE players SET money = money - ? WHERE user_id = ?", (item['buy'], uid))
            c.execute("INSERT INTO plots (user_id, crop_key, plant_time) VALUES (?, ?, ?)", (uid, action[2], time.time()))
            conn.commit() ; conn.close()
            bot.answer_callback_query(call.id, f"ปลูก {item['name']} แล้ว!")
            bot.edit_message_text(f"🌱 ปลูก {item['emoji']} {item['name']} เรียบร้อย! รดน้ำรอเก็บเกี่ยว", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "เงินไม่พอจ้า!", show_alert=True)
            
    elif action[1] == "ani":
        item = ANIMAL_BOOK[action[2]]
        if p[2] >= item['buy']:
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE players SET money = money - ? WHERE user_id = ?", (item['buy'], uid))
            c.execute("INSERT INTO animals (user_id, ani_key, last_collect) VALUES (?, ?, ?)", (uid, action[2], time.time()))
            conn.commit() ; conn.close()
            bot.answer_callback_query(call.id, f"ซื้อ {item['name']} แล้ว!")
            bot.edit_message_text(f"✨ {item['emoji']} เข้าคอกเรียบร้อย! รอเก็บผลผลิตนะ", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "เงินไม่พอซื้อสัตว์!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == '🚜 ตรวจฟาร์ม')
def view_farm(message):
    uid = str(message.from_user.id)
    weather_name, speed = get_weather()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT plot_id, crop_key, plant_time FROM plots WHERE user_id=?", (uid,))
    plots = c.fetchall()
    conn.close()

    if not plots:
        bot.send_message(message.chat.id, "🏜️ ฟาร์มว่างเปล่า ไปหาซื้อเมล็ดมาปลูกกันเถอะ")
        return

    res = f"🌤 สภาพอากาศ: **{weather_name}**\n👨‍🌾 **ฟาร์มของคุณ**\n\n"
    now = time.time()
    for pid, key, ptime in plots:
        crop = CROP_BOOK[key]
        elapsed = (now - ptime) * speed
        percent = int((elapsed / crop['time']) * 100)
        
        if percent >= 100:
            res += f"✅ {crop['emoji']} {crop['name']} | **สุกแล้ว!** /harvest_{pid}\n"
        else:
            bar_count = min(percent // 10, 10)
            bar = "▓" * bar_count + "░" * (10 - bar_count)
            res += f"⏳ {crop['emoji']} {crop['name']} | {bar} {percent}%\n"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

# --- จุดแก้ไขสำคัญ: แก้ไขคำสั่งเก็บเกี่ยว ---
@bot.message_handler(regexp=r'^/harvest_(\d+)')
def harvest(message):
    try:
        # ดึงเลข ID จากคำสั่ง /harvest_123
        pid = int(message.text.split('_')[1].split('@')[0])
    except:
        return

    uid = str(message.from_user.id)
    conn = get_db()
    c = conn.cursor()
    
    # ตรวจสอบว่ามีพืชชิ้นนี้อยู่จริงและเป็นของคนคนนี้
    c.execute("SELECT crop_key FROM plots WHERE plot_id=? AND user_id=?", (pid, uid))
    row = c.fetchone()
    
    if row:
        crop_key = row[0]
        crop = CROP_BOOK[crop_key]
        
        # 1. ลบออกจากแปลงทันที
        c.execute("DELETE FROM plots WHERE plot_id=?", (pid,))
        # 2. เพิ่มเงินและค่าประสบการณ์
        c.execute("UPDATE players SET money = money + ?, exp = exp + ? WHERE user_id = ?", (crop['sell'], crop['exp'], uid))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"💰 เก็บเกี่ยว {crop['emoji']} {crop['name']} ขายได้ {crop['sell']:,}.- ✨+{crop['exp']} EXP")
        
        # เช็คเลเวลอัป
        new_lvl = check_levelup(uid)
        if new_lvl: 
            bot.send_message(message.chat.id, f"🎊 LEVEL UP! ตอนนี้เลเวล {new_lvl} แล้ว!")
    else:
        conn.close()
        bot.reply_to(message, "❌ ไม่พบพืชชิ้นนี้ (อาจถูกเก็บไปแล้ว หรือถูกขโมย)")

@bot.message_handler(func=lambda m: m.text == '🐥 ตรวจคอกสัตว์')
def view_barn(message):
    uid = str(message.from_user.id)
    conn = get_db()
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

# --- จุดแก้ไขสำคัญ: แก้ไขคำสั่งเก็บผลผลิตสัตว์ ---
@bot.message_handler(regexp=r'^/collect_(\d+)')
def collect_yield(message):
    try:
        aid = int(message.text.split('_')[1].split('@')[0])
    except:
        return
        
    uid = str(message.from_user.id)
    conn = get_db()
    c = conn.cursor()
    
    # ตรวจเช็คว่าสัตว์มีตัวตนอยู่จริง
    c.execute("SELECT ani_key FROM animals WHERE ani_id=? AND user_id=?", (aid, uid))
    row = c.fetchone()
    
    if row:
        ani = ANIMAL_BOOK[row[0]]
        # เพิ่มเงินและ EXP
        c.execute("UPDATE players SET money = money + ?, exp = exp + ? WHERE user_id = ?", (ani['yield'], ani['exp'], uid))
        # อัปเดตเวลาเก็บล่าสุด
        c.execute("UPDATE animals SET last_collect = ? WHERE ani_id = ?", (time.time(), aid))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🥛 เก็บผลผลิตจาก {ani['emoji']} {ani['name']} ได้เงิน {ani['yield']:,}.- ✨+{ani['exp']} EXP")
    else: 
        conn.close()
        bot.reply_to(message, "ไม่พบสัตว์ตัวนี้")

@bot.message_handler(commands=['steal'])
def steal(message):
    uid = str(message.from_user.id)
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ วิธีขโมย: ให้ Reply ข้อความเพื่อนแล้วพิมพ์ /steal")
        return
    victim_id = str(message.reply_to_message.from_user.id)
    if uid == victim_id: return
    
    v_data = get_player(victim_id)
    if v_data and v_data[5] > time.time():
        bot.reply_to(message, "🚫 ขโมยไม่สำเร็จ! บ้านนี้มีหมาดุมาก คุณเผ่นหนีเกือบไม่ทัน")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT plot_id, crop_key, plant_time FROM plots WHERE user_id=?", (victim_id,))
    plots = c.fetchall()
    
    ready = [p for p in plots if (time.time() - p[2]) >= CROP_BOOK[p[1]]['time']]
    
    if ready and random.random() < 0.4:
        target = random.choice(ready)
        crop = CROP_BOOK[target[1]]
        loot = int(crop['sell'] * 0.7)
        c.execute("DELETE FROM plots WHERE plot_id=?", (target[0],))
        c.execute("UPDATE players SET money = money + ? WHERE user_id=?", (loot, uid))
        conn.commit()
        bot.reply_to(message, f"🥷 ขโมยสำเร็จ! คุณจิ๊ก {crop['emoji']} {crop['name']} ของเพื่อนไปขาย ได้เงิน {loot}.-")
    else:
        penalty = 200
        c.execute("UPDATE players SET money = MAX(0, money - ?) WHERE user_id=?", (penalty, uid))
        conn.commit()
        bot.reply_to(message, f"👮‍♂️ โดนจับได้! คุณถูกปรับ {penalty}.-")
    conn.close()

@bot.message_handler(func=lambda m: m.text == '💰 กระเป๋าตังค์')
def wallet(message):
    p = get_player(message.from_user.id)
    if p:
        bot.reply_to(message, f"👤 {p[1]}\n⭐ เลเวล: {p[4]}\n✨ EXP: {p[3]}/{p[4]*150}\n💰 เงิน: {p[2]:,} บาท")

@bot.message_handler(func=lambda m: m.text == '🏆 อันดับ')
def top_players(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, money FROM players ORDER BY money DESC LIMIT 5")
    rows = c.fetchall()
    res = "🏆 **เกษตรกรที่รวยที่สุด**\n"
    for i, r in enumerate(rows, 1): res += f"{i}. {r[0]} - {r[1]:,} บาท\n"
    bot.send_message(message.chat.id, res, parse_mode="Markdown")
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Bot is ready! (สำเร็จรูป: แก้ไขระบบเก็บเกี่ยวเรียบร้อย)")
    bot.polling(none_stop=True)
