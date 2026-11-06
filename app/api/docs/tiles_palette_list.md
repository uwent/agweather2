# Map palettes

Every color palette available for maps, named by its colors from low to high (`BuYlRd` runs from blue through yellow to red), with its colors in that order and where they come from. Each layer in `/layers` names the palette it uses by default and the range of values it spans; use `scale` to choose another range. A palette name ending in `_r` means that palette in reverse order: dew point depression uses `BrBG_r`, which runs from blue-green through white to brown. Use `palette` on a map image, colored tiles or a legend to choose any of these palettes, reversed or not.

The palettes layers use by default were chosen to stay distinguishable to readers with the common forms of color blindness, with clear steps between neighboring colors. Others, such as the rainbow palette of AgWeather's earlier maps, are listed for readers who prefer them and are marked `colorblind_safe: false`.
