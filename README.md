# nzb-scripts

Provides a framework and some custom scripts to handle the most common cases that most users would need. The framework helps to ensure that code is not copied back and forth and provides consistency.

## NZBGET

### Framework
TODO: nzb.py

### Scripts

#### EventHelper
Helps to debug and understand what events fire when downloading an NZB. Mainly it's only useful for developers writing scripts. Please also see nzbdebug.py. If you are writing your own scripts, use the .template.py file.

#### FileMover
Moves random video files associated with a specific category that has no manager to move the files. Is smart enough to only move the largest video file.

#### HealthCheck
Checks the NZB during queueing and post-processing to determine if the NZB file needs to be requeued because not all files have propagated to your NNTP server.

#### Rejector
Provides a set of common checks and ensures that a specific action is taken if it finds an unacceptable NZB. It can perform password checking, fake detection, and disc images.
