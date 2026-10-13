// Visible embedded browser surfaces can throttle animation callbacks even
// while their document remains visible. A bounded timer keeps pose drawing
// responsive there; normal display callbacks still set the foreground pace.
export function scheduleFrame(callback, api = window) {
  let finished = false, animation, timer;
  const run = () => {
    if (finished) return;
    finished = true;
    api.cancelAnimationFrame(animation);
    api.clearTimeout(timer);
    callback(api.performance.now());
  };
  animation = api.requestAnimationFrame(run);
  timer = api.setTimeout(run, 33);
  return () => {
    finished = true;
    api.cancelAnimationFrame(animation);
    api.clearTimeout(timer);
  };
}
