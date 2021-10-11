# import pycurl
import requests
import xml.etree.ElementTree as ET
import time
import dash
import plotly.express as px
import pandas as pd
import sys
import logging
import logging.handlers
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from requests.api import get
import random
from clinched import calculateClinch

pd.options.plotting.backend = "plotly"

app = dash.Dash(__name__)

ns = "{http://ergast.com/mrd/1.4}"

# Dictionary containing keys of drivers name, and values of Lists containing total points after each race
standings = dict()

# Array containing colours to use for each driver
standingsTeamColours = []

# Array containing marks that indicate if they are still in contension
standingsEliminated = []

teamColours = {
    "Alfa Romeo": "maroon",
    "AlphaTauri": "grey",
    "Alpine F1 Team": "blue",
    "Aston Martin": "green",
    "Red Bull": "navy",
    "Brawn": "chartreuse",
    "BAR": "whitesmoke",
    "BMW Sauber": "cornflowerblue",
    "BRM": "darkgreen",
    "Benetton": "skyblue",
    "Brabham": "darkblue",
    "Brabham-Repco": "green",
    "Caterham": "green",
    "Cooper-Castellotti": "green",
    "Cooper-Climax": "midnightblue",
    "Cooper-Maserati": "red",
    "Dallara": "red",
    "Epperly": "yellow",
    "Euro Brun": "orange",
    "Fittipaldi": "yellow",
    "Footwork": "whitesmoke",
    "Forti": "yellow",
    "Force India": "coral",
    "Ferrari": "red",
    "HRT": "whitesmoke",
    "Haas F1 Team": "whitesmoke",
    "Honda": "whitesmoke",
    "Jaguar": "green",
    "Jordan": "limegreen",
    "Larrousse": "navy",
    "Leyton House": "lightskyblue",
    "Ligier": "blue",
    "Lotus": "black",
    "Lotus F1": "black",
    "MF1": "red",
    "Manor Marussia": "orange",
    "Marussia": "red",
    "Maserati": "darkred",
    "McLaren": "orange",
    "McLaren-Alfa Romeo": "yellow",
    "McLaren-Ford": "whitesmoke",
    "Mercedes": "aqua",
    "Minardi": "yellow",
    "Renault": "yellow",
    "Racing Point": "hotpink",
    "Sauber": "crimson",
    "Spyker": "orange",
    "Spyker MF1": "orange",
    "Super Aguri": "whitesmoke",
    "Team Lotus": "green",
    "Toro Rosso": "midnightblue",
    "Toleman": "blue",
    "Toyota": "whitesmoke",
    "Tyrrell": "mediumblue",
    "Williams": "lightblue",
    "Virgin": "orange",
    "Gold": "gold",
    "Silver": "silver",
}
# Use this to build out list of colours

maxRace = 100
driverStandings = True

raceNames = dict()

years = [*range(1950, 2022, 1)]

# Variables that contain the year that the standings have been loaded for and amount of races the dictionary has been filled out for
loadedYear = 0
loadedRaces = 0
inProgress = False

# Set up the logging
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

# Build our log handler with formatting
fileHandler = logging.FileHandler('f1-visualizer.log')
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(level=logging.INFO)

rootLogger.error("This is a test error")
rootLogger.warning("This is a test warning")
rootLogger.debug("This is a test debug")
rootLogger.info("This is a test info")

app.layout = html.Div([
    html.Div(
        dcc.Graph(
            id='f1-graph',
        )
    ),
    html.Div([
        html.Div([
            html.Div([
                dcc.Slider(
                    id='f1-slider',
                    min=1,
                    max=maxRace,
                    value=1,
                    step=1,
                    dots=True
                ),
                ], style={'width': '50%', 'display': 'inline-block'}
            ),
            dcc.Dropdown(
                id='f1-year',
                options=[{'label': str(i), 'value': str(i)} for i in years],
                value='2021',
                style={'width': '50%', 'display': 'inline-block'}
            ),
            ], style={'text-align': 'center'}
        ),
        html.Div([
            html.Button("Previous Race", id="previousRace", style={'margin': 'auto', 'padding': '10px', 'width': '30%'}),
            html.Button("Next Race", id="nextRace", style={'margin': 'auto', 'padding': '10px', 'width': '30%'})
            ], style={'text-align': 'center', 'margin': 'auto', 'padding': '10px', 'width': '50%'}
        ),
        html.Div([
            html.Button("Toggle Drivers/Constructors Standings", id="standingsToggle", style={'margin': 'auto', 'padding': '10px', 'width': '30%'})
            ], style={'text-align': 'center', 'margin': 'auto', 'padding': '10px', 'width': '50%'}
        )
    ])
])

