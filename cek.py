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

def baca_multi_sites(file_name="multi.txt"):
    try:
        with open(file_name, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def proses_site(playwright: Playwright, site: str) -> int:
    userid_site = os.getenv("USER_ID")
    password = os.getenv("pw")
    ada_error = False

    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()

        print(f"🌐 Membuka {site}...")
        page.goto(f"https://{site}", timeout=60000)

        page.locator('input[placeholder="Username"]').fill(userid_site)
        page.locator('input[placeholder="Password"]').fill(password)
        page.locator('button:has-text("Masuk")').click()
        page.wait_for_timeout(3000)

        page.locator('text=Menu').click()
        page.wait_for_timeout(1000)
        page.locator('text=Togel').click()
        page.wait_for_timeout(1000)
        page.locator('text=History').click()
        page.wait_for_timeout(3000)

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
                        f"🧩 Situs: {site}\n"
                        f"🏆 Menang: {format_rupiah(nilai)}\n"
                        f"💰 Saldo: {format_rupiah(current_saldo)}\n"
                        f"⌚ {wib()}"
                    )
                    kirim_telegram_log(pesan, parse_mode="HTML")

                    # ==== AUTO WD ====
                    try:
                        if os.path.exists("autowd.txt"):
                            autowd_config = baca_file("autowd.txt")
                            if ':' in autowd_config:
                                batas_str, wd_amount_str = autowd_config.split(":")
                                batas_saldo = int(batas_str.strip())
                                wd_amount = wd_amount_str.strip()

                                if current_saldo >= batas_saldo:
                                    print(f"💳 Auto WD {wd_amount} di {site}")
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
                                        f"🧩 Situs: {site}\n"
                                        f"💰 Sisa: {format_rupiah(current_saldo - int(wd_amount))}\n"
                                        f"⌚ {wib()}",
                                        parse_mode="HTML"
                                    )
                    except Exception as e:
                        print(f"⚠️ Gagal auto WD: {e}")
                    break

            if not found_win:
                saldo_text = page.locator("text=Rp").nth(0).inner_text()
                current_saldo = int(re.sub(r"[^\d]", "", saldo_text))
                kirim_telegram_log(
                    f"<b>{userid_site}</b>\n🧩 Situs: {site}\n😢 Tidak Menang\n💰 Saldo: {format_rupiah(current_saldo)}\n⌚ {wib()}",
                    parse_mode="HTML"
                )

        context.close()
        browser.close()

    except Exception as e:
        ada_error = True
        print(f"❌ Error di {site}: {e}")
        try:
            context.close()
            browser.close()
        except:
            pass

    return 1 if ada_error else 0

if __name__ == "__main__":
    sites = baca_multi_sites()
    if not sites:
        print("❌ File multi.txt kosong atau tidak ditemukan.")
        sys.exit(1)

    with sync_playwright() as playwright:
        for site in sites:
            proses_site(playwright, site)
