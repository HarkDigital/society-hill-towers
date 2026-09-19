# Philly3D design and product review

Reviewed September 18, 2026. This pass focuses on the interface, first visit, navigation, and accessibility, with suggestions for the 3D experience and maintainability. The changes are in the local checkout and rebuilt HTML; production has not been deployed.

## Overall assessment

The city itself is the product's strongest asset. Measured buildings, terrain, the solar clock, and live transit make this much more interesting than a conventional map. The interface had accumulated controls faster than it had developed a clear hierarchy: six unlabelled icons, small uppercase text, destinations hidden inside Layers, and a time panel containing several unrelated facts in one line.

The best direction is a restrained city atlas: charcoal surfaces, warm gold accents, readable typography, and enough open space for the city to remain the focus. This pass keeps the existing City Hall mark, Montserrat font, top navigation, default layers, and single-file architecture.

## Changes implemented

- **Welcome:** larger, calmer title, shorter introduction, a clear entry button, and an accessible progress bar driven by downloaded data and completed build steps. Progress describes assembly completion, not an estimate of time remaining.
- **Navigation:** a unified floating dock with visible Explore, Layers, and Sun & sky labels on desktop. A small brand signature, north indicator, and neighborhood/time readout help orient the visitor. Compact layouts keep accessible names and icon controls.
- **Explore:** the existing eight viewpoints now have a prominent home beside search, with short descriptions. Choosing one closes the panel and uses the existing camera glide. Clearing a query restores the suggestions.
- **Layers:** more consistent row spacing, clear on/off switches, readable counts, and a dedicated close button. All fourteen layer flags and shortcuts are preserved.
- **Sun & sky:** a prominent clock, separately labelled sunrise, sunset, weather, air-quality, moon, and skyline-light information, and selected states for time presets and the live clock.
- **Share, guide, About, and information cards:** consistent panel geometry, spacing, borders, button styles, and typography. Credits remain accessible through the guide.
- **Accessibility:** native buttons for all search result types; labelled controls; visible focus states; hidden guide slides removed from the accessibility tree; Credits included in the guide's keyboard focus loop; the welcome screen made inert after entry, and background controls inert before entry. Reduced-motion preferences are respected.
- **Share correctness:** the card now refreshes during the automatic camera orbit as well as manual flight. Its pose readout and URL previously froze during the orbit.
- **Search correctness:** editing a query or switching away from search invalidates an outstanding lookup so an old response cannot unexpectedly move the camera after the user has moved on.
- **Guide accuracy:** corrected references to the old bottom toolbar, relocated viewpoints, game-day banners, and the expanded tree coverage.

## Suggested next work, in order

| Priority | Addition or improvement | Why it matters | Suggested scope |
| --- | --- | --- | --- |
| 1 | Saved viewpoints | Users can find a view worth returning to but currently need to save its URL themselves. | Store named views locally using the existing view-state serialization. Offer rename, delete, and share. No account required. |
| 2 | Explicit live-feed status | An empty feed, a disabled layer, and an unavailable feed should look different. Counts alone do not explain the distinction. | Add Live, Updated, Unavailable, or No activity status per feed, based on the actual last successful response and that feed's polling interval. |
| 3 | Curated journeys | First-time visitors may not know where to fly or what to look for. | Short routes such as Historic Philadelphia, Along the Rivers, and Architecture after Dark, with a short description at each stop. Reuse the existing viewpoint and glide code. |
| 4 | Photo mode | The changing light and skyline are an obvious reason to share the app. | Hide the interface, pause camera movement, provide framing guides and named compositions, and keep the existing image export. Offer golden-hour and night presets without replacing the real-time default. |
| 5 | Quieter, more informative map markers | Many transit and event markers can compete with the architecture. | Review marker density at the same camera pose, distance, and time. Prioritize selected or nearby items and expose optional decluttering without changing the default layer set casually. |
| 6 | Destination previews | The new list is easier to discover, but pictures would make unfamiliar places easier to choose. | Small thumbnails captured from the actual model at fixed poses. Budget their compressed size before embedding them in the single-file page. |
| 7 | Device performance and scene polish | Smooth movement is part of the visual experience. The built page is approximately 27.43 MB before transfer compression, and the scene is substantial. | Profile on real phones. Prioritize geometry and label cost before adding rendering effects. Compare material, shadow, atmospheric-depth, and distant-detail changes at fixed day and night poses. |

For the 3D art direction, start with consistent facade contrast and distant-detail readability, then evaluate subtle contact shading and sky/ground separation. These are proposals, not verified defects. The existing renderer, geometry, shaders, weather, and city data were not retuned in this interface pass; those changes deserve their own reproducible scene comparisons.

## Maintainability

`app.js` is roughly 1.13 MB and combines rendering, feeds, controls, and UI. Gradually separate source files by responsibility while having the Python build concatenate them into the same self-contained output. Start with UI and guide code, then feeds; avoid rewriting the renderer or introducing a framework just to organize the files.

The stylesheet also contains several generations of rules. The new visual system is grouped at its end to make this design pass reviewable. Once the direction is accepted, consolidate superseded rules into the original sections. Documentation should be reconciled too: the older handoff still references GitHub Pages deployment and a 25 MB guard, while the current build uses a 75 MB guard and the current project notes identify the VPS as production.

## Validation and limits

- Built the real single-file application with all required data and existing build guards.
- JavaScript syntax check passed.
- Existing Python suite: 103 tests, with one expected failure. Pre-existing resource warnings in the lighting tests remain.
- Documentation/input coverage check passed.
- Inspected the rendered welcome, Explore, Layers, guide, time, and share interfaces in the local browser.
- Exercised a destination glide, local City Hall search, Tab navigation to its results, clearing search, panel switching, and time presets.
- Checked layouts at the normal desktop viewport, 844 × 390, and 390 × 844. These are browser viewport checks, not a physical iPhone/Safari or touch-device certification.
- The design adds approximately 24 KB to the existing 27.4 MB HTML, with no new dependencies, fonts, image downloads, or asset requests.

This is a focused design and usability review, not an exhaustive security, data-accuracy, or performance audit. Live feeds still depend on their upstream services and the production relay endpoints.

## Follow-up: model and lighting

The stadium and skyline work is implemented in the local build. See [MODEL-REVIEW.md](MODEL-REVIEW.md) for the architectural changes, sources, approximations, and validation. Explore now contains twelve destinations, including direct views of all three South Philadelphia venues and Center City.
