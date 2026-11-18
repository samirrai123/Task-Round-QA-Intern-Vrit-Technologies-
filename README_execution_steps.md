# Selenium Signup Automation

This small Python project fills the signup form on the Authorized Partner
website:

`https://authorized-partner.vercel.app/register`

## What the script does

1. Opens Chrome.
2. Accepts the terms checkbox.
3. Enters the account details.
4. Enters agency details on the following pages.
5. Uploads documents when file paths are provided.
6. Enters the OTP and submits only when `--submit` is used.

The normal command is a safe dry run. It fills the form but does not create an
account.

## Setup

Requirements:

- Python 3.10 or newer
- Google Chrome
- Internet connection
- PowerShell

Run these commands in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item test_data.example.json test_data.json
```

Open `test_data.json` and replace the example email, phone number, password,
and OTP with authorized test values. Do not upload real personal documents.

The project uses Python, Selenium WebDriver, Chrome, JSON test data, and
PowerShell.

## Run a safe test

```powershell
py signup_automation_script.py --data test_data.json
```

## Submit a real test registration

Only use a test account approved by the site owner:

```powershell
py signup_automation_script.py --data test_data.json --submit --prompt-otp
```

The site still controls OTP verification and rejects duplicate email or phone
numbers. The script does not bypass those checks.

When the OTP verification page opens, update the `otp` field in
`test_data.json` with the code received by email or phone. Do not paste the OTP
or password into terminal chat or source control. The script waits up to 10
minutes and checks the local file every 2 seconds.

To run in the background after setup, use:

```powershell
cd "C:\Users\Sameer\OneDrive\Desktop\Assignment"
.\.venv\Scripts\Activate.ps1
py signup_automation_script.py --data test_data.json --submit --prompt-otp
```

## Files

- `signup_automation_script.py` - the Selenium automation
- `test_data.example.json` - safe example data
- `test_data.json` - local authorized test credentials (keep private)
- `requirements.txt` - Selenium dependency
