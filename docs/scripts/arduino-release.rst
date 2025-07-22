arduino-release
===============

The ``arduino-release`` script is an utility for managing semantic versioning releases of Arduino assets (libraries and cores). It supports with the automation of the entire release process including version validation, CI workflow verification, git tagging, and library.properties file management.

Overview
--------

This tool provides a complete solution for releasing Arduino projects following semantic versioning (semver) best practices. It integrates with GitHub Actions to ensure all CI workflows pass before creating releases, maintains proper version consistency across different files, and automates git operations.

The script supports both **Arduino libraries** and **Arduino cores**, automatically detecting the asset type and applying the appropriate release workflow.

Features
--------

- **Semantic versioning support**: Full semver compliance with validation
- **CI/CD integration**: Verifies GitHub Actions workflows before release
- **Automatic version bumping**: Supports major, minor, and patch increments
- **library.properties management**: Automatically updates version for libraries
- **Git automation**: Handles tagging, committing, and pushing
- **Branch protection**: Ensures releases only from main/master branches
- **Release verification**: Post-release validation capabilities
- **Asset type detection**: Automatically identifies libraries vs cores

Supported asset types
---------------------

**Arduino libraries:**
    - Detected by presence of ``library.properties`` file
    - Automatically updates version field in ``library.properties``
    - Creates commit for version change before tagging

**Arduino cores:**
    - Detected by presence of ``platform.txt``, ``boards.txt``, ``cores/``, and ``variants/``
    - Only performs git tagging (no file modifications needed)

Usage
-----

The script provides three main subcommands:

.. code:: bash

    python arduino-release.py <command> [options]

Commands
^^^^^^^^

**new**
    Create a new release with version validation and CI checks.

**verify**
    Verify that all requirements are met for an existing release.

**info**
    Display information about the current repository state.

Basic examples
^^^^^^^^^^^^^^

Create a new patch release:

.. code:: bash

    python arduino-release.py new patch

Create a new minor release:

.. code:: bash

    python arduino-release.py new minor

Create a new major release:

.. code:: bash

    python arduino-release.py new major

Create a specific version release:

.. code:: bash

    python arduino-release.py new 2.1.0

Verify an existing release:

.. code:: bash

    python arduino-release.py verify

Get repository information:

.. code:: bash

    python arduino-release.py info head-tag
    python arduino-release.py info repo-name
    python arduino-release.py info asset-type

Detailed command reference
--------------------------

new
^^^

Creates a new release for the specified version.

**Syntax:**

.. code:: bash

    python arduino-release.py new <version> [options]

**Arguments:**

``version``
    The new version to create. Can be:
    
    - **Bump type**: ``major``, ``minor``, or ``patch``
    - **Specific version**: Semver format like ``1.2.3``, ``2.0.0-rc.1``

**Options:**

``--root-path <path>``
    Path to the Arduino asset root directory.
    
    **Default**: Current working directory

``--any-branch``
    Allow releases from any branch (bypasses main/master requirement).
    
    **Default**: false (releases only from main/master)

**Process flow:**

1. **Branch validation**: Ensures HEAD is on main/master branch
2. **CI verification**: Waits for and validates all GitHub Actions workflows
3. **Tag check**: Ensures HEAD is not already tagged
4. **Version calculation**: Determines new version from current tags
5. **Version validation**: Validates semver compliance and proper increment
6. **File updates**: For libraries, updates ``library.properties``
7. **Git operations**: Creates commit (if needed), tag, and pushes to remote

**Example process output:**

.. code:: text

    --> Checking if repo HEAD in the default branch... [OK]
    --> Waiting for all ci workflows completion for HEAD... [OK]
    --> Checking if HEAD is not already tagged... [OK]
    --> Previous last version: 1.2.0
    --> New bumped version: 1.3.0
    --> Updating "library.properties" file with new version... [OK]
    --> Committing changes to library.properties file... [OK]
    --> Creating new git tag... [OK]
    --> Pushing new git tag... [OK]

verify
^^^^^^

Verifies that all requirements are met for an existing release.

**Syntax:**

.. code:: bash

    python arduino-release.py verify [options]

**Validation checks:**

1. **CI workflows**: All GitHub Actions workflows must be successful
2. **Version validity**: Current tag must be valid semver increment from previous
3. **File consistency**: For libraries, ``library.properties`` version must match git tag

**Use cases:**
- Post-release validation in CI/CD pipelines
- Troubleshooting release issues
- Ensuring release integrity

info
^^^^

Displays information about the current repository state.

**Syntax:**

.. code:: bash

    python arduino-release.py info <key> [options]

**Available keys:**

``head-tag``
    Shows the git tag of the current HEAD commit.

