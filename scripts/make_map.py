"""World map of economic remoteness -> figures/remoteness_map.pdf (vector).

Equal Earth projection centred on the Pacific (150 deg E) so the most remote
economies sit in the middle of the page rather than split across its edges.
Small island states are drawn as dots at their representative points,
because their land area is invisible at this scale.
"""

from __future__ import annotations

import zipfile

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from shapely.affinity import translate
from shapely.geometry import box

from _common import FIGURES, PROCESSED, RAW, log

LON0 = 150
CUT = LON0 - 180  # -30: the new map edge
PROJ = f"+proj=eqearth +lon_0={LON0} +datum=WGS84 +units=m +no_defs"

TEAL, EMBER, MIST, INK, SLATE = "#0F5E66", "#D9622B", "#EEF5F5", "#1E2A2C", "#6B7B7D"


def setup_fonts() -> None:
    import subprocess
    for name in ("SourceSansPro-Regular.otf", "SourceSansPro-Semibold.otf"):
        try:
            path = subprocess.run(["kpsewhich", name], capture_output=True,
                                  text=True, check=True).stdout.strip()
            font_manager.fontManager.addfont(path)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    mpl.rcParams.update({
        "font.family": ["Source Sans Pro", "DejaVu Sans"],
        "pdf.fonttype": 42,
        "svg.hashsalt": "widening-edge",
    })


def shift(geom):
    """Split at the new antimeridian and move the western part east by 360."""
    west = geom.intersection(box(-180, -90, CUT, 90))
    east = geom.intersection(box(CUT, -90, 180, 90))
    parts = [g for g in (translate(west, 360) if not west.is_empty else None, east)
             if g is not None and not g.is_empty]
    from shapely.ops import unary_union
    return unary_union(parts)


def main() -> None:
    setup_fonts()
    with zipfile.ZipFile(RAW / "naturalearth" / "ne_50m_admin_0_countries.zip") as z:
        z.extractall(RAW / "naturalearth" / "ne50")
    world = gpd.read_file(RAW / "naturalearth" / "ne50" / "ne_50m_admin_0_countries.shp")
    world["iso3"] = np.where(world.ISO_A3_EH != "-99", world.ISO_A3_EH, world.ADM0_A3)
    world.loc[world.ADM0_A3 == "KOS", "iso3"] = "XKX"
    world = world[world.ADM0_A3 != "ATA"]

    c = pd.read_csv(PROCESSED / "countries.csv", index_col="iso3")
    world = world.merge(c[["remoteness_km", "sids"]], left_on="iso3",
                        right_index=True, how="left")
    world["geometry"] = world.geometry.apply(shift)
    world = world.set_crs(4326, allow_override=True)
    proj = world.to_crs(PROJ)

    bounds = [5500, 6500, 7500, 8500, 9500, 10500, 11500, 12500, 14000]
    cmap = LinearSegmentedColormap.from_list("edge", ["#E3EEEF", "#7FB0B3", TEAL, "#06292D"])
    norm = BoundaryNorm(bounds, cmap.N)

    fig, ax = plt.subplots(figsize=(6.5, 3.75))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.16)
    # Densified globe outline (straight lon/lat edges curve under projection).
    lat = np.linspace(-90, 90, 181)
    lon = np.linspace(CUT, CUT + 360, 361)
    ring = ([(CUT + 1e-6, y) for y in lat] + [(x, 90) for x in lon]
            + [(CUT + 360 - 1e-6, y) for y in lat[::-1]] + [(x, -90) for x in lon[::-1]])
    from shapely.geometry import Polygon
    globe = gpd.GeoSeries([Polygon(ring)], crs=4326).to_crs(PROJ)
    globe.plot(ax=ax, color="#FAFCFC", edgecolor="#C9D6D7", linewidth=0.5)
    gx0, gy0, gx1, gy1 = globe.total_bounds
    ax.set_xlim(gx0, gx1)
    ax.set_ylim(gy0 + 0.11 * (gy1 - gy0), gy1)  # trim the empty Southern Ocean
    proj[proj.remoteness_km.isna()].plot(ax=ax, color="#F2F2F2", edgecolor="white",
                                         linewidth=0.15)
    proj[proj.remoteness_km.notna()].plot(ax=ax, column="remoteness_km", cmap=cmap,
                                          norm=norm, edgecolor="white", linewidth=0.15)

    sids = proj[(proj.sids == 1) & proj.remoteness_km.notna()].copy()
    pts = sids.geometry.representative_point()
    ax.scatter(pts.x, pts.y, s=11, c=sids.remoteness_km, cmap=cmap, norm=norm,
               edgecolors=EMBER, linewidths=0.7, zorder=5)

    labels = {"TON": "Tonga", "TUV": "Tuvalu", "KIR": "Kiribati", "FJI": "Fiji",
              "ISL": "Iceland", "SGP": "Singapore", "MUS": "Mauritius",
              "MDV": "Maldives", "CPV": "Cabo Verde", "NZL": "New Zealand"}
    offsets = {"TON": (6, -8), "TUV": (6, 3), "KIR": (6, 2), "FJI": (-24, -3),
               "ISL": (-4, 6), "SGP": (-30, -6), "MUS": (6, -4), "MDV": (-30, 2),
               "CPV": (5, -7), "NZL": (6, -6)}
    for iso, text in labels.items():
        row = proj[proj.iso3 == iso]
        if row.empty:
            continue
        p = row.geometry.iloc[0].representative_point()
        ax.annotate(text, (p.x, p.y), xytext=offsets[iso], textcoords="offset points",
                    fontsize=6.2, color=INK, zorder=6)
    ax.set_axis_off()

    cax = fig.add_axes([0.2, 0.1, 0.5, 0.025])
    cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, orientation="horizontal",
                                   ticks=bounds)
    cb.ax.set_xticklabels([f"{b/1000:g}" for b in bounds], fontsize=6.5, color=SLATE)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, pad=2)
    cb.set_label("GDP-weighted distance to world output, thousand km", fontsize=7,
                 color=INK, labelpad=3)
    fig.text(0.73, 0.1075, "○ small island state", fontsize=6.5, color=EMBER,
             va="center")

    out = FIGURES / "remoteness_map.pdf"
    fig.savefig(out, metadata={"CreationDate": None, "ModDate": None,
                               "Producer": None, "Creator": None})
    log(f"wrote {out.relative_to(FIGURES.parent)}")


if __name__ == "__main__":
    main()
