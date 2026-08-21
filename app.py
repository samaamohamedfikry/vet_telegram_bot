import os
import streamlit as st

# تمرير المتغيرات للنظام تلقائياً
os.environ["TELEGRAM_BOT_TOKEN"] = "8862865656:AAFg9gTHF-a7_-oOlaFn__rEV8AeVTZmxFw"
os.environ["ADMIN_USER_IDS"] = "5731687491"

st.title("🤖 Vet Telegram Bot is Active!")
st.write("البوت شغال بنجاح على تليجرام.")

# تشغيل البوت
import telegram_bot
telegram_bot.build_application().run_polling()
