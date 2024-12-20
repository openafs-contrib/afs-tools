# AFS Tools

This is a collection of tools to aid in administration and debugging the
OpenAFS distributed filesystem.

## Administration

  * `afs-client-accessd` - gather access info from the audit log into a database
  * `afsdirstat` - report afs directory statistics
  * `afs-dumpster` - nightly dumps of afs volumes
  * `afsfree` - report free space on afs servers
  * `afs-get-versions` - report server versions
  * `afs-read-audit` - example sysvmq audit reader
  * `afs-vol-check` - check for volume inconsistencies
  * `afs-vol-paths` - process output of volscan
  * `afs-vos2sysid` - rebuild `/afs/usr/local/sysid` from VLDB
  * `cw_graphify.pl` - use gnuplot to graph fileserver "calls waiting for thread"
  * `snips` - `snips` monitoring plugin for AFS
  * `xstat.py` - gather server statistics (requires a patched `xstat_fs_test`)
  * `openafs-wiki-gerrits` - update the list of open gerrit changes on wiki.openafs.org

## Troubleshooting and debugging

  * `cachemiss` - report cache miss rates
  * `cachestat` - report what is cached for certain files
  * `cbread` - decode file server callback dump files
  * `ciread` - decode cache manager `CacheItems` file
  * `cisearch`- search cache manager `CacheItems` for a file
  * `dirobj` - decode afs directory objects
  * `dirtydirs` - find volumes with dirty directory objects
  * `stack-usage` - calculate stack usage from object dumps (`x86_64` only)
  * `translate_err` - translate afs and krb5 error codes
  * `viread` - decode cache manager `VolumeItems` file
  * `vixlink` - find volumes with `cross-device link` errors
  * `volnamei` - convert volume numbers to fileserver namei paths

