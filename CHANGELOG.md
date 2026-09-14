# Changelog

## [0.2.0]
### Added
- Kpm to manage apps
- Event lister for core
- Better logging

### Fixed
- Traversal bugs

### Changed
- Changed app, data config models
- Moved storage directory to kikxfs
- Changed services logics
- Removed plugins, system for now
- Removed shortlinks

## [0.2.3]
### Added
- App version checks

### Fixed
- App tasks module task buffer size limit to 10mb

### Changed
- Updated app version manifest model kikx_version or min, max
- Fs service list directory with meta

### MUI Updates
- Close app on update or uninstalling app

## [0.2.4]
### Added
- Default icon for apps

### Fixed
- App close in service route
- Some minor updates & fixes

### Changed
- Removed serve route in fs service

### MUI Updates
- Fixed app icons grid and control center icons
- Minor UI updates
- Bug fixes

## [0.3.0]
### Added
- OS Service
- KV Service
- Micro Service
- App Invoke
- Sessions info, apps info, kikx info
- Open app from app using args, query
- Explorer system app

### Fixed
- Some Bugs :)

### Changed
- Changed app.manifest.json to app.json
- Tasks app module quick & long task
- Sessions & Kpm require sudo
- Removed default icons
- Removed notify
- App models
- Removed kikxlib
- fs service routes
- updated logging

## MUI updates
- App invoking
- App Invoke Actions (wallpaper & share)
- Added video wallpaper support
- Updated ui
- Live update alerts
- UI updates

## [0.3.1]
### Fixed
- Bug Fixes

### MUI
- Option to keep app data on uninstall
- Better error information

## [0.3.2]
### Fixed
- Bug Fixes
- Added types hints, comments, code cleaning

### MUI
- Added Errors store

## [0.3.3]
### Fixed
- Bug Fixes

### Updates
- System service info updates

## [0.3.4]
### Added
- Added back navigation app option

### Fixed
- Fixed fs service client resolve path

### Updates
- Changed app tasks module kikx env variables works without shell option

## [0.3.5]
### Added
- Alert label, sticky

### Updates
- FS list files update limit can be set to < 0 for all files and thumbnail generate option

## [0.4.0]
### Added
- Tasker service
- OS service functions
- FS serve expose routes

### Updates
- App manifest model changes
- Moved every config to kikx.json file
- Removed funcx, app modules
- Moved app tasks -> tasker service
- Moved system sub service app -> kpm
- FS, KV, Micro, Proxy, System services Updates

### Fixed
- Bugs