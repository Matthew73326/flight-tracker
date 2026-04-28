import sys
import os
import time
import urllib.request
import shutil

def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    target_file  = sys.argv[1]
    download_url = sys.argv[2]

    # Wait for main app to close
    time.sleep(3)

    try:
        # Download new file
        tmp_file = target_file + ".new"
        urllib.request.urlretrieve(download_url, tmp_file)

        # Backup old file
        backup = target_file + ".bak"
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copy2(target_file, backup)

        # Replace with new file
        os.remove(target_file)
        shutil.move(tmp_file, target_file)

        # Relaunch
        app_dir = os.path.dirname(target_file)
        launcher = os.path.join(app_dir, "Launch_FlightTracker.vbs")
        if os.path.exists(launcher):
            os.startfile(launcher)
        else:
            os.startfile(target_file)

    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Update Failed", str(e))
        root.destroy()

if __name__ == "__main__":
    main()
