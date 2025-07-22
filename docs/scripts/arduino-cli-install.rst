arduino-cli-install
===================

The ``arduino-cli-install`` script is a cross-platform Python utility that automates the installation of the `Arduino CLI <https://arduino.github.io/arduino-cli/>`_ tool on Linux, macOS, and Windows systems.

Arduino CLI is a command-line interface that provides all the functionality of the Arduino IDE in a scriptable and automatable way. It's particularly useful for continuous integration (CI) workflows, automated testing, and batch operations.

Features
--------

- **Cross-platform support**: Works on Linux, macOS, and Windows
- **Version-specific installation**: Install any specific version of Arduino CLI
- **Automated download and setup**: Handles downloading, extracting, and placing the executable in the system PATH
- **Error handling**: Provides clear error messages if installation fails

Usage
-----

Basic usage:

.. code:: bash

    python arduino-cli-install.py <version>

Where ``<version>`` is the specific version of Arduino CLI you want to install.

Examples
^^^^^^^^

Install a specific version:

.. code:: bash

    python arduino-cli-install.py 0.34.2

Installation process
--------------------

The script performs the following steps based on your operating system:

**Linux and macOS:**

1. Downloads the appropriate tar.gz archive from the Arduino CLI releases
2. Extracts the archive
3. Moves the executable to ``/usr/local/bin/`` (requires sudo privileges)
4. Cleans up temporary files

**Windows:**

1. Downloads the Windows zip archive using PowerShell
2. Extracts the archive
3. Moves the executable to ``C:\Windows\System32\`` (requires administrator privileges)
4. Cleans up temporary files

Prerequisites
-------------

- Python 3.x installed on your system
- Internet connection to download Arduino CLI
- Administrator/sudo privileges for system-wide installation
- On Linux/macOS: ``curl`` and ``tar`` commands available
- On Windows: PowerShell available

.. note::
    The script installs Arduino CLI system-wide, making it available from any directory in your terminal or command prompt.

.. warning::
    This script requires elevated privileges (sudo on Linux/macOS, administrator on Windows) to install Arduino CLI in system directories. Make sure you trust the source before running with elevated privileges.