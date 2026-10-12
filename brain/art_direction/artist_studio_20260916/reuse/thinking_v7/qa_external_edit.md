# Approved file mismatch

The QA baseline is correct. Both `qa_baseline_files.json` and root's `approved_runtime_hashes.json` recorded production `brain/ui/static/drawn_face_renderer.js` as `3a600d7b08f15bf96c5a74ee353bc01403c09b7bf744e12f9c7c62485ee60f5a`. The retained studio copy and the v6 downloadable pack still have exactly those bytes.

At the first comparison, production alone had hash `22084e744e8d11ed0484b273b8f82ee3af8c9e9e11070c6290a3e535f6d48ce3`. During the subsequent integration run the studio copy also changed to that hash. The only difference from the retained v6 pack is the container positioning guard near line 165:

```diff
- if(!container.style.position) container.style.position='relative';
+ const position=container.style.position||root.getComputedStyle?.(container)?.position;
+ if(!position||position==='static') container.style.position='relative';
```

This honors an existing position supplied through CSS rather than replacing it merely because no inline position exists. It does not alter eye geometry, audio, or animation. The separate thinking preview loads `../runtime/drawn_face_renderer.js`. Its new `22084e...` version passed independent original-face and audio regression comparisons after the change.

This is an actual production-file edit after both baselines, not a stale QA baseline. The author or originating task cannot be identified from the file bytes. QA has not reverted, copied over, or changed the production file. Keep this mismatch visible as a separate out-of-scope observation; do not describe all live files as byte-identical to their starting versions.
