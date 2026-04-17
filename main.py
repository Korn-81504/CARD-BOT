import os
import telebot
from telebot import types
from datetime import datetime, timedelta, timezone

# --- ข้อมูลสำคัญ ---
API_TOKEN = os.environ.get('API_TOKEN', '8618360067:AAHA7FxHpnXXtTqF-dwWoD25iMWQZ6G8Jr0')

# กำหนดทีมและอิโมจิ
TEAMS = {
    "DEPOSIT": "💰 DEPOSIT",
    "WITHDRAW": "🤖 WITHDRAW AUTO",
    "MANUAL": "👤 WITHDRAW MANUAL",
    "ENQUIRY": "💬 ENQUIRY"
}

# ฐานข้อมูลชั่วคราว (แนะนำให้ใช้ไฟล์ JSON หรือ Database ในอนาคตถ้ากลัวข้อมูลหายเมื่อบอทดับ)
TEMP_DB = {}

def get_thai_now():
    return datetime.now(timezone(timedelta(hours=7)))

bot = telebot.TeleBot(API_TOKEN)

# --- HANDLERS ---

@bot.message_handler(commands=['start', 'out'])
def start(message):
    u_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # สร้างปุ่มสำหรับแต่ละทีม
    for key, display_name in TEAMS.items():
        btn = types.InlineKeyboardButton(display_name, callback_data=f"out_{key}_{u_id}")
        markup.add(btn)
        
    btn_cancel = types.InlineKeyboardButton("❌ ปิดเมนู", callback_data=f"c_{u_id}")
    markup.add(btn_cancel)

    bot.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text=f"🕒 **ระบบบันทึกเวลาทีมงาน**\nกรุณาเลือกทีมของคุณเพื่อเริ่มจับเวลา:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    data = call.data.split('_')
    cmd = data[0]

    # --- 1. ปิดเมนู ---
    if cmd == 'c':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    # --- 2. แจ้งออก (เริ่มจับเวลา) ---
    if cmd == 'out':
        team_key, u_id = data[1], data[2]
        u_name = call.from_user.first_name # ดึงชื่อจาก Telegram User
        now = get_thai_now()
        mid = str(call.message.message_id)
        
        # เก็บข้อมูลลง DB
        TEMP_DB[mid] = {
            "time": now.isoformat(),
            "team": TEAMS[team_key],
            "user": u_name,
            "uid": int(u_id)
        }

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"✨ กลับเข้างาน (กดโดย {u_name})", callback_data=f"back_{mid}_{u_id}"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(f"📍 **แจ้งเตือนการออกข้างนอก**\n"
                  f"👥 ทีม: **{TEAMS[team_key]}**\n"
                  f"👤 ผู้แจ้ง: **{u_name}**\n"
                  f"🕒 เวลาเริ่ม: `{now.strftime('%H:%M:%S')}`"),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # --- 3. แจ้งกลับ (หยุดจับเวลา) ---
    if cmd == 'back':
        msg_id, out_uid = data[1], int(data[2])
        
        # เช็คว่าคนกดกลับคือคนเดียวกับคนกดออกไหม
        if call.from_user.id != out_uid:
            bot.answer_callback_query(call.id, "⚠️ เฉพาะคนที่แจ้งออกเท่านั้นที่กดกลับได้!", show_alert=True)
            return

        now = get_thai_now()
        if msg_id in TEMP_DB:
            info = TEMP_DB[msg_id]
            start_t = datetime.fromisoformat(info["time"])
            diff = now - start_t
            
            # คำนวณเวลา
            h, rem = divmod(int(diff.total_seconds()), 3600)
            m, s = divmod(rem, 60)

            res = (f"✅ **กลับเข้างานเรียบร้อย**\n"
                   f"👥 ทีม: **{info['team']}**\n"
                   f"👤 ผู้แจ้ง: **{info['user']}**\n"
                   f"🕒 เริ่มเมื่อ: `{start_t.strftime('%H:%M:%S')}`\n"
                   f"✨ กลับเมื่อ: `{now.strftime('%H:%M:%S')}`\n"
                   f"⌛️ ใช้เวลาไป: **{h} ชม. {m} นาที {s} วินาที**")

            del TEMP_DB[msg_id]
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=int(msg_id),
                text=res,
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "❌ ไม่พบข้อมูล หรือมีการกดกลับไปแล้ว")

if __name__ == "__main__":
    print("TEAM TRACKING BOT IS RUNNING...")
    bot.infinity_polling()
