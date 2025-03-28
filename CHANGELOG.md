# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], [markdownlint],
and this project adheres to [Semantic Versioning].

## [Unreleased]

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
