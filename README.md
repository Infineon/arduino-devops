# Arduino DevOps

[![Check links](https://github.com/Infineon/arduino-devops/actions/workflows/check_links.yml/badge.svg)](https://github.com/Infineon/arduino-devops/actions/workflows/check_links.yml)

This repository contains a **collection of utilities** designed to ease and support the **DevOps** of **Arduino third-party cores** and **libraries**.

## Audience

You might want to give this repository a try if:

* You are a recurrent developer/maintainer 👩‍💻 of Arduino third-party cores or libraries .
* You are struggling 😓 to consistently verify ✅ that your library or core works with a wide range of Arduino boards after each code change.
* You are wasting your time by manually 🔨 creating releases and distributing your Arduino libraries or cores 📦.
* You are looking for a way to automate 🪄 the build check or/and release processes of your Arduino assets.

## Features

Currently, following processes are supported:

- **Build check.** Compile a matrix of Arduino sketches and boards easily, and check it continuously to ensure your code always works.
- **Release management.** Create new releases of your Arduino libraries and cores effortlessly, ensuring the proper distribution generation and versioning.

> [!NOTE] 
> This repository has been initially created by Infineon Technologies AG. 
While it is intended to be generic and extensible to any Arduino third-party core or library, we might have included certain feature or functionality that is specific to our use cases. Sorry 🙏.
Please, [let us know](https://github.com/Infineon/arduino-devops/issues) if you find any such feature that is not generic enough, and we will try to make it more generic.

## Getting started

You can get started by enabling the following workflows for your Arduino assets:

* [Enable *compile-examples* build check for Arduino assets](https://ifx-arduino-devops.readthedocs.io/en/latest/compile-examples/getting-started.html)
* [Enable *release* management for Arduino assets](https://ifx-arduino-devops.readthedocs.io/en/latest/release/getting-started.html)

## More information

Find the complete information in the repo [docs](https://ifx-arduino-devops.readthedocs.io/en/latest).

## Contributing

We welcome contributions to this repository! 

If you have ideas, suggestions, or improvements, please go with the following approach:

* Discuss 💬 it with us by opening an [issue](https://github.com/Infineon/arduino-devops/issues).

If modifications to the repository are required:

* [Fork](https://github.com/Infineon/arduino-devops/fork) ⤵ the repository, and work on your contribution.

* Once you are ready, you can create [pull request](https://github.com/Infineon/arduino-devops/compare) to `main`.
 
For small changes, like typos or fixes, or small improvements you can directly create the pull request without discussion 👉.

Thanks a lot for your contribution! 🙏

## License

See the [LICENSE](/LICENSE) file for more details.