"""
Flight Tracker Updater
This script is called by the main app to perform the update.
It waits for the main app to close, downloads the new version, then relaunches.
"""

import sys, os, time, urllib.request, shutil

def main():
    if len(sys.argv) < 3:
        print("Usage: updater.py <target_file> <download_url>")
        sys.exit(1)

    target_file  = sys.argv[1]
    download_url = sys.argv[2]

    # Wait a moment for the main app to fully close
    time.sleep(2)

    try:
        # Download new version to a temp file
        tmp_file = target_file + ".new"
        urllib.request.urlretrieve(download_url, tmp_file)

        # Backup old version
        backup = target_file + ".bak"
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copy2(target_file, backup)

        # Replace with new version
        os.remove(target_file)
        shutil.move(tmp_file, target_file)

        # Relaunch the app
        app_dir = os.path.dirname(target_file)
        launcher = os.path.join(app_dir, "Launch_FlightTracker.vbs")
        if os.path.exists(launcher):
            os.startfile(launcher)
        else:
            os.startfile(target_file)

    except Exception as e:
        # Write error and open a simple message
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Update Failed", f"Could not update:\n{e}\n\nPlease update manually from GitHub.")
        root.destroy()

if __name__ == "__main__":
    main()
