# Third-Party Notices

This document records the direct runtime dependencies and bundled scientific
work distributed with Antarctic Atlas v3.2.2. Each component remains subject to
its own license. This list does not replace the license and notice files shipped
by those components or cover every transitive library in the packaged app.

## Antarctic Atlas project code

Copyright © 2026 Omica.

The Antarctic Atlas source code is distributed under the
[MIT License](LICENSE). That license applies to the project code, not to the
third-party dependencies or bundled paper listed below.

## Direct runtime dependencies

Versions are pinned in [`requirements-desktop.txt`](requirements-desktop.txt).

| Component | Version | Purpose | Upstream license | Official project |
| --- | --- | --- | --- | --- |
| PySide6 | 6.10.3 | Qt desktop UI and embedded web view | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | [Qt for Python](https://doc.qt.io/qtforpython/) |
| pdfplumber | 0.11.10 | PDF text and page extraction | MIT | [pdfplumber](https://github.com/jsvine/pdfplumber) |
| pypdfium2 | 5.9.0 | PDFium bindings and PDF rendering runtime | BSD-3-Clause, Apache-2.0, and dependency licenses | [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) |
| pdfminer.six | 20260107 | PDF text analysis used by pdfplumber | MIT | [pdfminer.six](https://github.com/pdfminer/pdfminer.six) |
| jieba | 0.42.1 | Chinese text segmentation for local search | MIT | [jieba](https://github.com/fxsjy/jieba) |
| Requests | 2.34.2 | HTTP client for optional AI backends | Apache-2.0 | [Requests](https://requests.readthedocs.io/) |

PySide6 and its bundled Qt components are offered under the license choices
shown above; downstream use must comply with the applicable Qt terms.
pypdfium2 wheels may include PDFium and other third-party binary components,
whose bundled dependency licenses and notices also remain in force. The
packaged application also contains transitive dependencies; consult each
component's included metadata and license files for the complete terms.

## Packaging component

The application bundle is assembled with PyInstaller 6.20.0. PyInstaller is
licensed under GPL-2.0-or-later with its special bootloader exception, which
permits distributing applications built with its bootloader. See the
[PyInstaller license](https://github.com/pyinstaller/pyinstaller/blob/v6.20.0/COPYING.txt)
for the complete terms.

The drag-to-install disk image is assembled with dmgbuild 1.6.7. dmgbuild is
licensed under the MIT License and uses macOS's native disk-image tools. See
the [dmgbuild project](https://github.com/dmgbuild/dmgbuild) for its source and
license.

## Bundled scientific paper

The included 89-page PDF is not covered by the project's MIT License:

> Noble, T. L. et al. (2020). *The Sensitivity of the Antarctic Ice Sheet to a
> Changing Climate: Past, Present, and Future.* Reviews of Geophysics, 58,
> e2019RG000663. [https://doi.org/10.1029/2019RG000663](https://doi.org/10.1029/2019RG000663)

Copyright © 2020 The Authors. The paper is an open-access article under the
**Creative Commons Attribution 4.0 International License
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))**, which permits
use, distribution, and reproduction provided that the original work is
properly cited. The
[publisher's article page](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2019RG000663)
provides the authoritative article record.

The CC BY 4.0 terms apply to the paper independently of the MIT-licensed
Antarctic Atlas code. Anyone redistributing or reusing the paper must preserve
appropriate attribution and comply with the paper's license.
