*******************
Arduino DevOps Docs
*******************

Welcome to the **Arduino DevOps Docs**!👋

We hope you find in these pages **all the required information** to use Arduino DevOps utilities. If that is not the case, let us know in the `issue <https://github.com/Infineon/arduino-devops/issues>`_ section.

.. warning::

   This repository is a work in progress. Changes not compatible with the current version may be introduced in the future.

.. toctree::
   :maxdepth: 1
   :caption: Overview
   
   overview/motivation
   overview/content
   overview/usage
   overview/requirements

.. toctree::
   :maxdepth: 3
   :caption: Workflows
   
   compile-examples/index
   release/index

.. toctree::
   :maxdepth: 1
   :caption: Scripts
   
   scripts/arduino-ci
   scripts/arduino-packager
   scripts/pckg-install-local
   scripts/arduino-release
   scripts/arduino-cli-install


.. warning::
    
    These scripts will be unified in upcoming iteration in a single tools, and refactored
    for clarity of usage.