def clearStandings():
    global loadedRaces
    standings.clear()
    standingsTeamColours.clear()
    standingsEliminated.clear()
    loadedRaces = 0


def getStandingsType():
    global driverStandings
    if driverStandings:
        return "driverStandings"
    else:
        return "constructorStandings"

def getLeaderPoints():
    leaderPoints = -1
    leaderName = "None"
    for key in standings:
        if standings[key][loadedRaces] > leaderPoints:
            leaderPoints = standings[key][loadedRaces]
            leaderName = key

    return { 'name': leaderName, 'points': leaderPoints }

def checkForClinch():
    leader = getLeaderPoints()
    leaderPoints = leader['points']
    leaderName = leader['name']
    racesLeft = int(maxRace) - int(loadedRaces)

    i = 0
    for name in standings:
        points = standings[name][loadedRaces]
        pointsFromLeader = float(leaderPoints) - float(points)
        if name == leaderName or calculateClinch(loadedYear, racesLeft, pointsFromLeader, driverStandings):
            rootLogger.info(f"{name} still in contension. Only {pointsFromLeader} back of 1st with {racesLeft} races left. Has {points} points")
        else:
            rootLogger.info(f"{name} NOT in contension. Is {pointsFromLeader} back of 1st with only {racesLeft} races left. Has {points} points")

            standingsEliminated.append({'x': loadedRaces, 'y': points})
        i += 1

### Summary: Initializes the drivers standing by adding an element into each driver's array for each race
### param race: Integer representing the amount of races to initialize up to (ex: race = 2 ==> [0, 0, 0])
### param year: Integer representing the year that will be parsed, if the year is changed then reset loadedRaces
def FillDriversStandings(race, year):
    global inProgress
    global loadedRaces
    global loadedYear
    global maxRace
    global standingsTeamColours

    if race > maxRace:
        race = maxRace

    if year != loadedYear:
        rootLogger.info("Year has changed, clearing standings.")
        clearStandings()
        loadedYear = year

    diff = int(loadedRaces) - int(race) # TODO: bug where race = 'None' :P
    if diff > 0:
        rootLogger.info('Clearing %s races', str(diff))
        for driver in standings:
            for i in range(0, diff):
                del standings[driver][-1] # must have an item in it
                # TODO going to need to delete annotations here
        loadedRaces = race

    standingsType = getStandingsType()

    if inProgress: 
        rootLogger.warning("Multiple threads detected. Not changing any data in this thread.")
        return False
    else: 
        inProgress = True

    if loadedRaces < 1: # If no races are loaded, then get the list of drivers to init as a request
        response = requests.get(f'http://ergast.com/api/f1/{year}/last/{standingsType}')
        content = response.text
        root = ET.fromstring(content)
        lastRace = root.find(f".//{ns}StandingsTable")

        maxRace = int(lastRace.attrib["round"])

        if standingsType == "driverStandings":
            allDriverRankings = lastRace.findall(f".//{ns}DriverStanding")
            for driver in allDriverRankings:
                # TODO maybe this isn't the best, what if driver of same name
                firstName = driver.find(f".//{ns}GivenName").text
                lastName = driver.find(f".//{ns}FamilyName").text
                fullName = firstName + " " + lastName

                team = driver.find(f".//{ns}Constructor/{ns}Name").text

                for i in range(loadedRaces, race):
                    if fullName not in standings:
                        standings[fullName] = [0.0, 0.0]
                        if team in teamColours:
                            standingsTeamColours.append(teamColours[team])
                        else:
                            standingsTeamColours.append(random.choice(list(teamColours.values())))
                    else:
                        standings[fullName].append(0.0)
        else:
            allTeams = lastRace.findall(f".//{ns}Constructor")
            for team in allTeams:
                name = team.find(f".//{ns}Name").text

                for i in range(loadedRaces, race):
                    if name not in standings:
                        standings[name] = [0.0, 0.0]
                        if name in teamColours:
                            standingsTeamColours.append(teamColours[name])
                        else:
                            standingsTeamColours.append(random.choice(list(teamColours.values())))
                    else:
                        standings[name].append(0.0)
    else: # If the driverStandings is already initialized then just add a new element for each new race
        for element in standings:
            for i in range(loadedRaces, race):
                standings[element].append(0.0)

    return True
    

