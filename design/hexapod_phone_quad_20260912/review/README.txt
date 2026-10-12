The assembly viewer reads the current CAD manifest and each individual STL in `cad/output`. Its meshes and joint transforms come from this quadruped design. The bundled Three.js files are generic libraries, supplied under the included MIT license.

Keep the complete design folder together when copying or unpacking this project. The viewer needs review/vendor, cad/output, printing, manufacturing and simulation beside one another. Python 3 is sufficient to serve the viewer; the browser uses the bundled libraries.

From inside the hexapod_phone_quad_20260912 folder, start the local viewer:

```powershell
python review/serve.py
```

Open `http://127.0.0.1:8138/review/`. The server binds to the local machine and serves only this design directory. All viewer libraries and assets are local.

Drag to orbit, scroll to zoom, and use the controls to rotate the phone, inspect a bounded leg pose, hide the cover or hardware, and separate the main assemblies. Hover over a part to see its name and estimated mass. The leg control shows joint geometry; it does not simulate balance, ground contact or motor torque.

This is a controlled prototype. Fit and load tests are the next physical steps; the geometry previews do not establish strength qualification or walking performance.

The estimated assembled mass comes from assembly_manifest_as_printed.json only when its CAD hash and production-property hash match the current files. This estimate uses integrated sliced model deposition, nominal hardware, wiring and fasteners. Support and bed-adhesion material are excluded. The separate full-solid CAD reference remains visible. Parts have not been weighed. A missing or mismatched mass file displays an unavailable estimate instead of substituting an infill multiplier.

The bare phone sits upright in landscape orientation, with the 147.5 mm dimension across the cradle. Hardware meshes represent component envelopes. The dark phone screen is a display illustration, not the running brain interface. Side openings permit parked charging in either phone orientation; the long edges have button relief.

The print-first guide is printing/PRINT_FIRST.txt. Follow it to verify the real servo, metal horn, fasteners and bare phone, then perform the controlled load tests. The viewer also links to the R4 strength assessment, production slicing report and simulation comparison. Those reports describe their assumptions and remaining physical checks.

Regenerate the static previews after changing the CAD manifest or meshes:

```powershell
python review/render_preview.py
```

The static renderer additionally requires NumPy, trimesh, matplotlib and Numba. It uses actual part meshes and a depth buffer. The PNG metadata records the geometry manifest SHA-256 and the matching mass manifest SHA-256 when the sliced estimate is used. Static previews show nominal geometry, with no uniform infill scaling.
