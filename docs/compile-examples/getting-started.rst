.. _compile_examples_getting_started:

Getting started
----------------

This section will guide you through the steps to setup the compile examples workflow in your repository.

Prerequisites
^^^^^^^^^^^^^^

Before you start, make sure you satisfy the following prerequisites:

- Your Arduino asset (library or core) is hosted in a GitHub repository.
- GitHub Actions is enabled in your repository. Check the `GitHub docs <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#managing-github-actions-permissions-for-your-repository>`_ to learn how to enable it.
- If your asset is an Arduino core, first you need to `configure the repository <df>`_ to be able to generate the core package with the ``core-packager.py`` tool. 

Enabling the reusable workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In your locally cloned repository, follow these steps:

0. Create a new branch, for example ``devops/compile-examples``.

    .. note::
        This is not strictly necessary, but recommended to avoid pushing changes directly to the main branch.

1. Create a new file in the ``.github/workflows`` directory, for example ``compile-examples.yml``.
2. Then add the following content to the file:

    .. code:: yaml

        name: Compile examples

        on: 
          push:
        
        jobs:
          compile-examples:
            uses: Infineon/arduino-devops/.github/workflows/compile-examples.yml@latest
        

    .. important::
        Notice the ``@latest`` at the end of the ``uses`` line. This will use the latest version of the reusable workflow.
        This is particularly useful to automatically get the latest updates in the reusable workflow. 
        Keep in mind that this may introduce breaking changes in case of major version updates.
        You can also specify a specific version, for example ``@0.4.0``, or a branch, for example ``@main``.

3. Commit your changes and push the branch to the remote.

Now, you can go to the ``Actions`` tab of your repository in GitHub and see the workflow running.

If your asset is an **Arduino core**, the workflow will compile all the available examples from the built-in libraries against each of the boards in the `board.txt <https://docs.arduino.cc/arduino-cli/platform-specification/#boardstxt>`_ file.

In the case of **Arduino libraries**, the workflow will compile all the examples available in the ``examples`` directory for the default set of boards defined
in the file: `config/ci-config-matrix-ifx-lib.yml <https://github.com/Infineon/arduino-devops/blob/main/config/ci-config-matrix-ifx-lib.yml>`_.


If you are lucky all the examples will compile successfully, and you will see a green check mark in the ``Actions`` tab of your repository.

However, it is quite likely that some combinations of boards and examples will fail. 
Some of these failures can be due to bugs or insufficient enablement. This is a good opportunity to fix in your Arduino asset. 

Although, in many cases, the reason will be the existence of incompatible combinations of boards and examples.
To handle such exceptions, jump to the next section `Matrix configuration`_.

Matrix configuration
^^^^^^^^^^^^^^^^^^^^^

A default set of automatically discovered sketches and boards is an ideal starting point. 
In practice, not all examples are going to be compatible or simply relevant to every board, and vice versa.

Let's configure a custom compilation matrix in this section.

#. In the root of your repository asset, create the YAML file ``ci-matrix-config.yml``.

   .. note::
        You can set any other name, but this is the default name used if you want to avoid specifying the configuration file 
        when calling the ``arduino-ci.py`` script.

#. Now in the file, we can overwrite the default set of boards, sketches, and add exceptions to that default board-sketch matrix. 
   The following is an example of a custom configuration file for an Arduino library asset:

    .. code:: yaml

        # Example of a custom compile matrix file for an Arduino library
 
        # The examples in the library will be compiled against the following boards defined by their Fully Qualified Board Names (FQBN).
        fqbn:
          - arduino:avr:uno
          - arduino:sam:arduino_due_x

        # We do not add a sketch list. This will be automatically discovered from the examples directory.
        # sketch:

        # The "blink" example will not be compiled against the Arduino Uno board
        # The sketch paths are relative to the root of the repository.
        exclude:
          - fqbn: arduino:avr:uno
            sketch: examples/blink/blink.ino
    
        # Only the "hello_world" example will be compiled only against the PSOC6 board
        include:
          - sketch: examples/hello_world/hello_world.ino
            fqbn: infineon:psoc6:cy8ckit_062s2_ai

        # As the PSOC6 board is a third-party board, we need to provide the additional URLs to the package index manifest
        additional_urls:
          - core: infineon:psoc6
            url:  https://github.com/Infineon/arduino-core-psoc6/releases/latest/download/package_psoc6_index.json


    Adapt this file for your own asset with your own boards and examples. 
    
    To find out of all the available configuration YAML keys and values, see the complete :ref:`YML matrix configuration file specification <yaml_config_matrix_specification>`. 

#. Commit the file and push it to the remote repository.

Now, only the desired combinations of boards and sketches will be considered in the CI workflow runs. 
And the workflow should be successfully executed! 

Additional workflow options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Github Action reusable workflow provides some additional options to add additional steps not covered in the standard workflow:

- ``ci-setup-script``
    Add a setup script that will be executed before compilation starts.
    For example:

    .. code:: yaml

        jobs:
          compile-examples:
            uses: Infineon/arduino-devops/.github/workflows/compile-examples.yml@latest
            with:
              ci-setup-script: bash scripts/ci-setup.sh

- ``core-setup-script`` (only for Arduino cores) 
    Add a setup script that will be executed before the core package is generated.
    For example:

    .. code:: yaml

        jobs:
          compile-examples:
            uses: Infineon/arduino-devops/.github/workflows/compile-examples.yml@latest
            with:
              core-setup-script: git submodule update --init extras/some-submodule-library

- ``os`` 
    A list of operating systems to compile the examples against. By default, for libraries it runs on `ubuntu-latest`, and for cores it runs on `ubuntu-latest`, `macos-latest`, and `windows-latest`.
    For example:

    .. code:: yaml

        jobs:
          compile-examples:
            uses: Infineon/arduino-devops/.github/workflows/compile-examples.yml@latest
            with:
              os: '"ubuntu-latest", "macos-latest"'