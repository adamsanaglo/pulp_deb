# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## [1.0.1](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/overview/1.0.1) - 2023-04-12


### Bug fixes

- Temporarily roll back minimum version check to accommodate server error. [#17684846](https://msazure.visualstudio.com/One/_workitems/edit/17684846)


## [1.0.0](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/overview/1.0.0) - 2023-04-11


### Breaking changes

- Results are now always a comma-separated list when using the `--id-only` option. These results can
  be passed to other commands such as `pmc repo package update`. [#17749140](https://msazure.visualstudio.com/One/_workitems/edit/17749140)


### Features

- Added the support for uploading and publishing Debian source packages.
  Introduced a `--source-artifact` parameter to the package upload command, which accepts a list
  of files, folders or URLs for the source package artifact. [#13082573](https://msazure.visualstudio.com/One/_workitems/edit/13082573)
- Added a feature to warn users if their CLI version is older than the recommended minimum version. [#17684846](https://msazure.visualstudio.com/One/_workitems/edit/17684846)
- Auto-increment the client correlation_id with each request [#17798770](https://msazure.visualstudio.com/One/_workitems/edit/17798770)


### Bug fixes

- Tolerate CR/LF line endings in pem-format certificate. [#17729715](https://msazure.visualstudio.com/One/_workitems/edit/17729715)
- Fixed outdated references to using semicolons to separate lists of values. [#17749074](https://msazure.visualstudio.com/One/_workitems/edit/17749074)


## [0.4.0](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/overview/0.4.0) - 2023-03-23


### Features

- Added support for reading configuration from environment variables. This includes a
  `PMC_CLI_MSAL_CERT` var that can be set to the msal cert string so users don't have to save their
  MSAL cert to the filesystem. [#17627301](https://msazure.visualstudio.com/One/_workitems/edit/17627301)
- Improved the error that gets displayed to users when an invalid MSAL cert is used. [#17628171](https://msazure.visualstudio.com/One/_workitems/edit/17628171)


## [0.3.1](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/overview/0.3.1) - 2023-03-14


### Bug fixes

- Fixed a bug where a PEM file with more than one intermediate CA would cause a cli crash. [#17544504](https://msazure.visualstudio.com/One/_workitems/edit/17544504)


## [0.3.0](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/overview/0.3.0) - 2023-03-13


### Breaking changes

- Changed the list separator from ";" to "," for options that accept lists as the former requires
  escaping in bash. [#17503174](https://msazure.visualstudio.com/One/_workitems/edit/17503174)


## [0.2.0](https://msazure.visualstudio.com/One/_artifacts/feed/Compute-PMC/PyPI/pmc-cli/overview/0.2.0) - 2023-03-07


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
