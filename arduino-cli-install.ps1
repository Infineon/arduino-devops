# The installation version is passed as argument
$arduino_cli_version = $args[0]

# Retrieve the arduino cli installation bash script
Invoke-WebRequest -Uri https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh -OutFile cli-install.sh

# Run the bash script to install the arduino cli
& bash.exe -c "sh cli-install.sh $arduino_cli_version"

# The arduino-cli installation path should be added to the system path.
# But these commands are not working within the GitHub Action workflow:
# >  Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" -Name "Path" -Value ("$(pwd)/bin;" + $env:Path) -Type String
# >  [Environment]::SetEnvironmentVariable("Path", "$(pwd)/bin;" + $env:Path, "Machine")
# So we will copy the arduino-cli.exe to the first path in the system path.
$path_in_sys_path = $env:PATH.Split(";")[0]
Copy-Item -Path "$(pwd)\bin\arduino-cli.exe" -Destination "$path_in_sys_path"