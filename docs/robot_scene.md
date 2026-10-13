# Original robot scene

The hero now loads the same public Spline scene referenced by Vox Trace's
`appConfig.agentScene` / `HeroAgent` frontend:

https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode

Observed on 13 October 2026 in the public site JavaScript. The scene contains
its original geometry and authored interactions. ADI's wrapper forwards pointer
movement from the page to the canvas, matching the reference's page-wide
pointer tracking. It disposes the runtime on unmount, pauses outside the viewport,
and stops animation for reduced-motion preferences.

This is an externally hosted scene, not an ADI-created or independently licensed
asset. Availability depends on Spline and the publisher. The repository does not
redistribute the downloaded scene. A failed load shows a retry control rather
than substituting a different robot.

Runtime: `@splinetool/runtime`, pinned in `frontend/package.json` and lockfile.
