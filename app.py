import os
import subprocess
import sys
import streamlit as st

st.set_page_config(page_title="Vet Bot Dashboard", page_icon="🤖")
st.title("🤖 Vet Telegram Bot is Active!")
st.success("البوت يعمل الآن في الخلفية 24/7 بنجاح!")

# ضبط المتغيرات
os.environ["TELEGRAM_BOT_TOKEN"] = "8862865656:AAFg9gTHF-a7_-oOlaFn__rEV8AeVTZmxFw"
os.environ["ADMIN_USER_IDS"] = "5731687491"

@st.cache_resource
def start_bot_process():
    process = subprocess.Popen([sys.executable, "telegram_bot.py"])
    return process

start_bot_process()