### Summary: Builds the drivers standing by looping for each standings after race amount of races
### param race: Integer representing the amount of races to parse for
### param year: Integer representing the year to parse for
def StandingsBuilder(race, year):
    global inProgress
    global loadedRaces
    global loadedYear
    global maxRace 
    global driverStandings

    if race > maxRace + 1:
        race = maxRace + 1
    
    standingsType = getStandingsType()

    rootLogger.info('Building Standings after %s races in %s', race, year)

    for currentRace in range(loadedRaces + 1, race + 1):

        rootLogger.info('Sending Request for Race %s', str(currentRace))

        response = requests.get(f'http://ergast.com/api/f1/{year}/{currentRace}/{standingsType}')
        rootLogger.info("Recieved Response")

        content = response.text
        # print(content)


        root = ET.fromstring(content)

        results = root.findall(f".//{ns}StandingsList/*")

        rootLogger.info("Parsing Start")
        for result in results:
            points = result.attrib["points"]

            if standingsType == "driverStandings":
                firstName = result.find(f"./{ns}Driver/{ns}GivenName")
                lastName = result.find(f"./{ns}Driver/{ns}FamilyName")

                name = f"{firstName.text} {lastName.text}"
                rootLogger.info("Driver: %s", name)
            else:
                name = result.find(f"./{ns}Constructor/{ns}Name").text
                rootLogger.info("Constructor: %s", name)

            if name not in standings: # If driver not initilized in standings then skip him
                continue

            standings[name][currentRace] = (float(points)) # TODO bug index out of range using previous twice then next once



        rootLogger.info("Parsing End")
        loadedRaces = currentRace
        checkForClinch()

    loadedRaces = race

    inProgress = False
    rootLogger.info(f"Loaded Races = {loadedRaces}. Loaded Year = {loadedYear}\n")
    


def get_max_races(year):
    global maxRace

    standingsType = getStandingsType()

    response = requests.get(f'http://ergast.com/api/f1/{year}/last/{standingsType}')
    content = response.text
    root = ET.fromstring(content)
    lastRace = root.find(f".//{ns}StandingsTable")

    maxRace = int(lastRace.attrib["round"])
    return maxRace

def get_race_names(year):
    raceNames.clear()

    response = requests.get(f'http://ergast.com/api/f1/{year}')
    content = response.text
    root = ET.fromstring(content)
    races = root.findall(f".//{ns}RaceTable/*")

    i = 1
    for race in races:
        raceName = race.find(f".//{ns}RaceName").text.replace(" Grand Prix", "") + " GP"
        raceNames[str(i)] = \
        {
            'label': raceName, 
            'style':
                {
                    'display': 'block', 'width': '50px', 'font-size': '7px', 'word-wrap': 'break-word', 'word-break': 'break-all', 'white-space': 'normal'
                }
        }
        i += 1


# FillDriversStandings(-1, 2021)
# get_race_names(2021)

