arduino-packager
================

The ``arduino-packager`` script generates the package assets for Arduino cores installation.
These include:

- The archive *.zip* file with the core `required sources and metafiles <https://docs.arduino.cc/arduino-cli/platform-specification>`_. 
- The `package index manifest <https://docs.arduino.cc/arduino-cli/package_index_json-specification/>`_ file, which contains the information required by Arduino (IDE and CLI) to install the core.

It requires two files for the asset generation:

- **The core packager YAML file**
  
  This file is used by the ``arduino-packager`` in both the creation of the sources archive and the package index JSON file.
  It specifies which files need to be included in the package, and provides some of the field values of the package index JSON. 
  See section `Packager config YAML specification`_ to check all the configurable parameters. 

- **The package index manifest template**

  It includes the JSON schema that needs to be filled in for every release. Some of the keys are already pre-filled. These are constant for every release.

  The rest of the empty keys will be added by the ``arduino-packager.py`` script based on the core sources archive and the provided packager configuration YAML.
  

.. note::

    Please locate these 2 files inside the ``package`` directory of the core root path. This is the default location where the tool will look for them. 


Additionally, the script will also include all the previous releases (``platforms`` key) based on the JSON package index manifest of the previous release.
This way, the user will have access to all the existing versions of the core. 

Packager config YAML specification
----------------------------------

The YAML file supports the following keys:

    - package-name:
        The name of the core package archive.

    - include:
        List of files and directories to include in the core package
        archive.

    - index-name:
        The name of the index file without the ".json" extension.
        
    - server:
        The server information for uploading the package.
        This is open to different specifications and approaches
        for the package sources archive and package index file hosting.
        Currently, the only one supported is:

        **GitHub**

        The GitHub server should have the following keys:

            - type: 
                github
            - owner: 
                The owner of the repository (user name or organization)
            - repo: 
                The repository name

        From this information, we can generate:

            - The URL to download the package.
            - The URL of the package index JSON file.


    Optional keys:

    - exclude:
        Specific files or subdirectories to exclude from any of the
        directories in the include list.

        This exclude list will be processed after the include list.
        Therefore, if a file is in both the exclude and
        include lists, it will be excluded.

    - index-template:
        The template for the package index file.
        If not provided, the expected default value is:
        "package/<index-name>.template.json"

    Reference example YAML file:

    .. code:: yaml

        package-name: arduino-core-vendor-product
        include:
            - cores
            - libraries
            - variants
            - boards.txt
            - platform.txt
            - LICENSE.md
            - README.md
            - post_install.sh
        index-name: package_vendor_product_index
        server:
            type: github
            owner: vendor-owner
            repo: arduino-core-repo-name

 .. note:: 

    Most of the configuration data in the YAML file can have a default value and/or can be auto-discovered. 
    Future versions of the scripts will try to provide such features. 
    This will simplify the configuration as much as possible, while providing alternatives through the YAML file to override the defaults.

Package index manifest template
--------------------------------

The package index manifest template is a JSON file that contains the schema for the package index manifest.
Find the description of each field in the `Arduino CLI package index JSON specification <https://docs.arduino.cc/arduino-cli/package_index_json-specification>`_.
This is the schema with the pre-filled keys containing dummy values, which can be fixed for every release:

.. code:: json

    {
        "packages": [
            {
                "name": "company_vendor",
                "maintainer": "company_or_person_maintainer",
                "websiteURL": "url_to_the_documentation",
                "email": "contact_email@email.com",
                "platforms": [
                    {
                        "name": "<vendor> <product> Boards",
                        "architecture": "<product_architecture>",
                        "version": "",
                        "category": "Contributed",
                        "url": "",
                        "archiveFileName": "",
                        "checksum": "",
                        "size": "",
                        "help": {
                            "online": ""
                        },
                        "boards": [
                            {
                                "name": "board_a_name"
                            },
                            {
                                "name": "board_b_name"
                            }
                        ],
                        "toolsDependencies": [
                            {
                                "packager": "vendor",
                                "name": "tool_x",
                                "version": "x.y.z"
                            },
                            {
                                "packager": "company",
                                "name": "tool_a",
                                "version": "a.b.c"
                            }
                        ]
                    }
                ],
                "tools": [
                    {
                        "name": "tool_x",
                        "version": "x.y.z",
                        "systems": [
                            {
                                "host": "i686-mingw32",
                                "archiveFileName": "tool_x-x.y.z-windows.zip",
                                "url": "https://url-to-package/tool_x-x.y.z-windows.zip",
                                "checksum": "SHA-256:a96002b4aebbd89b1ace6a2da3f591d27d168fe56c1decd401bfb7a88d509260",
                                "size": "305588533"
                            },
                            {
                                "host": "x86_64-pc-linux-gnu",
                                "archiveFileName": "tool_x-x.y.z-linux.tar.gz",
                                "url": "https://url-to-package/tool_x-x.y.z-linux.tar.gz",
                                "checksum": "SHA-256:76fb2d76080c3c2966983d8d8053cb7082416b83d8f5f6caa3d69bc8287d7846",
                                "size": "212727150"
                            },
                            {
                                "host": "x86_64-apple-darwin",
                                "archiveFileName": "tool_x-x.y.z-macosx.tar.gz",
                                "url": "https://url-to-package/tool_x-x.y.z-macosx.tar.gz",
                                "checksum": "SHA-256:081417273428cd7c929e8206c823c8681e53c84ee86f8ce95f71e726702e7d75",
                                "size": "206451774"
                            }
                        ]
                    },
                    {
                        "name": "tool_a",
                        "version": "a.b.c",
                        "systems": [
                            {
                                "host": "i686-mingw32",
                                "archiveFileName": "tool_a-a.b.c-windows.zip",
                                "url": "https://url-to-package/tool_a-a.b.c-windows.zip",
                                "checksum": "SHA-256:858d7370ea29bd70f22a017976248c7df82076d401a05420b1a479ebadb1f7b2",
                                "size": "4932550"
                            },
                            {
                                "host": "x86_64-pc-linux-gnu",
                                "archiveFileName": "tool_a-a.b.c-linux.tar.gz",
                                "url": "https://url-to-package/tool_a-a.b.c-linux.tar.gz",
                                "checksum": "SHA-256:2ea4721039cbfd3859ddac87eda8c3a10284c7404a77fdcb69e9a96378ea880b",
                                "size": "4620637"
                            },
                            {
                                "host": "x86_64-apple-darwin",
                                "archiveFileName": "tool_a-a.b.c-macos.zip",
                                "url": "https://url-to-package/tool_a-a.b.c-macos.zip",
                                "checksum": "SHA-256:563dd0ad0dfabc05a8832c068e85b330d93248cc907978b29c3d3d95710dc077",
                                "size": "4901567"
                            }
                        ]
                    }
                ]
            }
        ]
    }

By default, the template will be searched in the ``package`` directory of the core root path, with the name ``<index-name>.template.json``.

You can override this by providing the ``index-template`` key in the packager YAML file.


