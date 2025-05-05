from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime
import pytz
import requests
import os
import sys
import time
import re

def format_rupiah(angka):
    try:
        angka = float(angka)
        return f"Rp {angka:,.0f}".replace(",", ".")
    except:
        return angka

def kirim_telegram_log(pesan: str, parse_mode="Markdown"):
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    print(pesan)
    if telegram_token and telegram_chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                data={
                    "chat_id": telegram_chat_id,
                    "text": pesan,
                    "parse_mode": parse_mode
                }
            )
        except Exception as e:
            print(f"⚠️ Error kirim Telegram: {e}")

def wib():
    return datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M WIB")

def baca_file(file_name: str) -> str:
    with open(file_name, 'r') as file:
        return file.read().strip()

def baca_file_list(file_name: str) -> list:
    with open(file_name, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def run(playwright: Playwright) -> int:
    daftar = baca_file_list("multi.txt")
    password = os.getenv("pw")
    ada_error = False

    if len(daftar) < 2:
        print("❌ multi.txt tidak memiliki minimal 2 baris.")
        return 1

    baris_kedua = daftar[1]
    bagian = baris_kedua.split('|')
    if len(bagian) < 2:
        print(f"❌ Format baris ke-2 tidak sesuai: {baris_kedua}")
        return 1

    sebelum_pipe = bagian[0].split(':')
    if len(sebelum_pipe) < 3:
        print(f"❌ Format sebelum '|' tidak sesuai di baris ke-2: {baris_kedua}")
        return 1

    site = sebelum_pipe[2]
    userid_site = setelah_pipe[2]
    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()

        print(f"🌐 Membuka halaman {site}...")
        page.goto(f"https://{site}", timeout=60000)

        # LOGIN
        page.locator('input[placeholder="Username"]').fill(userid_site)
        page.locator('input[placeholder="Password"]').fill(password)
        page.locator('button:has-text("Masuk")').click()
        page.wait_for_timeout(3000)

        # BUKA MENU -> TOGEL -> HISTORY
        page.locator('text=Menu').click()
        page.wait_for_timeout(1000)
        page.locator('text=Togel').click()
        page.wait_for_timeout(1000)
        page.locator('text=History').click()
        page.wait_for_timeout(3000)

        # CEK DATA TRANSAKSI
        rows = page.locator("table tr").all()
        if not rows:
            print("❌ Tidak ada data transaksi.")
        else:
            found_win = False
            for row in rows:
                text = row.inner_text()
                if "Menang" in text and "HOKI DRAW" in text:
                    found_win = True
                    match = re.search(r"Menang\s([\d.,]+)", text)
                    nilai = match.group(1) if match else "?"

                    saldo_text = page.locator("text=Rp").nth(0).inner_text()
                    current_saldo = int(re.sub(r"[^\d]", "", saldo_text))

                    pesan = (
                        f"<b>{userid_site}</b>\n"
                        f"🏆 Menang: {format_rupiah(nilai)}\n"
                        f"💰 Saldo: {format_rupiah(current_saldo)}\n"
                        f"⌚ {wib()}"
                    )
                    kirim_telegram_log(pesan, parse_mode="HTML")

                    # ==== AUTO WD LOGIC ====
                    try:
                        if os.path.exists("autowd.txt"):
                            autowd_config = baca_file("autowd.txt")
                            if ':' in autowd_config:
                                batas_str, wd_amount_str = autowd_config.split(":")
                                batas_saldo = int(batas_str.strip())
                                wd_amount = wd_amount_str.strip()

                                if current_saldo >= batas_saldo:
                                    print(f"💳 Saldo {current_saldo} >= {batas_saldo}, auto WD {wd_amount}")
                                    page.locator('text=Menu').click()
                                    page.wait_for_timeout(1000)
                                    page.locator('text=Withdraw').click()
                                    page.wait_for_timeout(3000)

                                    page.locator('input[placeholder*="Jumlah"]').fill(wd_amount)
                                    page.locator('button:has-text("kirim")').click()
                                    page.wait_for_timeout(3000)

                                    kirim_telegram_log(
                                        f"<b>{userid_site}</b>\n"
                                        f"✅ Auto WD {format_rupiah(wd_amount)} berhasil\n"
                                        f"💰 Sisa: {format_rupiah(current_saldo - int(wd_amount))}\n"
                                        f"⌚ {wib()}",
                                        parse_mode="HTML"
                                    )
                    except Exception as e:
                        print(f"⚠️ Gagal auto WD: {e}")
                    break  # hanya proses kemenangan pertama

            if not found_win:
                saldo_text = page.locator("text=Rp").nth(0).inner_text()
                current_saldo = int(re.sub(r"[^\d]", "", saldo_text))
                kirim_telegram_log(
                    f"<b>{userid_site}</b>\n😢 Tidak Menang\n💰 Saldo: {format_rupiah(current_saldo)}\n⌚ {wib()}",
                    parse_mode="HTML"
                )

        context.close()
        browser.close()

    except Exception as e:
        ada_error = True
        print(f"❌ Error: {e}")
        try:
            context.close()
            browser.close()
        except:
            pass

    return 1 if ada_error else 0

if __name__ == "__main__":
    with sync_playwright() as playwright:
        sys.exit(run(playwright))
