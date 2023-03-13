# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## [0.3.0](https://msazure.visualstudio.com/One/_git/Compute-PMC?version=GTcli-0.3.0) - 2023-03-13


### Breaking changes

- Changed the list separator from ";" to "," for options that accept lists as the former requires
  escaping in bash. [#17503174](https://msazure.visualstudio.com/One/_workitems/edit/17503174)


## [0.2.0](https://msazure.visualstudio.com/One/_git/Compute-PMC?version=GTcli-0.2.0) - 2023-03-07


### Breaking changes

- The package upload command now returns a list of packages instead of a single package json. [#17315271](https://msazure.visualstudio.com/One/_workitems/edit/17315271)


### Features

- Added feature to allow users to upload multiple packages in a directory. [#17315271](https://msazure.visualstudio.com/One/_workitems/edit/17315271)
- Made package upload command return the existing package instead of failing in the case where the
  package already exists. [#17338874](https://msazure.visualstudio.com/One/_workitems/edit/17338874)
- Added tool to start generating a changelog for the CLI. [#17364320](https://msazure.visualstudio.com/One/_workitems/edit/17364320)
- Added a --quiet option that will silence all output except for warnings, errors, and the command's final result. [#17421046](https://msazure.visualstudio.com/One/_workitems/edit/17421046)


### Bug fixes

- Fixed error when running config commands. [#17397726](https://msazure.visualstudio.com/One/_workitems/edit/17397726)
- Fixed a bug where an error was incorrectly raised if a required setting was supplied as an option
  but not in the settings file. [#17428893](https://msazure.visualstudio.com/One/_workitems/edit/17428893)
- Fixed bug where parse errors and stacktrace were being emitted rather than a user friendly error
  when the settings file had invalid toml/json. [#17436981](https://msazure.visualstudio.com/One/_workitems/edit/17436981)
