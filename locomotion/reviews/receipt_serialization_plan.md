# Receipt serialization correction

The frozen `acceptance.score` returns some NumPy boolean checks. Its aggregate `passed` is already a Python boolean. Training serializes through `json_value`, so this defect does not change training, reward, eligibility, checkpoint selection or learned weights. The direct sensitivity CLI attempts plain JSON serialization and can fail when writing an otherwise completed receipt. The final matrix wrapper had the same boundary defect.

The wrapper repair converts NumPy scalars with `.item()` and arrays with `.tolist()`, rejects unsupported objects, and retains `allow_nan=False`. This preserves scalar values and acceptance results. The wrapper is independently fingerprinted and lies outside the training envelope. Its repair does not require rebinding the training artifacts. The wrapper's `core` suite covers cardinal commands and stop; yaw, combined and transient cases require `all`, so a core result cannot establish all-command coverage.

No frozen core source was edited during this work. The source fingerprint remains `8793d43d546c95c6fd695860305f96a0627e49be9ec81779e313b63d1b92e8c1`.

After all training processes finish, the narrow proposed core repair adds a NumPy-scalar JSON default handler only to the sensitivity receipt write. `scripts/migrate_receipt_only.py` prints the exact permitted patch when run without arguments. It does not apply the patch. The archived original sensitivity source is pinned by hash inside the tool.

If that exact repair is applied, existing checkpoint sidecars correctly become incompatible with current source. The migration utility offers an explicit diagnostic copy rather than overwriting that history:

1. Verify original checkpoint, replay and envelope hashes. Require the exact old sensitivity source and exact reviewed replacement bytes.
2. Require the same complete source inventory, with only the sensitivity serializer hash changed. Physical dynamics, sensor/control code, training code, observation contract, lock, cases and experiment parameters must be identical.
3. Copy the checkpoint and SAC replay without deserializing or rewriting them. Archive the original sidecar under `original_metadata/provenance.json` and a full byte snapshot of its source/CAD inputs; all copied hashes are checked.
4. Write a new envelope and audit showing the old/new identities, exact patch and unchanged weights/replay. Mark the new sidecar `diagnostic_revalidation_required_receipt_only_migration`. Set its continuation seed to null, so the trainer refuses ordinary continuation through this diagnostic copy. The original artifact retains its seed and remains intact.
5. Recheck current sources and original artifacts, and verify the copied checkpoint. Re-run meaningful diagnostic acceptance before interpreting new receipts. A failed migration retains a failure marker and removes any new usable sidecar.

Usage after source repair and training completion:

```sh
python locomotion/scripts/migrate_receipt_only.py --checkpoint path/to/final.zip --output path/to/new-diagnostic-copy
```

The nine targeted migration tests and two final-matrix receipt tests passed. They check serializer value preservation and rejection of unknown/nonfinite values, byte-identical migration and full old-source preservation, refusal to overwrite, and rejection of changed weights, replay, physics, envelope or any extra source edit. They also verify that an input named `original.zip` cannot collide with the archived sidecar and that a late verification failure removes the exact generated sidecar while preserving the archive. This utility is deliberately excluded from the training envelope and cannot waive broader compatibility failures. No actual checkpoint migration has been performed yet.
