import os
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError


def masked_input(prompt="Password: "):
    if os.name == "nt":
        import msvcrt
        sys.stdout.write(prompt); sys.stdout.flush()
        buf = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\\r", "\\n"):
                sys.stdout.write("\\n"); break
            if ch == "\\x03":
                raise KeyboardInterrupt
            if ch in ("\\b", "\\x08"):
                if buf:
                    buf.pop(); sys.stdout.write("\\b \\b"); sys.stdout.flush()
                continue
            buf.append(ch); sys.stdout.write("*"); sys.stdout.flush()
        return "".join(buf)
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        pwd = ""
        try:
            sys.stdout.write(prompt); sys.stdout.flush()
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\\n", "\\r"):
                    sys.stdout.write("\\n"); break
                if ch == "\\x03":
                    raise KeyboardInterrupt
                if ch in ("\\x7f", "\\b"):
                    if pwd:
                        pwd = pwd[:-1]; sys.stdout.write("\\b \\b"); sys.stdout.flush()
                    continue
                pwd += ch; sys.stdout.write("*"); sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return pwd


class WorkMarketAuth:
    LOGIN_URL = "https://www.workmarket.com/login"
    HOME_URL  = "https://www.workmarket.com/home"

    def __init__(self, headless=False):
        self.data_dir = Path("data"); self.data_dir.mkdir(exist_ok=True)
        self.storage_path = self.data_dir / "storage_state.json"
        self.creds_path   = self.data_dir / "credentials.json"
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = None

    def create_context_from_storage(self):
        if self.storage_path.exists():
            self.context = self.browser.new_context(storage_state=str(self.storage_path))
        else:
            self.context = self.browser.new_context()
        return self.context

    def _save_context(self):
        if self.context:
            self.context.storage_state(path=str(self.storage_path))

    def _avatar_locator(self, page):
        return page.locator(".logged-in-user sdf-avatar[aria-label]").first
    def _tile_name_locator(self, page):
        return page.locator(".tile.-home h2").first

    def get_username(self) -> str:
        page = self.context.new_page()
        try:
            try:
                page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=12000)
            except PWTimeoutError:
                pass
            page.wait_for_timeout(500)
            av = self._avatar_locator(page)
            if av.count() > 0:
                lab = av.get_attribute("aria-label")
                if lab:
                    return lab.strip()
            h2 = self._tile_name_locator(page)
            if h2.count() > 0:
                txt = h2.inner_text().strip()
                if txt:
                    return txt
            any_av = page.locator("sdf-avatar[aria-label]").first
            if any_av.count() > 0:
                lab = any_av.get_attribute("aria-label")
                if lab:
                    return lab.strip()
            return "Unknown"
        finally:
            page.close()

    def is_logged_in(self) -> bool:
        page = self.context.new_page()
        try:
            try:
                page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=12000)
            except PWTimeoutError:
                pass
            page.wait_for_timeout(500)
            if self._avatar_locator(page).count() > 0:
                return True
            if self._tile_name_locator(page).count() > 0:
                return True
            return False
        finally:
            page.close()

    def _fill_input(self, page, host_selector, value, timeout=15000):
        host = page.locator(host_selector).first
        host.wait_for(state="visible", timeout=timeout)
        inner = host.locator("input").first
        inner.wait_for(state="visible", timeout=timeout)
        inner.click(); inner.fill(""); inner.type(value, delay=8)

    def _click_login(self, page):
        try:
            page.locator("sdf-input#login-password input").press("Enter")
            page.wait_for_timeout(200)
        except Exception:
            pass
        try:
            page.get_by_role("button", name=lambda n: n and n.strip().lower() == "login").click(timeout=800); return
        except Exception:
            pass
        for sel in ["sdf-button:has-text('Login')", ".button:has-text('Login')", "form#page_form sdf-button", "form#page_form .button"]:
            try:
                page.locator(sel).first.click(timeout=800); return
            except Exception:
                continue
        try:
            page.evaluate("document.querySelector('form#page_form')?.requestSubmit?.()")
        except Exception:
            pass

    def _wait_until_home_or_user_visible(self, page, timeout_s=30):
        import time as _t
        end = _t.time() + timeout_s
        twofa = page.locator("sdf-input#tfaToken")
        while _t.time() < end:
            try:
                if "/home" in page.url and (self._avatar_locator(page).count() > 0 or self._tile_name_locator(page).count() > 0):
                    return True
                if twofa.count() == 0 and "/login" not in page.url:
                    if self._avatar_locator(page).count() > 0 or self._tile_name_locator(page).count() > 0:
                        return True
                if self._avatar_locator(page).count() > 0 or self._tile_name_locator(page).count() > 0:
                    return True
                page.wait_for_timeout(120)
            except Exception:
                pass
        return False

    def _handle_2fa(self, page):
        print("Security Checkpoint: Enter the code sent to your email.")
        tfa_host = page.locator("sdf-input#tfaToken").first
        tfa_host.wait_for(state="visible", timeout=15000)

        try:
            trust = page.locator("#tfa-trusted-device-checkbox").first
            if trust.count() > 0:
                aria_checked = (trust.get_attribute("aria-checked") or "false").lower()
                if aria_checked != "true":
                    trust.click()
        except Exception:
            pass

        for _ in range(5):
            code = input("Verification code (or 'r' to Resend): ").strip()
            if not code:
                continue
            if code.lower() == "r":
                for sel in ("[data-attr-id='resend']", "sdf-button:has-text('Resend Code')", ".button:has-text('Resend Code')"):
                    try:
                        page.locator(sel).first.click(timeout=800); print("Resent."); break
                    except Exception:
                        continue
                continue

            self._fill_input(page, "sdf-input#tfaToken", code)
            clicked = False
            for sel in ("button:has-text('Verify')", "sdf-button:has-text('Verify')", ".button:has-text('Verify')"):
                try:
                    page.locator(sel).first.click(timeout=600); clicked = True; break
                except Exception:
                    continue
            if not clicked:
                try:
                    page.locator("sdf-input#tfaToken input").press("Enter")
                except Exception:
                    pass

            if self._wait_until_home_or_user_visible(page, timeout_s=25):
                print("Verification success!")
                return

            if page.locator("text=verification failed").count() > 0:
                print("Invalid/expired code.")
                continue

        raise RuntimeError("2FA failed.")

    def _login(self, email, password):
        page = self.context.new_page()
        page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
        print("Filling login fields...")
        self._fill_input(page, "sdf-input#login-email", email)
        self._fill_input(page, "sdf-input#login-password", password)
        print("Submitting form..."); self._click_login(page)

        import time as _t
        start = _t.time(); checkpoint = False
        while _t.time() - start < 25:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=500)
            except PWTimeoutError:
                pass
            if page.locator("h1:has-text('Security Checkpoint')").count() > 0 or page.locator("sdf-input#tfaToken").count() > 0:
                checkpoint = True; break
            if self._wait_until_home_or_user_visible(page, timeout_s=1):
                print("Logged in without 2FA prompt.")
                self._save_context(); page.close(); return
            page.wait_for_timeout(120)

        if checkpoint:
            self._handle_2fa(page)
            if not self._wait_until_home_or_user_visible(page, timeout_s=20):
                page.screenshot(path=str(self.data_dir / "post_2fa_debug.png"))
                page.close()
                raise RuntimeError("2FA accepted but /home not detected in time.")
            self._save_context(); page.close(); return

        if not self._wait_until_home_or_user_visible(page, timeout_s=10):
            page.screenshot(path=str(self.data_dir / "login_debug.png"))
            page.close()
            raise RuntimeError("Login did not reach /home.")
        self._save_context(); page.close()

    def authenticate(self, force=False):
        # Try storage-only first
        self.create_context_from_storage()
        if not force and self.is_logged_in():
            print("User Login Successful.")
            try:
                name = self.get_username()
                print("User: " + name)
            except Exception:
                pass
            return "OK", True

        try:
            self.context.close()
        except Exception:
            pass
        # Fresh context for interactive login
        self.context = self.browser.new_context()

        email = password = None
        if self.creds_path.exists():
            try:
                creds = json.loads(self.creds_path.read_text())
                email = creds.get("email"); password = creds.get("password")
            except Exception:
                pass
        if not email:
            email = input("Email: ").strip()
        if not password:
            password = masked_input("Password: ")
            try:
                json.dump({"email": email, "password": password}, open(self.creds_path, "w"), indent=2)
                print("Saved credentials!!")
            except Exception as e:
                print(f"Warning: couldn't save credentials file: {e}")

        self._login(email, password)
        print("User Login Successful.")
        try:
            name = self.get_username()
            print("User: " + name)
        except Exception:
            pass
        return "OK", False

    def close(self):
        try:
            if self.browser:
                self.browser.close()
        finally:
            try:
                self.pw.stop()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Interactive WorkMarket authentication (saves cookies).")
    parser.add_argument("--headless", type=lambda x: x.lower() != "false", default="false",
                        help="Set to 'false' for visible browser (default false).")
    parser.add_argument("--force-reauth", action="store_true", help="Ignore stored session and login again.")
    args = parser.parse_args()

    auth = WorkMarketAuth(headless=(str(args.headless).lower() != "false"))
    try:
        if args.force_reauth:
            auth.authenticate(force=True)
        else:
            auth.authenticate(force=False)
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        auth.close()
