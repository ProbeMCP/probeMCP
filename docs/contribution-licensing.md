# Contribution Licensing and Third-Party Artifacts

ProbeMCP uses Apache-2.0. Contributions are accepted under the same inbound
license unless the project later adopts a stronger contributor agreement.

## Allowed Artifacts

- source code contributed under Apache-2.0-compatible terms
- sanitized GDB/MI transcripts created by contributors
- minimal SVD fixtures authored for tests
- documentation and examples under the repository license

## Restricted Artifacts

- proprietary vendor SVD files unless their license permits redistribution
- proprietary ELF/firmware binaries
- private hardware logs with serial numbers, secrets, or customer data
- debugger configs copied from SDKs with unclear redistribution rights

When in doubt, include a generator, a minimal synthetic fixture, or a link to
the vendor source instead of committing the third-party artifact.
