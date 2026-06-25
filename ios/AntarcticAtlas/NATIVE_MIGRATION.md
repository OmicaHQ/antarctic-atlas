# Native iOS Migration Plan

The goal is a complete native iOS Antarctic Atlas, not a WebView wrapper. The Web tab remains only as a temporary fallback while native modules catch up.

## Native Status

| Streamlit module | Native iOS status | Notes |
| --- | --- | --- |
| Research Universe Explorer | In progress | Native interactive graph with center, research-area nodes, topic nodes, search focus, and detail panel. Still needs animation parity and AI classifier. |
| Antarctic System Explorer | Partial | Native case/tool switching. Still needs visual sensor layers and synthesis builder. |
| AI Visualizer | Partial | Native story beats and reveal controls. Still needs animated mechanism canvas and export text parity. |
| Mini Research Lab | Partial | Native conceptual vulnerability model. Still needs the three full labs: glacier flow, buttressing, hydrofracture. |
| Research Compass | Partial | Native direction cards and metrics. Still needs timeline, region map, proposal builder, and downloads. |
| Read Raw Paper | In progress | Native PDFKit reader with bundled paper and keyword search. |
| AI Backends | Not native yet | Need OpenAI/DeepSeek configuration, secure key storage, and paper-grounded answer generation. |
| Web fallback | Temporary | Available only so users can access missing features while migration continues. |

## Next Native Milestones

1. Expand the Research Universe graph with richer animations, labels, and AI-backed node classification.
2. Port the three Mini Research Lab simulations with native charts/canvas.
3. Add AI backend settings using Keychain storage and source-grounded retrieval over bundled paper text.
4. Port Research Compass timeline, region map, proposal builder, and export actions.
5. Add native System Explorer visual layers for altimetry, InSAR, GRACE, GNSS, radar, and cores.
6. Remove or hide the Web fallback once native parity is strong enough.
