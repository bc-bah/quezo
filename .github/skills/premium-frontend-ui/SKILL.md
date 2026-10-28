---
name: premium-frontend-ui
description: 'Design and implement polished, immersive frontend experiences: premium landing pages, interactive portfolios, high-fidelity components, motion design, and visual refreshes. Use when a request calls for distinctive art direction or exceptional UI polish.'
---

# Premium Frontend UI

Create intentional, memorable interfaces without sacrificing usability, accessibility, performance, or the product's existing behavior. Treat the visual techniques below as a design toolkit, not a checklist: choose only what supports the user's request and the product context.

## Workflow

1. **Understand the surface.** Inspect the relevant page, shared layout, styles, tests, and package manifest before changing code. Identify the framework, rendering boundaries, existing design patterns, and the behavior that must remain unchanged.
2. **Set a clear art direction.** Choose a coherent visual concept suited to the product and audience: editorial, organic, technical, cinematic, or another specific direction. Define a restrained palette, type hierarchy, spacing rhythm, and surface treatment. Do not mix styles just to add effects.
3. **Design the complete experience.** Consider loading, success, empty, error, and narrow-screen states where applicable. Keep content hierarchy and primary actions immediately understandable.
4. **Build with the existing stack.** Reuse the project's components, tokens, fonts, and styling conventions. Do not add a dependency, remote asset, font service, or animation library unless the request needs it and the project can support it.
5. **Add motion selectively.** Use motion to clarify hierarchy, state, or spatial relationships. Prefer CSS transitions and animations for simple effects; use an existing animation library or propose one only when timeline complexity warrants it.
6. **Verify the result.** Run the smallest relevant checks. Review responsive layouts, keyboard operation, reduced-motion behavior, and states affected by the change. Preserve existing behavior and report any validation limitations.

## Visual craft

- Establish hierarchy through typography, composition, spacing, contrast, and a consistent grid before adding decoration.
- Use fluid sizing such as `clamp()` where it improves responsive type or layout. Keep body text readable and preserve user zoom.
- Prefer project-provided or locally bundled fonts. Do not introduce unlicensed typefaces or make the interface depend on a third-party font request.
- Use imagery, gradients, blur, translucency, and texture only when they strengthen the concept and maintain text contrast. Noise overlays and glass effects are optional, not defaults.
- Give buttons, links, and other controls clear resting, hover, focus-visible, active, and disabled states. Do not rely on color alone to communicate meaning.
- Treat full-viewport heroes, oversized headlines, pinned sections, parallax, and horizontal galleries as situational compositions, not required page structure.

## Interaction and motion

- Keep native document scrolling unless a task has a compelling, accessible reason to do otherwise. Do not add smooth-scroll hijacking by default.
- Do not hide primary navigation solely based on scroll direction. If a design explicitly calls for collapsing navigation, ensure it remains discoverable, keyboard reachable, and stable while focus is inside it.
- Do not add a preloader to mask ordinary page rendering. If an experience genuinely needs asset initialization, show a meaningful, accessible loading state, avoid a blank screen, and provide a failure or fallback path.
- Use entrance sequences, scroll-linked effects, pinned content, and parallax sparingly. Content must remain available without completing an animation, and scrolling must not trap or disorient users.
- Custom cursors and magnetic controls are opt-in enhancements only. Keep the native pointer and control semantics; never make cursor tracking necessary to discover or operate an action. Restrict pointer-specific effects to `(hover: hover) and (pointer: fine)`.
- Prefer animating `transform` and `opacity` when practical. Avoid repeatedly animating layout- or paint-intensive properties. Apply `will-change` only to measured, short-lived needs and remove it when no longer needed.
- Honor `prefers-reduced-motion: reduce`: remove or substantially simplify nonessential movement, parallax, and scroll effects. Do not hide content or necessary state changes behind animation.
- Avoid continuous animation, excessive layers, large blocking assets, and decorative effects that degrade performance on touch devices or low-powered hardware.

## Accessibility and responsive behavior

- Preserve semantic HTML, heading order, labels, accessible names, landmarks, and existing keyboard workflows. Prefer native controls over recreating them.
- Ensure all functionality is keyboard operable with a visible focus indicator. Manage focus intentionally for menus, dialogs, and other overlays.
- Check contrast and text legibility across all states, including overlays and imagery. Do not convey status by color, hover, or animation alone.
- Support touch and narrow viewports without hover-dependent interactions, clipped content, or unnecessary horizontal scrolling. Respect safe areas where relevant.
- Keep server/client boundaries intact in Next.js. Add client-side code only for interactions that require it, and do not move server-only data access into the browser.

## Quezo implementation notes

- The web app is Next.js with React and TypeScript. Follow existing App Router, CSS, component, and test patterns.
- The frontend currently has no motion-library dependency. Do not add GSAP, Motion, Lenis, SplitType, or React Three Fiber as a default. Use them only when the requested experience justifies the dependency and obtain user direction when it materially expands scope.
- Preserve the current application flows and accessibility cues, including the skip link and visible focus styles. A visual refresh must not change authentication, authoring, learner, or result behavior unless explicitly requested.
- Keep changes within the requested surface; do not turn an isolated component request into a broad redesign.
