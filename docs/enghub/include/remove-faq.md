### Version N of my package is really broken. Can I delete it from the repo? Should I delete it?

- If the problem is exposure of a secret or something like it, where continued visibility is unacceptable, then you need to delete version N as quickly as possible.
  This is only "best effort" removal of visibility, as customers may be caching this version or customers have have already downloaded it.
  If the exposure is truly severe (e.g. sev 2 incident against your team, CELA request for immediate action) create a sev 2 incident in IcM assigned to __AzTux / PMC Repo Team__ requesting your package be purged from our edge cache.
- If the problem is just a bug, then regardless of severity, you don’t need to delete version N; you just need to supersede it as quickly as possible.
 
### Can’t I just tell my customers to roll back to version N-1?

No matter what the problem is, you must ensure your customers have an easy path past version N.
To the extent that any customer has an automated process for updating packages in their environment, the vast majority of those processes only address rolling forward to the next version.
It’s unreasonable to expect customers to “just roll back to version N-1”. You must supply a version N+1 to which they can roll forward.

There are many folks out there who clone Microsoft’s public repos for various reasons.
Many repo cloning tools don’t handle deletes, which means any customer installing from a cloned repo will continue to get version N even after you’ve deleted it.
You must supply a version N+1 for the cloners to pick up and expose to their users.
 
### What’s the fastest way to get to version N+1?

If the fix to the problem is obvious, easy to implement and test, and safe to push through your SDP-equivalent process, then it makes sense to incorporate the fix into N+1 and publish it.

If, on the other hand, there's no immediate fix, or the fix involves risk for you or your customers, then the fastest way forward is to provide a stop-gap by republishing version N-1 as version N+1.
That may be as simple as:
  - Crack open the package archive of N-1.
  - Update the package metadata to have the smallest possible version increment over version N.
  - Sign the new package.
  - Publish the new package.
