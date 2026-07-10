@echo off
setlocal
cd /d "%~dp0.."
if not exist "desktop\node_modules\electron" (
  echo Installing desktop deps...
  pushd desktop
  call npm install
  popd
)
start "" /D "%~dp0..\desktop" cmd /c "npm start"
endlocal
