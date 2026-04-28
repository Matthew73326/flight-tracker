"""
Flight Tracker Updater v2
Waits for main app to close, downloads new version, swaps files, relaunches.
"""

import sys, os, time, urllib.request, shutil, traceback

def main():
    if len(sys.argv) < 3:
        print("Usage: updater.py <target_file> <download_url>")
        input("Press Enter to exit...")
        sys.exit(1)

    target_file  = sys.argv[1]
    download_url = sys.argv[2]
    tmp_file     = target_file + ".download"
    backup_file  = target_file + ".bak"

    print(f"Flight Tracker Updater")
    print(f"Target : {target_file}")
    print(f"URL    : {download_url}")
    print()

    # Wait for main app to fully exit
    print("Waiting for app to close...")
    time.sleep(3)

    try:
        # Download new file
        print("Downloading update...")
        urllib.request.urlretrieve(download_url, tmp_file)
        size = os.path.getsize(tmp_file)
        print(f"Downloaded {size} bytes OK")

        if size < 1000:
            raise Exception(f"Downloaded file too small ({size} bytes) - likely a 404 error")

        # Verify it looks like Python
        with open(tmp_file, 'r', encoding='utf-8') as f:
            first_line = f.read(200)
        if 'def ' not in first_line and 'import' not in first_line and '"""' not in first_line:
            raise Exception("Downloaded file doesn't look like valid Python")

        # Backup old version
        print("Backing up old version...")
        if os.path.exists(backup_file):
            os.remove(backup_file)
        shutil.copy2(target_file, backup_file)

        # Replace with new version
        print("Installing new version...")
        os.remove(target_file)
        shutil.move(tmp_file, target_file)
        print("Update installed successfully!")

        # Relaunch
        print("Relaunching app...")
        time.sleep(1)
        app_dir = os.path.dirname(target_file)
        launcher = os.path.join(app_dir, "Launch_FlightTracker.vbs")
        if os.path.exists(launcher):
            os.startfile(launcher)
        else:
            os.startfile(target_file)

        print("Done!")
        time.sleep(2)

    except Exception as e:
        # Clean up temp file if it exists
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass

        print(f"\nERROR: {e}")
        print(traceback.format_exc())

        # Show error dialog
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Update Failed",
                f"Could not update Flight Tracker:\n\n{e}\n\nPlease download the latest version manually from:\nhttps://github.com/Matthew73326/flight-tracker")
            root.destroy()
        except Exception:
            pass

        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
