' Launch Flight Tracker with no console window at all
' Double-click this file to run silently

Dim objShell
Set objShell = CreateObject("WScript.Shell")

' Get the folder this script is in
Dim strPath
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Run pythonw (no console) with the tracker script
objShell.Run "pythonw.exe """ & strPath & "\flight_tracker.py""", 0, False
