arduino-extlib
==============

The ``arduino-extlib.py`` is a Python utility designed to manage external library submodules in Arduino library projects. It provides a flexible way to integrate external dependencies while supporting both development (symlink) and distribution (copy) workflows.

Overview
--------

This tool addresses the common challenge of integrating external C/C++ libraries into Arduino projects. It allows developers to:

- Work with live submodule updates during development using symbolic links
- Create stable copies for distribution and release builds
- Verify that copied files match their source submodule versions
- Maintain version control and integrity of external dependencies

The tool operates based on a ``.extlib.yml`` configuration file that defines how external libraries should be integrated into your Arduino project.

Motivation
----------

Arduino libraries often depend on external C/C++ libraries that are maintained as separate repositories. Managing these dependencies presents several challenges:

**Development Workflow**
   During active development, you want changes in external libraries to be immediately reflected in your project. Traditional copying approaches require manual synchronization.

**Distribution Workflow**
   For releases and distribution, you need stable, versioned copies of external code that won't change unexpectedly. Symbolic links are not suitable for distribution packages.

**Version Control**
   You need to track which exact version of each external library is being used, including detecting uncommitted changes.

**File Management**
   Different projects may need different subsets of files from external libraries, and the destination structure may differ from the source.

The ``arduino-extlib.py`` tool solves these challenges by providing:

- **Dual-mode operation**: Seamless switching between symlink (development) and copy (distribution) modes
- **Automatic version tracking**: Git tags and commit hashes are automatically recorded
- **Flexible file mapping**: Configure exactly which files go where
- **Integrity verification**: Ensure copied files haven't been modified locally
- **Dirty state detection**: Detect uncommitted changes in submodules

Installation and Setup
----------------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.6 or higher
- Git command line tools
- PyYAML library

Install PyYAML if not already available:

.. code-block:: bash

   pip install PyYAML

Usage
-----

The tool provides three main commands:

