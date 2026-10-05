# UI/UX Design System Specification (Design.md)

## Project Title
**AI-Powered Smart Tourist Guide Platform for Karnataka**

---

## 1. Visual Identity & Heritage Inspiration

The design language fuses **State-of-the-Art Modern AI SaaS aesthetics** (inspired by Linear, Apple, Stripe, Perplexity) with the timeless architectural majesty of **Karnataka Heritage** — specifically the intricate soapstone carvings, starry stellate plinths, and golden sanctum lanterns of 12th-century **Hoysala architecture (Belur, Halebidu, Somanathapura)**.

```
       ┌────────────────────────────────────────────────────────┐
       │                KARNATAKA HERITAGE DNA                  │
       │                                                        │
       │   ✦ Intricate Soapstone Textures & Carved Reliefs      │
       │   ✦ Stellate Geometric Star-Plinths & Polished Pillars │
       │   ✦ Radiant Temple Gold & Warm Sanctum Illumination   │
       │   ✦ Elegant Kannada Calligraphy & High-Contrast Glyphs │
       └────────────────────────────────────────────────────────┘
```

The interface conveys **warmth, scholarly authority, reverence for history, and effortless modern speed**. It strictly avoids generic bootstrap cards or raw unstyled components.

---

## 2. Color Palette & Design Tokens

### 2.1 Primary Heritage Colors (Locked)
| Token Name | Hex Code | HSL Value | Semantic Role |
|---|---|---|---|
| `--color-temple-gold` | `#D4AF37` | `hsl(46, 65%, 52%)` | Primary brand accent, focus states, active pins, voice wave glow |
| `--color-deep-brown` | `#2C1810` | `hsl(18, 47%, 12%)` | Primary light-mode text, dark-mode surfaces, header gradients |
| `--color-soapstone-grey`| `#4A4A4A` | `hsl(0, 0%, 29%)` | Secondary text, subtle borders, card outlines, structural dividers |
| `--color-ivory` | `#FDFBF7` | `hsl(40, 50%, 98%)` | Primary light-mode background, dark-mode text, pure contrast layer |

### 2.2 Secondary & Functional Palette
| Token Name | Hex Code | Semantic Role |
|---|---|---|
| `--color-sandstone-gold` | `#C2A649` | Hover states on golden buttons, badge highlights |
| `--color-muted-saffron` | `#E58A2B` | Heritage highlights, warm notifications, caution badges |
| `--color-malnad-green` | `#2E5A44` | Verified citations, grounded answers, healthy system status |
| `--color-crimson-rubric` | `#9E2A2B` | Error alerts, failed stages, destructive admin actions |
| `--color-night-slate` | `#161311` | Pure dark-mode viewport background (Belur Night) |
| `--color-night-card` | `#211C1A` | Dark-mode elevated card background |
| `--color-night-border` | `#3A322E` | Dark-mode subtle card border |

### 2.3 Glassmorphic Surfaces
- **Light Glass**: `background: rgba(253, 251, 247, 0.82); backdrop-filter: blur(16px); border: 1px solid rgba(212, 175, 55, 0.18);`
- **Dark Glass**: `background: rgba(22, 19, 17, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(212, 175, 55, 0.22);`

---

## 3. Typography & Internationalization System

### 3.1 Font Families
- **Display / English Headings**: `Outfit`, `sans-serif` (Geometric, clean, modern elegance).
- **Body & Interface (English)**: `Inter`, `sans-serif` (Optimal legibility at all densities).
- **Kannada Script (ಕನ್ನಡ)**: `Noto Sans Kannada`, `sans-serif` (Flawless conjunct rendering, zero glyph clipping, balanced line heights).
- **Code / Vector Diagnostics**: `JetBrains Mono`, `monospace`.

### 3.2 Typographic Hierarchy & Scale
| Scale Token | Font Size | Line Height | Weight | Usage |
|---|---|---|---|---|
| `text-display` | $2.5\text{rem}$ ($40\text{px}$) | $1.2$ | $700$ (Bold) | Hero landing title, Karnataka heritage headers |
| `text-h1` | $2.0\text{rem}$ ($32\text{px}$) | $1.25$ | $600$ (SemiBold) | Page titles, major destination names |
| `text-h2` | $1.5\text{rem}$ ($24\text{px}$) | $1.3$ | $600$ (SemiBold) | Section headers, modal titles, card groups |
| `text-h3` | $1.25\text{rem}$ ($20\text{px}$) | $1.4$ | $500$ (Medium) | Chat sender names, citation card headers |
| `text-body` | $1.0\text{rem}$ ($16\text{px}$) | $1.6$ | $400$ (Regular) | Primary chat bubbles, tourist descriptions |
| `text-small` | $0.875\text{rem}$ ($14\text{px}$)| $1.5$ | $400$ (Regular) | Citations, metadata, map coordinates, timestamps |
| `text-xs` | $0.75\text{rem}$ ($12\text{px}$) | $1.4$ | $500$ (Medium) | Badges, token counts, status indicators |

### 3.3 Kannada Typography Rules
- Add $+10\%$ line-height padding (`leading-relaxed`) for all Kannada text blocks to accommodate complex consonant conjuncts (*ottakshara*) without ascender/descender clipping.

