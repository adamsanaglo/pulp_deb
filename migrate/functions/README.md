# Migrate functions

These migration functions facilitate communication between the csd.apt.linux app (aka vCurrent) with
the Compute-PMC app (aka v4/vNext).

## Functions

### add_package_to_vnext

This function adds packages to vNext by calling sync in vNext. The sync is an additive sync and will
only retrieve the packages that are new.

### remove_package_from_vnext

This function removes a package from vNext after it has been removed from vCurrent.

### remove_package_from_vcurrent

This function removes a package from vCurrent once it has been removed from vNext. It is necessary
to remove packages from vCurrent so they do not get re-added to vNext.