Command Line Interface
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python arduino-extlib.py [OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options
~~~~~~~~~~~~~~

.. option:: -r, --root-path PATH

   Path to the Arduino library root directory. Default is the current directory.

.. option:: -e, --extlib-yml PATH

   Path to the .extlib.yml configuration file. Default is ``<root-path>/.extlib.yml``.

.. option:: -s, --submodule NAME

   Name of the external library submodule to process. If not provided, all submodules will be processed.

.. option:: -v, --version

   Show version information.

.. option:: -h, --help

   Show help message.

Commands
~~~~~~~~

mode
""""

Set the operation mode for external libraries.

.. code-block:: bash

   python arduino-extlib.py mode [OPTIONS] {symlink|copy}

**Arguments:**

- ``symlink``: Create symbolic links to submodule files (development mode)
- ``copy``: Copy files from submodules (distribution mode)

**Examples:**

.. code-block:: bash

   # Set all submodules to symlink mode
   python arduino-extlib.py mode symlink
   
   # Set specific submodule to copy mode
   python arduino-extlib.py -s extras/xensiv-pas-gas-sensor mode copy
   
   # Use custom paths
   python arduino-extlib.py -r /path/to/project -e custom-extlib.yml mode symlink

verify
""""""

Verify that copied files match their source submodule versions.

.. code-block:: bash

   python arduino-extlib.py verify [OPTIONS]

This command:

- Checks if the recorded git tag and hash match the current submodule state
- Compares copied files with their source files
- Reports any discrepancies or modifications
- Exits with error code 1 if verification fails

**Examples:**

.. code-block:: bash

   # Verify all submodules
   python arduino-extlib.py verify
   
   # Verify specific submodule
   python arduino-extlib.py -s extras/xensiv-pas-gas-sensor verify

Configuration File Format
--------------------------

The ``.extlib.yml`` file defines how external libraries are integrated. It uses YAML format and supports both single library entries and lists of multiple libraries.

Schema Specification
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Single library configuration
   - repo: string              # Required: Path to submodule (relative to root)
     tag: string               # Git tag (auto-updated in copy mode)
     head: string              # Git commit hash (auto-updated in copy mode)
     mode: string              # Current mode: "symlink" or "copy"
     files:                    # File mapping configuration
       dest: string            # Required: Destination path (relative to root)
       src: string|list        # Required: Source files/directories

   # Multiple libraries
   - repo: extras/lib1
     # ... configuration for lib1 ...
   - repo: extras/lib2
     # ... configuration for lib2 ...

Field Descriptions
~~~~~~~~~~~~~~~~~~

**repo** (required)
   Path to the external library submodule, relative to the project root directory.
   
   Example: ``extras/xensiv-pas-gas-sensor``

**tag** (auto-managed)
   Git tag of the external library submodule. This field is automatically updated when the mode is set to ``copy``. Set to ``"unset"`` in symlink mode.
   
   Example: ``v1.2.3`` or ``v1.0.0-dirty`` (if uncommitted changes exist)

**head** (auto-managed)
   Git commit hash of the external library submodule. Automatically updated in copy mode with the full commit hash, potentially suffixed with ``-dirty`` if there are uncommitted changes.
   
   Example: ``fa3b2c1d4e5f67890123456789abcdef12345678`` or ``fa3b2c1d4e5f67890123456789abcdef12345678-dirty``

**mode** (auto-managed)
   Current operation mode. Automatically set by the tool:
   
   - ``symlink``: Files are symbolically linked
   - ``copy``: Files are copied
   - ``pre-symlink`` / ``pre-copy``: Intermediate states during mode transitions

**files** (required)
   Defines the file mapping from submodule to destination. Can be a single mapping or a list of mappings.

   **dest** (required)
      Destination directory path, relative to the project root where files will be placed.
      
      Example: ``src/core-c``

   **src** (required)
      Source files or directories within the submodule. Can be:
      
      - A single string: ``src``
      - A list of strings: ``[include, src]``
      - Wildcard patterns: ``*.h`` (expanded using glob)

Example Configurations
~~~~~~~~~~~~~~~~~~~~~~

**Basic Single Library**

.. code-block:: yaml

   - repo: extras/xensiv-pas-gas-sensor
     tag: v1.2.3
     head: fa3b2c1d4e5f67890123456789abcdef12345678
     files:
       dest: src/core
       src: src
     mode: copy

**Multiple Files from Same Library**

.. code-block:: yaml

   - repo: extras/external-lib
     tag: v2.0.1
     head: 1234567890abcdef1234567890abcdef12345678
     files:
       - dest: src/headers
         src: include
       - dest: src/implementation  
         src: src
     mode: copy

**Multiple Source Files**

.. code-block:: yaml

   - repo: extras/multi-component-lib
     tag: v3.1.0
     head: abcdef1234567890abcdef1234567890abcdef12
     files:
       dest: src/external
       src: 
         - core
         - utils
         - drivers
     mode: copy

**Development Mode (Symlink)**

.. code-block:: yaml

   - repo: extras/active-development-lib
     tag: unset
     head: unset
     files:
       dest: src/dev-lib
       src: src
     mode: symlink

**Multiple Libraries**

.. code-block:: yaml

   - repo: extras/sensor-lib
     tag: v1.5.2
     head: 11111111222222223333333344444444aaaaaaaa
     files:
       dest: src/sensors
       src: src
     mode: copy

   - repo: extras/communication-lib
     tag: v2.1.0
     head: bbbbbbbb5555555566666666777777778888888
     files:
       dest: src/comms
       src: [include, src]
     mode: copy

   - repo: extras/utils-lib
     tag: unset
     head: unset
     files:
       dest: src/utils
       src: utilities
     mode: symlink

Workflow Examples
-----------------

Development Workflow
~~~~~~~~~~~~~~~~~~~~

1. **Initial Setup**: Create your ``.extlib.yml`` configuration
2. **Development Mode**: Set libraries to symlink mode for active development
3. **Testing**: Work with live updates from submodules
4. **Pre-release**: Switch to copy mode and verify integrity
5. **Release**: Distribute with stable copied files

.. code-block:: bash

   # Start development with symlinks
   python arduino-extlib.py mode symlink
   
   # Later, prepare for release
   python arduino-extlib.py mode copy
   
   # After committing all changes. 
   # Verify everything matches 
   python arduino-extlib.py verify

Version Management
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check current status
   cat .extlib.yml
   
   # Update submodule and switch to copy mode
   cd extras/my-submodule
   git pull origin main
   cd ../..
   python arduino-extlib.py mode copy
   
   # This automatically updates tag and head in .extlib.yml

Error Handling
--------------

The tool provides comprehensive error handling and logging:

**Common Error Scenarios:**

- **Missing submodule**: Submodule path doesn't exist
- **Git errors**: Unable to read git information from submodule
- **File conflicts**: Destination files already exist and are not links/copies
- **Permission errors**: Insufficient permissions to create symlinks or copy files
- **Verification failures**: Copied files don't match source or have been modified

**Exit Codes:**

- ``0``: Success
- ``1``: Error occurred (verification failure, missing files, etc.)

Troubleshooting
---------------

**Permission Issues on Windows**
   Creating symbolic links on Windows may require administrator privileges. Run the command prompt as administrator or use copy mode instead.

**Submodule Not Found**
   Ensure the submodule path in ``.extlib.yml`` is correct and the submodule has been initialized:
   
   .. code-block:: bash
   
      git submodule update --init --recursive

**Verification Failures**
   If verification fails, check:
   
   - Whether files have been manually modified in the destination
   - If the submodule has uncommitted changes
   - Whether the recorded tag/hash matches the actual submodule state

**File Conflicts**
   Before switching modes, the tool removes existing destination paths. Ensure you don't have important files in destination directories that aren't managed by this tool.

