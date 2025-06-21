# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], [markdownlint],
and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.0.25] - 2025-06-21

### Removed in 0.0.25

- Use of packaging module

## [0.0.24] - 2025-06-20

### Added in 0.0.24

- sz_update_project can now upgrade V3 -> V4 and V4 -> V4 projects

### Changed in 0.0.24

- Update tools from get_configs() to get_config_registry() (SDK change)
- sz_command now uses the setting and command `scroll` instead of `page`

### Fixed in 0.0.24

- sz_create_project shouldn't copy sz_update_project to a new project

## [0.0.23] - 2025-06-12

### Fixed in 0.0.23

- Support for all versions of prettytable
- Update for default flags
- Multi_source_summary renamed to entity_source_summary

### Added in 0.0.23

- New search_feature command

## [0.0.22] - 2025-06-06

### Fixed in 0.0.22

- sz_file_loader thread pool could slowly drain with certain non-critical errors

## [0.0.21] - 2025-05-14

### Fixed in 0.0.21

- Flag SZ_ENTITY_INCLUDE_RECORD_FEATURE_IDS was changed to SZ_ENTITY_INCLUDE_RECORD_FEATURES in the SDK, update in sz_explorer and sz_export
- Update help examples in sz_command

## [0.0.20] - 2025-05-06

### Added in 0.0.20

- sz_explorer addition of why search
- sz_explorer adjustments to how grids and order

### Fixed in 0.0.20

- sz_configtool documentation updates

## [0.0.19] - 2025-05-01

### Added in 0.0.19

- sz_update_project
- sz_file_loader sanity checks for user supplied paths and files
- sz_file_loader make file permissions for error, with info and shuffled files more restrictive
- sz_file_loader new arguments to specify paths for created files

### Fixed in 0.0.19

- sz_command issue with a decorator on Python 3.9

### Changed in 0.0.19

- sz_file_loader exit earlier if unrecoverable error occurs
- sz_file_loader improvements to use in Docker container

## [0.0.18] - 2025-04-22

### Added in 0.0.18

- sz_command added why_search

## [0.0.17] - 2025-04-15

### Added in 0.0.17

- Various improvements to sz_file_loader

### Changed in 0.0.17

- Modifications for new szconfig and szconfigmgr

### Fixed in 0.0.17

- Various fixes to sz_file_loader
- Data source filter not working for sz_snapshot

## [0.0.16] - 2025-03-28

### Fixed in 0.0.16

- Exception raised in sz_configtool when no config fresh database and trying to create a default config

## [0.0.15] - 2025-03-27

### Fixed in 0.0.15

- Fix SIGALRM in helpers not resetting alarm

## [0.0.14] - 2025-03-19

### Changed in 0.0.14

- Improved handling of config file reading/writing & default values

## [0.0.13] - 2025-03-06

### Added in 0.0.13

- Autocomplete for per command settings 

### Fixed in 0.0.13

- Fix error when trying to write a command history file in a container without write permissions

## [0.0.12] - 2025-02-14

### Added in 0.0.12

- New commands for V3 to V4 migrations in sz_configtool
- New sz_audit, sz_explorer and sz_snapshot
- New helper function
- Code added to sz_file_loader for testing retryable errors

## [0.0.11] - 2025-02-11

### Changed in 0.0.11

- Change G2Module.ini to sz_engine_config.ini 
- Improvements to some output

## [0.0.10] - 2025-02-08

### Fixed in 0.0.10

- With info commands in sz_command detect "" instead of "{}" when with info not requested
- Revert sz_engine_config.ini to G2Module.ini in helpers until V4 builds have made the change

## [0.0.9] - 2025-02-05

### Added in 0.0.9

- New sz_audit, sz_explorer and sz_snapshot

### Changed in 0.0.9

- Continued initial V4 work

## [0.0.8] - 2025-01-29

### Fixed in 0.0.8

- Closing ) was missing

## [0.0.7] - 2025-01-28

### Changed in 0.0.7

- Continued initial V4 work
- Align to new SDK and abstract 

## [0.0.6] - 2024-12-20

### Changed in 0.0.6

- Continued initial V4 work

## [0.0.5] - 2024-12-04

### Changed in 0.0.5

- Align to senzing-core

## [0.0.4] - 2024-12-02

### Changed in 0.0.4

- Small fix to incorrect method merge

## [0.0.3] - 2024-12-02

### Changed in 0.0.3

- Align to new SDK and abstract

### Added to 0.0.3

- Continued initial V4 work

## [0.0.2] - 2024-11-22

### Added to 0.0.2

- Continued V4 work

## [0.0.1] - 2024-11-05

### Added to 0.0.1

- Initial V4 work

[Keep a Changelog]: https://keepachangelog.com/en/1.0.0/
[markdownlint]: https://dlaa.me/markdownlint/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
