Introduction
============

Motivation
----------

This project was initiated to address the need for harmonizing and effectively managing DevOps processes for multiple Arduino libraries and cores developed and maintained by Infineon Technologies AG. The primary goal is to streamline and automate tasks, ensuring seamless integration and efficient management of Arduino assets.

Background
----------

The introduction of `arduino-cli <https://docs.arduino.cc/arduino-cli/>`_ has been a significant step forward in enabling programmatic handling of the Arduino toolchain and processes. This has opened up possibilities for automation via scripts and command line interfaces, making it easier to integrate tasks like build verification and testing into continuous integration servers.

Current state and objectives
----------------------------

While existing DevOps solutions, such as `compile-sketches action <https://github.com/arduino/compile-sketches>`_, provide some functionality, they do not fully meet our requirements. This project aims to fill this gap by providing a collection of utilities that solve specific DevOps use cases for managing Arduino assets. The scope of this project is intentionally open-ended, allowing it to evolve and adapt to emerging needs.

Key features and design principles
----------------------------------

The project's features are designed to be used via command line interface, making it easy to integrate with any non-GUI CI/CD framework and environment. Python is the language of choice, ensuring cross-platform compatibility. Although our primary development and testing platform is Linux, we strive to ensure platform independence.

When applicable, the features presented rely on the Arduino `platform <https://docs.arduino.cc/arduino-cli/platform-specification>`_ and `library <https://docs.arduino.cc/arduino-cli/library-specification/>`_ specifications.

The solutions provided for CI/CD are implemented through GitHub Actions `reusable workflows <https://docs.github.com/en/actions/sharing-automations/reusing-workflows>`_. This allows for easy deployment and upgrading of workflows with minimal effort. Given GitHub's popularity among Arduino developers, we have chosen to focus on GitHub Actions initially. However, we believe it should be straightforward to port the workflows to other CI/CD frameworks, such as GitLab, Jenkins, or Travis.

Community engagement and contributions
--------------------------------------

We believe these tools can be of general interest and applicability to any Arduino library or core developer. We encourage users to try them out, provide feedback, and contribute to making them more extensible and adaptable to various use cases.