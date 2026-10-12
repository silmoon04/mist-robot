# Live thinking faces

The live expression policy now rotates existing faces 20, 40 and 39 during a
sustained thinking/checking state. A brief wait still keeps the available face.
Each thinking face stays for 3.6 seconds plus its entrance duration, and the
sequence continues across turns without adjacent repeats.

Explicit model, manual and system choices keep priority. Audible speech clears
the thinking rotation. Repeated state events do not restart it. The focused
thinking tests, expression-policy tests, actual app-handler tests and activity
state tests passed after the change.

The new 24-drawing activity artwork is presented in the v8 preview. This live
policy change uses the existing face art and does not replace the live activity
asset loader or voice backend.
