"""Telegram bot to record Parkir Mobil data into Odoo.

Environment variables required:
- TELEGRAM_BOT_TOKEN
- ODOO_URL (e.g. http://localhost:8069)
- ODOO_DB
- ODOO_USERNAME
- ODOO_PASSWORD

Usage in Telegram:
/parkir YYYY-MM-DD PLAT HH:MM [HH:MM]
Example:
/parkir 2024-05-15 B1234CD 08:30 11:15
"""

import os
from datetime import datetime
from xmlrpc import client as xmlrpc_client

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _time_to_float(value: str) -> float:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour + parsed.minute / 60.0


def _get_odoo_clients():
    url = _env("ODOO_URL")
    db = _env("ODOO_DB")
    username = _env("ODOO_USERNAME")
    password = _env("ODOO_PASSWORD")

    common = xmlrpc_client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, username, password, {})
    if not uid:
        raise RuntimeError("Authentication to Odoo failed. Check credentials.")

    models = xmlrpc_client.ServerProxy(f"{url}/xmlrpc/2/object")
    return db, uid, password, models


def _format_help() -> str:
    return (
        "Format perintah:\n"
        "/parkir YYYY-MM-DD PLAT HH:MM [HH:MM]\n"
        "Contoh: /parkir 2024-05-15 B1234CD 08:30 11:15"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_format_help())


async def parkir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    if not context.args or len(context.args) < 3:
        await update.message.reply_text(_format_help())
        return

    tanggal = context.args[0]
    nomor_plat = context.args[1]
    jam_masuk_text = context.args[2]
    jam_keluar_text = context.args[3] if len(context.args) > 3 else None

    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Tanggal harus format YYYY-MM-DD.")
        return

    try:
        jam_masuk = _time_to_float(jam_masuk_text)
        jam_keluar = _time_to_float(jam_keluar_text) if jam_keluar_text else None
    except ValueError:
        await update.message.reply_text("Jam harus format HH:MM.")
        return

    db, uid, password, models = _get_odoo_clients()
    values = {
        "tanggal": tanggal,
        "nomor_plat": nomor_plat,
        "jam_masuk": jam_masuk,
        "jam_keluar": jam_keluar,
    }

    record_id = models.execute_kw(db, uid, password, "parkir.mobil", "create", [values])
    await update.message.reply_text(
        f"Data parkir tersimpan dengan ID {record_id} untuk {nomor_plat}."
    )


def main() -> None:
    token = _env("8498543613:AAERSSpz5kd__pl_Xnz2JmgCxg3uE1Nqzu8")
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("parkir", parkir_command))

    application.run_polling()


if __name__ == "__main__":
    main()
