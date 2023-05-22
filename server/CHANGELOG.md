# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## [1.0.1](https://msazure.visualstudio.com/One/_git/Compute-PMC?version=GTserver-1.0.1) - 2023-05-22


### Features

- Added the capability to sign and verify the Account table rows. [#13082554](https://msazure.visualstudio.com/One/_workitems/edit/13082554)
- Refactor: make automatic and deduplicate the translation between Identifier to pulp_href [#20540888](https://msazure.visualstudio.com/One/_workitems/edit/20540888)


### Bug fixes

- Fixed a bug where server version was reported incorrectly at /api/ (in addition to /api/v4/). Now
  the correct version is reported solely at /api/v4/. [#19563187](https://msazure.visualstudio.com/One/_workitems/edit/19563187)
- Fixed bug where API rejected repo version ids as invalid ids. [#20702703](https://msazure.visualstudio.com/One/_workitems/edit/20702703)


## [1.0.0](https://msazure.visualstudio.com/One/_git/Compute-PMC?version=GTserver-1.0.0) - 2023-04-25


### Features

- Exposed server version at `/api/v4/` and added a server changelog. [#17506214](https://msazure.visualstudio.com/One/_workitems/edit/17506214)
- Turn the RepoOperator privilege off by default and add a switch [#18548711](https://msazure.visualstudio.com/One/_workitems/edit/18548711)
