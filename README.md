# File Compression Watcher

This script acts as a system janitor. It runs in the background (as a daemon), looks for large files in a specific folder, compresses them to save space, and sends you an email report of its progress.

## INSTALL NOTES:  
   To get this daemon running, you’ll need to set up the Python environment, install specific system-level dependencies for `psutil`, and configure a way to send emails.

---

## 1. Prerequisites

* **Python:** Version 3.6 or higher is recommended.
* **Permissions:** You may need **Administrator (Windows)** or **Root/Sudo (Linux)** privileges because the script scans process handles across the entire system.

## 2. Install Required Libraries

Open your terminal or command prompt and run the following:

```bash
# Core requirements mentioned in the script
pip install psutil
pip install validate-email-address

```

> [!IMPORTANT]
> **Linux Users:** `psutil` often requires Python development headers to compile. If the installation fails, run:
> * **Ubuntu/Debian:** `sudo apt install python3-dev gcc`
> * **RHEL/CentOS:** `sudo yum install python3-devel gcc`
> 
> 

## 3. Email Configuration (SMTP)

The script is currently hardcoded to use `localhost` as the SMTP host. Unless you have a mail server running on your machine (like Postfix or Sendmail), you have two options:

### Option A: Use a real Email Provider (Gmail, Outlook, etc.)

You will need to run the script with the `-e` and `-m` flags to point to your provider.

* **Example for Gmail:** `python script.py -e smtp.gmail.com -m yourname@gmail.com [target_dir] [recipient] [threshold]`
* *Note: Most modern providers require SSL/TLS and an "App Password," which might require a small code tweak to `smtplib.SMTP_SSL`.*

### Option B: Local Testing (No real emails sent)

If you just want to see if the script works without setting up a real mail server, you can run a **dummy SMTP server** in a separate terminal window:

```bash
# This will catch emails and print them to your terminal instead of sending them
python -m smtpd -n -c DebuggingServer localhost:1025

```

Then run your script using `-e localhost:1025`.

---

## 4. Running the Script

The script uses a mix of "positional arguments" (required) and "options" (optional flags).

### Standard Run

To scan a folder called `logs`, email `admin@example.com`, and only touch files over 5MB (5,242,880 bytes):

```bash
python your_script.py /home/user/logs admin@example.com 5242880

```

### Dry Run (Recommended for first time)

To see what files *would* be compressed without actually changing anything:

```bash
python your_script.py -r /home/user/logs admin@example.com 5242880

```

### Custom Sleep Time

To make the daemon wait 10 minutes (600 seconds) between scans instead of the default 5:

```bash
python your_script.py -s 600 /home/user/logs admin@example.com 5242880

```

---

## 5. Deployment as a "True" Daemon

Since this script is a loop, it will "lock" your terminal window while it runs.

* **Linux:** Run it with `nohup` and `&` to keep it alive after you close the terminal:
`nohup python3 your_script.py [args] > output.log 2>&1 &`
* **Windows:** You can run it using `pythonw.exe` to execute it without a console window.

**Would you like me to show you how to modify the email section to support secure Gmail (SSL/TLS) authentication?**
