# Get the version from the command line arguments
ard_cli_version= $1
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh -s $ard_cli_version
sudo mv bin/arduino-cli /usr/local/bin/arduino-cli
arduino-cli version