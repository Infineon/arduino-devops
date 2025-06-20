.. _requirements:

Requirements
=============

To enable the reusable workflows in your project, ensure that:

- You have a GitHub-hosted Arduino library or core.
- GitHub Actions is enabled for your repository.
- You have the necessary permissions to create and manage workflows in your repository.

The software requirements (section below) and dependencies installation is handled directly within the workflows.

Local environment requirements
-------------------------------

To run the scripts locally, please install the following software:

- `git <https://git-scm.com/>`_.
- `arduino-cli <https://docs.arduino.cc/arduino-cli/>`_ 1.2 or higher.
- `python <https://www.python.org/>`_ 3.11 or later.
- `pip <https://pip.pypa.io/en/stable/>`_ (Python package manager).

Ensure that they are properly installed and accessible in your system's PATH.

The preferred operating system to use this software is **Linux**.
Most of the scripts have been developed and tested in this environment. Specifically in Ubuntu 22.04 LTS or higher.

However, the scripts are designed to be platform-independent and should work on any operating system. Yet, we have not thoroughly tested them on Windows or macOS.

