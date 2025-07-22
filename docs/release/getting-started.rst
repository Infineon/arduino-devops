.. _release_getting_started:

Getting started
----------------

This section will guide you through the steps to setup the release workflow in your Arduino asset repository.

Prerequisites
^^^^^^^^^^^^^^

Before you start, make sure you satisfy the following prerequisites:

- Your Arduino asset (library or core) is hosted in a GitHub repository.
- GitHub Actions is enabled in your repository. Check the `GitHub docs <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#managing-github-actions-permissions-for-your-repository>`_ to learn how to enable it.
- You have appropriate permissions to create releases in your repository.
- If your asset is an Arduino core, ensure it's properly configured for packaging with the :doc:`arduino-packager.py <../scripts/arduino-packager>` tool.

Setting up the reusable workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In your locally cloned repository, follow these steps:

0. Create a new branch, for example ``devops/release-workflow``.

    .. note::
        This is not strictly necessary, but recommended to avoid pushing changes directly to the main branch.

1. Create a new file in the ``.github/workflows`` directory, for example ``release.yml``.

2. Add the following content to the file:

    .. code:: yaml

        name: Release

        on:
          push:
            tags: 
              - '[0-9]+.[0-9]+.[0-9]+**'
          workflow_dispatch:
            inputs:
              version:
                description: 'Release version'
                required: true
                default: ''
                type: choice
                options:
                  - patch
                  - minor
                  - major

        jobs:
          arduino-devops:
            uses: Infineon/arduino-devops/.github/workflows/release.yml@latest
            with:
              version: ${{ inputs.version }}
            secrets: inherit

    .. important::
        Notice the ``@latest`` at the end of the ``uses`` line. This will use the latest version of the reusable workflow.
        This is particularly useful to automatically get the latest updates in the reusable workflow.
        Keep in mind that this may introduce breaking changes in case of major version updates.
        You can also specify a specific version, for example ``@0.4.0``, or a branch, for example ``@main``.

3. Commit your changes and push the branch to the remote.

Additional workflow options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The GitHub Action reusable workflow provides some additional options often used in the release process:

- ``setup-script``
    Add a setup script that will be executed before building the release asset.
    For example:

    .. code:: yaml

        jobs:
          compile-examples:
            uses: Infineon/arduino-devops/.github/workflows/compile-examples.yml@latest
            with:
              setup-script: bash scripts/before-core-build-setup.sh

- ``release-ssh-key``
    This is used to provide a secret SSH key from the repository secrets to the workflow.

    For example:

    .. code:: yaml

        jobs:
          arduino-devops:
            uses: Infineon/arduino-devops/.github/workflows/release.yml@latest
            with:
              version: ${{ inputs.version }}
            secrets:
              release-ssh-key: ${{ secrets.release_wflow_key }}

    This is required for Arduino libraries when using protection rules that prevent direct 
    commit to the default branch.

    As the workflow creates new commits and pushes them to the remote repository, the new 
    commits will be rejected.
    
    To avoid this, you can use the SSH key to push the changes to the remote repository.

    Follow the steps to allow GitHub Actions to push changes directly to the default (protected) branch:
        
        1. Add a new `deploy key <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#deploy-keys>`_ to your repository with write access.
           This is available in the repository settings under "Deploy keys".
        2. `Add the private key to your repository secrets <https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/using-secrets-in-github-actions>`_ with the name ``release_wflow_key``.
        3. If you have any protection rules that prevent direct commits to the default branch, 
           `enable the bypass option <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository#granting-bypass-permissions-for-your-branch-or-tag-ruleset>`_ for deploy keys.

    More information about this approach in this `GitHub discussion <https://github.com/orgs/community/discussions/25305#discussioncomment-3247415>`_.

Creating a release
^^^^^^^^^^^^^^^^^^

Once the workflow is set up, you can create releases in different ways:

Release via GitHub actions 
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Navigate to the ``Actions`` tab of your repository in GitHub.
2. Select the ``Release`` workflow from the list.

    .. image:: ../img/release-from-ga-wflow.png
        :alt: Release workflow selection 
        :width: 60%
        :align: center

    |

3. Click ``Run workflow`` and select the default branch (usually ``main`` or ``master``) and the version increment: major, minor, or patch.
    
    .. image:: ../img/release-from-ga-select-version.png
        :alt: Release workflow select version 
        :width: 50%
        :align: center

    |

4. The workflow will automatically:

   - Validate the version format
   - Generate a changelog
   - Create a GitHub release
   - Upload release assets

5. Once the workflow completes, you will see all the release steps passing, and the new release will be available in the ``Releases`` section of your repository.

Release via GitHub release section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Navigate to the ``Releases`` section of your repository.

    .. image:: ../img/release-from-release-new-release.png
        :alt: Release from release section
        :width: 80%
        :align: center

    |

2. Click on the ``Draft a new release`` button.

    .. image:: ../img/release-from-release-tag.png
        :alt: Set new tag manually
        :width: 60%
        :align: center

    |

3. Fill in the release tag (e.g., ``0.9.0``), and click on ``Create new tag: 0.9.0``. 

    .. warning::
        You are going to set the tag manually. It should be a valid semantic version (semver) format, with a valid increment.
        
4. This will trigger the release workflow, and it will automatically:

   - Validate the version format
   - Generate a changelog
   - Create a GitHub release
   - Upload release assets

5. Once the workflow completes, the new release will be updated with the corresponding title, changelog and assets.

Release from local push
~~~~~~~~~~~~~~~~~~~~~~~

In your local repository, use the ``arduino-script.py`` to create a new release. Assuming that you are in the root path of your repository, and that the script is located in the ``arduino-devops`` directory:

  .. code:: bash

    python arduino-devops/arduino-script.py new <version>

This will automatically modify the required files, create a new tag, and push the changes to the remote repository.
The release workflow will be triggered, verifying the version and creating the release.
Check the ``release`` section of your repository to see the new release.

  .. warning::
    In case of an Arduino library, make sure that you have the necessary permissions to push modifications directly to the default (usually ``main`` or ``master``) branch of the repository.
    The script will not only create a tag, but also update the `library.properties` file with the new version and push the changes to the remote repository.
    The remote will reject the push if you do not have the right permissions. 
