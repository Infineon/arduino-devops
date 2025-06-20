Usage
=====

This repository is designed to automate DevOps processes for Arduino libraries and cores.  
Thus, we recommend starting by adding the available `reusable workflows <https://github.com/Infineon/arduino-devops/tree/main/.github/workflows>`_ to your GitHub-hosted library or core.
Before running the workflows, you'll need to configure them with some minimal settings.

Step-by-Step Enablement
-----------------------

To begin, we recommend following our Getting Started guides, which will walk you through the process of enabling the workflows:

- :ref:`Getting started with compile-examples <compile_examples_getting_started>` workflow enablement. Learn how to set up the compile-examples workflow and start automating your build processes.
- :ref:`Getting started with release <release_getting_started>` workflow enablement. Discover how to enable the release workflow and streamline your library or core releases.

Advanced Customizations and Local Usage
---------------------------------------

As you become more familiar with the workflows and scripts, you might need advanced customizations to tailor them to your needs. You can also use the scripts locally on your development machine.

Running Scripts Locally
~~~~~~~~~~~~~~~~~~~~~~~

To run the scripts locally, first ensure you have the required dependencies installed (see :ref:`Requirements <requirements>`).

Then, follow these steps:

1. Clone the repository inside your Arduino asset repository:

 .. code:: bash

    cd my-arduino-asset
    git clone https://github.com/Infineon/arduino-devops.git

2. Install the required Python dependencies:

 .. code:: bash

    pip install -r arduino-devops/requirements.txt

3. Run the scripts from your Arduino asset repository:

 .. code:: bash

    python arduino-devops/<script-name>.py [args]

.. note::
        
    You can run the scripts from anywhere in your system, but you'll need to specify the root path of your Arduino asset using the required flag (see ``--help`` option).

The scripts are designed as CLI tools, and you can run them with the ``--help`` option to see available options and usage examples. For example:

 .. code:: bash

    python arduino-devops/<script-name>.py --help