``repo-name``
    Shows the repository name (without owner).

``asset-type``
    Shows whether the asset is a "library" or "core".

**Examples:**

.. code:: bash

    $ python arduino-release.py info head-tag
    1.2.3
    
    $ python arduino-release.py info asset-type
    library

Version management
------------------

Semantic versioning rules
^^^^^^^^^^^^^^^^^^^^^^^^^

The script enforces strict semantic versioning rules:

**Major version (X.0.0):**
- Breaking changes
- Minor and patch must be 0
- Can only increment by 1

**Minor version (0.X.0):**
- New features, backward compatible
- Patch must be 0
- Major stays the same, minor increments by 1

**Patch version (0.0.X):**
- Bug fixes, backward compatible
- Major and minor stay the same, patch increments by 1

**Pre-release support:**
- Supports release candidates: ``1.0.0-rc.1``
- Can release final version from RC: ``1.0.0-rc.1`` → ``1.0.0``

Version bump examples
^^^^^^^^^^^^^^^^^^^^^

.. code:: bash

    # From 1.2.3 to 1.2.4 (patch)
    python arduino-release.py new patch
    
    # From 1.2.3 to 1.3.0 (minor)
    python arduino-release.py new minor
    
    # From 1.2.3 to 2.0.0 (major)
    python arduino-release.py new major
    
    # Specific version
    python arduino-release.py new 1.5.0

CI/CD integration
-----------------

GitHub actions integration
^^^^^^^^^^^^^^^^^^^^^^^^^^

The script integrates deeply with GitHub Actions:

1. **Workflow Detection**: Automatically finds all workflows for the HEAD commit
2. **Status monitoring**: Waits for in-progress workflows to complete
3. **Success validation**: Ensures all workflows pass before proceeding
4. **Release workflow Skip**: Ignores workflows containing "release" in the name

**Workflow status handling:**

- ``in_progress`` / ``requested``: Waits with progress animation
- ``success``: Continues with release process
- ``failure``: Stops and exits with error

**API requirements:**

- Uses GitHub REST API (no authentication required for public repos)
- Requires internet connection
- Works with both public and private repositories

Prerequisites
-------------

**System requirements:**
- Python 3.x with required packages: ``requests``, ``semver``
- Git installed and configured
- Internet connection for GitHub API access

**Repository requirements:**
- Git repository with GitHub remote (https or ssh)
- At least one existing commit
- For libraries: valid ``library.properties`` file
- For cores: valid ``platform.txt``, ``boards.txt``, ``cores/``, ``variants/``

**Git configuration:**
- Git user.name and user.email configured (or will be set to GitHub Actions bot)
- Push permissions to the remote repository
- Proper authentication for git push operations

Error handling
--------------

The script provides comprehensive error handling with detailed messages:

**Common errors:**

``Release is allowed only from permanent branches``
    Solution: Switch to main/master branch or use ``--any-branch``

``This HEAD is already tagged``
    Solution: Make new commits or use existing tag for verification

``The new version is not a valid semver increment``
    Solution: Check version rules and use proper semver increments

``All CI workflows must be successful``
    Solution: Fix failing workflows before creating release

``Package index file not found``
    Solution: Ensure proper Arduino asset structure

**Exit codes:**
- ``0``: Success
- ``1``: Error occurred (check error message for details)

Advanced usage
--------------

**Release from feature branch:**

.. code:: bash

    # Allow releases from any branch (use with caution)
    python arduino-release.py new patch --any-branch

**Custom root directory:**

.. code:: bash

    # Release from specific directory
    python arduino-release.py new minor --root-path /path/to/arduino/project

**CI/CD pipeline integration:**

.. code:: yaml

    # GitHub Actions workflow example
    - name: Create Release
      run: |
        python arduino-release.py new patch
    
    - name: Verify Release
      run: |
        python arduino-release.py verify

**Batch operations:**

.. code:: bash

    # Get current version for other scripts
    CURRENT_VERSION=$(python arduino-release.py info head-tag)
    echo "Current version: $CURRENT_VERSION"

Best practices
--------------

1. **Always run from main/master**: Use default branch protection unless absolutely necessary
2. **Verify CI first**: Ensure all tests pass before creating releases
3. **Use semantic versioning**: Follow semver rules for version increments
4. **Test releases**: Use the verify command to validate releases
5. **Automate in CI**: Integrate into GitHub Actions for consistent releases
6. **Backup important work**: Script modifies git history and files

.. warning::
    This script performs git operations including creating commits, tags, and pushing to remote repositories. Always ensure your work is backed up and you have proper permissions before running.

.. tip::
    Use the ``--any-branch`` flag carefully in development environments. For production releases, always use the default main/master branch requirement.