---

## 4. Spacing, Radius, Shadows & Elevation

### 4.1 Spacing Scale (4px Base Grid)
`4px` (1), `8px` (2), `12px` (3), `16px` (4), `24px` (6), `32px` (8), `48px` (12), `64px` (16).

### 4.2 Border Radius
- `rounded-sm`: `4px` (Tooltips, small badges)
- `rounded-md`: `8px` (Input fields, chat pills, dropdowns)
- `rounded-lg`: `12px` (Chat message bubbles, citation cards)
- `rounded-xl`: `16px` (Panels, modal windows, map view containers)
- `rounded-full`: `9999px` (Voice mic button, language switchers, avatars)

### 4.3 Elevation & Shadows
- **Shadow Low**: `0 2px 8px -2px rgba(44, 24, 16, 0.08)`
- **Shadow Medium**: `0 8px 24px -4px rgba(44, 24, 16, 0.12)`
- **Temple Gold Glow**: `0 0 20px rgba(212, 175, 55, 0.35)` (Active voice recording, highlighted citation card)

---

## 5. Core Tourist UI Components

### 5.1 Bilingual AI Chat UX
- **Desktop 3-Panel Layout**:
  - **Left Sidebar**: Featured Destinations, Recent Conversations, Quick Tourist Prompts.
  - **Center Stage**: Main conversational thread with smooth SSE token streaming and instant voice waveform toggles.
  - **Right Panel (Collapsible)**: Interactive Citation Inspector, Source Document Excerpt, and Linked Map Locator.
- **Message Bubbles**:
  - **Tourist (User)**: Right-aligned, Deep Heritage Brown background with Ivory text in light mode; subtle Soapstone Dark surface in dark mode.
  - **Guide (Assistant)**: Left-aligned, Glassmorphic ivory card with Temple Gold accent border, grounded citation badges `[1]`, `[2]`, and audio playback controls.

```
┌────────────────────────────────────────────────────────────────────────┐
│ ✦ AI Tourist Guide                                   [🔊 Listen] [ಕನ್ನಡ]│
├────────────────────────────────────────────────────────────────────────┤
│ The Chennakeshava Temple at Belur was commissioned by King             │
│ Vishnuvardhana in 1117 CE to commemorate his victory over the Cholas  │
│ at the Battle of Talakad [1]. The temple is built using fine-grained   │
│ chloritic schist (soapstone) [2].                                      │
│                                                                        │
│ ┌─────────────────────────┐  ┌──────────────────────────────────────┐ │
│ │ 📖 [1] Belur_History.pdf │  │ 📖 [2] Hoysala_Architecture.pdf      │ │
│ │ Page 14 • Section 2.1   │  │ Page 38 • Soapstone Masonry          │ │
│ └─────────────────────────┘  └──────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│ Suggested: [Who sculpted Darpana Sundari?] [What are the temple timings?] │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Voice Assistant & Animated Waveform
- **Mic Trigger**: Circular gold floating button with subtle pulsating glow when active.
- **Waveform**: Smooth 5-bar SVG/Canvas frequency visualizer reacting to audio input levels in real-time.
- **Audio Feedback**: Instant chime upon recording start/stop with visual countdown timer.

### 5.3 Interactive Heritage Map
- **Map Surface**: Custom styled OpenStreetMap tiles with warm sepia / stone tones.
- **Pins**: Custom SVG markers shaped as Hoysala temple *kalashas* with gold glow on selection.
- **Popup Cards**: High-resolution destination thumbnail, opening hours, entry fee, audio guide trigger, and "Ask AI about this site" action.

---

## 6. Admin Command Dashboard UX

- **Design Tone**: Utilitarian, precise, high-density, dark-mode first with gold telemetry highlights.
- **Key Views**:
  1. **Telemetry Bar**: Live gauges for CPU, RAM, Disk, MySQL, ChromaDB, Ollama latency.
  2. **Knowledge Pipeline Kanban**: Real-time progress bars for `EXTRACTION` $\rightarrow$ `CHUNKING` $\rightarrow$ `EMBEDDING` $\rightarrow$ `INDEXING`.
  3. **Diagnostics Console**: Side-by-side comparison of BM25 sparse scores, dense cosine similarity, and Cross-Encoder weights.

---

## 7. Responsive Breakpoints & Accessibility (WCAG 2.1 AA)

### 7.1 Breakpoints
- **Mobile (`< 768px`)**: Single-column view with bottom navigation bar. Citation panel slides up as a bottom sheet.
- **Tablet (`768px - 1024px`)**: Two-column layout (Chat + Drawer).
- **Desktop (`> 1024px`)**: Full 3-panel layout with synchronized citation inspector.

### 7.2 Accessibility Requirements
- High contrast: Text contrast $\ge 4.5:1$ against all backgrounds.
- Complete keyboard navigability with visible `ring-2 ring-amber-500` focus outlines.
- Semantic HTML (`<main>`, `<article>`, `<aside>`, `<nav>`) and explicit ARIA live regions for streaming AI responses.
- Respect `prefers-reduced-motion` by disabling non-essential parallax or pulse animations.
