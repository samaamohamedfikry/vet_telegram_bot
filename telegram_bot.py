"""
Telegram study-materials administration system - Ultra Fast & Feature-Complete.
Includes: Inline Buttons, Favorites, Recent Uploads, Cloning, Title Editing, and Menu Button.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
ADMIN_IDS_ENV_VAR = "ADMIN_USER_IDS"
DB_ENV_VAR = "BOT_DB_PATH"

LANG_AR = "ar"
LANG_EN = "en"

CANCEL = "إلغاء"
CONFIRM = "تأكيد"
SKIP = "تخطي"
DONE_UPLOAD = "✅ تم إنهاء الرفع"

EDIT_TITLE_ONLY = "✏️ تعديل الاسم فقط"
EDIT_TITLE_AND_FILES = "🔄 تعديل الاسم والملفات"

STRINGS = {
    LANG_AR: {
        "main_menu": "القائمة الرئيسية",
        "back": "رجوع",
        "admin_menu": "لوحة الإدارة",
        "cancel": "إلغاء",
        "confirm": "تأكيد",
        "skip": "تخطي",
        "search_btn": "🔍 بحث سريع",
        "fav_btn": "⭐ المفضلة",
        "recent_btn": "🆕 أحدث الإضافات",
        "lang_btn": "🌐 English",
        "choose_lang": "اختر اللغة / Choose language:",
        "lang_changed": "تم تغيير اللغة إلى العربية بنجاح.",
        "search_prompt": "🔎 أرسل اسم المادة أو المحاضرة التي تبحث عنها:",
        "search_results": "🔍 نتائج البحث عن: {query}",
        "no_search_results": "عفواً، لم أجد نتائج مطابقة لبحثك.",
        "select_from_menu": "اختر من القائمة:",
        "admin_location": "لوحة الإدارة\nالموقع الحالي: {loc}\n\nاختر إجراءً:",
        "no_permission": "ليس لديك صلاحية للوصول إلى لوحة الإدارة.",
        "canceled": "تم الإلغاء.",
    },
    LANG_EN: {
        "main_menu": "Main Menu",
        "back": "Back",
        "admin_menu": "Admin Panel",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "skip": "Skip",
        "search_btn": "🔍 Search",
        "fav_btn": "⭐ Favorites",
        "recent_btn": "🆕 Recent Uploads",
        "lang_btn": "🌐 عربي",
        "choose_lang": "Choose language / اختر اللغة:",
        "lang_changed": "Language changed to English successfully.",
        "search_prompt": "🔎 Send the name of the material or lecture to search for:",
        "search_results": "🔍 Search results for: {query}",
        "no_search_results": "Sorry, no results matched your search.",
        "select_from_menu": "Select from menu:",
        "admin_location": "Admin Panel\nCurrent Location: {loc}\n\nChoose an action:",
        "no_permission": "You do not have admin permissions.",
        "canceled": "Canceled.",
    }
}

ADD_BUTTON = "إضافة زر"
EDIT_CURRENT_BUTTON = "تعديل هذا الزر"
DELETE_CURRENT_BUTTON = "حذف هذا الزر"
CLONE_NODE_BUTTON = "📋 نسخ هيكل هذا الزر"
ADD_CONTENT = "إضافة محتوى"
EDIT_CONTENT = "تعديل محتوى"
DELETE_CONTENT = "حذف محتوى"
MANAGE_ADMINS = "إدارة المشرفين"
WELCOME_SETTINGS = "رسالة الترحيب"
ARRANGE_BUTTONS = "ترتيب الأزرار"
BROADCAST_BUTTON = "📢 إذاعة للدفعة"
STATS_BUTTON = "📊 إحصائيات البوت"
USERS_LIST_BUTTON = "👥 قائمة المشتركين"
ACTIVITY_LOG_BUTTON = "📈 سجل النشاط والضغطات"

UP = "أعلى ⬆️"
DOWN = "أسفل ⬇️"
LEFT = "يسار ⬅️"
RIGHT = "يمين ➡️"
TOGGLE_LAYOUT = "تبديل عرض الزر"
BACK_TO_MENU = "العودة للقائمة"
ADD_ADMIN = "إضافة مشرف"
REMOVE_ADMIN = "حذف مشرف"
LIST_ADMINS = "قائمة المشرفين"
BACK_TO_ADMIN = "العودة للوحة الإدارة"

DEFAULT_WELCOME = (
    "مساء الجمال والكريستال ❤️\n"
    "يا اهلا بالدكتور {first_name} 🥼\n\n"
    "اختر من القائمة للوصول إلى المواد الدراسية:"
)


def database_path() -> Path:
    path = Path(os.getenv(DB_ENV_VAR, "bot.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


DB = sqlite3.connect(database_path(), check_same_thread=False, timeout=15.0)
DB.row_factory = sqlite3.Row
DB.execute("PRAGMA foreign_keys = ON")
DB.execute("PRAGMA journal_mode = WAL")


def db_execute(query: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
    with DB:
        return DB.execute(query, parameters)


def db_one(query: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return db_execute(query, parameters).fetchone()


def db_all(query: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return db_execute(query, parameters).fetchall()


def get_user_lang(user_id: int) -> str:
    row = db_one("SELECT language FROM users WHERE user_id = ?", (user_id,))
    if row and row["language"]:
        return row["language"]
    return LANG_AR


def set_user_lang(user_id: int, lang: str) -> None:
    db_execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))


def tr(context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs: Any) -> str:
    lang = context.user_data.get("lang", LANG_AR)
    text = STRINGS.get(lang, STRINGS[LANG_AR]).get(key, "")
    return text.format(**kwargs) if kwargs else text


def menu_items(node_id: int | None) -> list[sqlite3.Row]:
    return db_all(
        """
        SELECT id, title, sort_order, layout_mode, 'node' AS item_type
        FROM menu_nodes
        WHERE parent_id IS ?
        UNION ALL
        SELECT id, title, sort_order, layout_mode, 'content' AS item_type
        FROM contents
        WHERE node_id IS ?
        ORDER BY sort_order, item_type, id
        """,
        (node_id, node_id),
    )


def track_user(user_id: int, username: str | None, first_name: str | None) -> None:
    db_execute(
        """
        INSERT INTO users (user_id, username, language)
        VALUES (?, ?, 'ar')
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            last_seen = CURRENT_TIMESTAMP
        """,
        (user_id, username or ""),
    )
    if first_name is not None:
        db_execute("UPDATE users SET first_name = ? WHERE user_id = ?", (first_name, user_id))


def log_user_activity(user_id: int, action_type: str, item_title: str) -> None:
    db_execute(
        """
        INSERT INTO user_activity (user_id, action_type, item_title)
        VALUES (?, ?, ?)
        """,
        (user_id, action_type, item_title),
    )


def is_favorite(user_id: int, content_id: int) -> bool:
    row = db_one("SELECT id FROM favorites WHERE user_id = ? AND content_id = ?", (user_id, content_id))
    return row is not None


def toggle_favorite(user_id: int, content_id: int) -> bool:
    if is_favorite(user_id, content_id):
        db_execute("DELETE FROM favorites WHERE user_id = ? AND content_id = ?", (user_id, content_id))
        return False
    else:
        db_execute("INSERT INTO favorites (user_id, content_id) VALUES (?, ?)", (user_id, content_id))
        return True


def clone_node_structure(source_node_id: int, target_parent_id: int | None, new_title: str) -> int:
    with DB:
        cursor = DB.execute(
            "INSERT INTO menu_nodes (parent_id, title, sort_order, layout_mode) VALUES (?, ?, 0, 'half')",
            (target_parent_id, new_title),
        )
        new_node_id = cursor.lastrowid

    def copy_children(src_id: int, tgt_id: int):
        children = db_all("SELECT * FROM menu_nodes WHERE parent_id = ?", (src_id,))
        for child in children:
            with DB:
                c = DB.execute(
                    "INSERT INTO menu_nodes (parent_id, title, sort_order, layout_mode) VALUES (?, ?, ?, ?)",
                    (tgt_id, child["title"], child["sort_order"], child["layout_mode"]),
                )
                child_new_id = c.lastrowid
            copy_children(child["id"], child_new_id)

    copy_children(source_node_id, new_node_id)
    return new_node_id


def initialize_database() -> None:
    with DB:
        DB.executescript(
            """
            CREATE TABLE IF NOT EXISTS menu_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER REFERENCES menu_nodes(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                layout_mode TEXT NOT NULL DEFAULT 'half',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS menu_nodes_parent_idx
                ON menu_nodes(parent_id, sort_order, id);

            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER REFERENCES menu_nodes(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                layout_mode TEXT NOT NULL DEFAULT 'half',
                content_type TEXT NOT NULL,
                file_id TEXT,
                text_value TEXT,
                created_by INTEGER NOT NULL,
                source_chat_id INTEGER,
                source_message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS contents_node_idx
                ON contents(node_id, id);

            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (user_id IS NOT NULL OR username IS NOT NULL)
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT NOT NULL DEFAULT 'ar',
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                item_title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content_id INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, content_id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        user_cols = {row["name"] for row in DB.execute("PRAGMA table_info(users)")}
        if "language" not in user_cols:
            DB.execute("ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'ar'")

        DB.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            ("welcome_message", DEFAULT_WELCOME),
        )


def bootstrap_admins() -> None:
    raw_ids = os.getenv(ADMIN_IDS_ENV_VAR, "")
    configured_ids = [value.strip() for value in raw_ids.split(",") if value.strip()]
    existing = db_one("SELECT id FROM admins LIMIT 1")

    if not existing and not configured_ids:
        raise RuntimeError(
            f"Set {ADMIN_IDS_ENV_VAR} to at least one Telegram user ID before the first run."
        )

    for raw_id in configured_ids:
        try:
            user_id = int(raw_id)
        except ValueError as error:
            raise RuntimeError(
                f"Invalid admin user ID in {ADMIN_IDS_ENV_VAR}: {raw_id}"
            ) from error
        db_execute(
            """
            INSERT INTO admins(user_id, display_name)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, f"User {user_id}"),
        )


def keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def current_path(context: ContextTypes.DEFAULT_TYPE) -> list[int]:
    return context.user_data.setdefault("menu_path", [])


def current_node_id(context: ContextTypes.DEFAULT_TYPE) -> int | None:
    path = current_path(context)
    return path[-1] if path else None


def set_flow(context: ContextTypes.DEFAULT_TYPE, flow_type: str, **values: Any) -> None:
    context.user_data["flow"] = {"type": flow_type, **values}


def get_flow(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any] | None:
    return context.user_data.get("flow")


def clear_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("flow", None)
    context.user_data.pop("selection_map", None)


def normalize_username(value: str) -> str:
    return value.strip().lstrip("@").lower()


def is_super_admin(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    raw_ids = os.getenv(ADMIN_IDS_ENV_VAR, "")
    configured_ids = [value.strip() for value in raw_ids.split(",") if value.strip()]
    return str(user.id) in configured_ids


def is_admin(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False

    if is_super_admin(update):
        return True

    username = (user.username or "").lower()
    row = db_one(
        """
        SELECT id, user_id
        FROM admins
        WHERE user_id = ? OR (username IS NOT NULL AND lower(username) = ?)
        LIMIT 1
        """,
        (user.id, username),
    )
    if not row:
        return False

    if row["user_id"] is None:
        db_execute("UPDATE admins SET user_id = ? WHERE id = ?", (user.id, row["id"]))
    return True


def welcome_message(update: Update) -> str:
    template_row = db_one(
        "SELECT value FROM settings WHERE key = ?", ("welcome_message",)
    )
    template = template_row["value"] if template_row else DEFAULT_WELCOME
    user = update.effective_user
    if user is None:
        return template

    replacements = {
        "{first_name}": user.first_name or "",
        "{last_name}": user.last_name or "",
        "{username}": f"@{user.username}" if user.username else "",
        "{user_id}": str(user.id),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def node_title(node_id: int | None) -> str:
    if node_id is None:
        return "الرئيسية"
    row = db_one("SELECT title FROM menu_nodes WHERE id = ?", (node_id,))
    return row["title"] if row else "الرئيسية"


def display_label(prefix: str, title: str, item_id: int) -> str:
    return title


def add_selection_map(
    context: ContextTypes.DEFAULT_TYPE, labels_to_ids: dict[str, int]
) -> None:
    context.user_data["selection_map"] = labels_to_ids


async def show_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    node_id = current_node_id(context)
    rows: list[list[str]] = []
    menu_selection_map: dict[str, tuple[str, int]] = {}
    half_row: list[str] = []
    for item in menu_items(node_id):
        label = display_label("", item["title"], item["id"])
        menu_selection_map[label] = (item["item_type"], item["id"])
        if item["layout_mode"] == "full":
            if half_row:
                rows.append(half_row)
                half_row = []
            rows.append([label])
        else:
            half_row.append(label)
            if len(half_row) == 2:
                rows.append(half_row)
                half_row = []
    if half_row:
        rows.append(half_row)
    context.user_data["menu_selection_map"] = menu_selection_map

    navigation_row = []
    if node_id is not None:
        navigation_row.extend([tr(context, "back"), tr(context, "main_menu")])
    elif current_path(context):
        navigation_row.append(tr(context, "main_menu"))

    if navigation_row:
        rows.append(navigation_row)

    if node_id is None:
        rows.append([tr(context, "search_btn"), tr(context, "fav_btn")])
        rows.append([tr(context, "recent_btn"), tr(context, "lang_btn")])

    if is_admin(update):
        rows.append([tr(context, "admin_menu")])

    description = node_title(node_id)
    if node_id is None:
        description = tr(context, "main_menu")
    await message.reply_text(
        f"{description}\n\n{tr(context, 'select_from_menu')}",
        reply_markup=keyboard(rows or [[tr(context, "main_menu")]]),
    )


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    message = update.effective_message
    if message is None:
        return

    node_id = current_node_id(context)
    rows = [
        [ADD_BUTTON],
        [EDIT_CURRENT_BUTTON, DELETE_CURRENT_BUTTON],
    ]

    if node_id is not None:
        rows.append([CLONE_NODE_BUTTON])

    rows.extend([
        [ARRANGE_BUTTONS],
        [ADD_CONTENT],
        [EDIT_CONTENT, DELETE_CONTENT],
        [BROADCAST_BUTTON, STATS_BUTTON],
    ])

    if is_super_admin(update):
        rows.append([USERS_LIST_BUTTON, ACTIVITY_LOG_BUTTON])
        rows.append([MANAGE_ADMINS, WELCOME_SETTINGS])

    rows.append([BACK_TO_MENU])

    location = node_title(node_id)
    await message.reply_text(
        tr(context, "admin_location", loc=location),
        reply_markup=keyboard(rows),
    )


async def show_arrange_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if message is None:
        return
    items = menu_items(current_node_id(context))
    if not items:
        await message.reply_text(
            "لا توجد أزرار لترتيبها في هذا المكان.",
            reply_markup=keyboard([[BACK_TO_ADMIN]]),
        )
        return
    labels: dict[str, tuple[str, int]] = {}
    for item in items:
        label = display_label("", item["title"], item["id"])
        labels[label] = (item["item_type"], item["id"])
    context.user_data["selection_map"] = labels
    set_flow(context, "arrange_select")
    await message.reply_text(
        "اختر الزر الذي تريد ترتيبَه:",
        reply_markup=keyboard([[label] for label in labels] + [[tr(context, "cancel")]]),
    )


async def show_arrange_controls(
    update: Update, context: ContextTypes.DEFAULT_TYPE, item_type: str, item_id: int
) -> None:
    message = update.effective_message
    if message is None:
        return
    table = "menu_nodes" if item_type == "node" else "contents"
    item = db_one(
        f"SELECT title, layout_mode FROM {table} WHERE id = ?", (item_id,)
    )
    if item is None:
        clear_flow(context)
        await message.reply_text("هذا الزر لم يعد موجوداً.")
        await show_admin_panel(update, context)
        return
    layout = "عرض كامل" if item["layout_mode"] == "full" else "نصف عرض"
    await message.reply_text(
        f"الزر: {item['title']}\nالتخطيط الحالي: {layout}\n\n"
        "اختر اتجاه الحركة أو غيّر عرض الزر:",
        reply_markup=keyboard(
            [[UP, DOWN], [LEFT, RIGHT], [TOGGLE_LAYOUT], [BACK_TO_ADMIN]]
        ),
    )


def move_menu_item(
    node_id: int | None, item_type: str, item_id: int, offset: int
) -> bool:
    items = menu_items(node_id)
    current_index = next(
        (
            index
            for index, item in enumerate(items)
            if item["item_type"] == item_type and item["id"] == item_id
        ),
        None,
    )
    if current_index is None:
        return False
    target_index = current_index + offset
    if target_index < 0 or target_index >= len(items):
        return False
    current = items[current_index]
    target = items[target_index]
    current_table = "menu_nodes" if item_type == "node" else "contents"
    target_table = "menu_nodes" if target["item_type"] == "node" else "contents"
    with DB:
        DB.execute(
            f"UPDATE {current_table} SET sort_order = ? WHERE id = ?",
            (target["sort_order"], item_id),
        )
        DB.execute(
            f"UPDATE {target_table} SET sort_order = ? WHERE id = ?",
            (current["sort_order"], target["id"]),
        )
    return True


def toggle_menu_item_layout(item_type: str, item_id: int) -> str:
    table = "menu_nodes" if item_type == "node" else "contents"
    item = db_one(f"SELECT layout_mode FROM {table} WHERE id = ?", (item_id,))
    if item is None:
        return "half"
    new_layout = "full" if item["layout_mode"] != "full" else "half"
    db_execute(
        f"UPDATE {table} SET layout_mode = ? WHERE id = ?",
        (new_layout, item_id),
    )
    return new_layout


async def show_admin_management(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(
        "إدارة المشرفين:",
        reply_markup=keyboard(
            [
                [ADD_ADMIN],
                [REMOVE_ADMIN],
                [LIST_ADMINS],
                [BACK_TO_ADMIN],
            ]
        ),
    )


async def show_content_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE, action: str
) -> None:
    message = update.effective_message
    if message is None:
        return
    contents = db_all(
        "SELECT id, title FROM contents WHERE node_id IS ? ORDER BY id",
        (current_node_id(context),),
    )
    if not contents:
        await message.reply_text(
            "لا يوجد محتوى في هذا الزر بعد.",
            reply_markup=keyboard([[BACK_TO_ADMIN]]),
        )
        return

    labels = {
        display_label("📄", row["title"], row["id"]): row["id"] for row in contents
    }
    add_selection_map(context, labels)
    set_flow(context, action)
    await message.reply_text(
        "اختر المحتوى:",
        reply_markup=keyboard([[label] for label in labels] + [[tr(context, "cancel")]]),
    )


async def show_admin_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if message is None:
        return
    
    raw_super_ids = os.getenv(ADMIN_IDS_ENV_VAR, "")
    super_ids = {int(x.strip()) for x in raw_super_ids.split(",") if x.strip().isdigit()}

    admins = db_all(
        "SELECT id, user_id, username, display_name FROM admins ORDER BY id"
    )
    
    labels: dict[str, int] = {}
    for admin in admins:
        if admin["user_id"] in super_ids:
            continue
        identity = (
            f"@{admin['username']}"
            if admin["username"]
            else f"ID {admin['user_id']}"
        )
        label = display_label("👤", identity, admin["id"])
        labels[label] = admin["id"]

    if not labels:
        await message.reply_text("لا يوجد مشرفون إضافيون لحذفهم.")
        await show_admin_management(update, context)
        return

    add_selection_map(context, labels)
    set_flow(context, "remove_admin")
    await message.reply_text(
        "اختر المشرف الذي تريد حذفه:",
        reply_markup=keyboard([[label] for label in labels] + [[tr(context, "cancel")]]),
    )


def content_from_message(message: Any) -> tuple[str, str] | None:
    if message.document:
        return "document", message.document.file_id
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.video:
        return "video", message.video.file_id
    if message.audio:
        return "audio", message.audio.file_id
    if message.text:
        text = message.text.strip()
        if re.match(r"^https?://\S+$", text):
            return "link", text
        return "text", text
    return None


def get_content_inline_markup(user_id: int, content_id: int) -> InlineKeyboardMarkup:
    fav_text = "⭐ إزالة من المفضلة" if is_favorite(user_id, content_id) else "⭐ حفظ في المفضلة"
    inline_k = [
        [
            InlineKeyboardButton(fav_text, callback_data=f"fav_{content_id}"),
            InlineKeyboardButton("⚠️ إبلاغ عن مشكلة", callback_data=f"rep_{content_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_k)


async def deliver_single_item(
    message: Any,
    c_type: str,
    c_val: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        if c_type == "document":
            await message.reply_document(document=c_val, caption=caption, reply_markup=reply_markup)
        elif c_type == "photo":
            await message.reply_photo(photo=c_val, caption=caption, reply_markup=reply_markup)
        elif c_type == "video":
            await message.reply_video(video=c_val, caption=caption, reply_markup=reply_markup)
        elif c_type == "audio":
            await message.reply_audio(audio=c_val, caption=caption, reply_markup=reply_markup)
        elif c_type == "link":
            await message.reply_text(f"{caption}\n\n{c_val}", disable_web_page_preview=False, reply_markup=reply_markup)
        else:
            await message.reply_text(f"{caption}\n\n{c_val}", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error delivering item: {e}")


async def deliver_content(update: Update, content: sqlite3.Row) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    title = content["title"]
    content_type = content["content_type"]
    content_id = content["id"]
    inline_markup = get_content_inline_markup(user.id, content_id)

    if content_type == "multi":
        items = []
        try:
            items = json.loads(content["text_value"] or "[]")
        except Exception:
            pass
        for i, item in enumerate(items):
            c_type = item.get("type", "text")
            c_val = item.get("value", "")
            sub_caption = f"{title}" if i == 0 else f"{title} (مرفق {i+1})"
            is_last = (i == len(items) - 1)
            await deliver_single_item(
                message,
                c_type,
                c_val,
                sub_caption,
                reply_markup=inline_markup if is_last else None,
            )
            await asyncio.sleep(0.04)
    else:
        value = content["file_id"] or content["text_value"] or ""
        await deliver_single_item(message, content_type, value, title, reply_markup=inline_markup)


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    favs = db_all(
        """
        SELECT c.* FROM contents c
        INNER JOIN favorites f ON c.id = f.content_id
        WHERE f.user_id = ?
        ORDER BY f.id DESC
        """,
        (user.id,),
    )
    if not favs:
        await update.effective_message.reply_text("⭐ ليس لديك أي ملفات محفوظة في المفضلة بعد.")
        return

    await update.effective_message.reply_text(f"⭐ قائمة ملفاتك المفضلة ({len(favs)}):")
    for content in favs:
        await deliver_content(update, content)


async def show_recent_uploads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    recent = db_all(
        """
        SELECT * FROM contents
        ORDER BY id DESC
        LIMIT 10
        """
    )
    if not recent:
        await update.effective_message.reply_text("🆕 لم يتم رفع أي محتوى بعد.")
        return

    await update.effective_message.reply_text("🆕 أحدث 10 محاضرات وملفات تم إضافتها:")
    for content in recent:
        await deliver_content(update, content)


async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    results = db_all(
        """
        SELECT * FROM contents
        WHERE title LIKE ?
        LIMIT 10
        """,
        (f"%{query}%",),
    )
    if not results:
        await update.effective_message.reply_text(tr(context, "no_search_results"))
        return

    await update.effective_message.reply_text(tr(context, "search_results", query=query))
    for content in results:
        await deliver_content(update, content)


async def send_broadcast(application: Application, message: Any) -> tuple[int, int]:
    users = db_all("SELECT user_id FROM users")
    success = 0
    fail = 0
    for user_row in users:
        user_id = user_row["user_id"]
        try:
            if message.text:
                await application.bot.send_message(
                    chat_id=user_id, text=f"📢 إشعار هام من الإدارة:\n\n{message.text}"
                )
            elif message.photo:
                await application.bot.send_photo(
                    chat_id=user_id,
                    photo=message.photo[-1].file_id,
                    caption=f"📢 {message.caption or ''}",
                )
            elif message.document:
                await application.bot.send_document(
                    chat_id=user_id,
                    document=message.document.file_id,
                    caption=f"📢 {message.caption or ''}",
                )
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            fail += 1
    return success, fail


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("fav_"):
        content_id = int(data.split("_")[1])
        is_fav = toggle_favorite(user_id, content_id)
        msg = "✅ تم الحفظ في المفضلة!" if is_fav else "❌ تمت الإزالة من المفضلة!"
        await query.answer(msg, show_alert=False)
        try:
            new_markup = get_content_inline_markup(user_id, content_id)
            await query.edit_message_reply_markup(reply_markup=new_markup)
        except Exception:
            pass

    elif data.startswith("rep_"):
        content_id = int(data.split("_")[1])
        content = db_one("SELECT title FROM contents WHERE id = ?", (content_id,))
        title = content["title"] if content else f"ID: {content_id}"
        await query.answer("تم إرسال بلاغك للإدارة بنجاح، شكراً لك!", show_alert=True)

        raw_ids = os.getenv(ADMIN_IDS_ENV_VAR, "")
        admin_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
        user_name = update.effective_user.first_name or f"User {user_id}"
        username = f"@{update.effective_user.username}" if update.effective_user.username else ""
        for a_id in admin_ids:
            try:
                await context.application.bot.send_message(
                    chat_id=a_id,
                    text=f"⚠️ بلاغ عن مشكلة في محتوى:\n\n• المحتوى: {title}\n• أرسل بواسطة: {user_name} ({username})\n• ID: `{user_id}`",
                )
            except Exception:
                pass


async def process_admin_flow(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    flow = get_flow(context)
    message = update.effective_message
    if not flow or message is None:
        return False

    text = message.text.strip() if message.text else ""
    cancel_words = {
        tr(context, "cancel"),
        CANCEL,
        "Cancel",
        "الغاء",
        "إلغاء",
        "القائمة الرئيسية",
        "Main Menu",
        "/cancel",
    }
    
    if text in cancel_words:
        clear_flow(context)
        context.user_data["menu_path"] = []
        await message.reply_text(tr(context, "canceled"))
        await show_node(update, context)
        return True

    flow_type = flow["type"]

    if flow_type == "search":
        if not text:
            await message.reply_text("يرجى إرسال كلمة البحث كنص.")
            return True
        clear_flow(context)
        if update.effective_user:
            log_user_activity(update.effective_user.id, "🔍 بحث", text[:50])
        await perform_search(update, context, text)
        await show_node(update, context)
        return True

    if not is_admin(update):
        return False

    if flow_type == "broadcast":
        clear_flow(context)
        status_msg = await message.reply_text("⏳ جاري إرسال الإذاعة لجميع الطلاب...")
        succ, fail = await send_broadcast(context.application, message)
        await status_msg.edit_text(
            f"✅ تم إرسال الإذاعة بنجاح!\n\n• وصل إلى: {succ} طالب\n• فشل: {fail}"
        )
        await show_admin_panel(update, context)
        return True

    if flow_type == "clone_node_name":
        if not text:
            await message.reply_text("أرسل اسم النسخة الجديدة كنص.")
            return True
        src_id = flow["source_id"]
        parent_id = flow["parent_id"]
        clone_node_structure(src_id, parent_id, text[:64])
        clear_flow(context)
        await message.reply_text(f"✅ تم نسخ هيكل المادة/الزر بالكامل بنجاح باسم «{text}»!")
        await show_admin_panel(update, context)
        return True

    if flow_type == "arrange_select":
        selection = context.user_data.get("selection_map", {}).get(text)
        if not selection:
            await message.reply_text("اختر زرّاً من لوحة المفاتيح أو اضغط إلغاء.")
            return True
        item_type, item_id = selection
        set_flow(
            context,
            "arrange_controls",
            item_type=item_type,
            item_id=item_id,
        )
        await show_arrange_controls(update, context, item_type, item_id)
        return True

    if flow_type == "arrange_controls":
        item_type = flow["item_type"]
        item_id = flow["item_id"]
        if text in {UP, DOWN, LEFT, RIGHT}:
            offset = -1 if text in {UP, LEFT} else 1
            moved = move_menu_item(
                current_node_id(context), item_type, item_id, offset
            )
            await message.reply_text(
                "تم تحريك الزر." if moved else "لا يمكن تحريك الزر في هذا الاتجاه."
            )
            await show_arrange_controls(update, context, item_type, item_id)
            return True
        if text == TOGGLE_LAYOUT:
            layout = toggle_menu_item_layout(item_type, item_id)
            await message.reply_text(
                "تم ضبط الزر بعرض كامل."
                if layout == "full"
                else "تم ضبط الزر بعرض نصف الصف."
            )
            await show_arrange_controls(update, context, item_type, item_id)
            return True
        if text == BACK_TO_ADMIN:
            clear_flow(context)
            await show_admin_panel(update, context)
            return True
        await message.reply_text("اختر إجراءً من لوحة الترتيب.")
        return True

    if flow_type == "add_button":
        if not text:
            await message.reply_text("أرسل اسم الزر كنص.")
            return True
        parent_id = current_node_id(context)
        items = menu_items(parent_id)
        next_order = max((item["sort_order"] for item in items), default=-1) + 1
        db_execute(
            """
            INSERT INTO menu_nodes(parent_id, title, sort_order, layout_mode)
            VALUES (?, ?, ?, 'half')
            """,
            (parent_id, text[:64], next_order),
        )
        clear_flow(context)
        await message.reply_text("تمت إضافة الزر.")
        await show_admin_panel(update, context)
        return True

    if flow_type == "edit_node_title":
        if not text:
            await message.reply_text("أرسل الاسم الجديد.")
            return True
        db_execute(
            "UPDATE menu_nodes SET title = ? WHERE id = ?",
            (text[:64], flow["node_id"]),
        )
        clear_flow(context)
        await message.reply_text("تم تعديل الزر.")
        await show_admin_panel(update, context)
        return True

    if flow_type == "confirm_delete_node":
        if text not in {CONFIRM, "Confirm", "تأكيد"}:
            await message.reply_text("اكتب تأكيد للحذف أو إلغاء.")
            return True
        node_id = flow["node_id"]
        db_execute("DELETE FROM menu_nodes WHERE id = ?", (node_id,))
        path = current_path(context)
        if path and path[-1] == node_id:
            path.pop()
        clear_flow(context)
        await message.reply_text("تم حذف الزر وكل ما بداخله.")
        await show_node(update, context)
        return True

    if flow_type == "add_content_title":
        if not text:
            await message.reply_text("أرسل عنوان المحتوى.")
            return True
        set_flow(
            context,
            "add_content_value",
            title=text[:100],
            node_id=current_node_id(context),
            items=[],
        )
        await message.reply_text(
            f"تم تحديد الزر: {text}\n\nأرسل الملفات أو الروابط الآن (سيتم جمعهم معاً في هذا الزر).\nعند الانتهاء اضغط على «✅ تم إنهاء الرفع».",
            reply_markup=keyboard([[DONE_UPLOAD], [tr(context, "cancel")]]),
        )
        return True

    if flow_type == "add_content_value":
        if text == DONE_UPLOAD:
            items_list = flow.get("items", [])
            if not items_list:
                await message.reply_text("لم يتم إرسال أي ملفات أو روابط.")
                clear_flow(context)
                await show_admin_panel(update, context)
                return True

            user = update.effective_user
            node_id = flow["node_id"]

            if len(items_list) == 1:
                content_type = items_list[0]["type"]
                val = items_list[0]["value"]
                db_execute(
                    """
                    INSERT INTO contents(
                        node_id, title, sort_order, layout_mode, content_type,
                        file_id, text_value,
                        created_by, source_chat_id, source_message_id
                    ) VALUES (?, ?, ?, 'half', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node_id,
                        flow["title"],
                        max((item["sort_order"] for item in menu_items(node_id)), default=-1) + 1,
                        content_type,
                        val if content_type in {"document", "photo", "video", "audio"} else None,
                        val if content_type in {"text", "link"} else None,
                        user.id if user else 0,
                        message.chat_id,
                        message.message_id,
                    ),
                )
            else:
                db_execute(
                    """
                    INSERT INTO contents(
                        node_id, title, sort_order, layout_mode, content_type,
                        file_id, text_value,
                        created_by, source_chat_id, source_message_id
                    ) VALUES (?, ?, ?, 'half', 'multi', NULL, ?, ?, ?, ?)
                    """,
                    (
                        node_id,
                        flow["title"],
                        max((item["sort_order"] for item in menu_items(node_id)), default=-1) + 1,
                        json.dumps(items_list, ensure_ascii=False),
                        user.id if user else 0,
                        message.chat_id,
                        message.message_id,
                    ),
                )

            clear_flow(context)
            await message.reply_text(f"✅ تم حفظ زر «{flow['title']}» ويحتوي على {len(items_list)} مرفق بنجاح!")
            await show_admin_panel(update, context)
            return True

        content = content_from_message(message)
        if content is None:
            await message.reply_text("أرسل ملفاً أو رابطاً، أو اضغط ✅ تم إنهاء الرفع.")
            return True

        content_type, value = content
        items_list = flow.setdefault("items", [])
        items_list.append({"type": content_type, "value": value})
        await message.reply_text(
            f"📥 تم استلام المرفق ({len(items_list)}).\nأرسل ملفاً آخر أو اضغط «✅ تم إنهاء الرفع»:",
            reply_markup=keyboard([[DONE_UPLOAD], [tr(context, "cancel")]]),
        )
        return True

    if flow_type in {"edit_content", "delete_content"}:
        selection_map = context.user_data.get("selection_map", {})
        content_id = selection_map.get(text)
        if not content_id:
            await message.reply_text("اختر عنصراً من لوحة المفاتيح أو اضغط إلغاء.")
            return True
        if flow_type == "delete_content":
            set_flow(context, "confirm_delete_content", content_id=content_id)
            await message.reply_text(
                "اكتب تأكيد لحذف هذا المحتوى أو إلغاء.",
                reply_markup=keyboard([[CONFIRM], [tr(context, "cancel")]]),
            )
        else:
            set_flow(context, "choose_edit_mode", content_id=content_id)
            await message.reply_text(
                "اختر نوع التعديل الذي تريده:",
                reply_markup=keyboard([[EDIT_TITLE_ONLY], [EDIT_TITLE_AND_FILES], [tr(context, "cancel")]]),
            )
        return True

    if flow_type == "choose_edit_mode":
        content_id = flow["content_id"]
        if text == EDIT_TITLE_ONLY:
            set_flow(context, "edit_content_title_only", content_id=content_id)
            await message.reply_text("أرسل الاسم الجديد للمحتوى:", reply_markup=keyboard([[tr(context, "cancel")]]))
            return True
        elif text == EDIT_TITLE_AND_FILES:
            set_flow(context, "edit_content_title", content_id=content_id)
            await message.reply_text(
                "أرسل العنوان الجديد، أو اكتب تخطي للاحتفاظ بالعنوان الحالي.",
                reply_markup=keyboard([[SKIP], [tr(context, "cancel")]]),
            )
            return True
        else:
            await message.reply_text("يرجى الاختيار من القائمة أدناه.")
            return True

    if flow_type == "edit_content_title_only":
        if not text:
            await message.reply_text("أرسل الاسم الجديد كنص.")
            return True
        db_execute(
            "UPDATE contents SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (text[:100], flow["content_id"]),
        )
        clear_flow(context)
        await message.reply_text("✅ تم تعديل اسم المحتوى بنجاح!")
        await show_admin_panel(update, context)
        return True

    if flow_type == "confirm_delete_content":
        if text not in {CONFIRM, "Confirm", "تأكيد"}:
            await message.reply_text("اكتب تأكيد للحذف أو إلغاء.")
            return True
        db_execute("DELETE FROM contents WHERE id = ?", (flow["content_id"],))
        clear_flow(context)
        await message.reply_text("تم حذف المحتوى.")
        await show_admin_panel(update, context)
        return True

    if flow_type == "edit_content_title":
        if text != SKIP and not text:
            await message.reply_text("أرسل عنواناً أو اكتب تخطي.")
            return True
        if text != SKIP:
            db_execute(
                "UPDATE contents SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (text[:100], flow["content_id"]),
            )
        set_flow(context, "edit_content_value", content_id=flow["content_id"], items=[])
        await message.reply_text(
            "أرسل المحتوى/الملفات الجديدة ثم اضغط «✅ تم إنهاء الرفع»، أو اكتب تخطي للاحتفاظ بالمحتوى الحالي.",
            reply_markup=keyboard([[DONE_UPLOAD], [SKIP], [tr(context, "cancel")]]),
        )
        return True

    if flow_type == "edit_content_value":
        if text == SKIP:
            clear_flow(context)
            await message.reply_text("تم تعديل المحتوى.")
            await show_admin_panel(update, context)
            return True

        if text == DONE_UPLOAD:
            items_list = flow.get("items", [])
            if not items_list:
                clear_flow(context)
                await message.reply_text("لم يتم تغيير المرفقات.")
                await show_admin_panel(update, context)
                return True

            if len(items_list) == 1:
                content_type = items_list[0]["type"]
                val = items_list[0]["value"]
                db_execute(
                    """
                    UPDATE contents
                    SET content_type = ?, file_id = ?, text_value = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        content_type,
                        val if content_type in {"document", "photo", "video", "audio"} else None,
                        val if content_type in {"text", "link"} else None,
                        flow["content_id"],
                    ),
                )
            else:
                db_execute(
                    """
                    UPDATE contents
                    SET content_type = 'multi', file_id = NULL, text_value = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        json.dumps(items_list, ensure_ascii=False),
                        flow["content_id"],
                    ),
                )
            clear_flow(context)
            await message.reply_text("تم تحديث المحتوى والمرفقات بنجاح.")
            await show_admin_panel(update, context)
            return True

        content = content_from_message(message)
        if content is None:
            await message.reply_text("أرسل ملفاً أو رابطاً أو نصاً، أو اضغط ✅ تم إنهاء الرفع.")
            return True

        content_type, value = content
        items_list = flow.setdefault("items", [])
        items_list.append({"type": content_type, "value": value})
        await message.reply_text(
            f"📥 تم استلام المرفق ({len(items_list)}).\nأرسل مرفقاً آخر أو اضغط «✅ تم إنهاء الرفع»:",
            reply_markup=keyboard([[DONE_UPLOAD], [tr(context, "cancel")]]),
        )
        return True

    if flow_type == "add_admin":
        if not is_super_admin(update):
            clear_flow(context)
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            await show_admin_panel(update, context)
            return True
        value = text.strip()
        if value.startswith("@") or not value.isdigit():
            username = normalize_username(value)
            if not re.fullmatch(r"[a-zA-Z0-9_]{5,32}", username):
                await message.reply_text("أرسل User ID رقمي أو username صحيحاً مثل @user.")
                return True
            try:
                db_execute(
                    "INSERT INTO admins(username, display_name) VALUES (?, ?)",
                    (username, f"@{username}"),
                )
            except sqlite3.IntegrityError:
                await message.reply_text("هذا المشرف موجود بالفعل.")
                return True
        else:
            user_id = int(value)
            try:
                db_execute(
                    "INSERT INTO admins(user_id, display_name) VALUES (?, ?)",
                    (user_id, f"User {user_id}"),
                )
            except sqlite3.IntegrityError:
                await message.reply_text("هذا المشرف موجود بالفعل.")
                return True
        clear_flow(context)
        await message.reply_text("تمت إضافة المشرف.")
        await show_admin_management(update, context)
        return True

    if flow_type == "remove_admin":
        if not is_super_admin(update):
            clear_flow(context)
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            await show_admin_panel(update, context)
            return True
        admin_id = context.user_data.get("selection_map", {}).get(text)
        if not admin_id:
            await message.reply_text("اختر مشرفاً من لوحة المفاتيح أو اضغط إلغاء.")
            return True
        admin_count = db_one("SELECT COUNT(*) AS count FROM admins")["count"]
        if admin_count <= 1:
            clear_flow(context)
            await message.reply_text("لا يمكن حذف آخر مشرف.")
            await show_admin_management(update, context)
            return True
        db_execute("DELETE FROM admins WHERE id = ?", (admin_id,))
        clear_flow(context)
        await message.reply_text("تم حذف المشرف.")
        await show_admin_management(update, context)
        return True

    if flow_type == "welcome_message":
        if not is_super_admin(update):
            clear_flow(context)
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            await show_admin_panel(update, context)
            return True
        if not text:
            await message.reply_text("أرسل رسالة الترحيب كنص.")
            return True
        db_execute(
            """
            INSERT INTO settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("welcome_message", text),
        )
        clear_flow(context)
        await message.reply_text(
            "تم حفظ رسالة الترحيب. يمكنك استخدام {first_name} و {username} و {user_id}."
        )
        await show_admin_panel(update, context)
        return True

    clear_flow(context)
    await show_admin_panel(update, context)
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_flow(context)
    context.user_data["menu_path"] = []
    if update.effective_user:
        user_id = update.effective_user.id
        track_user(
            user_id,
            update.effective_user.username,
            update.effective_user.first_name,
        )
        context.user_data["lang"] = get_user_lang(user_id)
    message = update.effective_message
    if message is not None:
        await message.reply_text(welcome_message(update))
    await show_node(update, context)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_flow(context, "search")
    await update.effective_message.reply_text(
        tr(context, "search_prompt"),
        reply_markup=keyboard([[tr(context, "cancel")]]),
    )


async def handle_navigation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    text = message.text.strip()
    path = current_path(context)

    if update.effective_user:
        user_id = update.effective_user.id
        track_user(
            user_id,
            update.effective_user.username,
            update.effective_user.first_name,
        )
        if "lang" not in context.user_data:
            context.user_data["lang"] = get_user_lang(user_id)

    if text in {STRINGS[LANG_AR]["lang_btn"], STRINGS[LANG_EN]["lang_btn"]}:
        new_lang = LANG_EN if context.user_data.get("lang") == LANG_AR else LANG_AR
        context.user_data["lang"] = new_lang
        if update.effective_user:
            set_user_lang(update.effective_user.id, new_lang)
        await message.reply_text(tr(context, "lang_changed"))
        await show_node(update, context)
        return

    if text in {STRINGS[LANG_AR]["fav_btn"], STRINGS[LANG_EN]["fav_btn"]}:
        await show_favorites(update, context)
        return

    if text in {STRINGS[LANG_AR]["recent_btn"], STRINGS[LANG_EN]["recent_btn"]}:
        await show_recent_uploads(update, context)
        return

    if text in {STRINGS[LANG_AR]["main_menu"], STRINGS[LANG_EN]["main_menu"]}:
        context.user_data["menu_path"] = []
        await show_node(update, context)
        return
    if text in {STRINGS[LANG_AR]["back"], STRINGS[LANG_EN]["back"]}:
        if path:
            path.pop()
        await show_node(update, context)
        return
    if text in {STRINGS[LANG_AR]["search_btn"], STRINGS[LANG_EN]["search_btn"]}:
        await search_command(update, context)
        return
    if text in {STRINGS[LANG_AR]["admin_menu"], STRINGS[LANG_EN]["admin_menu"]}:
        if is_admin(update):
            await show_admin_panel(update, context)
        else:
            await message.reply_text(tr(context, "no_permission"))
        return

    if text == BACK_TO_MENU:
        clear_flow(context)
        await show_node(update, context)
        return
    if text == BACK_TO_ADMIN:
        clear_flow(context)
        await show_admin_panel(update, context)
        return

    if text == ADD_BUTTON and is_admin(update):
        set_flow(context, "add_button")
        await message.reply_text(
            f"أرسل اسم الزر الجديد داخل: {node_title(current_node_id(context))}",
            reply_markup=keyboard([[tr(context, "cancel")]]),
        )
        return
    if text == CLONE_NODE_BUTTON and is_admin(update):
        node_id = current_node_id(context)
        if node_id is None:
            await message.reply_text("لا يمكن نسخ القائمة الرئيسية.")
            return
        parent_row = db_one("SELECT parent_id, title FROM menu_nodes WHERE id = ?", (node_id,))
        parent_id = parent_row["parent_id"] if parent_row else None
        set_flow(context, "clone_node_name", source_id=node_id, parent_id=parent_id)
        await message.reply_text(
            f"📋 سيتم نسخ هيكل وتفريعات «{parent_row['title']}» بالكامل.\n\nأرسل اسم المادة/الزر الجديد:",
            reply_markup=keyboard([[tr(context, "cancel")]]),
        )
        return
    if text == EDIT_CURRENT_BUTTON and is_admin(update):
        node_id = current_node_id(context)
        if node_id is None:
            await message.reply_text("لا يمكن تعديل القائمة الرئيسية.")
        else:
            set_flow(context, "edit_node_title", node_id=node_id)
            await message.reply_text("أرسل الاسم الجديد للزر.", reply_markup=keyboard([[tr(context, "cancel")]]))
        return
    if text == DELETE_CURRENT_BUTTON and is_admin(update):
        node_id = current_node_id(context)
        if node_id is None:
            await message.reply_text("لا يمكن حذف القائمة الرئيسية.")
        else:
            set_flow(context, "confirm_delete_node", node_id=node_id)
            await message.reply_text(
                "سيتم حذف الزر وكل المحتوى والأزرار بداخله. اكتب تأكيد للمتابعة.",
                reply_markup=keyboard([[CONFIRM], [tr(context, "cancel")]]),
            )
        return
    if text == ARRANGE_BUTTONS and is_admin(update):
        await show_arrange_selection(update, context)
        return
    if text == BROADCAST_BUTTON and is_admin(update):
        set_flow(context, "broadcast")
        await message.reply_text(
            "📢 أرسل الرسالة أو الإشعار (نص، صورة، أو ملف) ليتم بثه لجميع الطلاب المشتركين:",
            reply_markup=keyboard([[tr(context, "cancel")]]),
        )
        return
    if text == STATS_BUTTON and is_admin(update):
        user_count = db_one("SELECT COUNT(*) AS total FROM users")["total"]
        node_count = db_one("SELECT COUNT(*) AS total FROM menu_nodes")["total"]
        content_count = db_one("SELECT COUNT(*) AS total FROM contents")["total"]
        fav_count = db_one("SELECT COUNT(*) AS total FROM favorites")["total"]
        await message.reply_text(
            f"📊 إحصائيات البوت:\n\n"
            f"👥 عدد الطلاب المشتركين: {user_count}\n"
            f"📁 عدد الأقسام والمواد: {node_count}\n"
            f"📄 إجمالي الملفات والمحاضرات: {content_count}\n"
            f"⭐ إجمالي الإضافات للمفضلة: {fav_count}"
        )
        await show_admin_panel(update, context)
        return

    if text == USERS_LIST_BUTTON and is_super_admin(update):
        users = db_all(
            "SELECT user_id, username, first_name, joined_at FROM users ORDER BY joined_at DESC"
        )
        if not users:
            await message.reply_text("لا يوجد مستخدمون مسجلون بعد.")
            return
        
        current_chunk = f"👥 إجمالي الطلاب المشتركين: {len(users)}\n\n"
        for i, u in enumerate(users, 1):
            uname = f"@{u['username']}" if u["username"] else "بدون يوزر"
            name = (u["first_name"] or "مجهول").replace("`", "")
            line = f"{i}. {name} ({uname}) | ID: `{u['user_id']}`\n"
            if len(current_chunk) + len(line) > 3900:
                await message.reply_text(current_chunk, parse_mode="Markdown")
                current_chunk = ""
            current_chunk += line
            
        if current_chunk:
            await message.reply_text(current_chunk, parse_mode="Markdown")
            
        await show_admin_panel(update, context)
        return

    if text == ACTIVITY_LOG_BUTTON and is_super_admin(update):
        logs = db_all(
            """
            SELECT ua.action_type, ua.item_title, ua.created_at, u.first_name, u.username
            FROM user_activity ua
            LEFT JOIN users u ON ua.user_id = u.user_id
            ORDER BY ua.id DESC
            LIMIT 30
            """
        )
        if not logs:
            await message.reply_text("لا يوجد نشاط مسجل للطلاب بعد.")
            return
        lines = ["📈 سجل آخر ضغطات ونشاط الطلاب:\n"]
        for log in logs:
            uname = f"@{log['username']}" if log["username"] else (log["first_name"] or "طالب")
            lines.append(f"• {uname} ⬅️ فتح: {log['item_title']} ({log['action_type']})")
        await message.reply_text("\n".join(lines))
        await show_admin_panel(update, context)
        return

    if text == ADD_CONTENT and is_admin(update):
        set_flow(context, "add_content_title")
        await message.reply_text("أرسل عنوان المحتوى أولاً.", reply_markup=keyboard([[tr(context, "cancel")]]))
        return
    if text == EDIT_CONTENT and is_admin(update):
        await show_content_selection(update, context, "edit_content")
        return
    if text == DELETE_CONTENT and is_admin(update):
        await show_content_selection(update, context, "delete_content")
        return
    if text == MANAGE_ADMINS and is_admin(update):
        if not is_super_admin(update):
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            return
        await show_admin_management(update, context)
        return
    if text == ADD_ADMIN and is_admin(update):
        if not is_super_admin(update):
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            return
        set_flow(context, "add_admin")
        await message.reply_text(
            "أرسل User ID الرقمي أو username مثل @example.",
            reply_markup=keyboard([[tr(context, "cancel")]]),
        )
        return
    if text == REMOVE_ADMIN and is_admin(update):
        if not is_super_admin(update):
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            return
        await show_admin_selection(update, context)
        return
    if text == LIST_ADMINS and is_admin(update):
        if not is_super_admin(update):
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            return
        admins = db_all(
            "SELECT user_id, username, display_name FROM admins ORDER BY id"
        )
        lines = []
        for admin in admins:
            identity = (
                f"@{admin['username']}"
                if admin["username"]
                else f"ID {admin['user_id']}"
            )
            lines.append(f"• {identity} — {admin['display_name']}")
        await message.reply_text("\n".join(lines) or "لا يوجد مشرفون.")
        await show_admin_management(update, context)
        return
    if text == WELCOME_SETTINGS and is_admin(update):
        if not is_super_admin(update):
            await message.reply_text("⚠️ هذا الإجراء مخصص لمالكة البوت فقط.")
            return
        current = db_one(
            "SELECT value FROM settings WHERE key = ?", ("welcome_message",)
        )
        set_flow(context, "welcome_message")
        await message.reply_text(
            f"رسالة الترحيب الحالية:\n\n{current['value'] if current else DEFAULT_WELCOME}\n\n"
            "أرسل الرسالة الجديدة. يمكنك استخدام {first_name}.",
            reply_markup=keyboard([[tr(context, "cancel")]]),
        )
        return

    selection = context.user_data.get("menu_selection_map", {}).get(text)
    if selection:
        selection_type, item_id = selection
        if selection_type == "node":
            child = db_one(
                "SELECT id, title FROM menu_nodes WHERE id = ? AND parent_id IS ?",
                (item_id, current_node_id(context)),
            )
            if child:
                if update.effective_user and not is_admin(update):
                    log_user_activity(update.effective_user.id, "قسم / زر", child["title"])
                path.append(item_id)
                await show_node(update, context)
                return
        elif selection_type == "content":
            content = db_one(
                "SELECT * FROM contents WHERE id = ? AND node_id IS ?",
                (item_id, current_node_id(context)),
            )
            if content:
                if update.effective_user and not is_admin(update):
                    log_user_activity(update.effective_user.id, "محاضرة / ملف", content["title"])
                await deliver_content(update, content)
                return

    await message.reply_text(tr(context, "select_from_menu"))
    await show_node(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if get_flow(context):
        handled = await process_admin_flow(update, context)
        if handled:
            return
    await handle_navigation(update, context)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start", "القائمة الرئيسية / Restart bot"),
        BotCommand("search", "بحث سريع عن مادة أو محاضرة"),
        BotCommand("cancel", "إلغاء العملية والعودة للرئيسية"),
    ])


def build_application() -> Application:
    token = os.getenv(TOKEN_ENV_VAR)
    if not token:
        raise RuntimeError(
            f"Set {TOKEN_ENV_VAR} before running the bot. Create the token with BotFather."
        )

    initialize_database()
    bootstrap_admins()

    application = Application.builder().token(token).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("cancel", start))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )
    return application


if __name__ == "__main__":
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)
