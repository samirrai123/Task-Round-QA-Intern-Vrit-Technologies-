"""Selenium automation for the Authorized Partner registration flow.

The script deliberately defaults to --dry-run. Use --submit only with a
test account and test documents that you are authorized to submit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = "https://authorized-partner.vercel.app"
REGISTER_URL = f"{BASE_URL}/register"


@dataclass
class RegistrationData:
    first_name: str
    last_name: str
    email: str
    phone_number: str
    phone_country: str = "+977"
    password: str = ""
    agency_name: str = ""
    agency_email: str = ""
    agency_address: str = ""
    agency_website: str = ""
    role_in_agency: str = "Owner"
    region_of_operation: list[str] = field(default_factory=list)
    services_provided: list[str] = field(default_factory=list)
    preferred_institution_types: list[str] = field(default_factory=list)
    years_of_experience: str = "1"
    number_of_students_recruited_annually: str = "1"
    business_registration_number: str = ""
    bank_name: str = ""
    branch_name: str = ""
    account_holder_name: str = ""
    account_number: str = ""
    document_paths: list[str] = field(default_factory=list)
    otp: str = ""

    @classmethod
    def from_json(cls, path: Path) -> "RegistrationData":
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("The test-data file must contain a JSON object.")
        return cls(**values)

    def validate(self, submit: bool) -> None:
        required = ("first_name", "last_name", "email", "phone_number", "password")
        missing = [key for key in required if not getattr(self, key)]
        if missing:
            raise ValueError(f"Missing required test-data fields: {', '.join(missing)}")
        if submit and not self.otp:
            raise ValueError(
                "OTP is required for --submit. Provide it in test-data JSON or "
                "the SIGNUP_OTP environment variable."
            )
        for document in self.document_paths:
            if not Path(document).is_file():
                raise FileNotFoundError(f"Document does not exist: {document}")


def load_data(path: Path | None) -> RegistrationData:
    if path:
        data = RegistrationData.from_json(path)
    else:
        data = RegistrationData(
            first_name=os.getenv("SIGNUP_FIRST_NAME", ""),
            last_name=os.getenv("SIGNUP_LAST_NAME", ""),
            email=os.getenv("SIGNUP_EMAIL", ""),
            phone_number=os.getenv("SIGNUP_PHONE", ""),
            phone_country=os.getenv("SIGNUP_PHONE_COUNTRY", "+977"),
            password=os.getenv("SIGNUP_PASSWORD", ""),
            agency_name=os.getenv("SIGNUP_AGENCY_NAME", ""),
            agency_email=os.getenv("SIGNUP_AGENCY_EMAIL", ""),
            agency_address=os.getenv("SIGNUP_AGENCY_ADDRESS", ""),
            agency_website=os.getenv("SIGNUP_AGENCY_WEBSITE", ""),
            role_in_agency=os.getenv("SIGNUP_ROLE", "Owner"),
            otp=os.getenv("SIGNUP_OTP", ""),
        )
    if not data.otp:
        data.otp = os.getenv("SIGNUP_OTP", "")
    return data


class SignupBot:
    def __init__(
        self,
        driver: WebDriver,
        data: RegistrationData,
        submit: bool,
        prompt_otp: bool = False,
    ) -> None:
        self.driver = driver
        self.data = data
        self.submit = submit
        self.prompt_otp = prompt_otp
        self.wait = WebDriverWait(driver, 15)

    def _visible(self, locator: tuple[str, str]) -> Any | None:
        try:
            element = self.wait.until(EC.presence_of_element_located(locator))
            return element if element.is_displayed() else None
        except TimeoutException:
            return None

    def _find_by_text(self, text: str) -> Any | None:
        xpath = (
            "//*[self::input or self::textarea or self::select or self::button or "
            "self::a or @role='combobox']"
            "[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            f"'{text.lower()}') or contains(translate(@placeholder,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
            f"'{text.lower()}')]"
        )
        try:
            return self.driver.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            return None

    def _fill(self, names: tuple[str, ...], value: str, required: bool = False) -> bool:
        if not value:
            return False
        for name in names:
            element = self._find_by_text(name)
            if element and element.tag_name in {"input", "textarea"}:
                element.clear()
                element.send_keys(value)
                return True
        if "phone number" in names:
            phone = self.driver.find_elements(
                By.CSS_SELECTOR, "input[placeholder*='00000000']"
            )
            if phone:
                phone[0].clear()
                phone[0].send_keys(value)
                return True
        if required:
            raise RuntimeError(f"Could not find a visible field for {names[0]!r}.")
        return False

    def _click_button(self, names: tuple[str, ...]) -> bool:
        for name in names:
            xpath = (
                f"//button[contains(translate(normalize-space(.),"
                f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{name.lower()}')]"
                f"|//a[contains(translate(normalize-space(.),"
                f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{name.lower()}')]"
            )
            try:
                button = self.driver.find_element(By.XPATH, xpath)
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    return True
            except NoSuchElementException:
                continue
        return False

    def accept_terms(self) -> None:
        checkbox = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[@type='checkbox']|//*[@role='checkbox']")
            )
        )
        if not checkbox.is_selected():
            checkbox.click()
        self._click_button(("continue",))
        self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder*='First Name']")
            )
        )

    def fill_account(self) -> None:
        self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder*='First Name']")
            )
        )
        self._fill(("first name", "first_name"), self.data.first_name, True)
        self._fill(("last name", "last_name"), self.data.last_name, True)
        self._fill(("email address", "email"), self.data.email, True)
        self._fill(("phone number", "phone_number"), self.data.phone_number, True)
        password_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        if len(password_fields) < 2:
            raise RuntimeError("The account password fields were not found.")
        password_fields[0].send_keys(self.data.password)
        password_fields[1].send_keys(self.data.password)
        self._click_button(("next",))

    def fill_visible_fields(self) -> None:
        values = {
            ("agency name", "agency_name"): self.data.agency_name,
            ("agency email", "agency_email"): self.data.agency_email,
            ("agency address", "agency_address"): self.data.agency_address,
            ("agency website", "agency_website"): self.data.agency_website,
            ("role in agency", "role_in_agency"): self.data.role_in_agency,
            ("years of experience", "years_of_experience"): self.data.years_of_experience,
            (
                "number of students recruited annually",
                "number_of_students_recruited_annually",
            ): self.data.number_of_students_recruited_annually,
            (
                "business registration number",
                "business_registration_number",
            ): self.data.business_registration_number,
            ("bank name", "bank_name"): self.data.bank_name,
            ("branch name", "branch_name"): self.data.branch_name,
            ("account holder name", "account_holder_name"): self.data.account_holder_name,
            ("account number", "account_number"): self.data.account_number,
        }
        for names, value in values.items():
            self._fill(names, value)
        self._upload_documents()

    def _upload_documents(self) -> None:
        if not self.data.document_paths:
            return
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if not inputs:
            raise RuntimeError("Documents are configured, but no file input is visible.")
        for index, path in enumerate(self.data.document_paths):
            target = inputs[min(index, len(inputs) - 1)]
            target.send_keys(str(Path(path).resolve()))

    def _fill_otp(self) -> None:
        if self.prompt_otp:
            otp_path = Path("test_data.json")
            print("Waiting for OTP. Update the otp field in test_data.json.")
            deadline = time.time() + 600
            while time.time() < deadline:
                try:
                    values = json.loads(otp_path.read_text(encoding="utf-8"))
                    otp = str(values.get("otp", "")).strip()
                    if otp and otp not in {"replace-with-test-otp", "prompt-in-terminal"}:
                        self.data.otp = otp
                        break
                except (json.JSONDecodeError, OSError):
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("Timed out waiting for the OTP in test_data.json.")

        digits = list(self.data.otp)
        inputs = self.driver.find_elements(
            By.CSS_SELECTOR,
            "input[autocomplete='one-time-code'], input[inputmode='numeric'], "
            "input[name*='otp' i], input[name*='code' i]",
        )
        if len(inputs) == 1:
            inputs[0].send_keys(self.data.otp)
        elif inputs:
            for element, digit in zip(inputs, digits):
                element.send_keys(digit)

    def run(self) -> None:
        self.driver.get(REGISTER_URL)
        self.accept_terms()
        self.fill_account()
        for _ in range(10):
            if self._find_by_text("otp") or self._find_by_text("verification code"):
                self._fill_otp()
                self._click_button(("verify code", "verify", "submit", "register"))
                break
            self.fill_visible_fields()
            if not self._click_button(("next", "continue", "submit", "register")):
                break
            time.sleep(0.5)
        if self.submit:
            self.wait.until(
                EC.any_of(
                    EC.url_contains("login"),
                    EC.text_to_be_present_in_element(
                        (By.TAG_NAME, "body"), "created successfully"
                    ),
                )
            )


def build_driver(headless: bool) -> WebDriver:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(options=options)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="JSON file containing authorized test data.")
    parser.add_argument("--submit", action="store_true", help="Submit the registration.")
    parser.add_argument("--headless", action="store_true", help="Run Chrome without a window.")
    parser.add_argument(
        "--prompt-otp",
        action="store_true",
        help="Pause and ask for the OTP when the verification page opens.",
    )
    args = parser.parse_args()
    data = load_data(args.data)
    if args.prompt_otp and args.submit:
        data.otp = "prompt-in-terminal"
    data.validate(args.submit)
    driver = build_driver(args.headless)
    try:
        SignupBot(driver, data, args.submit, args.prompt_otp).run()
        print("Signup flow completed.")
        return 0
    except Exception as exc:
        print(f"Signup flow failed: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
