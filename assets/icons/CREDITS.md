# Weather icons

The condition icons in this folder (`sun/partly/cloud/fog/rain/thunder.png`) are
rasterised from **Meteocons** by Bas Milius — https://github.com/basmilius/weather-icons
Licensed under the MIT License (see `LICENSE.txt`).

Regenerate them (build-time only; not a runtime dependency) with:

    pip install cairosvg
    python tools/render_icons.py
