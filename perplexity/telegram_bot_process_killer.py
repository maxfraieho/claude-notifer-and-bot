#!/usr/bin/env python3
"""
Telegram Bot Process Killer Utility
Finds and kills existing Telegram bot processes
"""

import os
import psutil
import signal
import sys
import time
from typing import List, Dict

def find_telegram_bot_processes() -> List[Dict]:
    """
    Find all running Telegram bot processes
    Returns list of process info dictionaries
    """
    processes = []
    current_pid = os.getpid()

    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                # Skip current process
                if proc.info['pid'] == current_pid:
                    continue

                cmdline = ' '.join(proc.info['cmdline'] or [])

                # Look for Python processes that might be Telegram bots
                if (('python' in proc.info['name'].lower()) and 
                    ('telegram' in cmdline.lower() or 
                     'bot' in cmdline.lower() or
                     'polling' in cmdline.lower())):

                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'create_time': proc.info['create_time'],
                        'process': proc
                    })

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    except Exception as e:
        print(f"Error scanning processes: {e}")

    return processes

def kill_process_gracefully(process_info: Dict, timeout: int = 10) -> bool:
    """
    Kill a process gracefully with timeout
    Returns True if successful, False otherwise
    """
    proc = process_info['process']
    pid = process_info['pid']

    try:
        print(f"Attempting to terminate PID {pid} gracefully...")

        # Send SIGTERM for graceful shutdown
        proc.terminate()

        # Wait for graceful shutdown
        try:
            proc.wait(timeout=timeout)
            print(f"✓ Process {pid} terminated gracefully")
            return True
        except psutil.TimeoutExpired:
            print(f"⚠ Process {pid} didn't respond to SIGTERM, using SIGKILL...")
            proc.kill()
            proc.wait(timeout=5)
            print(f"✓ Process {pid} force killed")
            return True

    except psutil.NoSuchProcess:
        print(f"✓ Process {pid} already terminated")
        return True
    except psutil.AccessDenied:
        print(f"✗ Access denied to terminate process {pid}")
        return False
    except Exception as e:
        print(f"✗ Error terminating process {pid}: {e}")
        return False

def kill_processes_by_pattern(name_pattern: str) -> int:
    """
    Kill processes matching a name pattern
    Returns number of processes killed
    """
    killed_count = 0
    current_pid = os.getpid()

    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] == current_pid:
                    continue

                cmdline = ' '.join(proc.info['cmdline'] or [])

                if (name_pattern.lower() in proc.info['name'].lower() or 
                    name_pattern.lower() in cmdline.lower()):

                    print(f"Found matching process: PID {proc.info['pid']}")
                    print(f"  Command: {cmdline}")

                    # Kill the process
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                        killed_count += 1
                        print(f"✓ Killed PID {proc.info['pid']}")
                    except psutil.TimeoutExpired:
                        proc.kill()
                        killed_count += 1
                        print(f"✓ Force killed PID {proc.info['pid']}")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    except Exception as e:
        print(f"Error: {e}")

    return killed_count

def list_telegram_bots():
    """List all found Telegram bot processes"""
    print("🔍 Scanning for Telegram bot processes...")
    processes = find_telegram_bot_processes()

    if not processes:
        print("✓ No Telegram bot processes found")
        return

    print(f"📋 Found {len(processes)} potential Telegram bot process(es):")
    print()

    for i, proc_info in enumerate(processes, 1):
        create_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                   time.localtime(proc_info['create_time']))
        print(f"{i}. PID: {proc_info['pid']}")
        print(f"   Name: {proc_info['name']}")
        print(f"   Started: {create_time}")
        print(f"   Command: {proc_info['cmdline'][:100]}...")
        print()

def kill_all_telegram_bots(interactive: bool = True) -> int:
    """
    Kill all found Telegram bot processes
    Returns number of processes killed
    """
    processes = find_telegram_bot_processes()

    if not processes:
        print("✓ No Telegram bot processes found to kill")
        return 0

    print(f"📋 Found {len(processes)} potential Telegram bot process(es)")

    if interactive:
        print("\nProcesses to be terminated:")
        for i, proc_info in enumerate(processes, 1):
            print(f"{i}. PID {proc_info['pid']}: {proc_info['name']}")

        response = input("\nContinue with termination? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Operation cancelled")
            return 0

    print("\n🔫 Terminating processes...")
    killed_count = 0

    for proc_info in processes:
        if kill_process_gracefully(proc_info):
            killed_count += 1

    if killed_count > 0:
        print(f"\n✅ Successfully terminated {killed_count} process(es)")
        time.sleep(1)  # Give time for cleanup

    return killed_count

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Telegram Bot Process Manager")
        print()
        print("Usage:")
        print("  python process_killer.py list                 - List all bot processes")
        print("  python process_killer.py kill                 - Kill all bot processes (interactive)")
        print("  python process_killer.py kill --force         - Kill all bot processes (no confirmation)")
        print("  python process_killer.py kill <pattern>       - Kill processes matching pattern")
        print()
        print("Examples:")
        print("  python process_killer.py list")
        print("  python process_killer.py kill")
        print("  python process_killer.py kill telegram_bot.py")
        print("  python process_killer.py kill --force")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        list_telegram_bots()

    elif command == "kill":
        if len(sys.argv) > 2:
            if sys.argv[2] == "--force":
                kill_all_telegram_bots(interactive=False)
            else:
                pattern = sys.argv[2]
                killed = kill_processes_by_pattern(pattern)
                print(f"Killed {killed} processes matching '{pattern}'")
        else:
            kill_all_telegram_bots(interactive=True)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
