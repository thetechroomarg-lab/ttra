# Classic Mobile Slack Carousel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Classic home recommendations on mobile slide as a persistent horizontal track, with the next recommendation partially visible like Slack mobile.

**Architecture:** Keep the existing recommendation batch, autoplay, color selector, cart action, analytics, and dots. Render every batch member into a track; CSS sets each slide to 88% of the viewport and JavaScript updates the track translation, active dot, and counter without rebuilding the carousel on every navigation.

**Tech Stack:** Vanilla JavaScript, CSS, FastAPI static assets, pytest.

**Spec:** User-approved design: “tipo Slack”.

## Global Constraints

- Apply only under the `max-width: 700px` Classic styles.
- Preserve desktop recommendations and all current mobile carousel controls.
- Use ASCII-only additions.

---

### Task 1: Lock the mobile carousel markup contract

**Files:**
- Modify: `tests/test_app_landing.py`
- Modify: `web/static/landing.js:1460-1550`

**Interfaces:**
- Consumes: `recomendacionesMobileLote`, `recomendacionesMobileIndice`.
- Produces: `.carrousel-recomendados-mobile-track` containing one `.carrousel-recomendados-mobile-card` per recommendation, and `actualizarCarrouselRecomendadosMobile(el)`.

- [ ] **Step 1: Write the failing test**

```python
def test_landing_define_track_mobile_de_recomendados():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    assert "carrousel-recomendados-mobile-track" in script
    assert "actualizarCarrouselRecomendadosMobile" in script
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/bin/pytest tests/test_app_landing.py::test_landing_define_track_mobile_de_recomendados -q`
Expected: FAIL because the mobile carousel has no horizontal track updater.

- [ ] **Step 3: Write minimal implementation**

```javascript
function actualizarCarrouselRecomendadosMobile(el) {
  const track = el.querySelector(".carrousel-recomendados-mobile-track");
  track.style.transform = `translateX(calc(${recomendacionesMobileIndice} * -88%))`;
}
```

Render all recommendations once in the mobile track and use this updater from dots, autoplay, and swipe navigation.

- [ ] **Step 4: Run test to verify it passes**

Run: `../../.venv/bin/pytest tests/test_app_landing.py::test_landing_define_track_mobile_de_recomendados -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_app_landing.py web/static/landing.js
git commit -m "feat: add mobile recommendation slide track"
```

### Task 2: Lock the Slack-style visual affordance

**Files:**
- Modify: `tests/test_app_landing.py`
- Modify: `web/static/classic.css:830-930`

**Interfaces:**
- Consumes: `.carrousel-recomendados-mobile-track` and `.carrousel-recomendados-mobile-card`.
- Produces: a clipped viewport, animated horizontal track, and 88% slide width with a visible next-card preview.

- [ ] **Step 1: Write the failing test**

```python
def test_classic_css_muestra_siguiente_card_mobile():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    assert ".carrousel-recomendados-mobile-track" in css
    assert "flex: 0 0 88%" in css
    assert "transform .32s ease" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/bin/pytest tests/test_app_landing.py::test_classic_css_muestra_siguiente_card_mobile -q`
Expected: FAIL because the current mobile grid holds only one full-width card.

- [ ] **Step 3: Write minimal implementation**

```css
.carrousel-recomendados-mobile-track {
  display: flex;
  gap: 12px;
  transition: transform .32s ease;
}
.carrousel-recomendados-mobile-card { flex: 0 0 88%; }
```

Keep the viewport clipped and preserve the current internal card layout.

- [ ] **Step 4: Run test to verify it passes**

Run: `../../.venv/bin/pytest tests/test_app_landing.py::test_classic_css_muestra_siguiente_card_mobile -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_app_landing.py web/static/classic.css
git commit -m "style: preview next mobile recommendation"
```

### Task 3: Verify interaction and staging route

**Files:**
- Verify: `web/static/landing.js`
- Verify: `web/static/classic.css`
- Verify: `tests/test_app_landing.py`

- [ ] **Step 1: Run the full suite**

Run: `../../.venv/bin/pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Verify mobile behavior in browser**

Run the FastAPI app, use a <=700px viewport, activate Classic home, and confirm the next card peeks on the right, dots/counter follow swipe and autoplay, and choosing a color still enables `Agregar`.

- [ ] **Step 3: Inspect deployment configuration and publish only through the repository's configured staging workflow**

Run: `git remote -v` and inspect repository deployment files or workflows.
Expected: identify an explicit staging target before pushing or deploying.
