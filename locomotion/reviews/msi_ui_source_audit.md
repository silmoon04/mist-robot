# MSI UI milestone source and receipt audit

Read-only checks on 12 October 2026 found no source or receipt mismatch in the audited evidence. The Windows review checkout and WSL runtime checkout retain all 55 original source/CAD bytes with inventory identity `8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1`. The WSL check also called the unchanged `provenance.source_hashes()` and verified its exact inventory against `handoff/frozen_sources.json`.

All 95 files tracked under `locomotion/runs/` at prior commit `116b2aaa` remain byte-identical in both checkouts. The seven earlier helpers referenced by the new support receipts also remain byte-identical to that commit. Windows comparisons read the original Git blobs and compared SHA-256 with current bytes. WSL lacks that commit object, so its historical comparison used exact SHA-256 equality with the independently verified Windows copies. This establishes the checked content lineage without claiming that WSL has the same Git history.

The new support receipts match the digests recorded in [the independent support-transfer review](msi_support_transfer_audit.md):

| Receipt in `runs/msi_20261012/` | SHA-256 | Recorded helper hashes checked |
| --- | --- | ---: |
| `dev_support_static_01.json` | `d2ca986b083e1d3c9e03ac8441c0546bc76b6e2bf05eba53bab4884a3f4aff10` | 11 |
| `dev_support_backward480_01.json` | `bd76c94e06c026e3eb00903a2dcbf8af0977b9efa1bce97bf6536cb98ce3c37e` | 11 |
| `dev_support_backward480_02.json` | `18b0b2ac700f308cb7b6f0b2b292f8e35c5fa314ef805e83b155744ffba2de90` | 13 |

Every recorded helper digest matches its current file in Windows and WSL; the union contains 13 helpers. Each receipt retains the exact original frozen inventory. The v2 static-evidence link points to the checked static receipt and its matching digest. No receipt or helper was rewritten by this audit.

The UI HTML files, launcher/session helpers and package-builder changes are outside the 55-file frozen training envelope. This audit does not claim those files are unchanged, nor does it substitute for their behavior tests or UI review. The unchanged-helper finding applies to the seven prior receipt-bound helpers, not to every packaging or presentation helper.

The support pilot remains failed development evidence under the independent review: nominal support feasibility improved while dynamic tracking and contact did not justify expansion. Hash agreement preserves that verdict; it does not establish continuous support robustness, a qualified walking controller, physical calibration or hardware transfer. No tests, physics, training, services or hardware operations ran for this audit. Only this new review file was written; moving continuation documents and screenshots were outside its scope.
