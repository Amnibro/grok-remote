@echo off
echo Quest AR link - plug the Quest 3 in (or adb connect over WiFi) first
adb devices
adb reverse tcp:2421 tcp:2421
adb reverse tcp:2423 tcp:2423
echo.
echo Open in the Quest browser:  http://localhost:2421/xr?key=YOUR_KEY
echo (both the hub and the motion service are reversed - AR button needs this secure context)
pause
