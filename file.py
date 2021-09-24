# import pycurl
import requests
import xml.etree.ElementTree as ET
import time
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

pd.options.plotting.backend = "plotly"

app = dash.Dash(__name__)

ns = "{http://ergast.com/mrd/1.4}"

# Dictionary containing keys of drivers name, and values of Lists containing total points after each race
driverStandings = dict() 
maxRace = 100

loadedYear = 0
loadedRaces = 0


def FillDriversStandings(race, year):
    global loadedRaces
    global loadedYear
    global maxRace 

    if year != loadedYear:
        print("Happy new year!!")
        driverStandings.clear()
        loadedRaces = 0
    diff = int(loadedRaces) - int(race)
    if diff > 0:
        print("Clearing")
        # driverStandings.clear()
        # loadedRaces = 0
        for driver in driverStandings:
            for i in range(0, diff):
                del driverStandings[driver][-1] # must have an item in it

        loadedRaces = race
            

    # TODO This needs to be changed due to the Anthony Davidson bug
    # - Try ignoring any new drivers that are found bc if they aren't in this first query they must not be important
    response = requests.get(f'http://ergast.com/api/f1/{year}/last/driverStandings')
    content = response.text
    root = ET.fromstring(content)
    lastRace = root.find(f".//{ns}StandingsTable")

    maxRace = int(lastRace.attrib["round"])

    allDrivers = lastRace.findall(f".//{ns}Driver")

    if race > maxRace:
        race = maxRace

    for driver in allDrivers:
        # TODO maybe this isn't the best
        firstName = driver.find(f".//{ns}GivenName").text
        lastName = driver.find(f".//{ns}FamilyName").text
        fullName = firstName + " " + lastName

        for i in range(loadedRaces, race):
            if fullName not in driverStandings:
                driverStandings[fullName] = [0.0, 0.0]
            else:
                driverStandings[fullName].append(0.0)


def DriverStandingsBuilder(race, year):
    global loadedRaces
    global loadedYear
    global maxRace 

    if race > maxRace + 1:
        race = maxRace + 1
    
    print("Building Standings after " + str(race) + " races")
    for currentRace in range(loadedRaces + 1, race):

        print("Sending Request for Race " + str(currentRace))
        response = requests.get(f'http://ergast.com/api/f1/{year}/{currentRace}/driverStandings')

        print("Recieved Response")
        content = response.text
        # print(content)


        root = ET.fromstring(content)

        results = root.findall(f".//{ns}StandingsList/*")

        print("Parsing Start")
        for result in results:
            points = result.attrib["points"]
            firstName = result.find(f"./{ns}Driver/{ns}GivenName")
            lastName = result.find(f"./{ns}Driver/{ns}FamilyName")

            driverName = firstName.text + " " + lastName.text
            if driverName not in driverStandings:
                driverStandings[driverName] = [0] * (race)

            driverStandings[driverName][currentRace] = (float(points))

        print("Parsing End")
    loadedRaces = race - 1
    loadedYear = year
    print("Loaded Races = " + str(loadedRaces) + " Loaded Years = " + str(loadedYear))

years = [*range(1960, 2022, 1)]

FillDriversStandings(-1, 2021)

df = pd.DataFrame(driverStandings)
fig = df.plot(title="2021 F1 Drivers Standings", labels=dict(index="Race", value="Points", variable="Driver", isinteractive="true"))

app.layout = html.Div([
    html.Div(
        dcc.Graph(
            id='f1-graph',
        )
    ),
    html.Div([
        dcc.Slider(
            id='f1-slider',
            min=1,
            max=maxRace,
            value=1,
            step=1
        ),
        dcc.Dropdown(
            id='f1-year',
            options=[{'label': str(i), 'value': str(i)} for i in years],
            value='2021'
        )
    ])
])

def create_f1_figure(race, year):
    FillDriversStandings(race, year)
    DriverStandingsBuilder(race + 1, year)
    df = pd.DataFrame(driverStandings)
    fig = df.plot(title=f"{year} F1 Drivers Standings", labels=dict(index="Race", value="Points", variable="Driver", isinteractive="true"))
    
    fig.update_layout(
        xaxis = dict(
            tickmode = 'linear',
            dtick = 1
        )
    )
    return fig

@app.callback(
    dash.dependencies.Output('f1-graph', 'figure'),
    [
        dash.dependencies.Input('f1-slider', 'value'),
        dash.dependencies.Input('f1-year', 'value')
    ]
    )
def update_graph(races, year):
    return create_f1_figure(races, year)


@app.callback(
    dash.dependencies.Output('f1-slider', 'max'),
    [
        dash.dependencies.Input('f1-year', 'value'),
        dash.dependencies.Input('f1-slider', 'value')

    ]
)
def update_graph(year, currentValue):
    return maxRace

if __name__ == '__main__':
    app.run_server(debug=True)