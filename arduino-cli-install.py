import os
import platform
import subprocess
import sys

def install_arduino_cli(version):
    system = platform.system()

    if system == "Linux" or system == "Darwin":
        # Linux or macOS installation
        try:
            print(f"Installing arduino-cli version {version} on {system}...")
            # Choose package os name
            if system == "Linux":
                os_name = "Linux"
            elif system == "Darwin":
                os_name = "macOS"

            subprocess.run([
                "curl", "-fsSL", f"https://downloads.arduino.cc/arduino-cli/arduino-cli_{version}_{os_name}_64bit.tar.gz",
                "-o", "arduino-cli.tar.gz"
            ], check=True)
            subprocess.run(["tar", "-xzf", "arduino-cli.tar.gz"], check=True)
            subprocess.run(["sudo", "mv", "arduino-cli", "/usr/local/bin/"], check=True)
            subprocess.run(["rm", "arduino-cli.tar.gz"], check=True)
            print("arduino-cli installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error during installation: {e}")
            sys.exit(1)

    elif system == "Windows":
        # Windows installation
        try:
            print(f"Installing arduino-cli version {version} on Windows...")
            subprocess.run([
                "powershell", "-Command",
                f"Invoke-WebRequest -Uri https://downloads.arduino.cc/arduino-cli/arduino-cli_{version}_Windows_64bit.zip -OutFile arduino-cli.zip"
            ], check=True)
            subprocess.run(["powershell", "-Command", "Expand-Archive -Path arduino-cli.zip -DestinationPath ."], check=True)
            subprocess.run(["powershell", "-Command", "Move-Item -Path .\\arduino-cli.exe -Destination C:\\Windows\\System32\\"], check=True)
            subprocess.run(["powershell", "-Command", "Remove-Item -Path arduino-cli.zip"], check=True)
            print("arduino-cli installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error during installation: {e}")
            sys.exit(1)

    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python arduino-cli-install.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    install_arduino_cli(version)