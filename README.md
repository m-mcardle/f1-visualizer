# f1-visualizer

---

This tool is used to visualize the progress of F1 drivers or constructors standings of a given season after<br> each race that is completed.

This is done by sending requests to the Ergast Developer API (http://ergast.com/mrd/).

The responses from this API are then plotted implementing Plotly (https://plotly.com/) which<br> implements Dash to manage the application infrastructure needed for interactive graphing.

The script install_deps.sh can be run to automatically install the needed dependencies for this program.

---

Known Issues:
- Spamming any of the buttons/sliders before the rendering is finished can cause weird states

---

<b>Matthew J. McArdle</b>
<br>
matthew.j.mcardle@gmail.com