colours = [
    "gold",
    "silver",
    "peru",
    "red",
    "crimson",
    "darkred",
    "orange",
    "lightsalmon",
    "yellow",
    "lime",
    "green",
    "seagreen",
    "aquamarine",
    "aqua",
    "blue",
    "darkblue",
    "navy",
    "indigo",
    "violet",
    "purple",
    "fuchsia",
    "hotpink",
    "lightpink",
    "magenta",
    "black",
]
df = pd.DataFrame(standings)
fig = df.plot(
    title="2021 F1 Drivers Standings",
    labels=dict(index="Race", value="Points", variable="Driver", isinteractive="true"),
    markers=True,
    color_discrete_sequence=colours
)


def create_f1_figure(race, year):
    standingsType = "Drivers"
    if not driverStandings:
        standingsType = "Constructors"

    if FillDriversStandings(race, year): # If the standings are successfully initilized then fill it with the correct Points
        StandingsBuilder(race, year)

    df = pd.DataFrame(standings)
    fig = df.plot(
        title=f"{year} F1 {standingsType} Standings",
        labels=dict(index="Race", value="Points",
        variable=f"{standingsType[:-1]}", isinteractive="true"),
        markers=True,
        color_discrete_sequence=standingsTeamColours
    )

    for xy in standingsEliminated:
        fig.add_annotation(
            x=xy['x'],
            y=xy['y'],
            text="x",
            showarrow=False
        )
    
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
        dash.dependencies.Input('f1-year', 'value'),
        dash.dependencies.Input('previousRace', 'n_clicks'),
        dash.dependencies.Input('nextRace', 'n_clicks'),
        dash.dependencies.Input('standingsToggle', 'n_clicks')
    ]
    ) # Update figure based on if the slider or year changes (either by year dial or prev next buttons)
def update_graph(races, year, prevClicks, nextClicks, toggleClicks):
    global driverStandings
    global loadedRaces

    if (races == None): # TODO this feels bad
        races = 1

    ctx = dash.callback_context
    if not ctx.triggered: # If no trigger then just use the values of year and value
        return create_f1_figure(races, year)

    trigger = ctx.triggered[0]['prop_id'].split('.')[0] # Gets the name of the id of the trigger
    if (trigger == "previousRace" and loadedRaces > 1):
        return create_f1_figure(loadedRaces - 1, year)
    elif (trigger == "nextRace" and loadedRaces != maxRace):
        return create_f1_figure(loadedRaces + 1, year)
    elif (trigger == "standingsToggle"):
        rootLogger.info("Standings type has be toggled. Clearing data.")
        driverStandings = not driverStandings
        clearStandings()
        return create_f1_figure(races, year)
    else:
        rootLogger.info("Fallback Path")
        return create_f1_figure(races, year)

@app.callback(
    dash.dependencies.Output('f1-slider', 'max'),
    [
        dash.dependencies.Input('f1-year', 'value')
    ]
) # Update the sliders max value when a new year is picked (the new race is a bit of a hack because it sometimes doesn't update)
def update_slider_max(year):
    get_max_races(year)
    return maxRace


@app.callback(
    dash.dependencies.Output('f1-slider', 'value'),
    [
        dash.dependencies.Input('f1-year', 'value'),
        dash.dependencies.Input('previousRace', 'n_clicks'),
        dash.dependencies.Input('nextRace', 'n_clicks')
    ]
) # Set the value to 1 every time the year changes
def update_slider_value(year, prevClicks, nextClicks): #year, 

    ctx = dash.callback_context
    if not ctx.triggered: # If no trigger then just set it to 1
        return 1

    trigger = ctx.triggered[0]['prop_id'].split('.')[0] # Gets the name of the id of the trigger
    if (trigger == "previousRace"):
        if (loadedRaces <= 1): return loadedRaces
        return loadedRaces - 1
    elif (trigger == "nextRace"):
        if (loadedRaces >= maxRace): return loadedRaces
        return loadedRaces + 1
    else:
        return 1

@app.callback(
    dash.dependencies.Output('f1-slider', 'marks'),
    [
        dash.dependencies.Input('f1-year', 'value')
    ]
)
def update_slider_labels(year):
    get_race_names(year)
    return raceNames

if __name__ == '__main__':
    app.run_server(debug=True)