# F1 Standings Visualizer 🏎️

## Python Data Visualization

### Description 📚

Python app built using Plotly to visualize the progression of F1 championship standings for all seasons to date. Built using a public F1 database API ([Ergast](http://ergast.com/mrd/)) and the Python Plotly framework to visualize the data script hosted via Heroku.

### Infrastructure 🏗️

Written using Python scripts that implement the Plotly graphing framework for the front-end UI. The back-end is built using simple API requests through Python's [requests](https://pypi.org/project/requests/) HTTP library that fetch data from a public API. The responses are cached via a MySQL database to increase the speed of subsequent requests. The entire application is hosted via Heroku for remote access to the visualizer.

### Related Concepts / Learnings 💭

* Python Scripting
* Data structures
* API integrations
* MySQL
* Caching / Rate-limiting
* Hosting (Heroku)

### Screenshots 📸

![image](https://user-images.githubusercontent.com/5607044/182189284-dee7b7a4-9e12-4465-aaba-fa20782228a7.png)


<b>Matthew J. McArdle</b>
<br>
matthew.j.mcardle@gmail.com
